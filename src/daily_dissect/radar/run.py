"""跑一次每日工作流：抓取 → 挑选 → 写入今日数据。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from daily_dissect.llm.client import DeepSeekClient, LLMClient
from daily_dissect.llm.config import LLMConfig
from daily_dissect.news.collect import collect_news
from daily_dissect.paths import CONTENT_DIR, POOL_FILE
from daily_dissect.projects.fetch import fetch_hellogithub_issue, fetch_trending_html
from daily_dissect.projects.pool import load_pool, save_pool
from daily_dissect.projects.sync import ingest_hellogithub, ingest_trending
from daily_dissect.radar.build import build_daily, save_daily
from daily_dissect.sources import load_sources

_MISSING = object()


@dataclass
class RadarReport:
    document: dict
    daily_path: Path
    pool_path: Path
    projects_ok: bool
    news_ok: bool


def _make_client() -> LLMClient | None:
    config = LLMConfig.from_env()
    if not config.enabled:
        return None
    return DeepSeekClient(config)


def run_radar(
    *,
    only: str | None = None,
    client: object = _MISSING,
    today: date | None = None,
    content_dir: Path | None = None,
    pool_path: Path | None = None,
) -> RadarReport:
    """only: None 表示两条线都跑；'projects' / 'news' 只跑一条。

    client 默认按 .env 决定；显式传 None 表示强制关键词兜底。
    """
    root = content_dir or CONTENT_DIR
    projects_dir = root / "projects"
    daily_dir = root / "daily"
    pool_file = pool_path or POOL_FILE
    sources = load_sources()

    if client is _MISSING:
        llm_client: LLMClient | None = _make_client()
    else:
        llm_client = client  # type: ignore[assignment]

    pool = load_pool(pool_file)
    projects_error: str | None = None
    news_error: str | None = None
    news_items = []

    run_projects = only in (None, "projects")
    run_news = only in (None, "news")

    if run_projects:
        try:
            trending_src = next(p for p in sources.projects if p.key == "github_trending")
            hello_src = next(p for p in sources.projects if p.key == "hellogithub")
            if trending_src.enabled:
                html = fetch_trending_html(trending_src)
                ingest_trending(pool, html, today=today)
            if hello_src.enabled:
                volume, markdown = fetch_hellogithub_issue(hello_src)
                ingest_hellogithub(
                    pool,
                    volume=volume,
                    markdown=markdown,
                    skip_sections=hello_src.skip_sections or ("开源书籍",),
                    today=today,
                )
            pool.expire_stale(today=today)
        except Exception as error:
            projects_error = str(error) or error.__class__.__name__
    else:
        projects_error = "本次只跑了资讯线"

    if run_news:
        try:
            fetched = collect_news(sources.news)
            news_items = list(fetched.items)
            enabled = [s for s in sources.news if s.enabled]
            if enabled and not news_items and len(fetched.failures) >= len(enabled):
                news_error = "；".join(f"{f.source}: {f.error}" for f in fetched.failures)
        except Exception as error:
            news_error = str(error) or error.__class__.__name__
    else:
        news_error = "本次只跑了项目线"

    document = build_daily(
        pool=pool,
        news_items=news_items,
        projects_dir=projects_dir,
        client=llm_client,
        today=today,
        projects_error=projects_error,
        news_error=news_error,
    )
    daily_path = save_daily(document, daily_dir)
    pool_saved = save_pool(pool, pool_file)
    return RadarReport(
        document=document,
        daily_path=daily_path,
        pool_path=pool_saved,
        projects_ok=document["projects"]["status"] == "ok",
        news_ok=document["news"]["status"] == "ok",
    )
