import json

from course.e01_success.code import agent_loop as first_loop
from course.e01_success.eval import evaluate as first_grade
from course.e02_samples.code import agent_loop
from course.e02_samples.eval import evaluate
from course.e02_samples.samples import to_deepeval, to_ragas_multi, to_ragas_single
from course.e02_samples.tools import execute


def model(responses):
    replies = iter(responses)
    return lambda _: {"reply": next(replies)}


def call(name, **arguments):
    return {"name": name, "arguments_json": json.dumps(arguments)}


def test_first_loop_requires_real_evidence(tmp_path):
    replies = [
        {
            "tool_calls": [
                {"command": "printf 'print(\"Hello, World!\")\\n' > hello.py; python3 hello.py"}
            ],
            "answer": "",
        },
        {"tool_calls": [], "answer": "done"},
    ]
    run = first_loop("hello", tmp_path, model(replies))
    assert first_grade(run, tmp_path, {})["passed"]
    (tmp_path / "hello.py").write_text("print('wrong')")
    assert not first_grade(run, tmp_path, {})["passed"]
    fake = first_loop("hello", tmp_path, model([{"tool_calls": [], "answer": "done"}]))
    assert not first_grade(fake, tmp_path, {})["passed"]


def test_same_run_keeps_feedback_and_exports_real_sdk_objects(tmp_path):
    (tmp_path / "source.txt").write_text("original")
    responses = iter(
        [
            {"tool_calls": [call("read_file", path="source.txt")], "answer": ""},
            {
                "tool_calls": [
                    call("write_file", path="result.txt", content="original"),
                    call("read_file", path="result.txt"),
                ],
                "answer": "",
            },
            {"tool_calls": [], "answer": "done"},
        ]
    )

    def next_reply(messages):
        if len(messages) == 3:
            assert messages[-1]["content"][0]["output"] == "original"
        return {"reply": next(responses)}

    run = {"run_id": "unit", "task": "copy", **agent_loop("copy", tmp_path, next_reply)}
    assert [e["id"] for e in run["events"]] == ["1.0", "2.0", "2.1"]
    deep = to_deepeval(run)
    assert deep.tools_called[1].input_parameters["content"] == "original"
    assert to_ragas_single(run).response == deep.actual_output
    multi = to_ragas_multi(run)
    assert [m.type for m in multi.user_input] == ["human", "ai", "tool", "ai", "tool", "ai"]
    assert evaluate(run, tmp_path, {"output_path": "result.txt", "output_content": "original"})[
        "passed"
    ]


def test_denial_error_and_bad_arguments_are_distinct(tmp_path):
    assert (
        execute("write_file", {"path": "../outside.txt", "content": "no"}, tmp_path)["status"]
        == "denied"
    )
    assert not (tmp_path.parent / "outside.txt").exists()
    assert execute("read_file", {"path": "missing.txt"}, tmp_path)["status"] == "error"
    assert execute("read_file", {"command": "bad"}, tmp_path)["status"] == "invalid"
    (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    assert (
        execute("write_file", {"path": "link/outside.txt", "content": "no"}, tmp_path)["status"]
        == "denied"
    )


def test_denied_call_survives_export(tmp_path):
    run = {
        "run_id": "unit",
        "task": "denied",
        **agent_loop(
            "denied",
            tmp_path,
            model(
                [
                    {
                        "tool_calls": [call("write_file", path="../outside.txt", content="no")],
                        "answer": "",
                    },
                    {"tool_calls": [], "answer": "denied"},
                ]
            ),
        ),
    }
    assert to_deepeval(run).tools_called[0].output["status"] == "denied"
    assert json.loads(to_ragas_multi(run).user_input[2].content)[0]["status"] == "denied"


def test_model_failure_and_budget_keep_observed_actions(tmp_path):
    run = agent_loop(
        "bounded",
        tmp_path,
        lambda _: {"reply": {"tool_calls": [call("read_file", path="missing")], "answer": ""}},
        max_steps=1,
    )
    assert run["status"] == "step_limit" and len(run["events"]) == 1

    def unavailable(_):
        raise OSError("unavailable")

    assert agent_loop("failed", tmp_path, unavailable)["status"] == "model_error"
