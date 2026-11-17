"""A factual input-coverage gate; eligibility is separate from semantic correctness."""

import argparse
import json
from pathlib import Path


def review_context_gate(visible_files, known_project_files):
    tests = {
        p for p in known_project_files if Path(p).name.startswith("test_") and p.endswith(".py")
    }
    missing = sorted(tests - set(visible_files))
    return {
        "passed": not missing,
        "status": "eligible_for_semantic_review" if not missing else "review_context_insufficient",
        "missing_known_test_files": missing,
        "semantic_correctness": None,
        "assumption": "known_project_files is the complete independently collected public project manifest",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases", type=Path, default=Path(__file__).parent / "cases/regression.jsonl"
    )
    args = parser.parse_args()
    rows = []
    for line in args.cases.read_text().splitlines():
        case = json.loads(line)
        rows.append(
            {
                "id": case["id"],
                **review_context_gate(case["visible_files"], case["known_project_files"]),
            }
        )
    print(
        json.dumps(
            {"rows": rows, "all_passed": bool(rows) and all(r["passed"] for r in rows)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(not rows or not all(r["passed"] for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
