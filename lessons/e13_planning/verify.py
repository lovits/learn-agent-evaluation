"""Check both public APIs in the prior bounded pure-Python runner."""

import ast
import hashlib
import re
import tempfile
from pathlib import Path

from lessons.e11_task_completion.verify import probe


class ContractViolation(ValueError):
    pass


def quote_source(core, checkout):
    """Bind the permitted import in-memory, then let the old runner validate all ASTs."""
    tree = ast.parse(checkout)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    if len(imports) != 1:
        raise ValueError("checkout needs exactly the declared shipping import")
    imported = imports[0]
    if (
        not isinstance(imported, ast.ImportFrom)
        or imported.module != "shipping"
        or imported.level != 0
        or [(n.name, n.asname) for n in imported.names] != [("shipping_fee", None)]
    ):
        raise ValueError("Only from shipping import shipping_fee is supported")
    tree.body.remove(imported)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "quote"]
    if len(functions) != 1:
        raise ContractViolation("One quote function is required")
    args = functions[0].args
    if (
        [a.arg for a in args.args] != ["weight_grams", "expedited"]
        or args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or len(args.defaults) != 1
        or not isinstance(args.defaults[0], ast.Constant)
        or args.defaults[0].value is not False
    ):
        raise ContractViolation("The public quote signature changed")
    if not any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "shipping_fee"
        for n in ast.walk(functions[0])
    ):
        raise ContractViolation("quote must call the core shipping_fee")
    core_tree = ast.parse(core)
    for n in ast.walk(core_tree):
        if isinstance(n, ast.FunctionDef) and n.name == "shipping_fee":
            n.name = "_core_shipping_fee"
        elif isinstance(n, ast.Name) and n.id == "shipping_fee":
            n.id = "_core_shipping_fee"
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id == "shipping_fee":
            n.id = "_core_shipping_fee"
    functions[0].name = "shipping_fee"
    return ast.unparse(ast.Module(body=[*core_tree.body, *tree.body], type_ignores=[])) + "\n"


def files_at(workspace, names):
    root = Path(workspace).resolve()
    result = {}
    for name in names:
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise ValueError("Artifact escapes workspace")
        result[name] = path.read_bytes().decode("utf-8") if path.is_file() else None
    return result


def unexpected_project_files(workspace, original_names):
    internal = {
        ".tasks": r"task_[a-f0-9]{8}\.json",
        ".transcripts": r"[a-f0-9]{32}\.txt",
        ".task_outputs": r"[a-f0-9]{32}\.txt",
        ".mailboxes": r"[a-z][a-z0-9_-]{0,31}\.jsonl",
    }
    modules = "|".join(re.escape(Path(n).stem) for n in original_names if n.endswith(".py"))
    internal["__pycache__"] = rf"(?:{modules})\.cpython-\d+(?:\.opt-\d+)?\.pyc"
    unexpected = []
    for path in Path(workspace).rglob("*"):
        relative = path.relative_to(workspace)
        if path.is_symlink() or (
            path.is_file()
            and str(relative) not in original_names
            and not (
                len(relative.parts) == 2
                and relative.parts[0] in internal
                and re.fullmatch(internal[relative.parts[0]], relative.parts[1])
            )
        ):
            unexpected.append(str(relative))
    return sorted(unexpected)


def verify(workspace, case, criteria):
    artifacts = files_at(workspace, case["files"])
    hashes = {
        name: hashlib.sha256(text.encode()).hexdigest() if text is not None else None
        for name, text in artifacts.items()
    }
    protected = {
        name: artifacts[name] == case["files"][name]
        for name in ("test_shipping.py", "test_checkout.py")
    }
    core = probe(Path(workspace), case, criteria)
    if artifacts["checkout.py"] is None or artifacts["shipping.py"] is None:
        return {
            "status": "scored",
            "passed": False,
            "checks": {"implementation_files_exist": False},
            "artifact_hashes": hashes,
            "core": core,
        }
    try:
        combined = quote_source(artifacts["shipping.py"], artifacts["checkout.py"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "shipping.py").write_text(combined)
            (root / "test_shipping.py").write_text(artifacts["test_shipping.py"] or "")
            entry = probe(root, case, criteria)
    except ContractViolation as error:
        return {
            "status": "scored",
            "passed": False,
            "checks": {"quote_contract": False},
            "error": str(error),
            "core": core,
            "artifact_hashes": hashes,
        }
    except (ValueError, TypeError, SyntaxError) as error:
        return {
            "status": "unscored",
            "passed": None,
            "error": str(error),
            "core": core,
            "artifact_hashes": hashes,
        }
    unexpected = unexpected_project_files(workspace, case["files"])
    checks = {
        **protected,
        "core_behavior": core["passed"] is True,
        "quote_behavior": entry["passed"] is True,
        "no_unexpected_project_files": not unexpected,
    }
    return {
        "status": "scored" if core["status"] == entry["status"] == "scored" else "unscored",
        "passed": all(checks.values()) if core["status"] == entry["status"] == "scored" else None,
        "checks": checks,
        "core": core,
        "quote_via_bound_core": entry,
        "quote_binding": "declared import removed and names bound for the restricted runner; not a new Agent execution",
        "artifact_hashes": hashes,
        "unexpected_project_files": unexpected,
    }


def scoped_public_review(workspace, files):
    """Public stop checks for the assigned component, separate from whole-project holdouts."""
    import json

    case = json.loads((Path(__file__).parent / "cases.jsonl").read_text())
    public = [
        {"id": name, "arguments": args, "expected": expected}
        for name, args, expected in [
            ("public-first", {"weight_grams": 1000}, {"value": 600, "type": "int"}),
            ("public-started-step", {"weight_grams": 1001}, {"value": 800, "type": "int"}),
            (
                "public-expedited-cap",
                {"weight_grams": 6000, "expedited": True},
                {"value": 2000, "type": "int"},
            ),
            ("public-over-cap", {"weight_grams": 6001}, {"exception": "ValueError"}),
            ("public-under-range", {"weight_grams": 0}, {"exception": "ValueError"}),
            ("public-weight-bool", {"weight_grams": True}, {"exception": "TypeError"}),
            (
                "public-expedited-type",
                {"weight_grams": 1000, "expedited": "yes"},
                {"exception": "TypeError"},
            ),
            (
                "public-type-before-range",
                {"weight_grams": 0, "expedited": "yes"},
                {"exception": "TypeError"},
            ),
        ]
    ]
    if "checkout.py" in files:
        evidence = verify(workspace, case, public)
    else:
        evidence = probe(Path(workspace), case, public)
        actual = files_at(workspace, ["test_shipping.py", "test_checkout.py"])
        retained = all(actual[n] == case["files"][n] for n in actual)
        evidence["protected_test_bytes_preserved"] = retained
        if evidence["status"] == "scored":
            evidence["passed"] = evidence["passed"] and retained
    return {
        "scope": files,
        "public_cases_per_api": len(public),
        "status": evidence["status"],
        "passed": evidence["passed"],
        "evidence": evidence,
        "not_whole_project_acceptance": True,
        "artifact_hashes": {
            name: hashlib.sha256((Path(workspace) / name).read_bytes()).hexdigest()
            for name in case["files"]
        },
        "original_test_hashes": {
            name: hashlib.sha256(case["files"][name].encode()).hexdigest()
            for name in ("test_shipping.py", "test_checkout.py")
        },
    }
