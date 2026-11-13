# TraceForge — Agent Failure Investigator

A local-first SQLite-backed execution trace collector with context-managed spans, error-category classification, and deterministic **recorded-output** replay.

## Quick start
```bash
python -m pip install -e '.[dev]'
traceforge demo --db traces.db
traceforge trace --db traces.db --trace-id TRACE_ID
traceforge classify --db traces.db --trace-id TRACE_ID
traceforge replay --db traces.db --trace-id TRACE_ID
pytest -q
```

The demo generates an agent trace with a failing validation span. Use the emitted trace ID for subsequent commands.

## Engineering features
- Parent/child spans with trace IDs, timestamps, status and duration inputs.
- SQLite persisted trace events and indexed lookup.
- Failure classification using a transparent error-type taxonomy.
- Replay **does not reexecute tools**; it reconstructs recorded outcomes offline.
- Stores error class but not exception messages to reduce leakage risk.

## Limitations and security
This is a functional observability core, not a distributed production platform. There is no dashboard, OpenTelemetry receiver, multi-tenant authorization, or full side-effect replay yet. Callers must avoid passing sensitive data as `output`: the store currently persists that field without redaction. No diagnostic-time improvement claims are validated.
