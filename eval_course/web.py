"""A local-only course reader. Experiments are explicit CLI commands."""

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from markdown_it import MarkdownIt

from lessons.e01_agent_baseline.code import load_cases

from .knowledge import PROJECT, catalog, document, search
from .records import NAME as REPORT_NAME

PAGES = {
    "/": ("课程首页", "README.md"),
    "/lesson": ("第1课：最小Agent", "lessons/e01_agent_baseline/README.zh.md"),
    "/lesson2": ("第2课：工具与轨迹", "lessons/e02_tools_traces/README.zh.md"),
    "/lesson3": ("第3课：规则与裁判", "lessons/e03_judges/README.zh.md"),
    "/lesson4": ("第4课：知识库检索", "lessons/e04_retrieval/README.zh.md"),
    "/lesson5": ("第5课：Faithfulness", "lessons/e05_faithfulness/README.zh.md"),
    "/lesson6": ("第6课：答案质量与拒答", "lessons/e06_answer_quality/README.zh.md"),
    "/lesson7": ("第7课：故障定位", "lessons/e07_failure_diagnosis/README.zh.md"),
    "/source": ("第1课源码", "lessons/e01_agent_baseline/source_walkthrough.md"),
    "/exercises": ("第1课练习", "lessons/e01_agent_baseline/exercises.md"),
    "/solutions": ("第1课答案", "lessons/e01_agent_baseline/solutions.md"),
    "/docker": ("Docker 与知识库", "docs/docker.md"),
    "/generation": ("PocketFlow 生成记录", "generation/README.md"),
}
DOCUMENTS = {
    **PAGES,
    "/source7": ("第7课源码", "lessons/e07_failure_diagnosis/source_walkthrough.md"),
    "/exercises7": ("第7课练习", "lessons/e07_failure_diagnosis/exercises.md"),
    "/solutions7": ("第7课答案", "lessons/e07_failure_diagnosis/solutions.md"),
    "/e07-results": ("第7课实测", "lessons/e07_failure_diagnosis/run_summary.md"),
    "/validation7": ("第7课验收", "docs/e07-validation.md"),
    "/generation7": ("第7课生成与审校", "generation/e07-README.md"),
    "/teaching7": ("第7课写作方式", "references/e07-teaching-pattern.md"),
    "/source6": ("第6课源码", "lessons/e06_answer_quality/source_walkthrough.md"),
    "/exercises6": ("第6课练习", "lessons/e06_answer_quality/exercises.md"),
    "/solutions6": ("第6课答案", "lessons/e06_answer_quality/solutions.md"),
    "/e06-results": ("第6课实测", "lessons/e06_answer_quality/run_summary.md"),
    "/validation6": ("第6课验收", "docs/e06-validation.md"),
    "/generation6": ("第6课生成与审校", "generation/e06-README.md"),
    "/generation4": ("第4课生成记录", "generation/e04-README.md"),
    "/source5": ("第5课源码", "lessons/e05_faithfulness/source_walkthrough.md"),
    "/exercises5": ("第5课练习", "lessons/e05_faithfulness/exercises.md"),
    "/solutions5": ("第5课答案", "lessons/e05_faithfulness/solutions.md"),
    "/e05-results": ("第5课实测", "lessons/e05_faithfulness/run_summary.md"),
    "/validation5": ("第5课验收", "docs/e05-validation.md"),
    "/source4": ("第4课源码", "lessons/e04_retrieval/source_walkthrough.md"),
    "/exercises4": ("第4课练习", "lessons/e04_retrieval/exercises.md"),
    "/solutions4": ("第4课答案", "lessons/e04_retrieval/solutions.md"),
    "/e04-results": ("第4课实测", "lessons/e04_retrieval/run_summary.md"),
    "/validation4": ("第4课验收", "docs/e04-validation.md"),
    "/validation3": ("第3课验收", "docs/e03-validation.md"),
    "/source3": ("第3课源码", "lessons/e03_judges/source_walkthrough.md"),
    "/exercises3": ("第3课练习", "lessons/e03_judges/exercises.md"),
    "/solutions3": ("第3课答案", "lessons/e03_judges/solutions.md"),
    "/e03-results": ("第3课实测", "lessons/e03_judges/run_summary.md"),
    "/source2": ("第2课源码分析", "lessons/e02_tools_traces/source_walkthrough.md"),
    "/exercises2": ("第2课练习", "lessons/e02_tools_traces/exercises.md"),
    "/solutions2": ("第2课参考答案", "lessons/e02_tools_traces/solutions.md"),
    "/e02-results": ("第2课实测结果", "lessons/e02_tools_traces/run_summary.md"),
    "/validation2": ("第2课验收", "docs/e02-validation.md"),
    "/generation2": ("第2课生成记录", "generation/e02-README.md"),
    "/curriculum": ("16课路线", "docs/curriculum.md"),
    "/validation": ("验证记录", "docs/validation.md"),
    "/third-party": ("第三方说明", "THIRD_PARTY.md"),
    "/plan": ("需求与项目计划", "docs/project-plan.md"),
    "/prompt": ("教材提示词", "generation/textbook_prompt.md"),
    "/brief": ("样章生成任务", "generation/lesson_brief.md"),
    "/teaching": ("Learn Claude Code 教学方式", "docs/teaching-method.md"),
    "/evaluation-map": ("评测与数据能力地图", "docs/evaluation-landscape.md"),
    "/production-plan": ("课程制作计划", "docs/course-production-plan.md"),
    "/curriculum-generation": ("课程规划生成记录", "generation/curriculum-README.md"),
    "/archive-24": ("原24课知识对照", "docs/archive/curriculum-24.md"),
    "/specification": ("16课详细设计与制作规范", "docs/course-specification.md"),
    "/curriculum-validation": ("课程设计核验", "docs/curriculum-validation.md"),
}
RENDERER = MarkdownIt("commonmark", {"html": False}).enable("table")


