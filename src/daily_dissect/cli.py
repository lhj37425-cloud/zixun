"""命令入口：uv run dd <命令>。

现在能用的命令：
- build：根据 content/ 生成网页，放到 site/
- open：生成网页，再用浏览器打开今日页（平时直接双击 site/index.html 也一样）
- radar：跑一次每日工作流，挑选并写入今日数据
其余命令（new-project）在后面的 BACKLOG 条目里逐个加上，见 docs/TECH.md 第 7 节。
"""

import argparse
import webbrowser
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

    open_cmd = commands.add_parser("open", help="生成网页，再用浏览器打开今日页")
    open_cmd.add_argument("--out", help="生成到哪个文件夹，默认是项目里的 site/")

    radar = commands.add_parser("radar", help="跑一次每日工作流，写入今日数据")
    radar.add_argument(
        "--only",
        choices=("projects", "news"),
        help="只跑项目线或资讯线",
    )
    return parser


def build_and_report(out: str | None):
    """生成网页，并把结果告诉用户。生成了就返回 BuildReport，没生成返回 None。"""
    from daily_dissect.web.build import SiteDirError, build_site

    try:
        report = build_site(out_dir=Path(out) if out else None)
    except SiteDirError as error:
        print(f"没有生成：{error}")
        return None
    print(f"生成了 {len(report.pages)} 个页面，放在 {report.out_dir}")
    return report


def run_build(out: str | None) -> int:
    return 0 if build_and_report(out) is not None else 1


def run_open(out: str | None) -> int:
    report = build_and_report(out)
    if report is None:
        return 1
    index = (report.out_dir / "index.html").resolve()
    # 网页是普通文件，不用开服务；交给系统打开，效果和双击这个文件一样
    if webbrowser.open(index.as_uri()):
        print(f"已经用浏览器打开今日页：{index}")
    else:
        print(f"没能自动打开浏览器，请双击这个文件：{index}")
    print("以后直接双击这个文件就能看，也可以在浏览器里按 Ctrl+D 把这一页加进收藏夹。")
    return 0


def run_radar(only: str | None) -> int:
    from daily_dissect.radar.run import run_radar as do_radar

    report = do_radar(only=only)
    print(f"今日数据已写入：{report.daily_path}")
    print(f"项目池已更新：{report.pool_path}")
    print(
        "项目线："
        + ("正常" if report.projects_ok else f"失败（{report.document['projects'].get('error')}）")
    )
    print(
        "资讯线："
        + ("正常" if report.news_ok else f"失败（{report.document['news'].get('error')}）")
    )
    llm = report.document.get("llm") or {}
    if llm.get("used"):
        print(f"DeepSeek：调用 {llm.get('calls')} 次（{llm.get('model')}）")
    else:
        print("DeepSeek：未使用（关键词兜底，页面会标没生成解读）")
    return 0 if report.projects_ok or report.news_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        return run_build(args.out)
    if args.command == "open":
        return run_open(args.out)
    if args.command == "radar":
        return run_radar(args.only)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
