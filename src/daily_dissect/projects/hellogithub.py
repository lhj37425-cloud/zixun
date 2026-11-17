"""解析 HelloGitHub 的 RSS 期号和某一期 Markdown。"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import feedparser

from daily_dissect.projects.models import RepoCandidate

_VOLUME_RE = re.compile(r"/periodical/volume/(\d+)")
_ITEM_RE = re.compile(
    r"^\s*(\d+)[、.]\s*\[([^\]]+)\]\(([^)]+)\)\s*[：:]\s*(.+?)\s*$"
)
_SECTION_RE = re.compile(r"^###\s+(.+?)\s*$")


def latest_hellogithub_volume(rss_text: str) -> int | None:
    """从 HelloGitHub RSS 里取出最新一期期号。"""
    feed = feedparser.parse(rss_text)
    volumes: list[int] = []
    for entry in feed.entries:
        for field in (entry.get("link"), entry.get("id"), entry.get("title")):
            if not field:
                continue
            match = _VOLUME_RE.search(str(field))
            if match:
                volumes.append(int(match.group(1)))
                break
    return max(volumes) if volumes else None


def _github_repo_from_link(link: str) -> str | None:
    """从 HelloGitHub 跳转链接里取出 GitHub 仓库 作者/项目名。"""
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    target = (query.get("target") or [None])[0]
    if not target:
        # 偶尔是直接的 github 链接
        target = link if "github.com" in link else None
    if not target:
        return None
    target_url = urlparse(target)
    if target_url.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [p for p in target_url.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def parse_hellogithub_issue(
    markdown: str,
    *,
    volume: int,
    skip_sections: list[str] | tuple[str, ...] = ("开源书籍",),
) -> list[RepoCandidate]:
    """解析某一期 Markdown。跳过指定分类，以及不是 GitHub 的链接。"""
    skip = {s.strip() for s in skip_sections}
    section: str | None = None
    results: list[RepoCandidate] = []
    seen: set[str] = set()

    for line in markdown.splitlines():
        section_match = _SECTION_RE.match(line)
        if section_match:
            section = section_match.group(1).strip()
            continue
        if section is None or section in skip:
            continue

        item_match = _ITEM_RE.match(line)
        if not item_match:
            continue

        _index, _name, link, description = item_match.groups()
        repo = _github_repo_from_link(link)
        if repo is None:
            continue
        key = repo.lower()
        if key in seen:
            continue
        seen.add(key)

        results.append(
            RepoCandidate(
                repo=repo,
                url=f"https://github.com/{repo}",
                description=description.strip(),
                source=f"HelloGitHub 第 {volume} 期 · {section}",
            )
        )
    return results
