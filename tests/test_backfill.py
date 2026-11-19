"""日期切换 + 手动抓取：补抓只跑资讯、覆盖前备份、页面控件。"""

import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from daily_dissect import server
from daily_dissect.news.models import NewsItem
from daily_dissect.radar.build import save_daily
from daily_dissect.radar.run import run_radar
from daily_dissect.web.build import build_site

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"


def _news(title: str, url: str) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="量子位",
        published=datetime(2026, 11, 13, 2, 0, tzinfo=timezone.utc),
    )


def test_backfill_runs_news_only_and_keeps_pool(tmp_path: Path):
    content = tmp_path / "content"
    (content / "projects").mkdir(parents=True)
    (content / "daily").mkdir()
    pool_file = tmp_path / "pool.json"
    called: list[str] = []

    def projects_fetcher(pool, sources, today):
        called.append("projects")
        return "不该跑到项目线"

    def news_fetcher(sources):
        return ([_news("那天的一条资讯", "https://ex.com/113")], None)

    report = run_radar(
        content_dir=content,
        pool_path=pool_file,
        client=None,
        today=date(2026, 11, 13),
        backfill=True,
        projects_fetcher=projects_fetcher,
        news_fetcher=news_fetcher,
    )

    assert called == []
    assert report.backfill is True
    assert report.projects_ok is False
    assert "没法回溯" in report.document["projects"]["error"]
    assert report.news_ok is True
    assert report.document["backfill"] is True
    assert (content / "daily" / "2026-11-13.json").is_file()
    # 补抓不改项目池
    assert not pool_file.exists()


def test_save_daily_backs_up_existing_file(tmp_path: Path):
    daily_dir = tmp_path / "daily"
    backup_dir = tmp_path / "backup"
    daily_dir.mkdir()
    old = daily_dir / "2026-11-13.json"
    old.write_text('{"date": "2026-11-13", "old": true}', encoding="utf-8")

    save_daily({"date": "2026-11-13", "new": True}, daily_dir, backup_dir)

    assert json.loads(old.read_text(encoding="utf-8"))["new"] is True
    backups = list(backup_dir.glob("2026-11-13-*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8"))["old"] is True


def test_pages_have_date_picker_and_fetch_button(tmp_path: Path):
    out = tmp_path / "site"
    build_site(content_dir=FIXTURE_CONTENT, out_dir=out)

    for rel in ("index.html", "daily/2026-11-15.html"):
        html = (out / rel).read_text(encoding="utf-8")
        assert 'id="jump-date"' in html
        assert 'id="fetch-day"' in html
        assert 'id="fetch-status"' in html
        assert 'id="day-index"' in html
        assert '"2026-11-16"' in html and '"2026-11-15"' in html


def test_backfill_page_explains_projects_cannot_be_filled(tmp_path: Path):
    content = tmp_path / "content"
    shutil.copytree(FIXTURE_CONTENT, content)
    path = content / "daily" / "2026-11-15.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["backfill"] = True
    data["projects"]["status"] = "failed"
    data["projects"]["error"] = "补抓历史日期：项目线只有此刻的榜单，这一天没法回溯"
    data["projects"]["pick"] = None
    data["projects"]["alternates"] = []
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    out = tmp_path / "site"
    build_site(content_dir=content, out_dir=out)

    html = (out / "daily" / "2026-11-15.html").read_text(encoding="utf-8")
    assert "这一天只能补资讯" in html
    assert "没有那一天的快照" in html


def test_available_days_newest_first(tmp_path: Path, monkeypatch):
    daily = tmp_path / "daily"
    daily.mkdir()
    (daily / "2026-11-13.json").write_text("{}", encoding="utf-8")
    (daily / "2026-11-16.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(server.paths, "CONTENT_DIR", tmp_path)
    assert server.available_days() == ["2026-11-16", "2026-11-13"]


def test_refresh_day_rejects_future_date():
    future = (datetime.now(timezone(timedelta(hours=8))).date()) + timedelta(days=1)
    with pytest.raises(ValueError, match="未来"):
        server.refresh_day(future)


def test_refresh_day_uses_backfill_for_past_dates(monkeypatch):
    called: dict = {}

    class FakeReport:
        projects_ok = True
        news_ok = True
        document = {"projects": {"error": None}, "news": {"items": [], "error": None}}

    def fake_run(**kwargs):
        called.update(kwargs)
        return FakeReport()

    monkeypatch.setattr(server, "run_radar", fake_run)
    monkeypatch.setattr(server, "build_site", lambda: called.setdefault("built", True))

    day = datetime.now(timezone(timedelta(hours=8))).date() - timedelta(days=3)
    result = server.refresh_day(day)

    assert called["today"] == day
    assert called["backfill"] is True
    assert called["built"] is True
    assert result["backfill"] is True
    assert result["ok"] is True
