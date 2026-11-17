"""Local model responses for the course; all tool execution stays in Docker."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from model_backend import complete


def contract(tools):
    fields = (
        {"command": {"type": "string"}}
        if tools is None
        else {
            "name": {"type": "string", "enum": list(tools)},
            "arguments_json": {"type": "string"},
        }
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string"},
            "tool_calls": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": fields,
                    "required": list(fields),
                },
            },
        },
        "required": ["answer", "tool_calls"],
    }


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            tools = payload.get("tools")
            instruction = (
                "Return the next response for a coding Agent. You only propose actions. "
                "The course runtime executes them in Linux; use python3. Read actual tool "
                "results before claiming completion. Empty tool_calls stops the loop. "
                "All paths are relative to the exercise workspace. Never bypass a denied action. "
            )
            instruction += (
                "Only tool: Bash, with a command string."
                if tools is None
                else "Tools: "
                + json.dumps(tools)
                + ". Supply arguments_json as a JSON object encoded "
                "in a string; every argument value must be a string. In a task explicitly "
                "asking to observe a file permission rejection, request it once, then respect it."
            )
            result = complete(
                instruction + "\nHistory:\n" + json.dumps(payload["messages"], ensure_ascii=False),
                schema=contract(tools),
                timeout=180,
            )
            self.respond(200, {"reply": json.loads(result.pop("text")), "model": result})
        except (ValueError, KeyError, TypeError, RuntimeError, OSError) as error:
            self.respond(502, {"error": str(error)})

    def respond(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
