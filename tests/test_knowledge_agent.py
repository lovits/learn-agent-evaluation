import copy
import hashlib

from course.e05_knowledge_context.code import run_task
from course.e05_knowledge_context.eval import check_run


def case_for(root):
    text = "Atlas release command is python -m pytest -q."
    (root / "release.md").write_text(text)
    (root / "other.md").write_text("Atlas release audit logs are retained.")
    return {
        "task": "Look up Atlas release",
        "reference": "python -m pytest -q",
        "source": {"path": "release.md", "sha256": hashlib.sha256(text.encode()).hexdigest()},
    }


def test_candidates_stay_out_of_model_input_and_snapshot_is_fixed(tmp_path):
    case = case_for(tmp_path)
    observed = []

    def model(messages):
        observed.append(copy.deepcopy(messages))
        if len(observed) == 1:
            # Changes on disk must not mutate this run's already-read documents.
            (tmp_path / "release.md").write_text("A changed policy")
            calls = [{"name": "search_knowledge", "arguments_json": '{"query":"Atlas release"}'}]
            return {"reply": {"answer": "", "tool_calls": calls}}
        return {"reply": {"answer": "Done", "tool_calls": []}}

    run = run_task(case, tmp_path, k=2, context_limit=1, root=tmp_path, model=model)
    query = run["retrievals"][0]
    assert len(query["hits"]) == 2 and len(query["selected"]) == 1
    assert run["sample"]["retrieval_context"] == query["emitted"]
    assert query["hits"][1]["text"] not in str(observed[-1])
    assert run["reference_status"] == "current"
    assert all(check_run(run).values())
    # A new run must notice the changed document and withdraw its stale reference.
    new = run_task(
        case,
        tmp_path,
        root=tmp_path,
        model=lambda _: {"reply": {"answer": "Done", "tool_calls": []}},
    )
    assert new["knowledge"]["sha256"] != run["knowledge"]["sha256"]
    assert new["reference_status"] == "source_changed_or_missing"
    assert new["sample"]["expected_output"] is new["sample"]["context"] is None


def test_unconsumed_last_tool_result_is_not_reported_as_model_context(tmp_path):
    case = case_for(tmp_path)

    def model(_):
        return {
            "reply": {
                "answer": "",
                "tool_calls": [
                    {"name": "search_knowledge", "arguments_json": '{"query":"Atlas release"}'}
                ],
            }
        }

    run = run_task(case, tmp_path, root=tmp_path, model=model)
    assert run["status"] == "step_limit" and len(run["retrievals"]) == 8
    assert len(run["sample"]["retrieval_context"]) == 7
    assert run["sample"]["retrieval_context"] == [r["emitted"][0] for r in run["retrievals"][:-1]]
