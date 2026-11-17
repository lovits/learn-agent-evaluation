"""Execute the declared pure-Python teaching subset in a bounded child process."""

import ast
import json
import resource
import sys

SAFE_BUILTINS = {
    f.__name__: f
    for f in (
        type,
        isinstance,
        int,
        bool,
        str,
        float,
        min,
        max,
        sum,
        len,
        range,
        abs,
        all,
        any,
        ValueError,
        TypeError,
        Exception,
    )
}
FORBIDDEN = (
    ast.Import,
    ast.ImportFrom,
    ast.Attribute,
    ast.Global,
    ast.Nonlocal,
    ast.ClassDef,
    ast.AsyncFunctionDef,
    ast.Await,
    ast.With,
    ast.Try,
)


def validate_source(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN):
            raise TypeError(f"Outside declared teaching subset: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Dunder names are outside the declared subset")
    functions = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "shipping_fee"
    ]
    if len(functions) != 1:
        raise ValueError("One top-level shipping_fee definition is required")
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
        raise ValueError("The required function signature must be preserved")
    return tree


def execute(source, cases):
    tree = validate_source(source)
    namespace = {"__builtins__": SAFE_BUILTINS.copy()}
    exec(compile(tree, "submitted-shipping.py", "exec"), namespace)  # noqa: S102
    function = namespace.get("shipping_fee")
    if not callable(function):
        raise TypeError("Missing shipping_fee function")
    results = []
    for case in cases:
        try:
            value = function(**case["arguments"])
            actual = {"value": value, "type": type(value).__name__}
        except Exception as error:  # noqa: BLE001 - submitted program exceptions are outcomes
            actual = {"exception": type(error).__name__}
        results.append(
            {
                "id": case["id"],
                "actual": actual,
                "expected": case["expected"],
                "passed": actual == case["expected"],
            }
        )
    return results


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    memory_bytes = 256 * 1024 * 1024 if sys.platform == "linux" else None
    if memory_bytes is not None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes,) * 2)
    payload = json.load(sys.stdin)
    try:
        results = execute(payload["source"], payload["cases"])
        output = {"status": "scored", "cases": results}
    except Exception as error:  # noqa: BLE001 - unsupported code is unscored, not a zero
        output = {"status": "unscored", "error": f"{type(error).__name__}: {error}"}
    output["limits"] = {"cpu_seconds": 2, "memory_bytes": memory_bytes, "platform": sys.platform}
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
