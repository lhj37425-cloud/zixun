"""B-4.6：挑选并写入今日数据（对照 PRD F1 / F2）。"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from daily_dissect.llm.client import LLMError
from daily_dissect.news.models import NewsItem
from daily_dissect.projects.models import RepoCandidate
from daily_dissect.projects.pool import ProjectPool
from daily_dissect.radar.build import build_daily, save_daily


def _entry(repo: str, description: str, *, language: str = "Python") -> RepoCandidate:
    return RepoCandidate(
        repo=repo,
        url=f"https://github.com/{repo}",
        description=description,
        language=language,
        source="GitHub Trending",
        stars=100,
        stars_today=10,
    )


def _news(title: str, url: str, source: str = "量子位") -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source=source,
        published=datetime(2026, 11, 17, 1, 0, tzinfo=timezone.utc),
    )


class ScriptedLLM:
    """按调用次序返回预设结果；写说明时根据请求里的 repo/id 动态生成。"""

    def __init__(self, score_projects: dict, score_news: dict):
        self._score_projects = score_projects
        self._score_news = score_news
        self._call_count = 0
        self._model = "fake-model"

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def model(self) -> str:
        return self._model

    def complete_json(self, *, system: str, user: str) -> dict:
        import json as _json

        self._call_count += 1
        if self._call_count == 1:
            return self._score_projects
        if self._call_count == 2:
            return self._score_news
        if self._call_count == 3:
            payload = _json.loads(user)
            projects = [
                {
                    "repo": row["repo"],
                    "one_liner": f"{row['repo']} 一句话",
                    "solves": "能解决谁的什么问题",
                    "for_you": "对你有什么价值",
                    "why_dissect": "为什么拆它",
                }
                for row in payload.get("projects") or []
            ]
            news = [
                {
                    "id": int(row["id"]),
                    "what": f"发生了什么（{row['title']}）",
                    "solves": "能解决谁的什么问题",
                    "for_you": "对你意味着什么",
                }
                for row in payload.get("news") or []
            ]
            return {"projects": projects, "news": news}
        raise LLMError("没有更多预设回答")


def test_build_daily_writes_pick_alternates_and_news(tmp_path: Path):
    pool = ProjectPool()
    repos = ["a/agent-one", "b/agent-two", "c/agent-three", "d/other"]
    pool.add_candidates(
        [_entry(r, f"{r} agent llm demo") for r in repos],
        today=date(2026, 11, 17),
    )
    news_items = [
        _news("同一件事来源A", "https://ex.com/same"),
        _news("同一件事来源B", "https://ex.com/same-b", "InfoQ 中文"),
        _news("工具上新", "https://ex.com/3"),
        _news("产品发布", "https://ex.com/4"),
        _news("落地案例甲", "https://ex.com/5"),
        _news("又一条能力", "https://ex.com/6"),
        _news("多余的工具", "https://ex.com/7"),
    ]
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    client = ScriptedLLM(
        score_projects={
            "scores": [
                {"repo": "a/agent-one", "relevance": 9.5, "beginner": 8.0},
                {"repo": "b/agent-two", "relevance": 8.5, "beginner": 8.0},
                {"repo": "c/agent-three", "relevance": 7.5, "beginner": 8.0},
                {"repo": "d/other", "relevance": 4.0, "beginner": 7.0},
            ]
        },
        score_news={
            "groups": [
                {"ids": [1, 2], "title": "合并后的大新闻", "category": "新能力", "score": 9.5},
                {"ids": [3], "title": "工具上新", "category": "新工具", "score": 8.8},
                {"ids": [4], "title": "产品发布", "category": "新产品", "score": 8.5},
                {"ids": [5], "title": "落地案例甲", "category": "落地案例", "score": 8.2},
                {"ids": [6], "title": "又一条能力", "category": "新能力", "score": 8.0},
                {"ids": [7], "title": "多余的工具", "category": "新工具", "score": 7.9},
            ]
        },
    )

    doc = build_daily(
        pool=pool,
        news_items=news_items,
        projects_dir=projects_dir,
        client=client,
        today=date(2026, 11, 17),
    )
    path = save_daily(doc, tmp_path / "daily")
    assert path.is_file()
    assert client.call_count == 3
    assert doc["llm"]["used"] is True
    assert doc["llm"]["calls"] == 3

    assert doc["projects"]["status"] == "ok"
    pick = doc["projects"]["pick"]
    alts = doc["projects"]["alternates"]
    assert pick["repo"] == "a/agent-one"
    assert len(alts) == 2
    assert {a["repo"] for a in alts} == {"b/agent-two", "c/agent-three"}
    assert pick["one_liner"] and pick["solves"] and pick["for_you"] and pick["why_dissect"]
    for alt in alts:
        assert alt["one_liner"]
        assert "why_dissect" not in alt

    items = doc["news"]["items"]
    assert len(items) == 5
    titles = [i["title"] for i in items]
    assert titles.count("合并后的大新闻") == 1
    assert "同一件事来源A" not in titles
    assert "同一件事来源B" not in titles
    from collections import Counter

    assert all(v <= 2 for v in Counter(i["category"] for i in items).values())
    for item in items:
        assert item["category"] in {"新能力", "新工具", "新产品", "落地案例"}
        assert item["what"]
        assert item["url"]
        assert len(item["what"]) < 500


def test_second_day_does_not_repeat_pick(tmp_path: Path):
    pool = ProjectPool()
    repos = ["a/one", "b/two", "c/three", "d/four"]
    pool.add_candidates(
        [_entry(r, f"{r} agent") for r in repos],
        today=date(2026, 11, 17),
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    news_items = [_news("n1", "https://ex.com/1"), _news("n2", "https://ex.com/2")]

    day1 = build_daily(
        pool=pool,
        news_items=news_items,
        projects_dir=projects_dir,
        client=None,
        today=date(2026, 11, 17),
    )
    first_pick = day1["projects"]["pick"]["repo"]
    assert any(row["repo"] == first_pick for row in pool.picked)

    day2 = build_daily(
        pool=pool,
        news_items=news_items,
        projects_dir=projects_dir,
        client=None,
        today=date(2026, 11, 18),
    )
    assert day2["projects"]["pick"]["repo"] != first_pick


def test_dissected_project_not_recommended(tmp_path: Path):
    pool = ProjectPool()
    pool.add_candidates(
        [
            _entry("example/agent-demo", "coding agent"),
            _entry("x/agent-kit", "another agent"),
            _entry("y/agent-lab", "agent lab"),
        ],
        today=date(2026, 11, 17),
    )
    projects_dir = tmp_path / "projects"
    meta_dir = projects_dir / "example-agent-demo"
    meta_dir.mkdir(parents=True)
    (meta_dir / "meta.json").write_text(
        json.dumps(
            {"repo": "example/agent-demo", "url": "https://github.com/example/agent-demo"}
        ),
        encoding="utf-8",
    )
    doc = build_daily(
        pool=pool,
        news_items=[_news("n", "https://ex.com/n")],
        projects_dir=projects_dir,
        client=None,
        today=date(2026, 11, 17),
    )
    chosen = {doc["projects"]["pick"]["repo"]} | {
        a["repo"] for a in doc["projects"]["alternates"]
    }
    assert "example/agent-demo" not in chosen


def test_line_failure_still_writes_other_line(tmp_path: Path):
    pool = ProjectPool()
    pool.add_candidates(
        [
            _entry("a/agent", "agent demo"),
            _entry("b/agent", "agent two"),
            _entry("c/agent", "agent three"),
        ],
        today=date(2026, 11, 17),
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    doc = build_daily(
        pool=pool,
        news_items=[_news("好消息", "https://ex.com/ok")],
        projects_dir=projects_dir,
        client=None,
        today=date(2026, 11, 17),
        projects_error="Trending 超时",
    )
    assert doc["projects"]["status"] == "failed"
    assert doc["projects"]["pick"] is None
    assert doc["news"]["status"] == "ok"
    assert len(doc["news"]["items"]) >= 1


def test_llm_score_failure_falls_back_to_keywords(tmp_path: Path):
    """打分接口 401/失败时，抓取结果仍应用关键词挑出主推和资讯。"""
    from daily_dissect.llm.client import LLMError

    class BoomClient:
        model = "boom"
        call_count = 0

        def complete_json(self, *, system: str, user: str):
            self.call_count += 1
            raise LLMError("401 Authorization Required")

    pool = ProjectPool()
    pool.add_candidates(
        [
            _entry("a/agent-kit", "coding agent llm"),
            _entry("b/agent-lab", "agent tools"),
            _entry("c/csv-tool", "csv converter"),
        ],
        today=date(2026, 11, 17),
    )
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    doc = build_daily(
        pool=pool,
        news_items=[
            _news("新 agent 框架", "https://ex.com/1"),
            _news("普通新闻", "https://ex.com/2"),
        ],
        projects_dir=projects_dir,
        client=BoomClient(),
        today=date(2026, 11, 17),
    )
    assert doc["projects"]["status"] == "ok"
    assert doc["projects"]["pick"] is not None
    assert doc["news"]["status"] == "ok"
    assert len(doc["news"]["items"]) >= 1
    assert doc["llm"]["used"] is False
