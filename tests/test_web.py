import json
import threading
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

import pytest

from eval_course.web import DOCUMENTS, Handler


@pytest.fixture
def reader(tmp_path, monkeypatch):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "policy.md").write_text("这是挂载测试知识库。", encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_DIR", str(kb))
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs if key == "href")
        if tag == "img":
            self.images.extend(value for key, value in attrs if key == "src")


@pytest.mark.parametrize(
    "route,count",
    [
        ("/lesson", 2),
        ("/lesson8", 1),
        ("/lesson10", 1),
        ("/lesson12", 1),
        ("/lesson13", 1),
        ("/lesson14", 1),
    ],
)
def test_lesson_diagrams_load_from_the_rendered_page(reader, route, count):
    with urlopen(reader + route) as reply:
        page = Links()
        page.feed(reply.read().decode())
    assert len(page.images) == count
    for src in page.images:
        assert src.startswith("/image?path=")
        with urlopen(reader + src) as reply:
            assert reply.headers.get_content_type() == "image/png"
            assert reply.read(8) == b"\x89PNG\r\n\x1a\n"


def test_course_documents_and_local_links_are_readable(reader):
    targets = set(DOCUMENTS) | {"/knowledge", "/reports"}
    for route in DOCUMENTS:
        with urlopen(reader + route) as reply:
            html = reply.read().decode()
            assert reply.status == 200
            assert 'lang="zh-CN"' in html
        links = Links()
        links.feed(html)
        for href in links.hrefs:
            parsed = urlparse(href)
            if not parsed.scheme and not parsed.netloc and parsed.path:
                assert parsed.path.startswith("/"), (route, href)
                targets.add(href)
    for target in targets:
        with urlopen(reader + target) as reply:
            assert reply.status == 200, target


def test_api_reads_the_selected_mount(reader):
    with urlopen(reader + "/api/knowledge") as reply:
        docs = json.load(reply)
    assert [d["path"] for d in docs] == ["policy.md"]
    assert "挂载测试" in docs[0]["text"]


@pytest.mark.parametrize(
    "path",
    [
        "/code?path=../../.env",
        "/code?path=secrets/judge_api_key.txt",
        "/knowledge?path=../README.md",
        "/reports?file=../README.md",
        "/image?path=../../.env",
        "/image?path=lessons/e01_agent_baseline/code.py",
    ],
)
def test_reader_rejects_files_outside_its_reading_scope(reader, path):
    with pytest.raises(HTTPError) as error:
        urlopen(reader + path)
    assert error.value.code == 400
    error.value.close()
