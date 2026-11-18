"""Rebuild portable SVG diagrams with native text, using the existing graph routes."""

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def element(parent, tag, **attributes):
    return ET.SubElement(
        parent, f"{{{NS}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attributes.items()}
    )


def text(parent, x, y, value, size=16, color="#334155", anchor="middle", weight="500"):
    node = element(
        parent, "text", x=x, y=y, fill=color, font_size=size, text_anchor=anchor, font_weight=weight
    )
    lines = value.splitlines()
    for i, line in enumerate(lines):
        element(node, "tspan", x=x, y=y + 21 * i).text = line
    return node


def arrow(parent, points, label="", at=None):
    element(
        parent,
        "path",
        d="M " + " L ".join(f"{x} {y}" for x, y in points),
        fill="none",
        stroke="#64748b",
        stroke_width="1.7",
        marker_end="url(#arrow)",
    )
    if label:
        node = text(parent, *at, label, size=14)
        node.set("paint-order", "stroke")
        node.set("stroke", "#fafbfc")
        node.set("stroke-width", "5")


def compact_evaluation(row):
    """The two wide diagrams need new routes rather than smaller text."""
    cells = {
        c.get("id"): c
        for c in ET.parse(PROJECT / row["candidate"]).findall(".//mxCell[@vertex='1']")
    }
    body = ET.Element(f"{{{NS}}}g")
    if row["name"].startswith("e01"):
        positions = {
            "runner": (250, 15, 220, 60),
            "agent": (35, 150, 245, 60),
            "report": (35, 260, 245, 60),
            "workspace": (35, 370, 245, 60),
            "evaluate": (420, 150, 235, 60),
            "rules": (420, 370, 235, 60),
            "grade": (420, 480, 235, 60),
        }
        for x, w, h, label in [
            (10, 295, 350, "Agent：执行并保存证据"),
            (390, 300, 465, "独立评分"),
        ]:
            element(
                body,
                "rect",
                x=x,
                y=100,
                width=w,
                height=h,
                rx=10,
                fill="#f1f5f9",
                stroke="#cbd5e1",
                stroke_dasharray="5,4",
            )
            text(body, x + w / 2, 125, label, size=15)
        routes = [
            ([(305, 75), (305, 85), (295, 85), (295, 180), (280, 180)], "①运行Agent", (190, 93)),
            ([(415, 75), (670, 75), (670, 180), (655, 180)], "②运行结束，独立评分", (550, 93)),
            ([(157, 210), (157, 260)], "记录", (185, 240)),
            ([(35, 180), (20, 180), (20, 400), (35, 400)], "Bash读写", (74, 346)),
            ([(280, 290), (340, 290), (340, 180), (420, 180)], "读取轨迹", (365, 252)),
            ([(280, 400), (420, 400)], "只读文件", (350, 388)),
            ([(537, 210), (537, 370)], "逐条检查", (585, 292)),
            ([(537, 430), (537, 480)], "汇总", (570, 461)),
        ]
        height = 580
    else:
        positions = {
            "record": (20, 25, 230, 60),
            "files": (20, 145, 230, 60),
            "checks": (420, 25, 235, 60),
            "event": (420, 145, 235, 80),
            "all": (450, 285, 180, 95),
            "yes": (20, 430, 220, 60),
            "no": (430, 430, 220, 60),
            "sample": (20, 285, 230, 60),
            "note": (210, 545, 350, 60),
        }
        routes = [
            ([(250, 55), (420, 55)], "读取记录", (335, 43)),
            ([(250, 175), (320, 175), (320, 55), (420, 55)], "读取产物", (360, 140)),
            ([(537, 85), (537, 145)], "选择本题事件", (595, 120)),
            ([(537, 225), (537, 285)], "汇总 checks", (595, 260)),
            ([(450, 332), (330, 332), (330, 460), (240, 460)], "是", (350, 420)),
            ([(540, 380), (540, 430)], "否", (562, 411)),
            ([(20, 55), (8, 55), (8, 315), (20, 315)], "", None),
            ([(130, 490), (130, 575), (210, 575)], "保留逐项判断", (130, 530)),
            ([(540, 490), (540, 545)], "", None),
        ]
        height = 620
    for points, label, at in routes:
        arrow(body, points, label, at)
    for id, (x, y, w, h) in positions.items():
        cell = cells[id]
        group = element(body, "g", data_cell_id=id)
        if id == "all":
            element(
                group,
                "polygon",
                points=f"{x + w / 2},{y} {x + w},{y + h / 2} {x + w / 2},{y + h} {x},{y + h / 2}",
                fill="#fff7ed",
                stroke="#d97706",
                stroke_width="1.8",
            )
        else:
            fill, stroke = (
                ("#ecfdf5", "#16a34a")
                if id in {"grade", "yes"}
                else ("#fef2f2", "#dc2626")
                if id == "no"
                else ("#eff6ff", "#2563eb")
            )
            element(
                group,
                "rect",
                x=x,
                y=y,
                width=w,
                height=h,
                rx=8,
                fill=fill,
                stroke=stroke,
                stroke_width="1.6",
            )
        value = cell.get("value", "")
        text(group, x + w / 2, y + h / 2 - (len(value.splitlines()) - 1) * 10.5 + 5, value)
    return body, 720, height


