"""Hand calculations only; these functions do not infer facts from natural language."""

import math


def fbeta(tp, fp, fn, beta=1.0):
    if min(tp, fp, fn) < 0 or beta <= 0:
        raise ValueError("Counts must be non-negative and beta positive")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    denominator = beta**2 * precision + recall
    return (1 + beta**2) * precision * recall / denominator if denominator else 0.0


def factual_from_verdicts(forward, backward, beta=1.0):
    """Pinned Ragas FactualCorrectness count convention, with two-decimal rounding."""
    if any(type(v) is not int or v not in (0, 1) for v in [*forward, *backward]):
        raise ValueError("Expected binary verdicts")
    tp, fp, fn = sum(forward), len(forward) - sum(forward), len(backward) - sum(backward)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(tp / (tp + fp + 1e-8), 2),
        "recall": round(tp / (tp + fn + 1e-8), 2),
        "f1": round(fbeta(tp, fp, fn, beta), 2),
    }


def cosine(a, b):
    if not a or len(a) != len(b):
        raise ValueError("Expected non-empty vectors with equal dimension")
    denominator = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    if denominator == 0:
        raise ValueError("Cosine is undefined for a zero vector")
    return sum(x * y for x, y in zip(a, b)) / denominator


def combine(factuality, similarity, weights=(0.75, 0.25)):
    if len(weights) != 2 or min(weights) < 0 or sum(weights) <= 0:
        raise ValueError("Expected two non-negative weights with positive sum")
    return (weights[0] * factuality + weights[1] * similarity) / sum(weights)
