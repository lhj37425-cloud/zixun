"""B-4.5：DeepSeek 三次调用 + 关键词兜底 + 假模型。"""

from pathlib import Path

from daily_dissect.llm.client import FakeLLMClient, LLMError
from daily_dissect.llm.config import LLMConfig
from daily_dissect.llm.fallback import score_projects_by_keywords
from daily_dissect.llm.pipeline import run_day_llm
from daily_dissect.web.content import load_days, load_projects


CANDIDATES = [
    {
        "repo": "example/agent-demo",
        "description": "A tiny coding agent",
        "language": "Python",
        "source": "GitHub Trending",
    },
    {
        "repo": "example/plain-tool",
        "description": "CSV converter",
        "language": "Go",
        "source": "HelloGitHub",
    },
]

NEWS_ITEMS = [
    {"id": "1", "title": "新 agent 框架发布", "source": "量子位", "url": "https://a.example/1"},
    {"id": "2", "title": "某公司融资", "source": "爱范儿", "url": "https://a.example/2"},
]

SELECTED_PROJECTS = [
    {
        "repo": "example/agent-demo",
        "description": "A tiny coding agent",
        "role": "pick",
    }
]

SELECTED_NEWS = [
    {"id": "1", "title": "新 agent 框架发布", "category": "新工具"},
]


def _ok_responses():
    return [
        {
            "scores": [
                {"repo": "example/agent-demo", "relevance": 9.0, "beginner": 8.0},
                {"repo": "example/plain-tool", "relevance": 3.0, "beginner": 7.0},
            ]
        },
        {
            "groups": [
                {"ids": [1], "title": "新 agent 框架发布", "category": "新工具", "score": 8.5},
                {"ids": [2], "title": "某公司融资", "category": "新产品", "score": 2.0},
            ]
        },
        {
            "projects": [
                {
                    "repo": "example/agent-demo",
                    "one_liner": "最小 agent 示例",
                    "solves": "想看懂 agent 循环的人",
                    "for_you": "适合零基础拆",
                    "why_dissect": "小而完整",
                }
            ],
            "news": [
                {
                    "id": 1,
                    "what": "出了新框架",
                    "solves": "想搭 agent 的人",
                    "for_you": "可对照学习",
                }
            ],
        },
    ]


def test_fake_model_makes_exactly_three_calls():
    client = FakeLLMClient(_ok_responses())
    result = run_day_llm(
        project_candidates=CANDIDATES,
        news_items=NEWS_ITEMS,
        selected_projects=SELECTED_PROJECTS,
        selected_news=SELECTED_NEWS,
        client=client,
    )
    assert result.used is True
    assert result.calls == 3
    assert client.call_count == 3
    assert result.model == "fake-model"
    assert result.project_scores[0].total == 8.5
    assert result.project_blurbs[0].one_liner == "最小 agent 示例"
    assert result.news_blurbs[0].what == "出了新框架"
    # 三次调用都读到了画像 / 打分说明
    assert "学习者画像" in client.calls[0][0]
    assert "项目线打分" in client.calls[0][0]
    assert "资讯线打分" in client.calls[1][0]
    assert "写今日说明" in client.calls[2][0]


def test_no_client_uses_keyword_fallback_and_empty_blurbs():
    result = run_day_llm(
        project_candidates=CANDIDATES,
        news_items=NEWS_ITEMS,
        selected_projects=SELECTED_PROJECTS,
        selected_news=SELECTED_NEWS,
        client=None,
    )
    assert result.used is False
    assert result.calls == 0
    assert result.project_blurbs[0].one_liner == ""
    assert result.news_blurbs[0].what == ""
    # agent 相关的项目分数应高于无关工具
    by_repo = {s.repo: s for s in result.project_scores}
    assert by_repo["example/agent-demo"].relevance > by_repo["example/plain-tool"].relevance


def test_llm_failure_falls_back_and_flow_continues():
    client = FakeLLMClient(
        [
            LLMError("网络超时"),
            {"groups": []},
            {"projects": [], "news": []},
        ]
    )
    result = run_day_llm(
        project_candidates=CANDIDATES,
        news_items=NEWS_ITEMS,
        selected_projects=SELECTED_PROJECTS,
        selected_news=SELECTED_NEWS,
        client=client,
    )
    assert result.used is False
    assert result.calls == 0
    assert result.error and "超时" in result.error
    assert len(result.project_scores) == 2
    assert result.project_blurbs[0].one_liner == ""


def test_config_without_key_is_disabled(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    config = LLMConfig.from_env()
    assert config.enabled is False


def test_keyword_scoring_boosts_agent_words():
    scores = score_projects_by_keywords(
        [
            {"repo": "x/agent-kit", "description": "LLM agent tools"},
            {"repo": "x/csv", "description": "parse csv files"},
        ]
    )
    assert scores[0].relevance > scores[1].relevance


def test_page_marks_no_insight_when_llm_not_used():
    """夹具日 2026-11-15：llm.used=false，页面应带「没生成解读」。"""
    fixture = Path(__file__).resolve().parent / "fixtures" / "content"
    projects = load_projects(fixture / "projects")
    days = {d.date.isoformat(): d for d in load_days(fixture / "daily", projects)}
    day = days["2026-11-15"]
    assert day.llm_used is False
    assert any(b.text == "没生成解读" for b in day.history_badges)
