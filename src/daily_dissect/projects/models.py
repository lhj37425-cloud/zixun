"""项目线上用到的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


def repo_key(repo: str) -> str:
    """小写的 作者/项目名，用来去重。"""
    return repo.strip().lower()


@dataclass(frozen=True)
class RepoCandidate:
    """从一个信源解析出来的候选项目。"""

    repo: str
    url: str
    description: str
    source: str
    language: str | None = None
    stars: int | None = None
    stars_today: int | None = None

    @property
    def key(self) -> str:
        return repo_key(self.repo)
