"""挑选并拼出今日 JSON，写入 content/daily/。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from daily_dissect.llm.client import LLMClient, LLMError
from daily_dissect.llm.fallback import (
    empty_news_blurbs,
    empty_project_blurbs,
    score_news_by_keywords,
    score_projects_by_keywords,
)
from daily_dissect.llm.pipeline import (
    score_news_with_llm,
    score_projects_with_llm,
    write_explanations_with_llm,
)
from daily_dissect.llm.types import NewsBlurb, ProjectBlurb
from daily_dissect.news.models import NewsItem
from daily_dissect.paths import CONTENT_DIR
from daily_dissect.projects.pool import ProjectPool
from daily_dissect.radar.select import (
    RankedNews,
    RankedProject,
    eligible_candidates,
    pick_news,
    pick_projects,
    rank_projects,
    repo_slug,
)

BEIJING = timezone(timedelta(hours=8))


def _iso_now() -> str:
    return datetime.now(BEIJING).replace(microsecond=0).isoformat()


def _today() -> date:
    return datetime.now(BEIJING).date()


@dataclass
class DailyBuildResult:
    document: dict[str, Any]
    path: Path | None = None


def _project_payload(entry) -> dict[str, str]:
    return {
        "repo": entry.repo,
        "description": entry.description or "",
        "language": entry.language or "",
        "source": entry.source or "",
    }


def _news_payload(items: list[NewsItem]) -> list[dict[str, str]]:
    return [
        {
            "id": str(index),
            "title": item.title,
            "source": item.source,
            "url": item.url,
        }
        for index, item in enumerate(items, start=1)
    ]


def _items_by_id(items: list[NewsItem]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for index, item in enumerate(items, start=1):
        result[index] = {
            "id": index,
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "published": item.published.astimezone(BEIJING).isoformat(),
        }
    return result


def _project_card(
    ranked: RankedProject,
    blurb: ProjectBlurb | None,
    *,
    is_pick: bool,
) -> dict[str, Any]:
    entry = ranked.entry
    card = {
        "repo": entry.repo,
        "url": entry.url,
        "slug": repo_slug(entry.repo),
        "source": entry.source,
        "description": entry.description,
        "language": entry.language,
        "stars": entry.stars,
        "stars_today": entry.stars_today,
        "score": ranked.score,
        "one_liner": blurb.one_liner if blurb else "",
        "solves": blurb.solves if blurb else "",
        "for_you": blurb.for_you if blurb else "",
    }
    if is_pick:
        card["why_dissect"] = blurb.why_dissect if blurb else ""
    return card


def _news_card(ranked: RankedNews, blurb: NewsBlurb | None) -> dict[str, Any]:
    item = ranked.item
    return {
        "title": item["title"],
        "url": item["url"],
        "source": item["source"],
        "published": item["published"],
        "category": item["category"],
        "score": item["score"],
        "what": blurb.what if blurb else "",
        "solves": blurb.solves if blurb else "",
        "for_you": blurb.for_you if blurb else "",
    }


def build_daily(
    *,
    pool: ProjectPool,
    news_items: list[NewsItem],
    projects_dir: Path,
    client: LLMClient | None = None,
    today: date | None = None,
    projects_error: str | None = None,
    news_error: str | None = None,
) -> dict[str, Any]:
    """根据项目池和资讯列表，挑选并生成今日文档（不写盘）。"""
    day = today or _today()
    day_text = day.isoformat()

    projects_block: dict[str, Any]
    selected_ranked: list[RankedProject] = []
    if projects_error:
        projects_block = {
            "status": "failed",
            "error": projects_error,
            "pick": None,
            "alternates": [],
        }
    else:
        try:
            eligible = eligible_candidates(pool, projects_dir=projects_dir)
            payloads = [_project_payload(entry) for entry in eligible]
            if client is not None and payloads:
                try:
                    scores = score_projects_with_llm(client, payloads)
                except LLMError:
                    # 模型失败不整线报废，改用关键词兜底（TECH 3.5）
                    scores = score_projects_by_keywords(payloads)
            else:
                scores = score_projects_by_keywords(payloads) if payloads else []
            ranked = rank_projects(eligible, scores)
            selected_ranked = pick_projects(ranked, limit=3)
            projects_block = {
                "status": "ok",
                "error": None,
                "pick": None,
                "alternates": [],
            }
        except Exception as error:
            projects_block = {
                "status": "failed",
                "error": str(error) or error.__class__.__name__,
                "pick": None,
                "alternates": [],
            }
            selected_ranked = []

    news_block: dict[str, Any]
    selected_news: list[RankedNews] = []
    if news_error:
        news_block = {"status": "failed", "error": news_error, "items": []}
    else:
        try:
            payloads = _news_payload(news_items)
            if client is not None and payloads:
                try:
                    groups = score_news_with_llm(client, payloads)
                except LLMError:
                    groups = score_news_by_keywords(payloads)
            else:
                groups = score_news_by_keywords(payloads) if payloads else []
            selected_news = pick_news(groups, _items_by_id(news_items), limit=5, max_per_category=2)
            news_block = {"status": "ok", "error": None, "items": []}
        except Exception as error:
            news_block = {
                "status": "failed",
                "error": str(error) or error.__class__.__name__,
                "items": [],
            }
            selected_news = []

    llm_used = False
    llm_model = ""
    llm_calls = 0
    project_blurbs: list[ProjectBlurb] = empty_project_blurbs(
        [r.entry.repo for r in selected_ranked]
    )
    news_blurbs: list[NewsBlurb] = empty_news_blurbs(
        [int(n.item["id"]) for n in selected_news]
    )

    if client is not None and (selected_ranked or selected_news):
        try:
            project_blurbs, news_blurbs = write_explanations_with_llm(
                client,
                projects=[
                    {
                        "repo": r.entry.repo,
                        "description": r.entry.description or "",
                        "source": r.entry.source or "",
                        "score": str(r.score),
                    }
                    for r in selected_ranked
                ],
                news=[
                    {
                        "id": str(n.item["id"]),
                        "title": n.item["title"],
                        "category": n.item["category"],
                        "source": n.item["source"],
                    }
                    for n in selected_news
                ],
            )
            llm_used = True
            llm_model = client.model
            llm_calls = client.call_count
        except LLMError:
            project_blurbs = empty_project_blurbs([r.entry.repo for r in selected_ranked])
            news_blurbs = empty_news_blurbs([int(n.item["id"]) for n in selected_news])

    if projects_block["status"] == "ok" and selected_ranked:
        blurb_by_repo = {b.repo: b for b in project_blurbs}
        pick = selected_ranked[0]
        projects_block["pick"] = _project_card(
            pick, blurb_by_repo.get(pick.entry.repo), is_pick=True
        )
        projects_block["alternates"] = [
            _project_card(item, blurb_by_repo.get(item.entry.repo), is_pick=False)
            for item in selected_ranked[1:3]
        ]
        # 记入主推，第二天不再推荐
        pool.picked.append({"date": day_text, "repo": pick.entry.repo})

    if news_block["status"] == "ok" and selected_news:
        blurb_by_id = {b.id: b for b in news_blurbs}
        news_block["items"] = [
            _news_card(item, blurb_by_id.get(int(item.item["id"]))) for item in selected_news
        ]

    return {
        "date": day_text,
        "generated_at": _iso_now(),
        "llm": {"used": llm_used, "model": llm_model or None, "calls": llm_calls},
        "projects": projects_block,
        "news": news_block,
    }


def save_daily(document: dict[str, Any], daily_dir: Path | None = None) -> Path:
    folder = daily_dir or (CONTENT_DIR / "daily")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document['date']}.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
