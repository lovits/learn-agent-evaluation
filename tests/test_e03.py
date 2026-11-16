import pytest

from lessons.e03_judges.code import rules, set_f1


@pytest.mark.parametrize(
    "expected,actual,f1",
    [
        ([], [], 1),
        (["a"], [], 0),
        ([], ["a"], 0),
        (["a", "b"], ["a"], 2 / 3),
        (["a"], ["a", "a"], 1),
    ],
)
def test_f1_boundaries(expected, actual, f1):
    assert set_f1(expected, actual)["f1"] == pytest.approx(f1)


@pytest.mark.parametrize(
    "response,valid",
    [
        ('{"result":48}', 1),
        ('{"result":true}', 0),
        ('{"result":48,"extra":1}', 0),
        ("48", 0),
        ("四十八", 0),
        ("bad json", 0),
    ],
)
def test_json_contract(response, valid):
    c = {
        "response": response,
        "artifact_verified": False,
        "expected_tools": [],
        "observed_tools": [],
    }
    result = rules(c)
    assert result["json_contract"] == valid
    assert result["state_contract"] == 0


def test_judge_failure_is_unscored(monkeypatch):
    from lessons.e03_judges.eval import Transport, evaluate

    def fail(self, prompt):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(Transport, "ask", fail)
    from ragas.llms import BaseRagasLLM

    async def fail_async(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(BaseRagasLLM, "generate", fail_async)
    row = evaluate(
        {
            "response": '{"result":48}',
            "artifact_verified": True,
            "expected_tools": [],
            "observed_tools": [],
        }
    )
    assert all(metric["score"] is None and "error" in metric for metric in row["judges"].values())
