"""命令行的测试：dd build 和 dd open。

dd open 会打开浏览器。测试里把"打开浏览器"换成一个假的函数，只记下它要打开哪个地址，
不会真的弹出浏览器。网页内容用 tests/fixtures/content/ 里固定的示例数据。
"""

import webbrowser
from pathlib import Path

import pytest

from daily_dissect import cli, paths

FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"


@pytest.fixture(autouse=True)
def fixture_content(monkeypatch):
    # 命令默认读项目里的 content/，测试改成读固定的示例数据
    monkeypatch.setattr(paths, "CONTENT_DIR", FIXTURE_CONTENT)


@pytest.fixture
def opened(monkeypatch) -> list[str]:
    urls: list[str] = []

    def fake_open(url, *args, **kwargs):
        urls.append(url)
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    return urls


def test_build_command(tmp_path, capsys):
    out = tmp_path / "site"
    assert cli.main(["build", "--out", str(out)]) == 0
    assert (out / "index.html").is_file()
    assert "生成了 6 个页面" in capsys.readouterr().out


def test_open_builds_and_opens_today_page(tmp_path, capsys, opened):
    # 文件夹名里带空格和中文，和真实的项目路径"GitHub 项目"一样
    out = tmp_path / "今日 一拆" / "site"
    assert cli.main(["open", "--out", str(out)]) == 0
    index = (out / "index.html").resolve()
    assert index.is_file()
    assert opened == [index.as_uri()]
    assert opened[0].startswith("file:///") and " " not in opened[0]
    text = capsys.readouterr().out
    assert "生成了 6 个页面" in text
    assert f"已经用浏览器打开今日页：{index}" in text
    assert "Ctrl+D" in text


def test_open_says_double_click_when_browser_fails(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(webbrowser, "open", lambda url, *args, **kwargs: False)
    assert cli.main(["open", "--out", str(tmp_path / "site")]) == 0
    assert "没能自动打开浏览器，请双击这个文件" in capsys.readouterr().out


def test_open_does_nothing_when_build_refused(tmp_path, capsys, opened):
    (tmp_path / "notes.txt").write_text("别删我", encoding="utf-8")
    assert cli.main(["open", "--out", str(tmp_path)]) == 1
    assert opened == []
    assert "没有生成" in capsys.readouterr().out
    assert (tmp_path / "notes.txt").exists()
