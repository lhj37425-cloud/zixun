"""从网上抓取 Trending 和 HelloGitHub（解析用夹具测；这里只负责发请求）。"""

from __future__ import annotations

import httpx

from daily_dissect.projects.hellogithub import latest_hellogithub_volume
from daily_dissect.sources import ProjectSource, load_sources

DEFAULT_TIMEOUT = 30.0
USER_AGENT = "daily-dissect/0.1 (+local learning tool)"


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )


def fetch_text(url: str, *, client: httpx.Client | None = None) -> str:
    own = client is None
    http = client or _client()
    try:
        response = http.get(url)
        response.raise_for_status()
        return response.text
    finally:
        if own:
            http.close()


def _project_source(key: str) -> ProjectSource:
    return next(p for p in load_sources().projects if p.key == key)


def fetch_trending_html(
    source: ProjectSource | None = None,
    *,
    client: httpx.Client | None = None,
) -> str:
    trending = source or _project_source("github_trending")
    if not trending.url:
        raise ValueError("GitHub Trending 缺少 url")
    return fetch_text(trending.url, client=client)


def fetch_hellogithub_issue(
    source: ProjectSource | None = None,
    *,
    client: httpx.Client | None = None,
) -> tuple[int, str]:
    """返回 (期号, 这一期的 Markdown)。"""
    hello = source or _project_source("hellogithub")
    if not hello.rss or not hello.issue_url:
        raise ValueError("HelloGitHub 缺少 rss 或 issue_url")
    rss_text = fetch_text(hello.rss, client=client)
    volume = latest_hellogithub_volume(rss_text)
    if volume is None:
        raise ValueError("HelloGitHub RSS 里没有解析到期号")
    url = hello.issue_url.format(volume=volume)
    return volume, fetch_text(url, client=client)
