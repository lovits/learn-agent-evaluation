import hashlib
import json
import os

import pytest

from eval_course.knowledge import catalog, search
from eval_course.tinyrag import chunks
from vendor.tinyrag.VectorBase import VectorStore


def test_chunk_windows_preserve_long_text_offsets_and_versions():
    text = "def f(x):\n    return x + 1\n" * 100
    source_hash = hashlib.sha256(text.encode()).hexdigest()
    parts = chunks([{"path": "api.md", "text": text, "sha256": source_hash}], 80, 15)
    restored = parts[0]["text"]
    previous_end = parts[0]["end"]
    for part in parts[1:]:
        assert part["start"] == previous_end - 15
        restored += part["text"][15:]
        previous_end = part["end"]
    assert restored == text
    assert all(p["text"] == text[p["start"] : p["end"]] for p in parts)
    assert all(p["source_sha256"] == source_hash for p in parts)
    assert all(p["sha256"] == hashlib.sha256(p["text"].encode()).hexdigest() for p in parts)
    with pytest.raises(ValueError):
        chunks([], 80, 80)


def test_search_calls_native_tinyrag_and_keeps_equal_passages_attributed(tmp_path, monkeypatch):
    for name in ("a.md", "b.md"):
        (tmp_path / name).write_text("upload maximum bytes 1048576")
    observed = []
    original = VectorStore.query

    def query(self, text, embedding, k):
        observed.append((text, k))
        return original(self, text, embedding, k)

    monkeypatch.setattr(VectorStore, "query", query)
    ca_bundle = os.environ.get("CURL_CA_BUNDLE")
    hits = search("upload maximum", 2, tmp_path)
    assert observed == [("upload maximum", 2)]
    assert {h["path"] for h in hits} == {"a.md", "b.md"}
    assert len({h["chunk_id"] for h in hits}) == 2
    assert all(h["retriever"] == "TinyRAG.VectorStore" for h in hits)
    assert all(h["embedding"] == "local-tfidf" and h["similarity"] > 0 for h in hits)
    assert os.environ.get("CURL_CA_BUNDLE") == ca_bundle
    json.dumps(hits, allow_nan=False)


def test_empty_or_nonmatching_corpus_does_not_invent_hits(tmp_path):
    assert search("upload", root=tmp_path) == []
    (tmp_path / "api.md").write_text("upload maximum 10")
    assert search("unfindable", root=tmp_path) == []
    old = search("upload", root=tmp_path)[0]
    (tmp_path / "api.md").write_text("upload maximum 20")
    new = search("upload", root=tmp_path)[0]
    assert old["source_sha256"] != new["source_sha256"]
    assert new["source_sha256"] == catalog(tmp_path)[0]["sha256"]
