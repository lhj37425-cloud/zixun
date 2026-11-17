"""资讯线上用到的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    published: datetime


@dataclass(frozen=True)
class SourceFailure:
    source: str
    error: str
