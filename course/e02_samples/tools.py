"""Three named tools; file tools check the path before touching the file."""

from eval_course.runtime import run_bash

TOOLS = {
    "bash": {"command": "Shell command"},
    "read_file": {"path": "Relative file path"},
    "write_file": {"path": "Relative file path", "content": "Text to write"},
}


def file_path(workspace, path):
    target = (workspace / path).resolve()
    if not target.is_relative_to(workspace.resolve()):
        raise PermissionError("Path is outside the workspace")
    return target


def read_file(workspace, path):
    return file_path(workspace, path).read_text()


def write_file(workspace, path, content):
    file_path(workspace, path).write_text(content)
    return "written"


HANDLERS = {"bash": run_bash, "read_file": read_file, "write_file": write_file}


def execute(name, arguments, workspace):
    if (
        name not in HANDLERS
        or set(arguments) != set(TOOLS[name])
        or not all(isinstance(v, str) for v in arguments.values())
    ):
        return {"status": "invalid", "output": "Unknown tool or invalid arguments"}
    try:
        output = HANDLERS[name](workspace=workspace, **arguments)
        status = output["status"] if name == "bash" else "ok"
        return {"status": status, "output": output}
    except PermissionError as error:
        return {"status": "denied", "output": str(error)}
    except (OSError, ValueError) as error:
        return {"status": "error", "output": str(error)}
