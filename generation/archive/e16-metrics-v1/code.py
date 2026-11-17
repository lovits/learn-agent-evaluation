"""Project one actual native repair trace into declared evaluation samples."""

import copy
import hashlib
import json


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def trace_samples(report):
    if report.get("status") != "returned" or report.get("error"):
        raise ValueError("Incomplete integration run cannot become an accepted regression sample")
    if report.get("origin") != "live_native_integration_with_declared_instructor_orchestration":
        raise ValueError("This projection requires the declared native integration experiment")
    worker = next(
        (
            c
            for c in report["model_calls"]
            if c["request"].get("tools")
            and c.get("response_received")
            and c["response"]["stop_reason"] == "end_turn"
        ),
        None,
    )
    if worker is None:
        raise ValueError("No completed worker response")
    message_id = worker["response"]["id"]
    matches = [
        trace
        for trace in report["native_traces"]
        if any(span.get("output", {}).get("id") == message_id for span in trace.get("llmSpans", []))
    ]
    if len(matches) != 1:
        raise ValueError("Worker response must link to exactly one actual native trace")
    trace = matches[0]
    tools = sorted(trace.get("toolSpans", []), key=lambda s: s["startTime"])
    response = "\n".join(b["text"] for b in worker["response"]["content"] if b["type"] == "text")
    task = worker["request"]["messages"][0]["content"]
    documents = []
    for span in tools:
        name = span["input"]["name"]
        text = str(span["output"])
        if len(text) > 20000:
            raise ValueError(
                "Over-limit tool evidence requires an explicit separate sampling policy"
            )
        documents.append(
            {
                "id": span["uuid"],
                "path": "native:" + span["uuid"],
                "text": text,
                "sha256": sha(text),
                "tool_name": name,
            }
        )
    retrieved = [d for d in documents if d["tool_name"] == "mcp__docs__search"]
    if not retrieved or not response:
        raise ValueError("Native repair trace lacks actual retrieval evidence or final text")
    common = {
        "question": task,
        "response": response,
        "origin": "actual_worker_response_projected_from_native_trace",
        "source_trace_uuid": trace["uuid"],
        "source_message_id": message_id,
        "human_reviewed": False,
    }
    faithful = [
        {
            **common,
            "id": "documents_only",
            "documents": retrieved,
            "scope": "Report support from retrieved specification only; does not prove test execution.",
        },
        {
            **common,
            "id": "observed_tools",
            "documents": documents,
            "scope": "Report support from this repair turn's observed tool outputs, including tests; not a pure RAG-only comparison.",
        },
    ]
    predicted = [
        {"name": span["input"]["name"], "args": span["input"]["args"], "source_span": span["uuid"]}
        for span in tools
        if span["input"]["name"] == "read_file"
        and span["input"]["args"].get("path") in {"shipping.py", "checkout.py"}
    ]
    baseline = {
        "id": "native_implementation_read_projection",
        "task": task,
        "origin": "actual_native_tool_spans_projected_to_implementation_reads",
        "source_trace_uuid": trace["uuid"],
        "predicted": predicted,
        "expected": [
            {"name": "read_file", "args": {"path": "shipping.py"}},
            {"name": "read_file", "args": {"path": "checkout.py"}},
        ],
        "scope": "Declared read-file sequence diagnostic, not a unique correct whole-task trajectory or completion criterion.",
    }
    degraded = copy.deepcopy(baseline)
    degraded.update(
        id="injected_missing_checkout_read",
        origin="instructor_deleted_a_projection_event_no_new_agent_execution",
    )
    degraded["predicted"] = [
        c for c in degraded["predicted"] if c["args"].get("path") != "checkout.py"
    ]
    return {
        "faithfulness": faithful,
        "tools": [baseline, degraded],
        "projection_version": "native-repair-v1",
        "new_agent_requests": 0,
    }


def critical_gate(checks):
    if not isinstance(checks, dict) or not checks:
        raise ValueError("Named critical checks are required")
    rejected = [name for name, passed in checks.items() if passed is not True]
    return {
        "passed": not rejected,
        "rejected": rejected,
        "rule": "Every named critical check must be exactly True; missing/unscored checks fail closed.",
    }


def trace_digest(report):
    return sha(json.dumps(report["native_traces"], ensure_ascii=False, sort_keys=True))
