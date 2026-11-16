"""网页生成器：读取 content/，生成今日、往期、拆解、术语表 4 个页面到 site/。

用法：uv run dd build
生成的页面和 B-3.3 验收过的原型长得一样（原型已删除，在 git 提交 e92b35f 里）；样式和脚本都在 web/static/。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from daily_dissect import paths
from daily_dissect.web.content import load_days, load_glossary, load_projects
from daily_dissect.web.markdown import make_markdown

# 生成器会在 site/ 里放这个标记文件。下次生成时，只有看到它才会清空文件夹，避免误删别的东西
SITE_MARKER = ".dd-site"

NAV = [
    ("today", "今日", "index.html"),
    ("history", "往期", "history.html"),
    ("projects", "拆解", "projects.html"),
    ("glossary", "术语表", "glossary.html"),
]


class SiteDirError(Exception):
    """输出文件夹里有不是生成器产生的文件。为了安全，不清空它。"""


@dataclass
class BuildReport:
    out_dir: Path
    pages: list[Path] = field(default_factory=list)


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(paths.TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.globals["nav"] = NAV
    return env


def prepare_out_dir(out: Path) -> None:
    if out.exists():
        if any(out.iterdir()) and not (out / SITE_MARKER).exists():
            raise SiteDirError(f"{out} 里已经有别的文件，为了安全没有清空它。请换一个空文件夹，或者确认后手动删掉它再生成。")
        shutil.rmtree(out)
    out.mkdir(parents=True)


def build_site(content_dir: Path | None = None, out_dir: Path | None = None) -> BuildReport:
    content = content_dir or paths.CONTENT_DIR
    out = out_dir or paths.SITE_DIR

    md = make_markdown()
    projects = load_projects(content / "projects", md)
    days = load_days(content / "daily", projects)
    terms = load_glossary(content / "glossary.md", projects)

    prepare_out_dir(out)
    env = make_env()
    report = BuildReport(out_dir=out)

    def write(rel_path: str, template: str, **context) -> None:
        # 子文件夹里的页面要用 ../ 才能找到 assets/ 和其他页面
        root = "../" * rel_path.count("/")
        html = env.get_template(template).render(root=root, **context)
        target = out / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        report.pages.append(target)

    write("index.html", "day.html", day=days[0] if days else None, active="today")
    for day in days[1:]:
        write(f"daily/{day.date.isoformat()}.html", "day.html", day=day, active="history")
    write("history.html", "history.html", days=days, active="history")
    write("projects.html", "projects.html", projects=projects, active="projects")
    for project in projects:
        write(f"projects/{project.slug}.html", "project.html", project=project, active="projects")
    write("glossary.html", "glossary.html", terms=terms, active="glossary")

    # 样式、脚本、图标放进 assets/；浏览器固定会去网站根目录找 favicon.ico
    shutil.copytree(paths.STATIC_DIR, out / "assets", ignore=shutil.ignore_patterns("favicon.ico"))
    shutil.copy2(paths.STATIC_DIR / "favicon.ico", out / "favicon.ico")
    (out / SITE_MARKER).write_text("这个文件夹由 dd build 生成，可以随时删掉重新生成。\n", encoding="utf-8")
    return report
