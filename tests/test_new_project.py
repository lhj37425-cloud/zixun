"""B-5.2：dd new-project 建文件夹和四步模板。"""

from datetime import date
from pathlib import Path

import pytest

from daily_dissect import cli
from daily_dissect.new_project import NewProjectError, create_project, parse_repo_ref
from daily_dissect.web.content import STEPS, TODO_MARK, load_projects, slug_of


@pytest.mark.parametrize(
    "raw, repo",
    [
        ("https://github.com/LearnPrompt/ai-news-radar", "LearnPrompt/ai-news-radar"),
        ("https://github.com/LearnPrompt/ai-news-radar.git", "LearnPrompt/ai-news-radar"),
        ("github.com/foo/bar/", "foo/bar"),
        ("foo/bar", "foo/bar"),
        ("git@github.com:foo/bar.git", "foo/bar"),
    ],
)
def test_parse_repo_ref_accepts_common_forms(raw, repo):
    got_repo, url = parse_repo_ref(raw)
    assert got_repo == repo
    assert url == f"https://github.com/{repo}"


@pytest.mark.parametrize(
    "raw",
    ["", "not-a-repo", "https://gitlab.com/a/b", "https://github.com/only-owner"],
)
def test_parse_repo_ref_rejects_bad_input(raw):
    with pytest.raises(NewProjectError):
        parse_repo_ref(raw)


def test_create_project_writes_meta_and_pending_steps(tmp_path: Path):
    report = create_project(
        "https://github.com/Acme/Demo-App",
        projects_dir=tmp_path,
        started=date(2026, 11, 18),
    )
    assert report.slug == "acme-demo-app"
    assert report.folder == tmp_path / "acme-demo-app"
    assert report.folder.is_dir()

    meta = (report.folder / "meta.json").read_text(encoding="utf-8")
    assert '"repo": "Acme/Demo-App"' in meta
    assert '"url": "https://github.com/Acme/Demo-App"' in meta
    assert '"started": "2026-11-18"' in meta
    assert "sample" not in meta

    for filename, _name, _pending in STEPS:
        text = (report.folder / filename).read_text(encoding="utf-8")
        assert text.startswith(TODO_MARK)
        assert f"：Acme/Demo-App" in text or f": Acme/Demo-App" in text or "Acme/Demo-App" in text

    projects = load_projects(tmp_path)
    assert len(projects) == 1
    project = projects[0]
    assert project.slug == slug_of("Acme/Demo-App")
    assert project.done_count == 0
    assert project.next_step is not None
    assert project.next_step.name == "一页纸"


def test_create_project_refuses_existing_folder(tmp_path: Path):
    create_project("owner/repo", projects_dir=tmp_path, started=date(2026, 11, 18))
    with pytest.raises(NewProjectError, match="已经存在"):
        create_project("https://github.com/owner/repo", projects_dir=tmp_path)


def test_cli_new_project_command(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr("daily_dissect.new_project.CONTENT_DIR", tmp_path)
    (tmp_path / "projects").mkdir()
    assert cli.main(["new-project", "https://github.com/foo/bar"]) == 0
    out = capsys.readouterr().out
    assert "已建好拆解文件夹" in out
    assert (tmp_path / "projects" / "foo-bar" / "meta.json").is_file()
    assert cli.main(["new-project", "foo/bar"]) == 1
    assert "没有建文件夹" in capsys.readouterr().out
