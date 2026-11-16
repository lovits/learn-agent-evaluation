"""Adapt Learn Claude Code s14 discovery/dispatch; no MCP wire transport."""

import copy
import json
import re

from eval_course.knowledge import document, search
from lessons.e02_tools_traces.code import TOOL_SPEC
from lessons.e04_retrieval.code import dispatch as previous_dispatch

HOST_POLICY = {("docs", "search"): "allow", ("docs", "get_version"): "allow"}


def normalize(name):
    if not isinstance(name, str) or not name:
        raise ValueError("Tool and server names must be nonempty strings")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def definition(name, fields, description):
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in fields},
            "required": list(fields),
            "additionalProperties": False,
        },
    }


class MCPClient:
    def __init__(self, name, tools, handlers):
        names = [t["name"] for t in tools]
        if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
            raise ValueError("Invalid or duplicate server tool names")
        if any(n not in handlers for n in names):
            raise ValueError("Missing server handler")
        self.name, self.tools, self.handlers = name, copy.deepcopy(tools), handlers.copy()

    def call_tool(self, name, args):
        try:
            value = self.handlers[name](**args)
            return {"status": "ok", "output": json.dumps(value, ensure_ascii=False)}
        except (KeyError, ValueError, TypeError, OSError) as error:
            return {"status": "error", "output": f"MCP error: {type(error).__name__}: {error}"}


def docs_server():
    def lookup(query):
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        return [{**d, "id": d["path"]} for d in search(query)]

    tools = [
        definition("search", ["query"], "Search mounted project documentation."),
        definition("get_version", [], "Read the synthetic billing document version and hash."),
    ]
    for tool in tools:
        tool["inputSchema"] = tool.pop("input_schema")
        tool["annotations"] = {"readOnlyHint": True}
    return MCPClient(
        "docs",
        tools,
        {
            "search": lookup,
            "get_version": lambda: {
                "version": "synthetic-billing-v1",
                "sha256": document("e10/billing.md")["sha256"],
            },
        },
    )


class ToolPool:
    def __init__(self, enabled=True):
        self.enabled, self.clients, self.bindings = enabled, {}, {}
        self.discovery_events = []

    def connect(self, name):
        if not self.enabled or name != "docs":
            raise ValueError("Only the configured docs teaching server can be connected")
        if name not in self.clients:
            self.clients[name] = docs_server()
            self.discovery_events.append(
                {
                    "server": name,
                    "tools": copy.deepcopy(self.clients[name].tools),
                    "transport": "in_process_teaching_stand_in",
                }
            )
        return {"server": name, "tools": [t["name"] for t in self.clients[name].tools]}

    def assemble(self):
        tools = [
            definition(n, fields, "Existing workspace tool.") for n, fields in TOOL_SPEC.items()
        ]
        tools.append(
            definition("search_knowledge", ["query"], "Search mounted project documentation.")
        )
        if self.enabled:
            tools.append(
                definition(
                    "connect_mcp",
                    ["name"],
                    "Connect the configured docs server and discover tools for the next turn.",
                )
            )
        names, bindings = {t["name"] for t in tools}, {}
        for client in self.clients.values():
            for tool in client.tools:
                name = f"mcp__{normalize(client.name)}__{normalize(tool['name'])}"
                if len(name) > 64 or name in names:
                    raise ValueError("Normalized tool name collision or length above 64")
                names.add(name)
                schema = tool.get("inputSchema")
                if not isinstance(schema, dict) or schema.get("type") != "object":
                    raise ValueError("Server tool inputSchema must describe an object")
                tools.append(
                    {
                        "name": name,
                        "description": tool.get("description", ""),
                        "input_schema": copy.deepcopy(schema),
                    }
                )
                bindings[name] = (client, tool["name"])
        self.bindings = bindings
        return tools

    def dispatch(self, call, workspace, approve=lambda n, a: False):
        name = call.get("name", "")
        if name != "connect_mcp" and not name.startswith("mcp__"):
            return previous_dispatch(call, workspace, approve)
        try:
            args = json.loads(call["arguments_json"])
            if not isinstance(args, dict):
                raise TypeError("Arguments must be a JSON object")
            if name == "connect_mcp":
                if set(args) != {"name"}:
                    raise ValueError("connect_mcp requires name only")
                value = self.connect(args["name"])
                return {"decision": "allow", "reason": "configured_discovery"}, {
                    "status": "ok",
                    "output": json.dumps(value),
                }
            self.assemble()
            client, raw = self.bindings[name]
            policy = HOST_POLICY.get((client.name, raw), "confirm")
            if policy != "allow" and not approve(name, args):
                return {"decision": "deny", "reason": "host_mcp_policy"}, {
                    "status": "denied",
                    "output": "External tool not approved",
                }
            # client and raw are fixed local bindings, never overridable argument defaults.
            return {"decision": "allow", "reason": "host_mcp_policy"}, client.call_tool(raw, args)
        except (ValueError, TypeError, KeyError, OSError) as error:
            return {"decision": "not_executed", "reason": "mcp_boundary_error"}, {
                "status": "error",
                "output": str(error),
            }
