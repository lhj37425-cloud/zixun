"""B-5.4：每完成一步并重新 build，网页进度会更新。"""

from __future__ import annotations

import shutil
from pathlib import Path

from daily_dissect.new_project import create_project
from daily_dissect.web.build import build_site
from daily_dissect.web.content import STEPS, TODO_MARK, load_projects

FIXTURE_CONTENT = Path(__file__).resolve().parent / "fixtures" / "content"


def _complete_step(folder: Path, filename: str, body: str) -> None:
    """写成正式内容：不能再有单独一行「待完成」标记。"""
    (folder / filename).write_text(body.strip() + "\n", encoding="utf-8")
    text = (folder / filename).read_text(encoding="utf-8")
    assert not any(line.strip() == TODO_MARK for line in text.splitlines())


def test_load_projects_marks_steps_by_todo_marker(tmp_path: Path):
    report = create_project("owner/progress-demo", projects_dir=tmp_path)
    folder = report.folder
    project = load_projects(tmp_path)[0]
    assert project.done_count == 0
    assert project.next_step is not None
    assert project.next_step.name == "一页纸"
    assert not project.finished

    _complete_step(
        folder,
        "01-overview.md",
        "# 一页纸：owner/progress-demo\n\n## 解决谁的什么问题\n\n演示进度。"
        "正文可以提到 `<!-- 待完成 -->`，只要它不是单独一行。\n",
    )
    project = load_projects(tmp_path)[0]
    assert project.done_count == 1
    assert project.next_step is not None
    assert project.next_step.name == "流程图"

    for filename, name, _pending in STEPS[1:]:
        _complete_step(folder, filename, f"# {name}\n\n已完成。\n")
    project = load_projects(tmp_path)[0]
    assert project.done_count == 4
    assert project.finished
    assert project.next_step is None


def test_rebuild_updates_progress_on_list_and_detail(tmp_path: Path):
    """从夹具的 2/4 做到 3/4、再做到 4/4，列表与详情页同步变化。"""
    content = tmp_path / "content"
    out = tmp_path / "site"
    shutil.copytree(FIXTURE_CONTENT, content)
    folder = content / "projects" / "example-agent-demo"

    build_site(content_dir=content, out_dir=out)
    list_html = (out / "projects.html").read_text(encoding="utf-8")
    detail = (out / "projects" / "example-agent-demo.html").read_text(encoding="utf-8")
    today = (out / "index.html").read_text(encoding="utf-8")

    assert "完成 2/4" in list_html
    assert "下一步：跑起来" in list_html
    assert list_html.count("is-done") == 2
    assert "完成 2/4" in detail
    assert '<span class="btn-label">继续拆解</span>' in detail
    assert detail.count('class="empty-step"') == 2
    assert "已完成 2/4，看拆解" in today

    _complete_step(
        folder,
        "03-run.md",
        "# 跑起来：example/agent-demo\n\n## 需要准备什么\n\nPython。\n\n"
        "## 安装和运行的每一步\n\n`pip install -e .`\n\n"
        "## 遇到的问题和解决办法\n\n无。\n\n"
        "## 跑起来之后看到了什么\n\n帮助信息。\n",
    )
    build_site(content_dir=content, out_dir=out)
    list_html = (out / "projects.html").read_text(encoding="utf-8")
    detail = (out / "projects" / "example-agent-demo.html").read_text(encoding="utf-8")
    today = (out / "index.html").read_text(encoding="utf-8")

    assert "完成 3/4" in list_html
    assert "下一步：追问" in list_html
    assert list_html.count("is-done") == 3
    assert "完成 3/4" in detail
    assert '<span class="btn-label">继续拆解</span>' in detail
    assert "会从「追问」接着做" in detail
    assert detail.count('class="empty-step"') == 1
    assert "已完成 3/4，看拆解" in today

    _complete_step(
        folder,
        "04-qa.md",
        "# 追问：example/agent-demo\n\n## 问答记录\n\n- Q：核心循环？\n- A：想一步、做一步、看结果。\n\n"
        "## 这次学到的概念\n\nagent 循环。\n",
    )
    build_site(content_dir=content, out_dir=out)
    list_html = (out / "projects.html").read_text(encoding="utf-8")
    detail = (out / "projects" / "example-agent-demo.html").read_text(encoding="utf-8")
    today = (out / "index.html").read_text(encoding="utf-8")

    assert "完成 4/4" in list_html
    assert "已拆完" in list_html
    assert "下一步：" not in list_html
    assert list_html.count("is-done") == 4
    assert "完成 4/4" in detail
    assert '<span class="btn-label">继续拆解</span>' not in detail
    assert detail.count('class="empty-step"') == 0
    assert detail.count("is-done") >= 4
    assert "已拆完" in today
    assert '<span class="btn-label">继续拆解</span>' not in today
