"""解析 RSS / Atom，并按时间过滤、按链接去重。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any

import feedparser

from daily_dissect.news.models import NewsItem

BEIJING = timezone(timedelta(hours=8))

# 只拉「当前时刻」近 24 小时内的资讯（实时）。
NEWS_WITHIN_HOURS = 24


def _from_struct_time(value: struct_time) -> datetime:
    # feedparser 给的是 UTC 元组
    return datetime(*value[:6], tzinfo=timezone.utc)


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if isinstance(parsed, struct_time):
            return _from_struct_time(parsed)
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, IndexError, OverflowError):
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _entry_url(entry: dict[str, Any]) -> str:
    link = (entry.get("link") or "").strip()
    if link:
        return link
    for item in entry.get("links") or []:
        href = (item.get("href") or "").strip()
        if href:
            return href
    return (entry.get("id") or "").strip()


def parse_feed(text: str, *, source: str) -> list[NewsItem]:
    """把一份 RSS/Atom 文本解析成资讯条目。没有发布时间的条目丢掉。"""
    feed = feedparser.parse(text)
    items: list[NewsItem] = []
    for entry in feed.entries:
        title = " ".join(str(entry.get("title") or "").split()).strip()
        url = _entry_url(entry)
        published = _parse_published(entry)
        if not title or not url or published is None:
            continue
        items.append(
            NewsItem(
                title=title,
                url=url,
                source=source,
                published=published.astimezone(timezone.utc),
            )
        )
    return items


def filter_recent(
    items: list[NewsItem],
    *,
    now: datetime | None = None,
    within_hours: int = NEWS_WITHIN_HOURS,
) -> list[NewsItem]:
    """只保留最近 within_hours 小时内发布的内容（默认 24 小时）。"""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    cutoff = moment - timedelta(hours=within_hours)
    return [item for item in items if item.published >= cutoff]


def dedupe_by_url(items: list[NewsItem]) -> list[NewsItem]:
    """链接完全相同的只留一条（先出现的优先）。"""
    seen: set[str] = set()
    result: list[NewsItem] = []
    for item in items:
        key = item.url.strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
