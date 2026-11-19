"""命令入口：uv run dd <命令>。

现在能用的命令：
- build：根据 content/ 生成网页，放到 site/
- open：生成网页，再用浏览器打开今日页（平时直接双击 site/index.html 也一样）
- radar：跑一次每日工作流，挑选并写入今日数据
- update：radar + build（双击 scripts/update*.bat 会调用它）
- serve：在本机起一个小服务，网页里可以按日期手动抓取
- new-project：为要拆的仓库建 content/projects/ 文件夹和四步模板
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

    update = commands.add_parser("update", help="跑每日工作流并重新生成网页（给双击脚本用）")
    update.add_argument(
        "--only",
        choices=("projects", "news"),
        help="只跑项目线或资讯线",
    )
    update.add_argument(
        "--open",
        action="store_true",
        help="完成后用浏览器打开今日页",
    )

    serve_cmd = commands.add_parser(
        "serve",
        help="在本机起一个小服务：浏览网页，并手动按日期抓取",
    )
    serve_cmd.add_argument("--port", type=int, default=8765, help="端口，默认 8765")
    serve_cmd.add_argument(
        "--open",
        action="store_true",
        help="启动后用浏览器打开",
    )

    new_project = commands.add_parser(
        "new-project",
        help="为要拆的项目建文件夹和四步模板",
    )
    new_project.add_argument(
        "repo",
        help="仓库地址，例如 https://github.com/作者/项目名 或 作者/项目名",
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


def run_new_project(repo: str) -> int:
    from daily_dissect.new_project import NewProjectError, create_project

    try:
        report = create_project(repo)
    except NewProjectError as error:
        print(f"没有建文件夹：{error}")
        return 1
    print(f"已建好拆解文件夹：{report.folder}")
    print(f"仓库：{report.repo}")
    print(f"开始日期：{report.started}")
    print("四步模板都带着「待完成」标记；按 prompts/dissect.md 往下写即可。")
    print("写完一步后运行：uv run dd build")
    return 0


def run_update(only: str | None, open_browser: bool) -> int:
    """先抓取写入今日数据，再生成网页；可选打开浏览器。"""
    code = run_radar(only)
    if code != 0:
        print("抓取没有成功产出可用数据，网页仍会按现有 content/ 生成。")
    if open_browser:
        open_code = run_open(None)
        return open_code if open_code != 0 else code
    build_code = run_build(None)
    if build_code != 0:
        return build_code
    print("更新完成。双击 site\\index.html 或运行 uv run dd open 就能看。")
    return code


def run_serve(port: int, open_browser: bool) -> int:
    from daily_dissect.server import serve

    try:
        serve(port=port, open_browser=open_browser)
    except OSError as error:
        print(f"没能启动本地服务：{error}")
        print("端口可能被占用了，可以换一个：uv run dd serve --port 8766")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        return run_build(args.out)
    if args.command == "open":
        return run_open(args.out)
    if args.command == "radar":
        return run_radar(args.only)
    if args.command == "update":
        return run_update(args.only, args.open)
    if args.command == "new-project":
        return run_new_project(args.repo)
    if args.command == "serve":
        return run_serve(args.port, args.open)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
