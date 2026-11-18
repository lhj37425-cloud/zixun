"""为要拆的项目建 content/projects/<slug>/ 和四步模板。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from daily_dissect.paths import CONTENT_DIR
from daily_dissect.web.content import STEPS, TODO_MARK, slug_of

BEIJING = timezone(timedelta(hours=8))

_GITHUB_HOSTS = {"github.com", "www.github.com"}


class NewProjectError(ValueError):
    """仓库地址无效，或项目文件夹已经存在。"""


@dataclass(frozen=True)
class NewProjectReport:
    repo: str
    url: str
    slug: str
    folder: Path
    started: str
    created_files: list[str]


def parse_repo_ref(raw: str) -> tuple[str, str]:
    """把用户输入收成 (作者/项目名, https://github.com/作者/项目名)。"""
    text = (raw or "").strip()
    if not text:
        raise NewProjectError("请给出仓库地址，例如 https://github.com/作者/项目名")

    candidate = text
    if candidate.startswith("git@"):
        # git@github.com:owner/repo.git
        match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", candidate)
        if not match:
            raise NewProjectError(f"无法识别的仓库地址：{raw}")
        repo = _clean_repo(match.group(1), match.group(2))
        return repo, f"https://github.com/{repo}"

    if "://" not in candidate and candidate.count("/") == 1 and not candidate.startswith("github.com/"):
        owner, name = candidate.split("/", 1)
        repo = _clean_repo(owner, name)
        return repo, f"https://github.com/{repo}"

    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in _GITHUB_HOSTS:
        raise NewProjectError(f"目前只支持 GitHub 地址：{raw}")

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise NewProjectError(f"地址里要有作者和项目名：{raw}")
    repo = _clean_repo(parts[0], parts[1].removesuffix(".git"))
    return repo, f"https://github.com/{repo}"


def _clean_repo(owner: str, name: str) -> str:
    owner = owner.strip()
    name = name.strip().removesuffix(".git")
    if not owner or not name or "/" in owner or "/" in name:
        raise NewProjectError(f"仓库名无效：{owner}/{name}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise NewProjectError(f"仓库名含有不支持的字符：{owner}/{name}")
    return f"{owner}/{name}"


def _step_template(repo: str, filename: str, step_name: str) -> str:
    title = f"# {step_name}：{repo}"
    if filename == "01-overview.md":
        body = "\n\n".join(
            [
                title,
                "## 解决谁的什么问题\n",
                "## 为什么是现在\n",
                "## 用户以前怎么解决\n",
                "## 它好在哪\n",
            ]
        )
    elif filename == "02-flows.md":
        body = "\n\n".join(
            [
                title,
                "## 用户的操作流程\n\n（在这里放第一张 mermaid 流程图）\n",
                "## agent（或系统）内部的流程\n\n（在这里放第二张 mermaid 流程图）\n",
            ]
        )
    elif filename == "03-run.md":
        body = "\n\n".join(
            [
                title,
                "## 需要准备什么\n",
                "## 安装和运行的每一步\n",
                "## 遇到的问题和解决办法\n",
                "## 跑起来之后看到了什么\n",
            ]
        )
    else:
        body = "\n\n".join([title, "## 问答记录\n", "## 这次学到的概念\n"])
    return f"{TODO_MARK}\n{body}\n"


def create_project(
    raw: str,
    *,
    projects_dir: Path | None = None,
    started: date | None = None,
) -> NewProjectReport:
    """建好 content/projects/<slug>/：meta.json + 四个带「待完成」的步骤文件。"""
    repo, url = parse_repo_ref(raw)
    slug = slug_of(repo)
    root = projects_dir or (CONTENT_DIR / "projects")
    folder = root / slug
    if folder.exists():
        raise NewProjectError(
            f"项目文件夹已经存在：{folder}\n"
            "如果要继续拆，直接让 agent 按 prompts/dissect.md 接着做；不要重复建。"
        )

    day = started or datetime.now(BEIJING).date()
    started_text = day.isoformat()
    folder.mkdir(parents=True, exist_ok=False)

    meta = {"repo": repo, "url": url, "started": started_text}
    meta_path = folder / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    created = ["meta.json"]
    for filename, step_name, _pending in STEPS:
        path = folder / filename
        path.write_text(_step_template(repo, filename, step_name), encoding="utf-8")
        created.append(filename)

    return NewProjectReport(
        repo=repo,
        url=url,
        slug=slug,
        folder=folder,
        started=started_text,
        created_files=created,
    )
