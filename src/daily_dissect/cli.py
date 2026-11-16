"""命令入口。

现在只是骨架：能显示帮助和版本号。具体命令（radar、build、serve、new-project）
在后面的 BACKLOG 条目里逐个加上，见 docs/TECH.md 第 7 节。
"""

import argparse

from daily_dissect import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dd",
        description="今日一拆：每日 AI 前沿精选 + 项目拆解",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
