"""按信源清单抓取全部资讯源，过滤、去重，汇总失败原因。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from daily_dissect.news.fetch import DEFAULT_TIMEOUT, USER_AGENT, fetch_one_source
from daily_dissect.news.models import NewsItem, SourceFailure
from daily_dissect.news.parse import NEWS_WITHIN_HOURS, dedupe_by_url, filter_recent
from daily_dissect.sources import NewsSource, load_sources

Fetcher = Callable[[NewsSource], tuple[list[NewsItem], SourceFailure | None]]


@dataclass(frozen=True)
class NewsFetchResult:
    items: tuple[NewsItem, ...]
    failures: tuple[SourceFailure, ...]


def collect_news(
    sources: list[NewsSource] | tuple[NewsSource, ...] | None = None,
    *,
    now: datetime | None = None,
    within_hours: int = NEWS_WITHIN_HOURS,
    timeout: float = DEFAULT_TIMEOUT,
    fetcher: Fetcher | None = None,
    client: httpx.Client | None = None,
) -> NewsFetchResult:
    """抓取启用的资讯源。一个源失败不影响其他源。"""
    selected = list(sources) if sources is not None else list(load_sources().news)
    selected = [s for s in selected if s.enabled]

    own_client = False
    http = client
    if fetcher is None and http is None:
        http = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        own_client = True

    items: list[NewsItem] = []
    failures: list[SourceFailure] = []
    try:
        for source in selected:
            if fetcher is not None:
                batch, failure = fetcher(source)
            else:
                batch, failure = fetch_one_source(source, client=http, timeout=timeout)
            items.extend(batch)
            if failure is not None:
                failures.append(failure)
    finally:
        if own_client and http is not None:
            http.close()

    moment = now or datetime.now(timezone.utc)
    recent = filter_recent(items, now=moment, within_hours=within_hours)
    unique = dedupe_by_url(recent)
    # 新的在前，方便后面挑选
    unique.sort(key=lambda item: item.published, reverse=True)
    return NewsFetchResult(items=tuple(unique), failures=tuple(failures))
