"""每天固定 3 次模型调用：项目打分 → 资讯打分 → 写说明；失败则关键词兜底。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from daily_dissect.llm.client import LLMClient, LLMError
from daily_dissect.llm.fallback import (
    empty_news_blurbs,
    empty_project_blurbs,
    score_news_by_keywords,
    score_projects_by_keywords,
)
from daily_dissect.llm.types import NewsBlurb, NewsGroupScore, ProjectBlurb, ProjectScore
from daily_dissect.prompts import load_prompt

CATEGORIES = {"新能力", "新工具", "新产品", "落地案例"}


@dataclass(frozen=True)
class DayLLMResult:
    used: bool
    model: str
    calls: int
    project_scores: tuple[ProjectScore, ...]
    news_groups: tuple[NewsGroupScore, ...]
    project_blurbs: tuple[ProjectBlurb, ...]
    news_blurbs: tuple[NewsBlurb, ...]
    error: str | None = None


def _system(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _parse_project_scores(data: dict[str, Any], repos: list[str]) -> list[ProjectScore]:
    by_repo = {str(row["repo"]): row for row in data.get("scores") or []}
    result: list[ProjectScore] = []
    for repo in repos:
        row = by_repo.get(repo)
        if row is None:
            raise LLMError(f"模型没有返回项目分数：{repo}")
        result.append(
            ProjectScore(
                repo=repo,
                relevance=float(row["relevance"]),
                beginner=float(row["beginner"]),
            )
        )
    return result


def _parse_news_groups(data: dict[str, Any], ids: list[int]) -> list[NewsGroupScore]:
    groups_raw = data.get("groups") or []
    seen: set[int] = set()
    groups: list[NewsGroupScore] = []
    for row in groups_raw:
        group_ids = tuple(int(x) for x in row["ids"])
        category = str(row["category"])
        if category not in CATEGORIES:
            raise LLMError(f"栏目不合法：{category}")
        for gid in group_ids:
            if gid in seen:
                raise LLMError(f"资讯编号重复：{gid}")
            seen.add(gid)
        groups.append(
            NewsGroupScore(
                ids=group_ids,
                title=str(row["title"]),
                category=category,
                score=float(row["score"]),
            )
        )
    missing = set(ids) - seen
    if missing:
        raise LLMError(f"模型漏了资讯编号：{sorted(missing)}")
    extra = seen - set(ids)
    if extra:
        raise LLMError(f"模型多了资讯编号：{sorted(extra)}")
    return groups


def _parse_blurbs(
    data: dict[str, Any],
    *,
    repos: list[str],
    news_ids: list[int],
) -> tuple[list[ProjectBlurb], list[NewsBlurb]]:
    by_repo = {str(row["repo"]): row for row in data.get("projects") or []}
    projects: list[ProjectBlurb] = []
    for index, repo in enumerate(repos):
        row = by_repo.get(repo)
        if row is None:
            raise LLMError(f"模型没有返回项目说明：{repo}")
        why = str(row.get("why_dissect") or "")
        if index > 0:
            why = ""
        projects.append(
            ProjectBlurb(
                repo=repo,
                one_liner=str(row.get("one_liner") or ""),
                solves=str(row.get("solves") or ""),
                for_you=str(row.get("for_you") or ""),
                why_dissect=why,
            )
        )

    by_id = {int(row["id"]): row for row in data.get("news") or []}
    news: list[NewsBlurb] = []
    for news_id in news_ids:
        row = by_id.get(news_id)
        if row is None:
            raise LLMError(f"模型没有返回资讯说明：{news_id}")
        news.append(
            NewsBlurb(
                id=news_id,
                what=str(row.get("what") or ""),
                solves=str(row.get("solves") or ""),
                for_you=str(row.get("for_you") or ""),
            )
        )
    return projects, news


def score_projects_with_llm(
    client: LLMClient,
    candidates: list[dict[str, str]],
) -> list[ProjectScore]:
    profile = load_prompt("profile")
    guide = load_prompt("score_projects")
    payload = [{"repo": c["repo"], "description": c.get("description") or "", "language": c.get("language") or "", "source": c.get("source") or ""} for c in candidates]
    data = client.complete_json(
        system=_system(profile, guide),
        user=json.dumps({"candidates": payload}, ensure_ascii=False),
    )
    return _parse_project_scores(data, [c["repo"] for c in candidates])


def score_news_with_llm(
    client: LLMClient,
    items: list[dict[str, str]],
) -> list[NewsGroupScore]:
    profile = load_prompt("profile")
    guide = load_prompt("score_news")
    payload = [
        {
            "id": int(item["id"]),
            "title": item.get("title") or "",
            "source": item.get("source") or "",
            "url": item.get("url") or "",
        }
        for item in items
    ]
    data = client.complete_json(
        system=_system(profile, guide),
        user=json.dumps({"items": payload}, ensure_ascii=False),
    )
    return _parse_news_groups(data, [int(i["id"]) for i in items])


def write_explanations_with_llm(
    client: LLMClient,
    *,
    projects: list[dict[str, str]],
    news: list[dict[str, str]],
) -> tuple[list[ProjectBlurb], list[NewsBlurb]]:
    profile = load_prompt("profile")
    guide = load_prompt("write")
    data = client.complete_json(
        system=_system(profile, guide),
        user=json.dumps({"projects": projects, "news": news}, ensure_ascii=False),
    )
    return _parse_blurbs(
        data,
        repos=[p["repo"] for p in projects],
        news_ids=[int(n["id"]) for n in news],
    )


def run_day_llm(
    *,
    project_candidates: list[dict[str, str]],
    news_items: list[dict[str, str]],
    selected_projects: list[dict[str, str]],
    selected_news: list[dict[str, str]],
    client: LLMClient | None = None,
) -> DayLLMResult:
    """跑完一天的三次调用。没有 client 或中途失败时走关键词兜底，说明留空。"""
    if client is None:
        return _fallback_result(
            project_candidates,
            news_items,
            selected_projects,
            selected_news,
            error=None,
        )

    try:
        project_scores = score_projects_with_llm(client, project_candidates)
        news_groups = score_news_with_llm(client, news_items)
        project_blurbs, news_blurbs = write_explanations_with_llm(
            client,
            projects=selected_projects,
            news=selected_news,
        )
    except LLMError as error:
        return _fallback_result(
            project_candidates,
            news_items,
            selected_projects,
            selected_news,
            error=str(error),
        )

    return DayLLMResult(
        used=True,
        model=client.model,
        calls=client.call_count,
        project_scores=tuple(project_scores),
        news_groups=tuple(news_groups),
        project_blurbs=tuple(project_blurbs),
        news_blurbs=tuple(news_blurbs),
    )


def _fallback_result(
    project_candidates: list[dict[str, str]],
    news_items: list[dict[str, str]],
    selected_projects: list[dict[str, str]],
    selected_news: list[dict[str, str]],
    *,
    error: str | None,
) -> DayLLMResult:
    return DayLLMResult(
        used=False,
        model="",
        calls=0,
        project_scores=tuple(score_projects_by_keywords(project_candidates)),
        news_groups=tuple(score_news_by_keywords(news_items)),
        project_blurbs=tuple(empty_project_blurbs([p["repo"] for p in selected_projects])),
        news_blurbs=tuple(empty_news_blurbs([int(n["id"]) for n in selected_news])),
        error=error,
    )
