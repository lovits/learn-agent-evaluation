"""Resolve annotated updates, inspect artifacts and retain conversational judgments."""

import hashlib
import json

from deepeval.metrics import ConversationCompletenessMetric, KnowledgeRetentionMetric
from deepeval.test_case import ConversationalTestCase, Turn

from course.e04_scoring.eval import score
from course.e12_task_completion.eval import fingerprint


def active_requirements(history):
    active, sources, superseded = {}, {}, []
    for turn in history:
        if turn["role"] != "user":
            continue
        for key in turn.get("drop", []):
            if key in active:
                superseded.append(
                    {"key": key, "value": active.pop(key), "source": sources.pop(key)}
                )
        for key, value in turn.get("set", {}).items():
            if key in active:
                superseded.append({"key": key, "value": active[key], "source": sources[key]})
            active[key], sources[key] = value, turn["id"]
    return {"active": active, "sources": sources, "superseded": superseded}


def check_delivery(run, workspace, scenario):
    state = active_requirements(scenario["history"])
    goal = state["active"]
    target = workspace / goal["path"]
    content = (
        target.read_text()
        if target.is_file() and target.resolve().is_relative_to(workspace.resolve())
        else None
    )
    old_paths = {v["value"] for v in state["superseded"] if v["key"] == "path"} - {goal["path"]}
    checks = {
        "requested_content": content is not None and content.rstrip("\n") == goal["body"],
        "old_paths_absent": all(not (workspace / path).exists() for path in old_paths),
        "policy_unchanged": fingerprint(workspace / "policy.txt")
        == hashlib.sha256(scenario["policy"].encode()).hexdigest(),
    }
    if "max_chars" in goal:
        checks["length_limit"] = content is not None and len(content) <= goal["max_chars"]
    first_input = json.dumps(run["model_inputs"][0], ensure_ascii=False)
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "state": state,
        "content": content,
        "expected_path_in_first_input": goal["path"] in first_input,
        "archive_read": any(
            e["name"] == "read_file"
            and e["arguments"].get("path") == "conversation.json"
            and e["result"]["status"] == "ok"
            for e in run["events"]
        ),
    }


def conversation_sample(run, scenario):
    turns = [{"role": t["role"], "content": t["content"]} for t in scenario["history"]]
    turns += [
        {"role": "user", "content": scenario["current"]},
        {"role": "assistant", "content": run["final_answer"] or ""},
    ]
    return ConversationalTestCase(turns=[Turn(**turn) for turn in turns])


def conversational_scores(sample, model):
    results = {}
    for name, cls in [
        ("retention", KnowledgeRetentionMetric),
        ("completeness", ConversationCompletenessMetric),
    ]:
        metric = cls(model=model, eval_mode="llm", async_mode=False, include_reason=False)
        result = score(metric, sample)
        verdicts = getattr(metric, "verdicts", [])
        knowledge = getattr(metric, "knowledges", [])
        intentions = getattr(metric, "user_intentions", [])
        expected = (
            sum(
                t.role == "assistant" and any(k and k.data for k in knowledge[:i])
                for i, t in enumerate(sample.turns)
            )
            if name == "retention"
            else len(intentions)
        )
        sdk_score = result["score"]
        if result["status"] == "ok":
            if any(v is None for v in verdicts) or len(verdicts) != expected:
                result.update(
                    status="error",
                    score=None,
                    passed=None,
                    reason="Conversational verdict coverage is incomplete",
                )
            elif not expected:
                result.update(
                    status="not_applicable",
                    score=None,
                    passed=None,
                    reason="No applicable conversational units",
                )
        results[name] = {
            **result,
            "sdk_score": sdk_score,
            "expected_units": expected,
            "verdicts": [v.model_dump(mode="json") if v else None for v in verdicts],
            "knowledges": [k.model_dump(mode="json") if k else None for k in knowledge],
            "intentions": intentions,
        }
    return results
