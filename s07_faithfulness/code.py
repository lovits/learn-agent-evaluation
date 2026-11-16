"""The lesson entry point. Run from the repository root or through Docker Compose."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_course.runner import run, save


def main():
    parser = argparse.ArgumentParser(description="s07 Faithfulness: real SDK replay or live judge")
    parser.add_argument("--mode", choices=["replay", "live"], default="replay")
    parser.add_argument("--sample", help="Only score this sample ID")
    args = parser.parse_args()
    report = run(args.mode, args.sample)
    for row in report["rows"]:
        scores = {name: value["score"] for name, value in row["metrics"].items()}
        print(row["id"], scores)
    print(report["interpretation"])
    print("已保存：", save(report))


if __name__ == "__main__":
    main()
