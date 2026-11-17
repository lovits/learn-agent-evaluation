import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from eval_course.web import PROJECT, Handler


def test_new_course_pages_and_source_boundary():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path in [
            "/",
            "/curriculum",
            "/lesson1",
            "/lesson2",
            "/source2",
            "/lesson3",
            "/source3",
            "/assessment3",
            "/lesson4",
            "/source4",
            "/assessment4",
            "/lesson5",
            "/source5",
            "/assessment5",
            "/lesson6",
            "/source6",
            "/assessment6",
            "/lesson7",
            "/source7",
            "/assessment7",
            "/lesson8",
            "/source8",
            "/assessment8",
            "/lesson9",
            "/source9",
            "/assessment9",
            "/lesson10",
            "/source10",
            "/assessment10",
            "/lesson11",
            "/source11",
            "/assessment11",
            "/assessment1",
            "/assessment2",
            "/code?path=course/e02_samples/code.py",
        ]:
            with urlopen(base + path) as response:
                assert response.status == 200
        with urlopen(base + "/image?path=course/e01_success/images/agent-loop.png") as response:
            assert response.headers.get_content_type() == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        diagrams = json.loads((PROJECT / "references/figures.json").read_text())
        for lesson, slug in [
            (1, "e01_success"),
            (2, "e02_samples"),
            (3, "e03_datasets"),
            (4, "e04_scoring"),
            (5, "e05_knowledge_context"),
            (6, "e06_context_precision"),
            (7, "e07_context_recall"),
            (8, "e08_faithfulness"),
            (9, "e09_answer_quality"),
            (10, "e10_rag_diagnosis"),
            (11, "e11_tool_quality"),
        ]:
            with urlopen(base + f"/lesson{lesson}") as response:
                body = response.read().decode()
            lesson_diagrams = [d for d in diagrams if d["slug"] == slug]
            assert len(lesson_diagrams) == 2
            for diagram in lesson_diagrams:
                assert f'src="/image?path={diagram["readme_preview"]}"' in body
                with urlopen(base + "/image?path=" + diagram["readme_preview"]) as response:
                    assert response.headers.get_content_type() == "image/png"
                    assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        for path in [
            "/code",
            "/code?path=../../.env",
            "/code?path=tools/model_backend.py",
            "/image?path=../../.env",
            "/diagram?path=tools/model_backend.py",
        ]:
            with pytest.raises(HTTPError) as error:
                urlopen(base + path)
            assert error.value.code == 400
            error.value.close()
        with pytest.raises(HTTPError) as old:
            urlopen(base + "/lesson16")
        assert old.value.code == 404
        old.value.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
