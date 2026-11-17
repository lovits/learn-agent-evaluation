"""A schema-validated DeepEval model using the existing host judge transport."""

import asyncio
import json
import os
from urllib.request import Request, urlopen

from deepeval.models import DeepEvalBaseLLM


class JudgeModel(DeepEvalBaseLLM):
    def __init__(self):
        self.calls = []
        super().__init__("course-judge")

    def load_model(self):
        return self

    def get_model_name(self):
        return "course-judge-bridge"

    def supports_log_probs(self):
        return False

    def generate(self, prompt, schema=None):
        if schema is not None:
            prompt += "\nReturn JSON matching this schema:\n" + json.dumps(
                schema.model_json_schema()
            )
        request = Request(
            os.environ.get("JUDGE_BRIDGE_URL", "http://host.docker.internal:8768/judge"),
            data=json.dumps({"prompt": prompt}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=210) as response:
            result = json.load(response)
        self.calls.append(result)
        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
            raise TypeError("Judge transport must return a text response")
        return schema.model_validate_json(result["text"]) if schema else result["text"]

    async def a_generate(self, prompt, schema=None):
        return await asyncio.to_thread(self.generate, prompt, schema)
