"""项目线：抓取 Trending / HelloGitHub，维护项目池。"""

from daily_dissect.projects.hellogithub import (
    latest_hellogithub_volume,
    parse_hellogithub_issue,
)
from daily_dissect.projects.models import RepoCandidate
from daily_dissect.projects.pool import ProjectPool, load_pool, save_pool
from daily_dissect.projects.sync import ingest_hellogithub, ingest_trending
from daily_dissect.projects.trending import parse_trending_html

__all__ = [
    "ProjectPool",
    "RepoCandidate",
    "ingest_hellogithub",
    "ingest_trending",
    "latest_hellogithub_volume",
    "load_pool",
    "parse_hellogithub_issue",
    "parse_trending_html",
    "save_pool",
]
