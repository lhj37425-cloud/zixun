"""从打分结果里挑主推/备选，以及最多 5 条资讯。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from daily_dissect.llm.types import NewsGroupScore, ProjectScore
from daily_dissect.projects.models import repo_key
from daily_dissect.projects.pool import PoolEntry, ProjectPool


def repo_slug(repo: str) -> str:
    return repo.strip().lower().replace("/", "-")


def dissected_repo_keys(projects_dir: Path) -> set[str]:
    """content/projects/ 里已经开始拆的项目（读 meta.json 的 repo）。"""
    import json

    keys: set[str] = set()
    if not projects_dir.is_dir():
        return keys
    for meta in projects_dir.glob("*/meta.json"):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        repo = data.get("repo")
        if repo:
            keys.add(repo_key(str(repo)))
    return keys


def picked_repo_keys(pool: ProjectPool) -> set[str]:
    return {repo_key(str(row["repo"])) for row in pool.picked if row.get("repo")}


def eligible_candidates(
    pool: ProjectPool,
    *,
    projects_dir: Path,
) -> list[PoolEntry]:
    """排除当过主推的、以及已经开始拆的。"""
    blocked = picked_repo_keys(pool) | dissected_repo_keys(projects_dir)
    return [entry for key, entry in pool.candidates.items() if key not in blocked]


@dataclass(frozen=True)
class RankedProject:
    entry: PoolEntry
    score: float
    relevance: float
    beginner: float


def rank_projects(
    entries: list[PoolEntry],
    scores: list[ProjectScore],
) -> list[RankedProject]:
    by_repo = {repo_key(s.repo): s for s in scores}
    ranked: list[RankedProject] = []
    for entry in entries:
        score = by_repo.get(repo_key(entry.repo))
        if score is None:
            continue
        ranked.append(
            RankedProject(
                entry=entry,
                score=score.total,
                relevance=score.relevance,
                beginner=score.beginner,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def pick_projects(ranked: list[RankedProject], *, limit: int = 3) -> list[RankedProject]:
    return ranked[:limit]


@dataclass(frozen=True)
class RankedNews:
    group: NewsGroupScore
    item: dict[str, Any]  # 原始资讯：title/url/source/published/id


def pick_news(
    groups: list[NewsGroupScore],
    items_by_id: dict[int, dict[str, Any]],
    *,
    limit: int = 5,
    max_per_category: int = 2,
) -> list[RankedNews]:
    """按分数从高到低选；同一栏目最多 max_per_category 条；同一组只出一条。"""
    ordered = sorted(groups, key=lambda g: g.score, reverse=True)
    counts: dict[str, int] = {}
    picked: list[RankedNews] = []
    for group in ordered:
        if len(picked) >= limit:
            break
        if counts.get(group.category, 0) >= max_per_category:
            continue
        rep_id = group.ids[0]
        item = items_by_id.get(rep_id)
        if item is None:
            continue
        # 合并后的标题优先
        merged = dict(item)
        merged["title"] = group.title
        merged["category"] = group.category
        merged["score"] = group.score
        picked.append(RankedNews(group=group, item=merged))
        counts[group.category] = counts.get(group.category, 0) + 1
    return picked