def rebuild(row):
    source = PROJECT / row.get("layout_source", row["output"])
    original = ET.parse(source).getroot()
    _, _, width, height = map(float, original.get("viewBox").split())
    body = copy.deepcopy(
        next(g for g in original.iter(f"{{{NS}}}g") if g.get("data-cell-id") == "0")
    )
    for parent in list(body.iter()):
        for child in list(parent):
            if child.tag == f"{{{NS}}}switch":
                texts = [t for t in child if t.tag == f"{{{NS}}}text"]
                position = list(parent).index(child)
                parent.remove(child)
                for i, node in enumerate(texts):
                    parent.insert(position + i, node)
        for key in ["style", "pointer-events"]:
            parent.attrib.pop(key, None)
    for node in body.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "text":
            size = float(node.get("font-size", "16").removesuffix("px"))
            node.set("font-size", str(max(14, size)))
            node.set(
                "font-family",
                "system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif",
            )
            node.set("fill", "#334155")
            node.set("font-weight", "500")
        elif tag in {"rect", "path", "ellipse"} and node.get("stroke") not in {None, "none"}:
            node.set("stroke-width", "1.6")
    colors = {
        "#9db8f2": "#2563eb",
        "#eef4ff": "#eff6ff",
        "#b9a6f0": "#818cf8",
        "#f3eeff": "#eef2ff",
        "#e8c36a": "#d97706",
        "#fff6e0": "#fff7ed",
        "#8bcb9f": "#16a34a",
        "#e7f6ec": "#ecfdf5",
        "#eba3a3": "#dc2626",
        "#fdecec": "#fef2f2",
    }
    for node in body.iter():
        for key in ["fill", "stroke"]:
            value = node.get(key, "").lower()
            if value in colors:
                node.set(key, colors[value])
    edges = {
        c.get("id") for c in ET.parse(PROJECT / row["candidate"]).findall(".//mxCell[@edge='1']")
    }
    for group in body.iter(f"{{{NS}}}g"):
        if group.get("data-cell-id") not in edges:
            continue
        for parent in group.iter():
            for child in list(parent):
                if child.tag == f"{{{NS}}}rect":
                    parent.remove(child)
        for node in group.iter(f"{{{NS}}}text"):
            node.set("font-size", "14")
            node.set("paint-order", "stroke")
            node.set("stroke", "#fafbfc")
            node.set("stroke-width", "5")
    if row["name"] in {"e01-evaluation-path", "e02-evaluation-path"}:
        body, width, height = compact_evaluation(row)
    canvas_width, canvas_height = max(640, width + 24), height + 76
    root = ET.Element(
        f"{{{NS}}}svg",
        viewBox=f"0 0 {canvas_width:g} {canvas_height:g}",
        width=f"{canvas_width:g}",
        height=f"{canvas_height:g}",
        attrib={
            "font-family": "system-ui, -apple-system, sans-serif",
            "role": "img",
            "aria-labelledby": "title desc",
        },
    )
    element(root, "title", id="title").text = row["title"]
    element(
        root, "desc", id="desc"
    ).text = "保留本课机制和评测关系。原生 SVG 文字与路径，放大可读。"
    defs = element(root, "defs")
    gradient = element(defs, "linearGradient", id="header", x1="0", y1="0", x2="1", y2="0")
    element(gradient, "stop", offset="0%", stop_color="#1e3a5f")
    element(gradient, "stop", offset="100%", stop_color="#2563eb")
    marker = element(
        defs,
        "marker",
        id="arrow",
        viewBox="0 0 10 10",
        refX="9",
        refY="5",
        markerWidth="6",
        markerHeight="6",
        orient="auto-start-reverse",
    )
    element(marker, "path", d="M 0 0 L 10 5 L 0 10 z", fill="#64748b")
    element(root, "rect", width="100%", height="100%", rx=8, fill="#fafbfc")
    element(root, "rect", width="100%", height=48, rx=8, fill="url(#header)")
    element(root, "rect", x=0, y=40, width="100%", height=8, fill="url(#header)")
    text(root, canvas_width / 2, 31, row["title"], size=18, color="white", weight="700")
    wrapper = element(root, "g", transform="translate(12,64)")
    wrapper.append(body)
    output = PROJECT / row["png"]
    ET.ElementTree(root).write(output.with_suffix(".svg"), encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    for figure in json.loads((PROJECT / "references/figures.json").read_text()):
        rebuild(figure)
