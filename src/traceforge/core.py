"""TraceForge: durable trace spans, sanitized errors, classification and deterministic replay."""
from __future__ import annotations
import argparse
import contextlib
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Callable, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS spans (
 id TEXT PRIMARY KEY,
 trace_id TEXT NOT NULL,
 parent_id TEXT,
 operation TEXT NOT NULL,
 start_ns INTEGER NOT NULL,
 end_ns INTEGER,
 status TEXT NOT NULL CHECK(status IN ('running','ok','error')),
 error_type TEXT,
 output_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id,start_ns);
"""
ERROR_TYPES = {"TimeoutError":"timeout","PermissionError":"permission","KeyError":"missing_key","ValueError":"validation","ConnectionError":"connection"}

class TraceStore:
    def __init__(self, path: str | Path = "traces.db"):
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)

    def start(self, operation: str, trace_id: str | None = None, parent_id: str | None = None) -> tuple[str, str]:
        trace_id = trace_id or uuid.uuid4().hex
        span_id = uuid.uuid4().hex
        self.connection.execute("INSERT INTO spans (id,trace_id,parent_id,operation,start_ns,status) VALUES (?,?,?,?,?,?)",
                                (span_id,trace_id,parent_id,operation,time.time_ns(),"running"))
        self.connection.commit()
        return trace_id, span_id

    def finish(self, span_id: str, *, output: Any = None, error: Exception | None = None) -> None:
        # Never persist raw exception messages, prompts, credentials or arbitrary tool outputs.
        status = "error" if error else "ok"
        error_type = type(error).__name__ if error else None
        output_json = json.dumps(output) if output is not None else None
        self.connection.execute("UPDATE spans SET end_ns=?,status=?,error_type=?,output_json=? WHERE id=?",
                                (time.time_ns(),status,error_type,output_json,span_id))
        if self.connection.total_changes < 1:
            raise KeyError(span_id)
        self.connection.commit()

    @contextlib.contextmanager
    def span(self, operation: str, trace_id: str | None = None, parent_id: str | None = None):
        tid, sid = self.start(operation, trace_id, parent_id)
        try:
            yield tid, sid
        except Exception as exc:
            self.finish(sid, error=exc)
            raise
        else:
            self.finish(sid)

    def trace(self, trace_id: str) -> list[dict]:
        cur = self.connection.execute("SELECT id,trace_id,parent_id,operation,start_ns,end_ns,status,error_type,output_json FROM spans WHERE trace_id=? ORDER BY start_ns,id", (trace_id,))
        return [dict(zip(("id","trace_id","parent_id","operation","start_ns","end_ns","status","error_type","output_json"), row)) for row in cur.fetchall()]

    def classify(self, trace_id: str) -> list[dict]:
        return [{"span": s["id"], "operation": s["operation"], "category": ERROR_TYPES.get(s["error_type"],"unknown")} for s in self.trace(trace_id) if s["status"] == "error"]

    def replay(self, trace_id: str, handlers: dict[str, Callable[...,Any]] | None = None) -> list[dict]:
        """Offline replay of recorded outputs. No live external side effects."""
        outcome = []
        for s in self.trace(trace_id):
            outcome.append({"operation":s["operation"],"status":s["status"],"result":json.loads(s["output_json"]) if s["output_json"] else None,"error_type":s["error_type"]})
        return outcome

def demo(store: TraceStore) -> str:
    trace_id, span_id = store.start("agent")
    with store.span("sec.fetch",trace_id,parent_id=span_id):
        pass
    try:
        with store.span("period.normalize",trace_id,parent_id=span_id):
            raise ValueError("Sensitive details excluded from traces")
    except ValueError:
        pass
    store.finish(span_id)
    return trace_id

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["demo","trace","classify","replay"])
    parser.add_argument("--db", default="traces.db")
    parser.add_argument("--trace-id")
    args = parser.parse_args()
    store = TraceStore(args.db)
    if args.command == "demo":
        identifier = demo(store)
        print("Trace ID:",identifier)
        print(json.dumps(store.classify(identifier),indent=2))
    else:
        if not args.trace_id:
            parser.error("--trace-id required")
        fn = {"trace":store.trace,"classify":store.classify,"replay":store.replay}[args.command]
        print(json.dumps(fn(args.trace_id),indent=2))

if __name__ == "__main__":
    main()
