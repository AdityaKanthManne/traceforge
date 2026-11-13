from traceforge.core import TraceStore, demo
import pytest

def test_trace_and_classification(tmp_path):
    store = TraceStore(tmp_path/"test.db")
    trace_id = demo(store)
    spans = store.trace(trace_id)
    assert len(spans) == 3
    categories = store.classify(trace_id)
    assert len(categories) == 1
    assert categories[0]["category"] == "validation"
    assert [s["operation"] for s in store.replay(trace_id)] == [s["operation"] for s in spans]

def test_error_is_sanitized(tmp_path):
    store = TraceStore(tmp_path/"test.db")
    tid, sid = store.start("unsafe")
    with pytest.raises(ValueError):
        with store.span("child",tid,sid):
            raise ValueError("TOP_SECRET")
    assert "TOP_SECRET" not in str(store.trace(tid))