def layout(title: str, body: str) -> bytes:
    navigation = "".join(
        f'<a href="{url}">{html.escape(label)}</a>' for url, (label, _) in PAGES.items()
    )
    navigation += '<a href="/knowledge">挂载知识库</a><a href="/reports">实验结果</a>'
    template = (PROJECT / "eval_course/page.html").read_text(encoding="utf-8")
    return (
        template.replace("{{TITLE}}", html.escape(title))
        .replace("{{NAV}}", navigation)
        .replace("{{BODY}}", body)
        .encode()
    )


def report_root() -> Path:
    return Path(os.environ.get("RUNS_DIR", PROJECT / "runs"))


def render_page(path: str) -> str:
    source = PROJECT / path
    tokens = RENDERER.parse(source.read_text(encoding="utf-8"))
    routes = {(PROJECT / filename).resolve(): url for url, (_, filename) in DOCUMENTS.items()}
    for block in tokens:
        for token in block.children or []:
            if token.type != "link_open":
                continue
            href = token.attrGet("href") or ""
            parsed = urlparse(href)
            if parsed.scheme or href.startswith(("/", "#")):
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            if target in routes:
                token.attrSet(
                    "href", routes[target] + ("#" + parsed.fragment if parsed.fragment else "")
                )
            elif target.is_relative_to(PROJECT) and target.suffix in {".py", ".json", ".jsonl"}:
                token.attrSet("href", "/code?path=" + quote(str(target.relative_to(PROJECT))))
    return RENDERER.renderer.render(tokens, RENDERER.options, {})


def knowledge_page(query: dict) -> bytes:
    if "path" in query:
        doc = document(query["path"][0])
        return layout(doc["path"], RENDERER.render(doc["text"]))
    term = query.get("q", [""])[0]
    docs = search(term, limit=10) if term else catalog()
    content = "<h1>当前挂载的知识库</h1><p>每次查询重新读文件，不依赖隐藏索引。</p>"
    content += '<form><label for="query">检索词：</label><input id="query" name="q" placeholder="例如：Python"'
    content += f' value="{html.escape(term, quote=True)}"><button>检索</button></form>'
    for doc in docs:
        content += f'<h2><a href="/knowledge?path={quote(doc["path"])}">'
        content += html.escape(doc["path"]) + "</a></h2>"
        content += "<p><code>" + doc["sha256"] + "</code></p>"
    return layout("知识库", content)


def reports_page(query: dict) -> bytes:
    name = query.get("file", [""])[0]
    if name:
        if not REPORT_NAME.fullmatch(name):
            raise ValueError("无效的实验文件名。")
        text = (report_root() / name).read_text(encoding="utf-8")
        return layout(name, "<h1>逐样本实验记录</h1><pre>" + html.escape(text) + "</pre>")
    files = sorted(report_root().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    links = "".join(
        f'<li><a href="/reports?file={p.name}">{p.name}</a></li>'
        for p in files
        if REPORT_NAME.fullmatch(p.name)
    )
    return layout(
        "实验结果",
        "<h1>实验结果</h1><p>运行课程Agent并独立验收后刷新此页。</p><ul>" + links + "</ul>",
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/healthz":
                return self.send(200, b'{"status":"ok"}', "application/json")
            if parsed.path == "/api/knowledge":
                payload = json.dumps(catalog(), ensure_ascii=False).encode()
                return self.send(200, payload, "application/json")
            if parsed.path == "/api/cases":
                payload = json.dumps(load_cases(), ensure_ascii=False).encode()
                return self.send(200, payload, "application/json")
            if parsed.path in DOCUMENTS:
                title, path = DOCUMENTS[parsed.path]
                body = layout(title, render_page(path))
            elif parsed.path == "/code":
                target = (PROJECT / query.get("path", [""])[0]).resolve()
                allowed = [PROJECT / n for n in ("lessons", "eval_course", "references", "tools")]
                if target.suffix not in {".py", ".txt", ".json", ".jsonl"} or not any(
                    target.is_relative_to(x) for x in allowed
                ):
                    raise ValueError("该文件不在课程源码阅读范围内。")
                body = layout(
                    target.name,
                    "<h1>"
                    + html.escape(target.name)
                    + "</h1><pre>"
                    + html.escape(target.read_text(encoding="utf-8"))
                    + "</pre>",
                )
            elif parsed.path == "/knowledge":
                body = knowledge_page(query)
            elif parsed.path == "/reports":
                body = reports_page(query)
            else:
                return self.send(404, b"Not found", "text/plain")
            self.send(200, body, "text/html")
        except (OSError, ValueError) as error:
            self.send(
                400,
                layout("读取失败", "<h1>读取失败</h1><p>" + html.escape(str(error)) + "</p>"),
                "text/html",
            )

    def send(self, status, body, kind):
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)


def serve(port: int):
    print(f"课程阅读服务：http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
