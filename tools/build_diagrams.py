"""Publish only the registered course diagrams, never workspaces or run data."""

import hashlib
import html
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination)
    diagrams = destination / "diagrams"
    diagrams.mkdir(parents=True, exist_ok=True)
    links = []
    for row in json.loads((PROJECT / "references/figures.json").read_text()):
        source = PROJECT / row["output"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row["artifact_sha256"]
        target = diagrams / (row["name"] + source.suffix)
        shutil.copyfile(source, target)
        preview = PROJECT / row["png"]
        assert hashlib.sha256(preview.read_bytes()).hexdigest() == row["png_sha256"]
        shutil.copyfile(preview, diagrams / (row["name"] + ".png"))
        title = html.escape(row.get("title", row["name"]))
        links.append(f'<li><a href="diagrams/{target.name}">{title}</a></li>')
    (destination / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>从编程 Agent 学评测 · 流程图</title>'
        '<style>body{font:18px/1.8 system-ui;max-width:760px;margin:60px auto;padding:24px}'
        'a{color:#1760b5}li{margin:12px 0}</style>'
        '<h1>从编程 Agent 学评测</h1><p>图中用方框和箭头解释 Agent 循环与独立评测。</p><ul>'
        + "".join(links)
        + '</ul><a href="https://github.com/lovits/learn-agent-evaluation">返回课程</a></html>',
        encoding="utf-8",
    )


if __name__ == "__main__":
    build(PROJECT / "_site")
