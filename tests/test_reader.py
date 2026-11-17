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
        for lesson, slug in [(1, "e01_success"), (2, "e02_samples")]:
            with urlopen(base + f"/lesson{lesson}") as response:
                body = response.read().decode()
            diagram = next(d for d in diagrams if d["slug"] == slug and d["generator"] == "Archify")
            assert f'href="/diagram?path={diagram["output"]}"' in body
            with urlopen(base + "/diagram?path=" + diagram["output"]) as response:
                assert b'data-motion-capable="true"' in response.read()
            with urlopen(base + f"/image?path=course/{slug}/images/task-evaluation.drawio.svg") as response:
                assert response.headers.get_content_type() == "image/svg+xml"
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
