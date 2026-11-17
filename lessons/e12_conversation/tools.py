"""Keep previous tools; make saved output recoverable in bounded character pages."""

import json

from lessons.e02_tools_traces.code import permission
from lessons.e10_tool_evaluation.mcp_tools import ToolPool


class PagedToolPool(ToolPool):
    def assemble(self):
        tools = super().assemble()
        reader = next(t for t in tools if t["name"] == "read_file")
        reader["description"] = (
            "Read workspace file. Optional offset is a zero-based CHARACTER offset; "
            "optional limit is 1..2000 CHARACTERS per page. Both are strings. "
            "Use pages to recover saved tool outputs without repeating a full-file read."
        )
        reader["input_schema"]["properties"].update(
            {"offset": {"type": "string"}, "limit": {"type": "string"}}
        )
        return tools

    def dispatch(self, call, workspace, approve=lambda n, a: False):
        if call.get("name") != "read_file":
            return super().dispatch(call, workspace, approve)
        try:
            args = json.loads(call["arguments_json"])
            if (
                not isinstance(args, dict)
                or "path" not in args
                or set(args) - {"path", "offset", "limit"}
            ):
                raise ValueError("read_file expects path and optional offset/limit")
            if not all(isinstance(v, str) for v in args.values()):
                raise TypeError("All read_file arguments must be strings")
            if set(args) == {"path"}:
                return super().dispatch(call, workspace, approve)
            if not args.get("offset", "0").isdigit() or not args.get("limit", "2000").isdigit():
                raise ValueError("offset/limit must be decimal integer strings")
            offset, limit = int(args.get("offset", "0")), int(args.get("limit", "2000"))
            if not 1 <= limit <= 2000:
                raise ValueError("Page limit must be within 1..2000 characters")
        except (ValueError, TypeError, KeyError) as error:
            return {"decision": "not_checked", "reason": "invalid_arguments"}, {
                "status": "invalid_arguments",
                "output": str(error),
            }
        decision, reason = permission("read_file", args, workspace, approve)
        policy = {"decision": decision, "reason": reason}
        if decision == "deny":
            return policy, {"status": "denied", "output": reason}
        try:
            text = (workspace / args["path"]).read_text()
            end = min(len(text), offset + limit)
            return policy, {
                "status": "ok",
                "output": text[offset:end],
                "offset": offset,
                "next_offset": end,
                "total_chars": len(text),
                "truncated": end < len(text),
            }
        except (OSError, UnicodeError) as error:
            return policy, {"status": "error", "output": str(error)}
