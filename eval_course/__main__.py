import argparse


def main():
    parser = argparse.ArgumentParser(description="从编程 Agent 学评测")
    parser.add_argument("command", choices=["serve"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    from .web import serve

    serve(args.port)


if __name__ == "__main__":
    main()
