"""把抓到的内容写进项目池。"""

from __future__ import annotations

from datetime import date

from daily_dissect.projects.hellogithub import (
    latest_hellogithub_volume,
    parse_hellogithub_issue,
)
from daily_dissect.projects.models import RepoCandidate
from daily_dissect.projects.pool import ProjectPool
from daily_dissect.projects.trending import parse_trending_html


def ingest_trending(
    pool: ProjectPool,
    html: str,
    *,
    today: date | None = None,
) -> list[RepoCandidate]:
    items = parse_trending_html(html)
    pool.add_candidates(items, today=today)
    return items


def ingest_hellogithub(
    pool: ProjectPool,
    *,
    volume: int,
    markdown: str,
    skip_sections: list[str] | tuple[str, ...] = ("开源书籍",),
    today: date | None = None,
    only_if_newer: bool = True,
) -> list[RepoCandidate]:
    """把某一期 HelloGitHub 放进池子。默认只在期号更新时写入。"""
    if (
        only_if_newer
        and pool.hellogithub_volume is not None
        and volume <= pool.hellogithub_volume
    ):
        return []
    items = parse_hellogithub_issue(
        markdown,
        volume=volume,
        skip_sections=skip_sections,
    )
    pool.add_candidates(items, today=today)
    pool.hellogithub_volume = volume
    return items


def ingest_hellogithub_from_rss(
    pool: ProjectPool,
    *,
    rss_text: str,
    markdown: str,
    skip_sections: list[str] | tuple[str, ...] = ("开源书籍",),
    today: date | None = None,
    only_if_newer: bool = True,
) -> tuple[int | None, list[RepoCandidate]]:
    volume = latest_hellogithub_volume(rss_text)
    if volume is None:
        return None, []
    items = ingest_hellogithub(
        pool,
        volume=volume,
        markdown=markdown,
        skip_sections=skip_sections,
        today=today,
        only_if_newer=only_if_newer,
    )
    return volume, items
