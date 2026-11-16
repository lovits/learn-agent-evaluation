"""Deterministic scores: explicit comparison units and empty-set policy."""

import json


def set_f1(expected, actual):
    expected, actual = set(expected), set(actual)
    if not expected and not actual:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    overlap = len(expected & actual)
    precision = overlap / len(actual) if actual else 0.0
    recall = overlap / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def rules(case):
    try:
        value = json.loads(case["response"])
        valid = (
            isinstance(value, dict)
            and set(value) == {"result"}
            and type(value["result"]) is int
            and value["result"] == 48
        )
    except (ValueError, TypeError):
        valid = False
    return {
        "exact_match": float(case["response"] == '{"result":48}'),
        "json_contract": float(valid),
        "state_contract": float(case["artifact_verified"]),
        "tools": set_f1(case["expected_tools"], case["observed_tools"]),
    }
