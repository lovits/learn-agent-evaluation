import argparse
import json
import sys

from .knowledge import search


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        from lessons.e01_agent_baseline.code import main as run

        return run(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        from lessons.e01_agent_baseline.eval import main as verify

        return verify(sys.argv[2:])
    parser = argparse.ArgumentParser(description="从编程Agent学评测")
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve")
    server.add_argument("--port", type=int, default=8000)
    find = commands.add_parser("search")
    find.add_argument("query")
    args = parser.parse_args()
    if args.command == "serve":
        from .web import serve

        serve(args.port)
    else:
        print(json.dumps(search(args.query), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
