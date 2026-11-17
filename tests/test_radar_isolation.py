"""B-4.7：两条线同时运行、互不影响；失败时页面有提示。"""

import threading
from datetime import date, datetime, timezone
from pathlib import Path

from daily_dissect.news.models import NewsItem
from daily_dissect.projects.models import RepoCandidate
from daily_dissect.projects.pool import ProjectPool
from daily_dissect.radar.build import build_daily
from daily_dissect.radar.run import run_radar
from daily_dissect.web.build import build_site


def _entry(repo: str) -> RepoCandidate:
    return RepoCandidate(
        repo=repo,
        url=f"https://github.com/{repo}",
        description=f"{repo} agent demo",
        language="Python",
        source="GitHub Trending",
        stars=10,
        stars_today=1,
    )


def _news(title: str, url: str) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="量子位",
        published=datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc),
    )


def test_both_lines_run_concurrently_even_if_one_fails(tmp_path: Path):
    """两条线一起启动；项目线失败时，资讯线仍能交结果。"""
    barrier = threading.Barrier(2, timeout=3)
    started: list[str] = []

    def projects_fetcher(pool, sources, today):
        started.append("projects")
        barrier.wait()
        return "Trending 模拟失败"

    def news_fetcher(sources):
        started.append("news")
        barrier.wait()
        return ([_news("资讯仍在", "https://ex.com/ok")], None)

    content = tmp_path / "content"
    (content / "projects").mkdir(parents=True)
    (content / "daily").mkdir()
    pool_file = tmp_path / "pool.json"

    # 先往池子里塞候选，项目线抓取失败后挑选阶段仍可能无候选——
    # 这里项目线在 fetch 阶段就失败，pool 为空，项目线 status=failed；资讯线应 ok
    report = run_radar(
        content_dir=content,
        pool_path=pool_file,
        client=None,
        today=date(2026, 11, 17),
        projects_fetcher=projects_fetcher,
        news_fetcher=news_fetcher,
    )

    assert set(started) == {"projects", "news"}
    assert report.projects_ok is False
    assert "模拟失败" in (report.document["projects"]["error"] or "")
    assert report.news_ok is True
    assert report.document["news"]["items"]


def test_news_failure_projects_still_ok(tmp_path: Path):
    pool = ProjectPool()
    pool.add_candidates(
        [_entry("a/agent"), _entry("b/agent"), _entry("c/agent")],
        today=date(2026, 11, 17),
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    doc = build_daily(
        pool=pool,
        news_items=[],
        projects_dir=projects_dir,
        client=None,
        today=date(2026, 11, 17),
        news_error="全部资讯源超时",
    )
    assert doc["news"]["status"] == "failed"
    assert doc["news"]["items"] == []
    assert doc["projects"]["status"] == "ok"
    assert doc["projects"]["pick"] is not None


def test_page_shows_line_failure_callout(tmp_path: Path):
    """用夹具里资讯线失败的那一天，生成网页后应看到红色提示。"""
    from daily_dissect.paths import ROOT

    fixture = ROOT / "tests" / "fixtures" / "content"
    out = tmp_path / "site"
    build_site(content_dir=fixture, out_dir=out)
    # 往期 2026-11-15：资讯线失败、项目线正常
    html = (out / "daily" / "2026-11-15.html").read_text(encoding="utf-8")
    assert "资讯线" in html and "没抓到" in html
    assert "项目线不受影响" in html
    assert "（示例）11 个资讯源都连接超时" in html
