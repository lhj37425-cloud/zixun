"""检查 content/ 里的数据是否符合 docs/TECH.md 第 5 节的格式。

示例数据和以后的真实数据都要通过这些检查。只针对示例项目的检查，
在示例数据删掉之后会自动跳过（见 BACKLOG 的 B-4.8）。
"""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SAMPLE_PROJECT = CONTENT / "projects" / "example-agent-demo"

CATEGORIES = {"新能力", "新工具", "新产品", "落地案例"}
STEP_FILES = ["01-overview.md", "02-flows.md", "03-run.md", "04-qa.md"]
TODO_MARK = "<!-- 待完成 -->"

MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)```", re.S)
CORE_CLASS = re.compile(r"^class\s+[\w,\s]+\s+core$", re.I)

PROJECT_FIELDS = {
    "repo", "url", "slug", "source", "description", "language",
    "stars", "stars_today", "score", "one_liner", "solves", "for_you",
}
PROJECT_TEXT_FIELDS = ("one_liner", "solves", "for_you")
NEWS_FIELDS = {
    "title", "url", "source", "published", "category",
    "score", "what", "solves", "for_you",
}
NEWS_TEXT_FIELDS = ("what", "solves", "for_you")


def slug_of(repo: str) -> str:
    """TECH 5.3：仓库名转成小写，"/" 换成 "-"。"""
    return repo.lower().replace("/", "-")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def daily_files() -> list[Path]:
    return sorted((CONTENT / "daily").glob("*.json"))


def project_folders() -> list[Path]:
    folder = CONTENT / "projects"
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.is_dir())


def test_daily_data_absent_or_present_is_ok():
    """B-4.8 清掉示例后，真实 radar 跑之前允许暂时没有今日数据。"""
    files = daily_files()
    if not files:
        pytest.skip("还没有今日数据（示例已清理，等真实 radar）")
    assert files


@pytest.mark.parametrize("path", daily_files() or [None], ids=lambda p: getattr(p, "name", "none"))
def test_daily_file_follows_format(path: Path):
    if path is None:
        pytest.skip("还没有今日数据")
    data = load_json(path)
    assert data["date"] == path.stem, "文件名必须是当天的日期"
    assert isinstance(data.get("sample", False), bool)
    assert {"used", "model", "calls"} <= set(data["llm"])
    llm_used = data["llm"]["used"]

    projects, news = data["projects"], data["news"]
    for line in (projects, news):
        assert line["status"] in {"ok", "failed"}
        # 成功时没有错误信息；失败时必须写原因
        assert (line["error"] is None) == (line["status"] == "ok")

    if projects["status"] == "ok":
        pick, alternates = projects["pick"], projects["alternates"]
        assert "why_dissect" in pick
        assert len(alternates) <= 2
        assert all("why_dissect" not in alt for alt in alternates)
        for item in [pick, *alternates]:
            assert PROJECT_FIELDS <= set(item), f"{item.get('repo')} 缺字段"
            assert item["slug"] == slug_of(item["repo"])
            assert item["url"] == f"https://github.com/{item['repo']}"
            if not llm_used:
                assert all(item[k] == "" for k in PROJECT_TEXT_FIELDS)
        if not llm_used:
            assert pick["why_dissect"] == ""
    else:
        assert projects["pick"] is None
        assert projects["alternates"] == []

    if news["status"] == "ok":
        items = news["items"]
        assert len(items) <= 5
        for item in items:
            assert NEWS_FIELDS <= set(item), f"{item.get('title')} 缺字段"
            assert item["category"] in CATEGORIES
            if not llm_used:
                assert all(item[k] == "" for k in NEWS_TEXT_FIELDS)
        per_category = Counter(item["category"] for item in items)
        assert max(per_category.values(), default=0) <= 2, "同一个栏目最多 2 条"
    else:
        assert news["items"] == []


@pytest.mark.parametrize("folder", project_folders() or [None], ids=lambda p: getattr(p, "name", "none"))
def test_project_folder_follows_format(folder: Path):
    if folder is None:
        pytest.skip("还没有拆解项目")
    meta = load_json(folder / "meta.json")
    assert {"repo", "url", "started"} <= set(meta)
    assert folder.name == slug_of(meta["repo"]), "文件夹名必须是仓库名转成的 slug"
    assert meta["url"] == f"https://github.com/{meta['repo']}"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["started"])
    for name in STEP_FILES:
        assert (folder / name).is_file(), f"{folder.name} 缺少 {name}"


@pytest.mark.parametrize("folder", project_folders() or [None], ids=lambda p: getattr(p, "name", "none"))
def test_flow_diagrams_use_lanes_and_core(folder: Path):
    """B-3.6：流程图必须能被站内渲染器画成泳道画板样式。

    检查的是 agents 最容易写偏的地方：方向、泳道、核心节点。
    第 2 步还没写完（文件里还有“待完成”标记）时跳过，不拦半成品。
    """
    if folder is None:
        pytest.skip("还没有拆解项目")
    text = (folder / "02-flows.md").read_text(encoding="utf-8")
    if TODO_MARK in text:
        pytest.skip(f"{folder.name} 的第 2 步还没写完")
    blocks = MERMAID_BLOCK.findall(text)
    assert len(blocks) == 2, f"{folder.name} 的 02-flows.md 要有两张 mermaid 流程图"
    for index, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        head = lines[0] if lines else ""
        assert head.lower().startswith("flowchart lr"), (
            f"{folder.name} 第 {index} 张图的第一行必须是 `flowchart LR`，现在是 `{head}`"
        )
        assert any(line.startswith("subgraph ") for line in lines), (
            f"{folder.name} 第 {index} 张图没有 subgraph 泳道"
        )
        cores = [line for line in lines if CORE_CLASS.match(line)]
        assert len(cores) == 1, (
            f"{folder.name} 第 {index} 张图要有且只有一个 `class 节点ID core`，现在是 {len(cores)} 个"
        )


@pytest.mark.skipif(not SAMPLE_PROJECT.exists(), reason="示例数据已经删掉了")
def test_sample_project_has_first_two_steps_done():
    done = [TODO_MARK not in (SAMPLE_PROJECT / n).read_text(encoding="utf-8") for n in STEP_FILES]
    assert done == [True, True, False, False]
    flows = (SAMPLE_PROJECT / "02-flows.md").read_text(encoding="utf-8")
    assert flows.count("```mermaid") == 2, "流程图那一步要有两张图"


def test_glossary_entries_have_first_seen_line():
    text = (CONTENT / "glossary.md").read_text(encoding="utf-8")
    entries = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    assert entries, "术语表里至少要有一个术语"
    for entry in entries:
        term, _, body = entry.partition("\n")
        assert term.strip(), "术语名不能为空"
        assert "- 第一次出现：" in body, f"术语「{term.strip()}」缺少“第一次出现”那一行"
        assert "示例项目" not in body and "（示例）" not in body, (
            f"术语「{term.strip()}」还在指向示例数据"
        )


def test_content_has_no_sample_flag():
    """B-4.8：content/ 里不应再有 sample: true 的今日数据或示例项目。"""
    for path in daily_files():
        data = load_json(path)
        assert data.get("sample") is not True, f"{path.name} 仍是示例数据"
    for folder in project_folders():
        meta = load_json(folder / "meta.json")
        assert meta.get("sample") is not True, f"{folder.name} 仍是示例项目"
    assert not SAMPLE_PROJECT.exists()
