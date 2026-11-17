"""没配 API Key 或调用失败时的关键词打分；说明字段留空。"""

from __future__ import annotations

from daily_dissect.llm.types import NewsGroupScore, ProjectBlurb, ProjectScore, NewsBlurb

PROJECT_KEYWORDS = (
    "agent",
    "llm",
    "gpt",
    "openai",
    "claude",
    "rag",
    "embedding",
    "模型",
    "智能体",
    "大模型",
    "prompt",
    "langchain",
    "autogen",
)

NEWS_CATEGORY_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("新能力", ("model", "gpt", "claude", "能力", "推理", "多模态", "上下文")),
    ("新工具", ("framework", "sdk", "cli", "工具", "框架", "langchain", "agent")),
    ("新产品", ("launch", "release", "上线", "发布", "产品")),
    ("落地案例", ("case", "customer", "落地", "客户", "行业")),
)


def _hits(text: str, words: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for word in words if word.lower() in lowered)


def score_projects_by_keywords(
    candidates: list[dict[str, str]],
) -> list[ProjectScore]:
    """candidates 每项至少有 repo、description。"""
    scores: list[ProjectScore] = []
    for item in candidates:
        repo = item["repo"]
        text = f"{repo} {item.get('description') or ''}"
        hit = _hits(text, PROJECT_KEYWORDS)
        relevance = min(10.0, round(3.0 + hit * 1.5, 1))
        # 兜底时不好判断安装难度，给中等分，避免全靠运气
        beginner = 6.0
        scores.append(ProjectScore(repo=repo, relevance=relevance, beginner=beginner))
    return scores


def score_news_by_keywords(
    items: list[dict[str, str]],
) -> list[NewsGroupScore]:
    """items 每项有 id（从 1 起）、title；可选 summary。不合并，每条单独一组。"""
    groups: list[NewsGroupScore] = []
    for item in items:
        item_id = int(item["id"])
        title = item.get("title") or ""
        blob = f"{title} {item.get('summary') or ''}"
        category = "新工具"
        best = -1
        for name, words in NEWS_CATEGORY_HINTS:
            score = _hits(blob, words)
            if score > best:
                best = score
                category = name
        hit = _hits(blob, PROJECT_KEYWORDS + tuple(w for _, ws in NEWS_CATEGORY_HINTS for w in ws))
        score = min(10.0, round(3.0 + hit * 1.2, 1))
        groups.append(
            NewsGroupScore(
                ids=(item_id,),
                title=title,
                category=category,
                score=score,
            )
        )
    return groups


def empty_project_blurbs(repos: list[str]) -> list[ProjectBlurb]:
    return [
        ProjectBlurb(repo=repo, one_liner="", solves="", for_you="", why_dissect="")
        for repo in repos
    ]


def empty_news_blurbs(ids: list[int]) -> list[NewsBlurb]:
    return [NewsBlurb(id=i, what="", solves="", for_you="") for i in ids]
