"""Only deterministic explanations of verdict aggregation and evidence identity."""

import hashlib
import json


def evidence_key(documents):
    payload = [{"id": d["id"], "sha256": d["sha256"]} for d in documents]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def require_same_evidence(old_key, documents):
    if old_key != evidence_key(documents):
        raise ValueError("Evidence changed; old annotations must not be reused")


def deep_aggregate(verdicts, penalize=False):
    if any(v not in ("yes", "no", "borderline") for v in verdicts):
        raise ValueError("Unknown verdict")
    if not verdicts:
        return 1.0
    passing = {"yes"} if penalize else {"yes", "borderline"}
    return sum(v in passing for v in verdicts) / len(verdicts)


def ragas_aggregate(verdicts):
    if any(type(v) is not int or v not in (0, 1) for v in verdicts):
        raise ValueError("Expected binary verdict")
    return sum(verdicts) / len(verdicts) if verdicts else None
