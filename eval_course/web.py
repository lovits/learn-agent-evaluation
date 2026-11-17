"""Read the course files; opening a page never executes an Agent."""

import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from markdown_it import MarkdownIt

from .knowledge import PROJECT, catalog

PAGES = {"/": "README.md", "/curriculum": "docs/curriculum.md"}
for number, slug in [
    (1, "e01_success"),
    (2, "e02_samples"),
    (3, "e03_datasets"),
    (4, "e04_scoring"),
    (5, "e05_knowledge_context"),
    (6, "e06_context_precision"),
    (7, "e07_context_recall"),
    (8, "e08_faithfulness"),
]:
    for route, name in [
        ("lesson", "README.zh.md"),
        ("source", "source_walkthrough.md"),
        ("exercises", "exercises.md"),
        ("solutions", "solutions.md"),
        ("assessment", "assessment.md"),
    ]:
        PAGES[f"/{route}{number}"] = f"course/{slug}/{name}"
PAGES["/specification"] = "docs/course-specification.md"
RENDERER = MarkdownIt("commonmark", {"html": False}).enable("table")


def render(path):
    source = PROJECT / path
    tokens = RENDERER.parse(source.read_text())
    routes = {(PROJECT / p).resolve(): route for route, p in PAGES.items()}
    diagrams = json.loads((PROJECT / "references/figures.json").read_text())
    for index, block in enumerate(tokens):
        if block.type == "heading_open":
            block.attrSet(
                "id", re.sub(r"[^\w-]", "", tokens[index + 1].content.lower().replace(" ", "-"))
            )
        for token in block.children or []:
            if token.type == "image":
                src = token.attrGet("src") or ""
                preview = next((row for row in diagrams if row.get("preview_url") == src), None)
                if preview:
                    token.attrSet("src", "/image?path=" + quote(preview["png"]))
                    continue
                image = urlparse(src)
                target = (source.parent / unquote(image.path)).resolve()
                if not image.scheme and target.is_relative_to(PROJECT / "course"):
                    token.attrSet(
                        "src", "/image?path=" + quote(target.relative_to(PROJECT).as_posix())
                    )
                continue
            if token.type != "link_open":
                continue
            href = token.attrGet("href") or ""
            hosted = next((row for row in diagrams if row.get("url") == href), None)
            if hosted:
                route = "/diagram" if hosted["generator"] == "Archify" else "/image"
                token.attrSet("href", route + "?path=" + quote(hosted["output"]))
                continue
            parsed = urlparse(href)
            if parsed.scheme or href.startswith(("/", "#")):
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            if target in routes:
                token.attrSet(
                    "href", routes[target] + ("#" + parsed.fragment if parsed.fragment else "")
                )
            elif target.is_relative_to(PROJECT / ".archify") and target.suffix == ".html":
                token.attrSet(
                    "href", "/diagram?path=" + quote(target.relative_to(PROJECT).as_posix())
                )
            elif target.is_relative_to(PROJECT) and target.suffix in {".py", ".json", ".jsonl"}:
                token.attrSet("href", "/code?path=" + quote(target.relative_to(PROJECT).as_posix()))
    return RENDERER.renderer.render(tokens, RENDERER.options, {})


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/healthz":
                return self.send(200, b'{"status":"ok"}', "application/json")
            if parsed.path == "/api/knowledge":
                return self.send(
                    200, json.dumps(catalog(), ensure_ascii=False).encode(), "application/json"
                )
            if parsed.path in {"/image", "/diagram"}:
                target = (PROJECT / parse_qs(parsed.query).get("path", [""])[0]).resolve()
                if parsed.path == "/image":
                    if (
                        not target.is_relative_to(PROJECT / "course")
                        or target.parent.name != "images"
                        or target.suffix not in {".png", ".svg"}
                    ):
                        raise ValueError("Unreadable image path")
                    mime = "image/svg+xml" if target.suffix == ".svg" else "image/png"
                    return self.send(200, target.read_bytes(), mime)
                if not target.is_relative_to(PROJECT / ".archify") or target.suffix != ".html":
                    raise ValueError("Unreadable diagram path")
                return self.send(200, target.read_bytes(), "text/html")
            if parsed.path == "/code":
                name = parse_qs(parsed.query).get("path", [""])[0]
                target = (PROJECT / name).resolve()
                if (
                    not target.is_relative_to(PROJECT)
                    or not any(
                        target.is_relative_to(PROJECT / folder)
                        for folder in ("course", "eval_course")
                    )
                    or target.suffix not in {".py", ".json", ".jsonl"}
                ):
                    raise ValueError("Unreadable source path")
                body = "<pre>" + html.escape(target.read_text()) + "</pre>"
            elif parsed.path in PAGES:
                body = render(PAGES[parsed.path])
            else:
                return self.send(404, b"Not found", "text/plain")
            template = (PROJECT / "eval_course/page.html").read_text()
            nav = '<a href="/">课程</a><a href="/curriculum">大纲</a><a href="/lesson1">第1课</a><a href="/lesson2">第2课</a><a href="/lesson3">第3课</a><a href="/lesson4">第4课</a><a href="/lesson5">第5课</a><a href="/lesson6">第6课</a><a href="/lesson7">第7课</a><a href="/lesson8">第8课</a>'
            page = (
                template.replace("{{TITLE}}", "从编程 Agent 学评测")
                .replace("{{NAV}}", nav)
                .replace("{{BODY}}", body)
            )
            self.send(200, page.encode(), "text/html")
        except (ValueError, OSError) as error:
            self.send(400, str(error).encode(), "text/plain")

    def send(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


def serve(port=8000):
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
