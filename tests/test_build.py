"""网页生成器的测试。

用 tests/fixtures/content/ 里固定的一份示例数据生成网页，再检查页面内容和链接。
这份数据是 B-3.2 示例数据的副本，以后 content/ 换成真实数据也不影响这些测试。
"""

import re
from pathlib import Path

import pytest

from daily_dissect.web.build import SITE_MARKER, SiteDirError, build_site
from daily_dissect.web.content import first_paragraph, looks_english, news_time_text
from daily_dissect.web.markdown import make_markdown, render_markdown

FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("build") / "site"
    build_site(content_dir=FIXTURE_CONTENT, out_dir=out)
    return out


def read(site: Path, rel_path: str) -> str:
    return (site / rel_path).read_text(encoding="utf-8")


def test_all_pages_and_assets_are_generated(site):
    expected = [
        "index.html", "history.html", "projects.html", "glossary.html",
        "daily/2026-11-15.html", "projects/example-agent-demo.html",
        "assets/style.css", "assets/app.js", "assets/diagrams.js", "assets/favicon.svg",
        "assets/vendor/mermaid.min.js", "favicon.ico", SITE_MARKER,
    ]
    for rel_path in expected:
        assert (site / rel_path).is_file(), f"缺少 {rel_path}"


def test_today_page(site):
    html = read(site, "index.html")
    assert '<h1 class="brand">' in html
    assert "11 月 16 日 · 周一" in html
    assert "这是示例数据" in html
    assert "今日推荐拆解" in html
    assert "example/agent-demo" in html
    # 主推已经拆了两步：显示进度，按钮写"继续拆解"
    assert "已完成 2/4，看拆解" in html
    assert '<span class="btn-label">继续拆解</span>' in html
    assert html.count('<span class="btn-label">开始拆解</span>') == 2
    assert html.count('class="card news-item"') == 5
    assert "今天 07:30" in html and "昨天 22:40" in html
    assert "解读由 DeepSeek（deepseek-chat）生成，调用 3 次" in html
    assert "没用上 DeepSeek" not in html
    assert 'aria-current="page">今日</a>' in html


def test_past_day_page_shows_failures(site):
    html = read(site, "daily/2026-11-15.html")
    assert '<a href="../history.html">往期</a>' in html
    assert '<h1 class="page-title">11 月 15 日 · 周日</h1>' in html
    assert "当天主推" in html
    assert "这天没用上 DeepSeek，所以没有中文解读" in html
    assert 'class="original-desc" lang="en"' in html
    assert 'class="facts"' not in html
    assert "资讯线这天没抓到" in html
    assert "资讯线失败" in html
    assert "当天 +87" in html
    assert 'href="../assets/style.css"' in html
    assert 'aria-current="page">往期</a>' in html


def test_history_page(site):
    html = read(site, "history.html")
    assert "共 2 天" in html
    assert 'href="index.html">11 月 16 日 · 周一' in html
    assert 'href="daily/2026-11-15.html">11 月 15 日 · 周日' in html
    for text in ["今天", "拆解中 2/4", "资讯 5 条", "资讯线没抓到", "没生成解读"]:
        assert text in html


def test_projects_page(site):
    html = read(site, "projects.html")
    assert "1 个项目" in html
    assert 'href="projects/example-agent-demo.html">example/agent-demo</a>' in html
    assert "下一步：跑起来" in html
    assert "示例项目" in html
    assert html.startswith("<!doctype html>")


def test_project_page(site):
    html = read(site, "projects/example-agent-demo.html")
    # 文件开头的"# 一页纸：……"不显示，## 标题降成 h3
    assert "一页纸：example/agent-demo" not in html
    assert "<h3>解决谁的什么问题</h3>" in html
    assert html.count('<pre class="mermaid">') == 2
    assert '<script src="../assets/vendor/mermaid.min.js"></script>' in html
    # 没拆完：有"继续拆解"按钮，提示从"跑起来"接着做
    assert '<span class="btn-label">继续拆解</span>' in html
    assert 'agent 会从"跑起来"接着做' in html
    assert html.count('class="empty-step"') == 2
    assert html.count("想接着拆，点页面上方的") == 1


def test_glossary_page(site):
    html = read(site, "glossary.html")
    assert html.count('class="card term"') == 7
    assert 'id="term-工作流"' in html
    assert '<a href="projects/example-agent-demo.html">example/agent-demo</a>' in html


def test_internal_links_resolve(site):
    """每个页面里指向本站文件的链接，以及页内锚点，都要能找到。"""
    missing = []
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        ids = set(re.findall(r'id="([^"]+)"', html))
        for ref in re.findall(r'(?:href|src)="([^"]+)"', html):
            if ref.startswith(("http://", "https://", "mailto:")):
                continue
            if ref.startswith("#"):
                if ref[1:] not in ids:
                    missing.append(f"{page.name}: {ref}")
                continue
            if not (page.parent / ref.split("#")[0]).resolve().exists():
                missing.append(f"{page.name}: {ref}")
    assert not missing, missing


def test_build_refuses_to_clear_a_foreign_folder(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("别删我", encoding="utf-8")
    with pytest.raises(SiteDirError):
        build_site(content_dir=FIXTURE_CONTENT, out_dir=tmp_path)
    assert notes.exists()


def test_build_twice_into_the_same_folder(tmp_path):
    out = tmp_path / "site"
    build_site(content_dir=FIXTURE_CONTENT, out_dir=out)
    build_site(content_dir=FIXTURE_CONTENT, out_dir=out)
    assert (out / "index.html").exists()


def test_build_without_any_data(tmp_path):
    out = tmp_path / "site"
    build_site(content_dir=tmp_path / "empty-content", out_dir=out)
    assert "还没有今日数据" in read(out, "index.html")
    assert "还没有拆过项目" in read(out, "projects.html")
    assert "术语表还是空的" in read(out, "glossary.html")


def test_markdown_rendering():
    md = make_markdown()
    text = "# 一页纸：x/y\n\n## 小标题\n\n正文 <script>alert(1)</script>\n\n```mermaid\nflowchart TD\n    A --> B\n```\n"
    html = str(render_markdown(md, text))
    assert "一页纸：x/y" not in html
    assert "<h3>小标题</h3>" in html
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert '<div class="diagram">\n<pre class="mermaid">flowchart TD\n    A --&gt; B</pre>' in html


def test_small_helpers():
    assert looks_english("(sample) Ask questions about your own notes")
    assert not looks_english("一个最小的 agent")
    assert first_paragraph("# 标题\n\n> 引用\n\n## 小标题\n\n第一段。\n\n第二段。") == "第一段。"
    from datetime import date
    assert news_time_text("2026-11-16T07:30:00+08:00", date(2026, 11, 16), True) == "今天 07:30"
    assert news_time_text("2026-11-15T22:40:00+08:00", date(2026, 11, 16), True) == "昨天 22:40"
    assert news_time_text("2026-11-15T22:40:00+08:00", date(2026, 11, 16), False) == "11 月 15 日 22:40"
