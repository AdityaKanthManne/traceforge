import pytest
from traceforge.anomaly import robust_latency_flags, binary_metrics


def test_latency_anomaly_and_scores():
    baseline = [90, 95, 98, 100, 101, 102, 105]
    flags = robust_latency_flags(baseline, [101, 350])
    assert flags == [False, True]
    metrics = binary_metrics(flags, [False, True])
    assert metrics["precision"] == metrics["recall"] == metrics["f1"] == 1.0


def test_invalid_baseline():
    with pytest.raises(ValueError):
        robust_latency_flags([], [100])


def test_constant_baseline():
    assert robust_latency_flags([10, 10, 10], [10, 11]) == [False, True]
