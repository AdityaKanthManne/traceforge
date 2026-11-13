"""Robust execution-latency anomaly detection for seeded/local traces.

A threshold flag is not a causal diagnosis; validate against labelled failures.
"""
from __future__ import annotations
from statistics import median


def robust_latency_flags(baseline_ms: list[float], observed_ms: list[float], *, threshold: float = 3.5) -> list[bool]:
    """Use median and MAD with a fallback for constant baselines.

    Flags unusually *slow* executions only. Zero MAD uses any positive deviation
    as a flag, appropriate for deterministic test fixtures but noise-sensitive.
    """
    if not baseline_ms or threshold <= 0 or any(v < 0 for v in baseline_ms + observed_ms):
        raise ValueError("Require nonnegative latencies, nonempty baseline, positive threshold")
    center = median(baseline_ms)
    mad = median([abs(value - center) for value in baseline_ms])
    if mad == 0:
        return [value > center for value in observed_ms]
    return [0.6745 * (value - center) / mad > threshold for value in observed_ms]


def binary_metrics(predicted: list[bool], actual: list[bool]) -> dict[str, float | int]:
    """Precision, recall and F1 for a labelled anomalous-execution dataset."""
    if len(predicted) != len(actual) or not predicted:
        raise ValueError("Expected equal nonempty label series")
    tp = sum(p and a for p, a in zip(predicted, actual))
    fp = sum(p and not a for p, a in zip(predicted, actual))
    fn = sum(not p and a for p, a in zip(predicted, actual))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}
