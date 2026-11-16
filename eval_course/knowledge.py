"""A small filesystem knowledge base; no vector database is required for this lesson."""

import hashlib
import os
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def knowledge_root() -> Path:
    return Path(os.environ.get("KNOWLEDGE_DIR", PROJECT / "knowledge_base")).resolve()


def document(path: str, root: Path | None = None) -> dict:
    root = (root or knowledge_root()).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or target.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("知识库路径必须是挂载目录内的 Markdown 或文本文件。")
    if not target.is_file():
        raise ValueError(f"知识库文件不存在：{path}")
    text = target.read_text(encoding="utf-8")
    return {"path": path, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}


def catalog(root: Path | None = None) -> list[dict]:
    root = (root or knowledge_root()).resolve()
    if not root.is_dir():
        raise ValueError("知识库目录不存在，请检查 KNOWLEDGE_DIR 和 Docker 挂载。")
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix in {".md", ".txt"})
    return [document(str(p.relative_to(root)), root) for p in paths]


def terms(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    return words | {part[i : i + 2] for part in chinese for i in range(max(1, len(part) - 1))}


def search(query: str, limit: int = 3, root: Path | None = None) -> list[dict]:
    if not query.strip() or not 1 <= limit <= 10:
        raise ValueError("请输入查询内容，limit 必须在 1–10 之间。")
    query_terms = terms(query)
    hits = [{**doc, "matches": len(query_terms & terms(doc["text"]))} for doc in catalog(root)]
    return sorted((x for x in hits if x["matches"]), key=lambda x: (-x["matches"], x["path"]))[
        :limit
    ]
