"""打分和写说明用到的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectScore:
    repo: str
    relevance: float
    beginner: float

    @property
    def total(self) -> float:
        return round((self.relevance + self.beginner) / 2, 2)


@dataclass(frozen=True)
class NewsGroupScore:
    ids: tuple[int, ...]
    title: str
    category: str
    score: float


@dataclass(frozen=True)
class ProjectBlurb:
    repo: str
    one_liner: str
    solves: str
    for_you: str
    why_dissect: str = ""


@dataclass(frozen=True)
class NewsBlurb:
    id: int
    what: str
    solves: str
    for_you: str
