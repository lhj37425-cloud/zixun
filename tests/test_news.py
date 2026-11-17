"""B-4.3：资讯线抓取——24 小时过滤、去重、单源失败隔离。"""

from datetime import datetime, timezone
from pathlib import Path

from daily_dissect.news.collect import collect_news
from daily_dissect.news.models import SourceFailure
from daily_dissect.news.parse import dedupe_by_url, filter_recent, parse_feed
from daily_dissect.sources import NewsSource

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "news"
NOW = datetime(2026, 11, 17, 5, 0, tzinfo=timezone.utc)  # 北京时间 13:00


def test_parse_rss_and_atom():
    rss_items = parse_feed(
        (FIXTURES / "qbitai.rss").read_text(encoding="utf-8"),
        source="量子位",
    )
    assert len(rss_items) == 3
    assert rss_items[0].title == "新模型发布"
    assert rss_items[0].source == "量子位"
    assert rss_items[0].published.tzinfo is not None

    atom_items = parse_feed(
        (FIXTURES / "simon.atom").read_text(encoding="utf-8"),
        source="Simon Willison",
    )
    assert len(atom_items) == 3
    assert atom_items[0].url.endswith("/fresh/")


def test_filter_keeps_only_last_24_hours():
    items = parse_feed(
        (FIXTURES / "qbitai.rss").read_text(encoding="utf-8"),
        source="量子位",
    )
    recent = filter_recent(items, now=NOW, within_hours=24)
    urls = [i.url for i in recent]
    assert "https://www.qbitai.com/2026/11/new-model.html" in urls
    assert "https://shared.example.com/same-story" in urls
    assert "https://www.qbitai.com/2026/10/old.html" not in urls


def test_dedupe_by_identical_url():
    rss = parse_feed((FIXTURES / "qbitai.rss").read_text(encoding="utf-8"), source="量子位")
    atom = parse_feed((FIXTURES / "simon.atom").read_text(encoding="utf-8"), source="Simon")
    merged = dedupe_by_url(rss + atom)
    same = [i for i in merged if i.url == "https://shared.example.com/same-story"]
    assert len(same) == 1
    assert same[0].source == "量子位"  # 先出现的保留


def test_collect_news_isolates_source_failure():
    feeds = {
        "https://www.qbitai.com/feed": (FIXTURES / "qbitai.rss").read_text(encoding="utf-8"),
        "https://simonwillison.net/atom/everything/": (FIXTURES / "simon.atom").read_text(
            encoding="utf-8"
        ),
    }
    sources = [
        NewsSource(name="量子位", url="https://www.qbitai.com/feed", enabled=True),
        NewsSource(name="坏掉的源", url="https://broken.example/feed", enabled=True),
        NewsSource(name="Simon Willison", url="https://simonwillison.net/atom/everything/", enabled=True),
        NewsSource(name="已关闭", url="https://off.example/feed", enabled=False),
    ]

    def fake_fetch(source: NewsSource):
        if source.url not in feeds:
            return [], SourceFailure(source=source.name, error="连接超时")
        from daily_dissect.news.parse import parse_feed as parse

        return parse(feeds[source.url], source=source.name), None

    result = collect_news(sources, now=NOW, fetcher=fake_fetch)

    assert any(f.source == "坏掉的源" and "超时" in f.error for f in result.failures)
    assert len(result.failures) == 1
    # 坏源不影响其他源；旧闻被滤掉；重复链接只留一条
    urls = [i.url for i in result.items]
    assert "https://www.qbitai.com/2026/11/new-model.html" in urls
    assert "https://simonwillison.net/2026/Nov/16/fresh/" in urls
    assert urls.count("https://shared.example.com/same-story") == 1
    assert "https://www.qbitai.com/2026/10/old.html" not in urls
    assert all(i.source != "已关闭" for i in result.items)
