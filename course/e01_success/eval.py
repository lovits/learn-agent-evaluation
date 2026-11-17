"""Judge this small file contract independently of the completion claim."""

import ast


def evaluate(run, workspace, case):
    target = workspace / "hello.py"
    try:
        correct_file = target.resolve().is_relative_to(workspace.resolve()) and ast.dump(
            ast.parse(target.read_text())
        ) == ast.dump(ast.parse('print("Hello, World!")'))
    except (OSError, SyntaxError, UnicodeError):
        correct_file = False
    checks = {
        "model_stopped": run["status"] == "finished",
        "output_observed": any(
            e["result"]["exit_code"] == 0 and "Hello, World!" in e["result"]["stdout"]
            for e in run["events"]
        ),
        "requested_file": correct_file,
    }
    return {"passed": all(checks.values()), "checks": checks}
