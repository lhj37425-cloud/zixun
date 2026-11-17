"""项目池：去重、合并、过期清理。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from daily_dissect.paths import POOL_FILE
from daily_dissect.projects.models import RepoCandidate, repo_key

BEIJING = timezone(timedelta(hours=8))
KEEP_DAYS = 30


def _today() -> date:
    return datetime.now(BEIJING).date()


def _iso_now() -> str:
    return datetime.now(BEIJING).replace(microsecond=0).isoformat()


@dataclass
class PoolEntry:
    repo: str
    url: str
    description: str
    language: str | None
    source: str
    first_seen: str
    last_seen: str
    stars: int | None = None
    stars_today: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "repo": self.repo,
            "url": self.url,
            "description": self.description,
            "language": self.language,
            "source": self.source,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }
        if self.stars is not None:
            data["stars"] = self.stars
        if self.stars_today is not None:
            data["stars_today"] = self.stars_today
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PoolEntry:
        return cls(
            repo=str(raw["repo"]),
            url=str(raw["url"]),
            description=str(raw.get("description") or ""),
            language=raw.get("language"),
            source=str(raw.get("source") or ""),
            first_seen=str(raw["first_seen"]),
            last_seen=str(raw["last_seen"]),
            stars=raw.get("stars"),
            stars_today=raw.get("stars_today"),
        )


@dataclass
class ProjectPool:
    updated_at: str = ""
    hellogithub_volume: int | None = None
    candidates: dict[str, PoolEntry] = field(default_factory=dict)
    picked: list[dict[str, str]] = field(default_factory=list)

    def add_candidates(
        self,
        items: list[RepoCandidate],
        *,
        today: date | None = None,
    ) -> None:
        """把一批候选放进池子。同一个项目只留一条，刷新 last_seen。"""
        day = (today or _today()).isoformat()
        for item in items:
            key = item.key
            existing = self.candidates.get(key)
            if existing is None:
                self.candidates[key] = PoolEntry(
                    repo=item.repo,
                    url=item.url,
                    description=item.description,
                    language=item.language,
                    source=item.source,
                    first_seen=day,
                    last_seen=day,
                    stars=item.stars,
                    stars_today=item.stars_today,
                )
                continue
            existing.last_seen = day
            if item.description:
                existing.description = item.description
            if item.language:
                existing.language = item.language
            if item.stars is not None:
                existing.stars = item.stars
            if item.stars_today is not None:
                existing.stars_today = item.stars_today
            # 来源保留第一次的；不覆盖 first_seen / source

    def expire_stale(self, *, today: date | None = None, keep_days: int = KEEP_DAYS) -> int:
        """删掉超过 keep_days 没再出现的候选；当前 HelloGitHub 期的项目除外。"""
        day = today or _today()
        cutoff = day - timedelta(days=keep_days)
        volume = self.hellogithub_volume
        keep_prefix = f"HelloGitHub 第 {volume} 期" if volume is not None else None

        removed = 0
        for key, entry in list(self.candidates.items()):
            if keep_prefix and entry.source.startswith(keep_prefix):
                continue
            try:
                last_seen = date.fromisoformat(entry.last_seen)
            except ValueError:
                continue
            if last_seen < cutoff:
                del self.candidates[key]
                removed += 1
        return removed

    def to_dict(self) -> dict[str, Any]:
        return {
            "updated_at": self.updated_at or _iso_now(),
            "hellogithub_volume": self.hellogithub_volume,
            "candidates": {k: v.to_dict() for k, v in sorted(self.candidates.items())},
            "picked": list(self.picked),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProjectPool:
        candidates = {
            repo_key(k): PoolEntry.from_dict(v)
            for k, v in (raw.get("candidates") or {}).items()
        }
        return cls(
            updated_at=str(raw.get("updated_at") or ""),
            hellogithub_volume=raw.get("hellogithub_volume"),
            candidates=candidates,
            picked=list(raw.get("picked") or []),
        )


def load_pool(path: Path | None = None) -> ProjectPool:
    file = path or POOL_FILE
    if not file.is_file():
        return ProjectPool()
    return ProjectPool.from_dict(json.loads(file.read_text(encoding="utf-8")))


def save_pool(pool: ProjectPool, path: Path | None = None) -> Path:
    file = path or POOL_FILE
    file.parent.mkdir(parents=True, exist_ok=True)
    pool.updated_at = _iso_now()
    file.write_text(
        json.dumps(pool.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return file
