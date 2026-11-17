"""Generate pending candidates from one source; generation never grants approval."""

import json
import os
import uuid
from urllib.request import Request, urlopen

from eval_course.knowledge import document
from eval_course.records import save


def generate():
    doc = document("course/upload.md")
    prompt = (
        "Return a JSON array of 3 candidate evaluation tasks grounded in this document. "
        "Fields: task, reference, quote (exact evidence), answerable (boolean), family, intent, "
        "category (normal/error/boundary/insufficient). Task must ask the Agent to read upload.md. "
        "Use upload-auth or upload-size for family; intent names a meaning, not a wording. "
        "Do not invent policies. Questions may be Chinese; reference must be independently checked.\n"
        + doc["text"]
    )
    request = Request(
        os.environ.get("GENERATION_BRIDGE_URL", "http://host.docker.internal:8769/generate"),
        data=json.dumps({"prompt": prompt}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=200) as response:
        transport = json.load(response)
    candidates = json.loads(transport.pop("text"))
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Expected a non-empty candidate array")
    fields = {"task", "reference", "quote", "answerable", "family", "intent", "category"}
    for index, row in enumerate(candidates):
        if not isinstance(row, dict) or not fields <= row.keys():
            raise ValueError("Candidate fields are missing")
        row.update(
            id=f"generated-{index}",
            origin="live_model_candidate",
            source={"path": doc["path"], "sha256": doc["sha256"]},
            review={"decision": "pending", "reviewer": None, "reason": "Await source review"},
        )
    return {
        "run_id": uuid.uuid4().hex,
        "kind": "generated_candidates",
        "candidates": candidates,
        "transport": transport,
    }


if __name__ == "__main__":
    print(save(generate(), prefix="e03-suite"))
