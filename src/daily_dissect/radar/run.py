"""跑一次每日工作流：两条线同时抓取，互不影响，再挑选写入今日数据。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from daily_dissect.llm.client import DeepSeekClient, LLMClient
from daily_dissect.llm.config import LLMConfig
from daily_dissect.news.collect import collect_news
from daily_dissect.news.models import NewsItem
from daily_dissect.paths import CONTENT_DIR, POOL_FILE
from daily_dissect.projects.fetch import fetch_hellogithub_issue, fetch_trending_html
from daily_dissect.projects.pool import ProjectPool, load_pool, save_pool
from daily_dissect.projects.sync import ingest_hellogithub, ingest_trending
from daily_dissect.radar.build import BEIJING, build_daily, save_daily
from daily_dissect.sources import Sources, load_sources

_MISSING = object()

ProjectsFetcher = Callable[[ProjectPool, Sources, date | None], str | None]
NewsFetcher = Callable[[Sources], tuple[list[NewsItem], str | None]]


@dataclass
class RadarReport:
    document: dict
    daily_path: Path
    pool_path: Path
    projects_ok: bool
    news_ok: bool
    backfill: bool = False


def _make_client() -> LLMClient | None:
    config = LLMConfig.from_env()
    if not config.enabled:
        return None
    return DeepSeekClient(config)


def fetch_projects_line(
    pool: ProjectPool,
    sources: Sources,
    today: date | None = None,
) -> str | None:
    """抓取项目线。成功返回 None，失败返回原因（不抛给外层）。"""
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
        return None
    except Exception as error:
        return str(error) or error.__class__.__name__


def fetch_news_line(
    sources: Sources,
    for_date: date | None = None,
) -> tuple[list[NewsItem], str | None]:
    """抓取资讯线。单个源失败不影响整条线；全部失败才记错误。"""
    try:
        fetched = collect_news(sources.news, for_date=for_date)
        items = list(fetched.items)
        enabled = [s for s in sources.news if s.enabled]
        if enabled and not items and len(fetched.failures) >= len(enabled):
            reason = "；".join(f"{f.source}: {f.error}" for f in fetched.failures)
            return [], reason
        return items, None
    except Exception as error:
        return [], str(error) or error.__class__.__name__


def run_radar(
    *,
    only: str | None = None,
    client: object = _MISSING,
    today: date | None = None,
    backfill: bool = False,
    content_dir: Path | None = None,
    pool_path: Path | None = None,
    projects_fetcher: ProjectsFetcher | None = None,
    news_fetcher: NewsFetcher | None = None,
) -> RadarReport:
    """两条线默认同时跑。only='projects'|'news' 时只跑一条。

    backfill=True 表示补抓历史日期：只跑资讯、项目线留一句说明，也不改项目池。
    client 默认按 .env；显式传 None 表示强制关键词兜底。
    测试可注入 projects_fetcher / news_fetcher。
    """
    root = content_dir or CONTENT_DIR
    projects_dir = root / "projects"
    daily_dir = root / "daily"
    pool_file = pool_path or POOL_FILE
    sources = load_sources()

    actual_today = datetime.now(BEIJING).date()
    if today is not None and today > actual_today:
        raise ValueError("不能抓未来的日期")
    # 历史日期：Trending / HelloGitHub 没有那天的快照，只能补资讯
    is_past = backfill and today is not None and today < actual_today
    if backfill and not is_past:
        raise ValueError("补抓只用于历史日期")

    if client is _MISSING:
        llm_client: LLMClient | None = _make_client()
    else:
        llm_client = client  # type: ignore[assignment]

    pool = load_pool(pool_file)
    fetch_projects = projects_fetcher or fetch_projects_line
    if news_fetcher is not None:
        fetch_news = news_fetcher
    elif is_past:
        def fetch_news(selected: Sources) -> tuple[list[NewsItem], str | None]:
            return fetch_news_line(selected, for_date=today)
    else:
        fetch_news = fetch_news_line

    run_projects = only in (None, "projects")
    run_news = only in (None, "news")

    projects_error: str | None = None
    news_error: str | None = None
    news_items: list[NewsItem] = []

    if is_past:
        run_projects = False
        run_news = True
        projects_error = "补抓历史日期：项目线只有此刻的榜单，这一天没法回溯"

    if run_projects and run_news:
        # 同时运行：一条线卡住或失败，不耽误另一条出结果
        with ThreadPoolExecutor(max_workers=2) as pool_exec:
            fut_projects = pool_exec.submit(fetch_projects, pool, sources, today)
            fut_news = pool_exec.submit(fetch_news, sources)
            projects_error = fut_projects.result()
            news_items, news_error = fut_news.result()
    elif run_projects:
        projects_error = fetch_projects(pool, sources, today)
        news_error = "本次只跑了项目线"
    elif run_news:
        news_items, news_error = fetch_news(sources)
        projects_error = projects_error or "本次只跑了资讯线"

    document = build_daily(
        pool=pool,
        news_items=news_items,
        projects_dir=projects_dir,
        client=llm_client,
        today=today,
        projects_error=projects_error,
        news_error=news_error,
        backfill=is_past,
    )
    daily_path = save_daily(document, daily_dir)
    # 补抓历史日期不改项目池：避免污染今天的推荐状态
    pool_saved = pool_file if is_past else save_pool(pool, pool_file)
    return RadarReport(
        document=document,
        daily_path=daily_path,
        pool_path=pool_saved,
        projects_ok=document["projects"]["status"] == "ok",
        news_ok=document["news"]["status"] == "ok",
        backfill=is_past,
    )
