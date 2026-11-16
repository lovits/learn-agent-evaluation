import pytest

from eval_course.judges import LiveJSON, api_key


def test_live_requires_explicit_model(monkeypatch):
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    with pytest.raises(ValueError, match="JUDGE_MODEL"):
        LiveJSON()


def test_live_requires_key_and_never_falls_back(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "configured-model")
    for name in ("JUDGE_API_KEY_FILE", "JUDGE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="live 需要"):
        LiveJSON()


def test_secret_file_takes_precedence(tmp_path, monkeypatch):
    key = tmp_path / "test-key"
    key.write_text("fixture-only-not-a-real-key\n")
    monkeypatch.setenv("JUDGE_API_KEY_FILE", str(key))
    monkeypatch.setenv("JUDGE_API_KEY", "wrong-fixture")
    assert api_key() == "fixture-only-not-a-real-key"
