"""B-4.2：解析 Trending / HelloGitHub，维护项目池。"""

from datetime import date
from pathlib import Path

from daily_dissect.projects.hellogithub import (
    latest_hellogithub_volume,
    parse_hellogithub_issue,
)
from daily_dissect.projects.models import RepoCandidate
from daily_dissect.projects.pool import ProjectPool, load_pool, save_pool
from daily_dissect.projects.sync import ingest_hellogithub, ingest_trending
from daily_dissect.projects.trending import parse_trending_html

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "projects"


def test_parse_trending_html_fields():
    html = (FIXTURES / "trending.html").read_text(encoding="utf-8")
    items = parse_trending_html(html)
    assert len(items) == 3

    first = items[0]
    assert first.repo == "ag-ui-protocol/ag-ui"
    assert first.url == "https://github.com/ag-ui-protocol/ag-ui"
    assert "agent" in first.description.lower()
    assert first.language == "TypeScript"
    assert first.stars == 19654
    assert first.stars_today == 791
    assert first.source == "GitHub Trending"


def test_parse_hellogithub_skips_books_and_non_github():
    md = (FIXTURES / "HelloGitHub127.md").read_text(encoding="utf-8")
    items = parse_hellogithub_issue(md, volume=127, skip_sections=["开源书籍"])
    repos = [i.repo for i in items]

    assert repos == [
        "clainstone/cbirds",
        "Inginnng/EditHere",
        "example/demo-skill",
    ]
    assert all("开源书籍" not in i.source for i in items)
    assert all(i.url.startswith("https://github.com/") for i in items)
    assert items[0].source == "HelloGitHub 第 127 期 · 人工智能"
    assert items[0].description.startswith("在终端里看鸟群")


def test_latest_hellogithub_volume_from_rss():
    rss = (FIXTURES / "hellogithub.rss").read_text(encoding="utf-8")
    assert latest_hellogithub_volume(rss) == 127


def test_pool_dedupes_same_repo():
    pool = ProjectPool()
    html = (FIXTURES / "trending.html").read_text(encoding="utf-8")
    md = (FIXTURES / "HelloGitHub127.md").read_text(encoding="utf-8")

    ingest_trending(pool, html, today=date(2026, 11, 17))
    pool.add_candidates(
        [
            RepoCandidate(
                repo="AG-UI-Protocol/ag-ui",  # 大小写不同，应并到同一条
                url="https://github.com/ag-ui-protocol/ag-ui",
                description="来自 HelloGitHub 的简介",
                source="HelloGitHub 第 127 期 · 人工智能",
            )
        ],
        today=date(2026, 11, 17),
    )
    ingest_hellogithub(
        pool,
        volume=127,
        markdown=md,
        today=date(2026, 11, 17),
        only_if_newer=False,
    )

    assert list(pool.candidates).count("ag-ui-protocol/ag-ui") == 1
    assert len(pool.candidates) == 6  # Trending 3 + HelloGitHub 3
    assert pool.candidates["ag-ui-protocol/ag-ui"].source == "GitHub Trending"
    assert pool.candidates["ag-ui-protocol/ag-ui"].description == "来自 HelloGitHub 的简介"
    assert pool.candidates["ag-ui-protocol/ag-ui"].repo == "ag-ui-protocol/ag-ui"


def test_pool_expires_old_but_keeps_current_hellogithub_volume():
    pool = ProjectPool(hellogithub_volume=127)
    pool.add_candidates(
        [
            RepoCandidate(
                repo="old/project",
                url="https://github.com/old/project",
                description="很久没出现",
                source="GitHub Trending",
            )
        ],
        today=date(2026, 9, 1),
    )
    pool.add_candidates(
        [
            RepoCandidate(
                repo="clainstone/cbirds",
                url="https://github.com/clainstone/cbirds",
                description="本期 HelloGitHub",
                source="HelloGitHub 第 127 期 · 人工智能",
            )
        ],
        today=date(2026, 9, 1),
    )

    removed = pool.expire_stale(today=date(2026, 11, 17), keep_days=30)
    assert removed == 1
    assert "old/project" not in pool.candidates
    assert "clainstone/cbirds" in pool.candidates


def test_save_and_load_pool(tmp_path):
    pool = ProjectPool(hellogithub_volume=127)
    html = (FIXTURES / "trending.html").read_text(encoding="utf-8")
    ingest_trending(pool, html, today=date(2026, 11, 17))
    path = tmp_path / "pool.json"
    save_pool(pool, path)

    loaded = load_pool(path)
    assert loaded.hellogithub_volume == 127
    assert "ag-ui-protocol/ag-ui" in loaded.candidates
    entry = loaded.candidates["ag-ui-protocol/ag-ui"]
    assert entry.stars == 19654
    assert entry.stars_today == 791
    assert entry.first_seen == "2026-11-17"
