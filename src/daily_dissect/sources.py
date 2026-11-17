"""读取 config/sources.toml。增删信源只改这个文件，不用改代码。"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from daily_dissect.paths import SOURCES_FILE


@dataclass(frozen=True)
class ProjectSource:
    """项目线的一个信源。"""

    key: str
    name: str
    enabled: bool
    url: str | None = None
    rss: str | None = None
    issue_url: str | None = None
    skip_sections: tuple[str, ...] = ()

    @property
    def line(self) -> str:
        return "projects"

    @property
    def address(self) -> str:
        """给人看的主地址：Trending 用网页，HelloGitHub 用 RSS。"""
        if self.url:
            return self.url
        if self.rss:
            return self.rss
        return ""


@dataclass(frozen=True)
class NewsSource:
    """资讯线的一个信源。"""

    name: str
    url: str
    enabled: bool

    @property
    def line(self) -> str:
        return "news"

    @property
    def address(self) -> str:
        return self.url


@dataclass(frozen=True)
class Sources:
    projects: tuple[ProjectSource, ...]
    news: tuple[NewsSource, ...]


def load_sources(path: Path | None = None) -> Sources:
    """从 TOML 读出全部信源。"""
    file = path or SOURCES_FILE
    data = tomllib.loads(file.read_text(encoding="utf-8"))

    projects: list[ProjectSource] = []
    for key, raw in (data.get("projects") or {}).items():
        projects.append(
            ProjectSource(
                key=key,
                name=str(raw["name"]),
                enabled=bool(raw.get("enabled", True)),
                url=raw.get("url"),
                rss=raw.get("rss"),
                issue_url=raw.get("issue_url"),
                skip_sections=tuple(raw.get("skip_sections") or ()),
            )
        )

    news: list[NewsSource] = []
    for raw in data.get("news") or []:
        news.append(
            NewsSource(
                name=str(raw["name"]),
                url=str(raw["url"]),
                enabled=bool(raw.get("enabled", True)),
            )
        )

    return Sources(projects=tuple(projects), news=tuple(news))
