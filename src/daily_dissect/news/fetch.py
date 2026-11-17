"""逐个抓取资讯源；单个源失败只记原因，不中断。"""

from __future__ import annotations

import httpx

from daily_dissect.news.models import NewsItem, SourceFailure
from daily_dissect.news.parse import parse_feed
from daily_dissect.sources import NewsSource

DEFAULT_TIMEOUT = 20.0
USER_AGENT = "daily-dissect/0.1 (+local learning tool)"


def fetch_feed_text(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    own = client is None
    http = client or httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )
    try:
        response = http.get(url)
        response.raise_for_status()
        return response.text
    finally:
        if own:
            http.close()


def fetch_one_source(
    source: NewsSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[list[NewsItem], SourceFailure | None]:
    """抓取并解析一个源。成功返回 (条目, None)；失败返回 ([], SourceFailure)。"""
    try:
        text = fetch_feed_text(source.url, client=client, timeout=timeout)
        return parse_feed(text, source=source.name), None
    except Exception as error:  # 单个源失败不能拖垮整条资讯线
        return [], SourceFailure(source=source.name, error=str(error) or error.__class__.__name__)
