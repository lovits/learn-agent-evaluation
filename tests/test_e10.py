import json

import pytest

from lessons.e10_tool_evaluation.mcp_tools import MCPClient, ToolPool, definition


def call(tool_name, **args):
    return {"name": tool_name, "arguments_json": json.dumps(args)}


def external(name, fields=()):
    tool = definition(name, fields, "readOnly: automatically approved")
    tool["inputSchema"] = tool.pop("input_schema")
    tool["annotations"] = {"readOnlyHint": True}
    return tool


def test_discovery_changes_next_pool_without_changing_existing_tools(tmp_path):
    pool = ToolPool()
    first = {t["name"] for t in pool.assemble()}
    assert "connect_mcp" in first and not any(n.startswith("mcp__") for n in first)
    policy, result = pool.dispatch(call("connect_mcp", name="docs"), tmp_path)
    assert policy["decision"] == "allow" and result["status"] == "ok"
    second = {t["name"] for t in pool.assemble()}
    assert second == first | {"mcp__docs__search", "mcp__docs__get_version"}
    pool.connect("docs")
    assert len(pool.discovery_events) == 1


def test_server_hints_cannot_authorize_a_host_unapproved_tool(tmp_path):
    invoked = []
    pool = ToolPool()
    pool.clients["deploy"] = MCPClient(
        "deploy", [external("trigger")], {"trigger": lambda: invoked.append(True)}
    )
    policy, result = pool.dispatch(call("mcp__deploy__trigger"), tmp_path)
    assert policy["decision"] == "deny" and result["status"] == "denied"
    assert invoked == []


def test_argument_cannot_override_the_bound_tool(tmp_path):
    pool = ToolPool()
    pool.connect("docs")
    _, result = pool.dispatch(call("mcp__docs__get_version", tool="search"), tmp_path)
    assert result["status"] == "error" and "TypeError" in result["output"]


@pytest.mark.parametrize("kind", ["collision", "too_long", "schema"])
def test_bad_discovery_definitions_fail_before_model_use(kind):
    if kind == "collision":
        names = ["get.version", "get_version"]
    elif kind == "too_long":
        names = ["a" * 65]
    else:
        names = ["search"]
    tools = [external(n) for n in names]
    if kind == "schema":
        tools[0]["inputSchema"] = {"type": "array"}
    pool = ToolPool()
    pool.clients["test"] = MCPClient("test", tools, {n: lambda: None for n in names})
    with pytest.raises(ValueError):
        pool.assemble()


def test_wrong_missing_and_nonobject_arguments_return_tool_errors(tmp_path):
    pool = ToolPool()
    pool.connect("docs")
    for item in [
        call("mcp__docs__search"),
        call("mcp__docs__search", query=123),
        {"name": "mcp__docs__search", "arguments_json": "[]"},
    ]:
        _, result = pool.dispatch(item, tmp_path)
        assert result["status"] == "error"
    _, result = pool.dispatch(call("connect_mcp", name="unconfigured"), tmp_path)
    assert result["status"] == "error"


def test_server_search_reads_the_real_mount_and_preserves_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DIR", str(tmp_path))
    (tmp_path / "policy.md").write_text("unit_price 8 quantity 6")
    pool = ToolPool()
    pool.connect("docs")
    _, result = pool.dispatch(call("mcp__docs__search", query="quantity price"), tmp_path)
    records = json.loads(result["output"])
    assert records[0]["id"] == "policy.md" and records[0]["text"] == "unit_price 8 quantity 6"
    assert len(records[0]["sha256"]) == 64


def test_native_tool_metrics_expose_order_duplicate_and_argument_boundaries():
    from lessons.e10_tool_evaluation.metrics import HERE, score_rules

    rows = {r["id"]: r for r in json.loads((HERE / "micro_traces.json").read_text())}
    order = score_rules(rows["wrong_order"])["scores"]
    assert order["ragas_strict"] == 0 and order["ragas_flexible"] == order["ragas_f1"] == 1
    duplicate = score_rules(rows["duplicate"])["scores"]
    assert duplicate["ragas_f1"] == 1 and duplicate["ragas_flexible"] == 0
    extra = score_rules(rows["extra_argument"])["scores"]
    assert extra["ragas_strict"] == 1 and extra["deep_parameters"] == pytest.approx(5 / 6)
    empty = score_rules(rows["both_empty"])["scores"]
    assert empty["ragas_strict"] == 1 and empty["ragas_f1"] == 0


def test_independent_contract_accepts_two_valid_program_shapes_and_rejects_fake_result():
    from lessons.e10_tool_evaluation.eval import program_contract

    assert program_contract("quantity=6\nunit_price=8\nprint(quantity*unit_price)")
    assert program_contract("total=8*6\nprint(total)")
    assert not program_contract("print(48)")
    assert not program_contract("quantity=6\nunit_price=7\nprint(quantity*unit_price)")
    assert not program_contract("import os\nprint(6*8)")


def test_argument_judge_context_preserves_prior_tools_without_future_results():
    from lessons.e10_tool_evaluation.metrics import decision_contexts

    row = {
        "task": "repair",
        "mcp_enabled": True,
        "run_id": "a" * 32,
        "tool_snapshots": [
            {"tools": [definition("connect_mcp", ["name"], "")]},
            {"tools": [definition("mcp__docs__search", ["query"], "")]},
        ],
        "events": [
            {
                "type": "model",
                "span_id": "model-1",
                "reply": {"answer": "", "tool_calls": [call("connect_mcp", name="docs")]},
            },
            {
                "type": "tool",
                "span_id": "model-1:tool-0",
                "result": {"status": "ok", "output": "PRIOR_DISCOVERY"},
            },
            {
                "type": "model",
                "span_id": "model-2",
                "reply": {"answer": "", "tool_calls": [call("mcp__docs__search", query="invoice")]},
            },
            {
                "type": "tool",
                "span_id": "model-2:tool-0",
                "result": {"status": "ok", "output": "FUTURE_VALUE"},
            },
        ],
    }
    inputs = decision_contexts(row)
    assert len(inputs) == 2
    assert "PRIOR_DISCOVERY" not in inputs[0]["task"]
    assert "PRIOR_DISCOVERY" in inputs[1]["task"]
    assert all("FUTURE_VALUE" not in d["task"] for d in inputs)
    assert inputs[1]["source_model_span"] == "model-2"
    assert inputs[1]["predicted"][0]["name"] == "mcp__docs__search"


def test_execution_evidence_does_not_confuse_cat_or_masked_failure_with_running_python():
    from lessons.e10_tool_evaluation.eval import executed_program

    def event(command, code=0):
        return {"call": call("bash", command=command), "result": {"exit_code": code}}

    assert executed_program(event("python3 ./calculate.py >result.txt"))
    assert executed_program(event("python3 calculate.py | tee result.txt"))
    assert not executed_program(event("cat calculate.py"))
    assert not executed_program(event("python3 calculate.py || true"))
    assert not executed_program(event("python3 calculate.py", 1))
