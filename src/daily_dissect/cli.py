"""命令入口：uv run dd <命令>。

现在能用的命令：
- build：根据 content/ 生成网页，放到 site/
其余命令（radar、serve、new-project）在后面的 BACKLOG 条目里逐个加上，见 docs/TECH.md 第 7 节。
"""

import argparse
from pathlib import Path

from daily_dissect import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dd",
        description="今日一拆：每日 AI 前沿精选 + 项目拆解",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="命令")

    build = commands.add_parser("build", help="根据 content/ 生成网页，放到 site/")
    build.add_argument("--out", help="生成到哪个文件夹，默认是项目里的 site/")
    return parser


def run_build(out: str | None) -> int:
    from daily_dissect.web.build import SiteDirError, build_site

    try:
        report = build_site(out_dir=Path(out) if out else None)
    except SiteDirError as error:
        print(f"没有生成：{error}")
        return 1
    print(f"生成了 {len(report.pages)} 个页面，放在 {report.out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        return run_build(args.out)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
