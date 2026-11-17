"""读取 prompts/ 里给模型看的说明。改 Markdown 就换标准，不用改代码。"""

from __future__ import annotations

from pathlib import Path

from daily_dissect.paths import PROMPTS_DIR

PROMPT_FILES = {
    "profile": "profile.md",
    "score_projects": "score-projects.md",
    "score_news": "score-news.md",
}


def prompt_path(name: str, *, root: Path | None = None) -> Path:
    """按逻辑名返回说明文件路径。name: profile / score_projects / score_news。"""
    try:
        filename = PROMPT_FILES[name]
    except KeyError as error:
        known = ", ".join(PROMPT_FILES)
        raise KeyError(f"未知说明：{name}。可用：{known}") from error
    return (root or PROMPTS_DIR) / filename


def load_prompt(name: str, *, root: Path | None = None) -> str:
    """读出一份说明的全文。"""
    path = prompt_path(name, root=root)
    return path.read_text(encoding="utf-8")


def load_scoring_prompts(*, root: Path | None = None) -> dict[str, str]:
    """一次读出画像和两份打分说明，供后面的模型调用使用。"""
    return {name: load_prompt(name, root=root) for name in PROMPT_FILES}
