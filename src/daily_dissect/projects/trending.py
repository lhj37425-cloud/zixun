"""解析 GitHub Trending 页面。"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from daily_dissect.projects.models import RepoCandidate

_STARS_TODAY_RE = re.compile(r"([\d,]+)\s+stars?\s+today", re.I)
_DIGITS_RE = re.compile(r"[\d,]+")


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    match = _DIGITS_RE.search(text)
    if not match:
        return None
    return int(match.group(0).replace(",", ""))


def parse_trending_html(html: str, *, source: str = "GitHub Trending") -> list[RepoCandidate]:
    """从 Trending HTML 解析出候选项目。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[RepoCandidate] = []

    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a[href]")
        if link is None:
            continue
        href = (link.get("href") or "").strip()
        if not href.startswith("/"):
            continue
        parts = [p for p in href.strip("/").split("/") if p]
        if len(parts) < 2:
            continue
        repo = f"{parts[0]}/{parts[1]}"

        desc_el = article.select_one("p")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        lang_el = article.select_one("[itemprop=programmingLanguage]")
        language = lang_el.get_text(strip=True) if lang_el else None

        stars_el = article.select_one('a[href$="/stargazers"]')
        stars = _parse_int(stars_el.get_text(" ", strip=True) if stars_el else None)

        stars_today = None
        today_el = article.select_one("span.float-sm-right")
        today_text = today_el.get_text(" ", strip=True) if today_el else ""
        if not today_text:
            for span in article.find_all("span"):
                text = " ".join(span.get_text().split())
                if "star" in text.lower() and "today" in text.lower():
                    today_text = text
                    break
        match = _STARS_TODAY_RE.search(today_text)
        if match:
            stars_today = int(match.group(1).replace(",", ""))

        results.append(
            RepoCandidate(
                repo=repo,
                url=f"https://github.com/{repo}",
                description=description,
                language=language,
                stars=stars,
                stars_today=stars_today,
                source=source,
            )
        )
    return results
