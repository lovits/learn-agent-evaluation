import argparse
import json
import sys

from .data import load_cases
from .knowledge import search


def main():
    parser = argparse.ArgumentParser(description="从项目学会 RAG 与 Agent 评测")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="打开本地课程阅读服务")
    serve.add_argument("--port", type=int, default=8000)
    for name in ("replay", "live"):
        sub = commands.add_parser(name)
        sub.add_argument("--sample", choices=[c["id"] for c in load_cases()])
    find = commands.add_parser("search", help="检索当前挂载知识库")
    find.add_argument("query")
    args = parser.parse_args()
    try:
        if args.command == "serve":
            from .web import serve

            serve(args.port)
        elif args.command == "search":
            print(json.dumps(search(args.query), ensure_ascii=False, indent=2))
        else:
            from .runner import run, save

            report = run(args.command, args.sample)
            for row in report["rows"]:
                print(row["id"], {k: v["score"] for k, v in row["metrics"].items()})
            print(report["interpretation"])
            print("已保存：", save(report))
    except (ValueError, RuntimeError, OSError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
