import hashlib
import json
import struct
import xml.etree.ElementTree as ET

from eval_course.knowledge import PROJECT


def test_all_course_vectors_have_portable_text_and_dense_png_fallbacks():
    rows = json.loads((PROJECT / "references/figures.json").read_text())
    assert len(rows) == 32
    for row in rows:
        svg = PROJECT / row["output"]
        tree = ET.parse(svg).getroot()
        tags = [node.tag.rsplit("}", 1)[-1] for node in tree.iter()]
        assert "text" in tags
        assert not {"foreignObject", "script", "image", "switch"} & set(tags)
        width, height = int(float(tree.get("width"))), int(float(tree.get("height")))
        assert width <= 760
        png = (PROJECT / row["png"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (width * 3, height * 3)
        assert hashlib.sha256(svg.read_bytes()).hexdigest() == row["artifact_sha256"]
        assert hashlib.sha256(png).hexdigest() == row["png_sha256"]
        assert row["readme_preview"] == row["output"]
        assert row["preview_url"].split("?")[0].endswith(".svg")
