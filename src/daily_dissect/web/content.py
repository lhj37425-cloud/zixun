"""读取 content/ 里的数据，整理成页面要用的样子。

数据格式见 docs/TECH.md 第 5 节。这里只读，不写。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from markdown_it import MarkdownIt
from markupsafe import Markup, escape

from daily_dissect.web.markdown import has_mermaid, make_markdown, render_markdown

# 拆解四步：文件名、名字、这一步还没做时页面上的说明
STEPS = [
    ("01-overview.md", "一页纸", "这一步还没做。agent 会先写一页纸：它解决谁的什么问题、为什么是现在、用户以前怎么解决、它好在哪。"),
    ("02-flows.md", "流程图", "这一步还没做。agent 会画两张流程图：一张是用户的操作流程，一张是 agent（或系统）内部的流程。"),
    ("03-run.md", "跑起来", "这一步还没做。agent 会带你在自己电脑上把项目装好、跑通，每条命令都讲清楚。"),
    ("04-qa.md", "追问", "这一步还没做。你在 agent 里哪里不懂问哪里，问答记录会出现在这里，以后回看都还在。"),
]
TODO_MARK = "<!-- 待完成 -->"

CATEGORIES = ["新能力", "新工具", "新产品", "落地案例"]
CATEGORY_CLASS = {"新能力": "tag-ability", "新工具": "tag-tool", "新产品": "tag-product", "落地案例": "tag-case"}
WEEKDAYS = "一二三四五六日"


def slug_of(repo: str) -> str:
    """TECH 5.3：仓库名转成小写，"/" 换成 "-"。"""
    return repo.lower().replace("/", "-")


# B-5.3 定稿：按钮复制的整句指令。改这里等于改产品约定，网页与测试会一起变。
DISSECT_INSTRUCTION_TEMPLATE = "请按照 prompts/dissect.md 拆解 {url}"


def dissect_instruction(url: str) -> str:
    """「开始拆解」「继续拆解」复制到剪贴板的那句话（PRD F4 / TECH 3.7）。"""
    return DISSECT_INSTRUCTION_TEMPLATE.format(url=url.strip())


def day_text(d: date) -> str:
    return f"{d.month} 月 {d.day} 日"


def weekday_text(d: date) -> str:
    return "周" + WEEKDAYS[d.weekday()]


def looks_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if c.isascii()) / len(letters) > 0.6


def first_paragraph(markdown_text: str) -> str:
    """取一页纸里的第一段正文，用在拆解列表的简介上。"""
    paragraph: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ">", "<!--", "```", "- ", "* ", "|")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    return re.sub(r"[*_`]", "", "".join(paragraph))


# ---------- 拆解项目 ----------


@dataclass
class Step:
    number: int
    name: str
    done: bool
    pending_text: str
    html: Markup = field(default_factory=Markup)
    has_mermaid: bool = False


@dataclass
class Project:
    slug: str
    repo: str
    url: str
    started: date
    sample: bool
    steps: list[Step]
    summary: str

    @property
    def done_count(self) -> int:
        return sum(1 for step in self.steps if step.done)

    @property
    def finished(self) -> bool:
        return self.done_count == len(self.steps)

    @property
    def next_step(self) -> Step | None:
        return next((step for step in self.steps if not step.done), None)

    @property
    def has_mermaid(self) -> bool:
        return any(step.has_mermaid for step in self.steps)

    @property
    def instruction(self) -> str:
        return dissect_instruction(self.url)

    @property
    def started_text(self) -> str:
        return day_text(self.started)


def load_projects(projects_dir: Path, md: MarkdownIt | None = None) -> list[Project]:
    """读取 content/projects/ 下的每个项目文件夹，最近开始的排在前面。"""
    md = md or make_markdown()
    if not projects_dir.exists():
        return []

    projects = []
    for folder in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        meta_path = folder / "meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        steps = []
        overview_text = ""
        for number, (filename, name, pending_text) in enumerate(STEPS, start=1):
            path = folder / filename
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            # 整行等于标记才算未完成；正文里提到「待完成」不算。
            has_todo_line = any(line.strip() == TODO_MARK for line in text.splitlines())
            done = bool(text.strip()) and not has_todo_line
            if number == 1 and done:
                overview_text = text
            steps.append(
                Step(
                    number=number,
                    name=name,
                    done=done,
                    pending_text=pending_text,
                    html=render_markdown(md, text) if done else Markup(""),
                    has_mermaid=done and has_mermaid(text),
                )
            )

        projects.append(
            Project(
                slug=folder.name,
                repo=meta["repo"],
                url=meta["url"],
                started=date.fromisoformat(meta["started"]),
                sample=bool(meta.get("sample")),
                steps=steps,
                summary=first_paragraph(overview_text),
            )
        )

    projects.sort(key=lambda p: (p.started, p.slug), reverse=True)
    return projects


# ---------- 每天的今日数据 ----------


@dataclass
class ProjectCard:
    repo: str
    url: str
    slug: str
    source: str
    description: str
    description_lang: str
    language: str
    stars_text: str
    stars_today_text: str
    one_liner: str
    solves: str
    for_you: str
    why_dissect: str
    progress: Project | None
    instruction: str

    @property
    def has_insight(self) -> bool:
        """有没有 DeepSeek 写的中文解读。"""
        return bool(self.one_liner)

    @property
    def finished(self) -> bool:
        return bool(self.progress and self.progress.finished)

    @property
    def button_label(self) -> str:
        return "继续拆解" if self.progress and not self.progress.finished else "开始拆解"


@dataclass
class NewsCard:
    title: str
    url: str
    source: str
    time_text: str
    category: str
    tag_class: str
    what: str
    solves: str
    for_you: str

    @property
    def has_insight(self) -> bool:
        return bool(self.what or self.solves or self.for_you)


@dataclass
class Badge:
    cls: str
    icon: str
    text: str


@dataclass
class DayPage:
    date: date
    is_latest: bool
    sample: bool
    llm_used: bool
    llm_model: str
    llm_calls: int
    generated_at: datetime | None
    projects_ok: bool
    projects_error: str
    pick: ProjectCard | None
    alternates: list[ProjectCard]
    news_ok: bool
    news_error: str
    news: list[NewsCard]

    @property
    def date_text(self) -> str:
        return day_text(self.date)

    @property
    def weekday(self) -> str:
        return weekday_text(self.date)

    @property
    def when(self) -> str:
        return "今天" if self.is_latest else "这天"

    @property
    def pick_badge(self) -> str:
        return "今日推荐拆解" if self.is_latest else "当天主推"

    @property
    def href(self) -> str:
        """往期列表里点进去的地址。"""
        return "index.html" if self.is_latest else f"daily/{self.date.isoformat()}.html"

    @property
    def projects_meta(self) -> str:
        if not self.projects_ok:
            return f"{self.when}没抓到"
        if self.alternates:
            return f"1 个主推 · {len(self.alternates)} 个备选"
        return "1 个主推"

    @property
    def news_meta(self) -> str:
        if not self.news_ok:
            return f"{self.when}没抓到"
        if not self.news:
            return "没有符合条件的资讯"
        counts = Counter(item.category for item in self.news)
        parts = [f"{name} {counts[name]}" for name in CATEGORIES if counts[name]]
        return " · ".join([f"{len(self.news)} 条", *parts])

    @property
    def updated_text(self) -> str:
        parts = []
        if self.generated_at:
            parts.append(f"{day_text(self.generated_at.date())} {self.generated_at:%H:%M} 更新")
        if self.llm_used:
            parts.append(f"解读由 DeepSeek（{self.llm_model}）生成，调用 {self.llm_calls} 次")
        else:
            parts.append("没用上 DeepSeek，只有原始简介")
        return " · ".join(parts)

    @property
    def history_text(self) -> Markup:
        if not self.projects_ok or not self.pick:
            return Markup("这天项目线没抓到")
        summary = self.pick.one_liner or self.pick.description
        return Markup("主推 <code>{}</code>：{}").format(self.pick.repo, summary)

    @property
    def history_badges(self) -> list[Badge]:
        badges = []
        if self.is_latest:
            badges.append(Badge("badge-accent", "", "今天"))
        if self.projects_ok and self.pick and self.pick.progress:
            progress = self.pick.progress
            text = "已拆完" if progress.finished else f"拆解中 {progress.done_count}/4"
            badges.append(Badge("badge-done", "check", text))
        if not self.projects_ok:
            badges.append(Badge("badge-danger", "x-circle", "项目线没抓到"))
        if self.news_ok:
            badges.append(Badge("", "", f"资讯 {len(self.news)} 条"))
        else:
            badges.append(Badge("badge-danger", "x-circle", "资讯线没抓到"))
        if not self.llm_used:
            badges.append(Badge("badge-warn", "info", "没生成解读"))
        return badges


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def news_time_text(published: str, page_date: date, is_latest: bool) -> str:
    moment = _parse_datetime(published)
    if moment is None:
        return ""
    day = moment.date()
    if is_latest and day == page_date:
        return f"今天 {moment:%H:%M}"
    if is_latest and day == page_date - timedelta(days=1):
        return f"昨天 {moment:%H:%M}"
    return f"{day_text(day)} {moment:%H:%M}"


def _project_card(item: dict, is_latest: bool, projects_by_slug: dict[str, Project]) -> ProjectCard:
    slug = item.get("slug") or slug_of(item["repo"])
    description = item.get("description") or ""
    stars = item.get("stars")
    stars_today = item.get("stars_today") or 0
    return ProjectCard(
        repo=item["repo"],
        url=item["url"],
        slug=slug,
        source=item.get("source") or "",
        description=description,
        description_lang="en" if looks_english(description) else "",
        language=item.get("language") or "",
        stars_text=f"{stars:,}" if isinstance(stars, int) else "",
        stars_today_text=f"{'今天' if is_latest else '当天'} +{stars_today:,}" if stars_today > 0 else "",
        one_liner=item.get("one_liner") or "",
        solves=item.get("solves") or "",
        for_you=item.get("for_you") or "",
        why_dissect=item.get("why_dissect") or "",
        progress=projects_by_slug.get(slug),
        instruction=dissect_instruction(item["url"]),
    )


def _news_card(item: dict, page_date: date, is_latest: bool) -> NewsCard:
    category = item.get("category") or ""
    return NewsCard(
        title=item["title"],
        url=item["url"],
        source=item.get("source") or "",
        time_text=news_time_text(item.get("published") or "", page_date, is_latest),
        category=category,
        tag_class=CATEGORY_CLASS.get(category, ""),
        what=item.get("what") or "",
        solves=item.get("solves") or "",
        for_you=item.get("for_you") or "",
    )


def load_days(daily_dir: Path, projects: list[Project]) -> list[DayPage]:
    """读取 content/daily/ 下每天的数据，最新的一天排在最前面。"""
    if not daily_dir.exists():
        return []
    files = sorted(daily_dir.glob("*.json"), reverse=True)
    projects_by_slug = {project.slug: project for project in projects}

    days = []
    for index, path in enumerate(files):
        data = json.loads(path.read_text(encoding="utf-8"))
        page_date = date.fromisoformat(data["date"])
        is_latest = index == 0
        projects_line, news_line, llm = data["projects"], data["news"], data.get("llm") or {}
        projects_ok = projects_line.get("status") == "ok"
        news_ok = news_line.get("status") == "ok"
        days.append(
            DayPage(
                date=page_date,
                is_latest=is_latest,
                sample=bool(data.get("sample")),
                llm_used=bool(llm.get("used")),
                llm_model=llm.get("model") or "",
                llm_calls=int(llm.get("calls") or 0),
                generated_at=_parse_datetime(data.get("generated_at")),
                projects_ok=projects_ok,
                projects_error=projects_line.get("error") or "",
                pick=_project_card(projects_line["pick"], is_latest, projects_by_slug) if projects_ok and projects_line.get("pick") else None,
                alternates=[_project_card(alt, is_latest, projects_by_slug) for alt in projects_line.get("alternates") or []] if projects_ok else [],
                news_ok=news_ok,
                news_error=news_line.get("error") or "",
                news=[_news_card(item, page_date, is_latest) for item in news_line.get("items") or []] if news_ok else [],
            )
        )
    return days


# ---------- 术语表 ----------


@dataclass
class Term:
    name: str
    anchor: str
    definition: str
    source_html: Markup


def load_glossary(path: Path, projects: list[Project]) -> list[Term]:
    """读取 content/glossary.md：每个"## 术语"是一条，"- 第一次出现："那一行是来源。"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    terms = []
    for entry in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        name, _, body = entry.partition("\n")
        name = name.strip()
        definition_lines, source = [], ""
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- 第一次出现："):
                source = stripped.removeprefix("- 第一次出现：")
            elif stripped:
                definition_lines.append(stripped)

        source_html = escape(source)
        for project in projects:
            # 来源里提到了拆过的项目，就链接到它的拆解页
            linked = Markup('<a href="projects/{}.html">{}</a>').format(project.slug, project.repo)
            source_html = Markup(str(source_html).replace(str(escape(project.repo)), str(linked), 1))

        terms.append(
            Term(
                name=name,
                anchor="term-" + re.sub(r"\s+", "-", name),
                definition="".join(definition_lines),
                source_html=source_html,
            )
        )
    return terms
