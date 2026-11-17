"""B-4.4：给模型的说明可读、可加载；改文件就换标准。"""

from pathlib import Path

from daily_dissect.prompts import load_prompt, load_scoring_prompts, prompt_path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"


def test_prompt_files_exist_and_are_readable():
    for name in ("profile", "score_projects", "score_news"):
        path = prompt_path(name)
        assert path.is_file(), path
        text = load_prompt(name)
        assert len(text) > 100
        # 用户要读得懂：用中文写，少堆术语标题
        assert any("\u4e00" <= ch <= "\u9fff" for ch in text)


def test_profile_covers_learner_and_goal():
    text = load_prompt("profile")
    assert "FDE" in text
    assert "编程基础" in text or "零基础" in text or "很少" in text


def test_score_projects_defines_two_scores_and_json():
    text = load_prompt("score_projects")
    assert "relevance" in text
    assert "beginner" in text
    assert '"scores"' in text or '"repo"' in text


def test_score_news_defines_four_categories():
    text = load_prompt("score_news")
    for category in ("新能力", "新工具", "新产品", "落地案例"):
        assert category in text
    assert "groups" in text


def test_changing_prompt_file_changes_loaded_text_without_code(tmp_path):
    """把说明复制到临时目录改一行，加载结果跟着变——证明不用改代码。"""
    for filename in ("profile.md", "score-projects.md", "score-news.md"):
        (tmp_path / filename).write_text(
            (PROMPTS / filename).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    edited = tmp_path / "score-projects.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\n\n## 测试标记\n只为验证改文件即生效。\n",
        encoding="utf-8",
    )

    loaded = load_scoring_prompts(root=tmp_path)
    assert "测试标记" in loaded["score_projects"]
    assert "测试标记" not in load_prompt("score_projects")  # 仓库原件未改
