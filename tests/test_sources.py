"""信源清单：每个源有名称、地址、属于哪条线；增删只改 TOML。"""

from pathlib import Path

from daily_dissect.sources import load_sources

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "config" / "sources.toml"

EXPECTED_NEWS = [
    "量子位",
    "InfoQ 中文",
    "OpenAI",
    "Google AI",
    "Hugging Face",
    "Simon Willison",
    "Latent Space",
    "smol.ai AI News",
    "Hacker News（100 分以上）",
    "GitHub 博客",
    "爱范儿",
    "极客公园",
]


def test_sources_file_exists():
    assert SOURCES.is_file()


def test_each_source_has_name_address_and_line():
    sources = load_sources(SOURCES)

    assert len(sources.projects) == 2
    by_key = {p.key: p for p in sources.projects}

    trending = by_key["github_trending"]
    assert trending.name == "GitHub Trending"
    assert trending.line == "projects"
    assert trending.address == "https://github.com/trending?since=daily"
    assert trending.enabled is True

    hello = by_key["hellogithub"]
    assert hello.name == "HelloGitHub"
    assert hello.line == "projects"
    assert hello.address == "https://hellogithub.com/rss"
    assert hello.issue_url and "{volume}" in hello.issue_url
    assert "开源书籍" in hello.skip_sections
    assert hello.enabled is True

    assert len(sources.news) == 12
    assert [n.name for n in sources.news] == EXPECTED_NEWS
    for item in sources.news:
        assert item.line == "news"
        assert item.address.startswith("http")
        assert item.enabled is True


def test_add_news_source_without_code_change(tmp_path):
    """往 TOML 多加一条资讯源，加载结果立刻变多，不用改 Python。"""
    text = SOURCES.read_text(encoding="utf-8")
    text += '\n[[news]]\nname = "测试源"\nurl = "https://example.com/feed"\nenabled = true\n'
    copy = tmp_path / "sources.toml"
    copy.write_text(text, encoding="utf-8")

    sources = load_sources(copy)
    assert len(sources.news) == 13
    assert sources.news[-1].name == "测试源"
    assert sources.news[-1].address == "https://example.com/feed"
    assert sources.news[-1].line == "news"


def test_disable_source_without_code_change(tmp_path):
    text = SOURCES.read_text(encoding="utf-8").replace(
        'name = "量子位"\nurl = "https://www.qbitai.com/feed"\nenabled = true',
        'name = "量子位"\nurl = "https://www.qbitai.com/feed"\nenabled = false',
        1,
    )
    copy = tmp_path / "sources.toml"
    copy.write_text(text, encoding="utf-8")

    sources = load_sources(copy)
    qbit = next(n for n in sources.news if n.name == "量子位")
    assert qbit.enabled is False
