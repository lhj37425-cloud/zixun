"""从 .env 读取 DeepSeek 配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())

    @classmethod
    def from_env(cls, *, dotenv_path: str | Path | None = None) -> LLMConfig:
        """优先读项目里的 .env，避免系统环境里的旧 Key 盖掉正确配置。"""
        from daily_dissect.paths import ROOT

        path = Path(dotenv_path) if dotenv_path else ROOT / ".env"
        file_vals = dotenv_values(path) if path.is_file() else {}

        def pick(name: str, default: str = "") -> str:
            raw = file_vals.get(name)
            if raw is not None and str(raw).strip() != "":
                return str(raw).strip()
            return (os.getenv(name) or default).strip()

        return cls(
            api_key=pick("DEEPSEEK_API_KEY"),
            base_url=pick("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/") or DEFAULT_BASE_URL,
            model=pick("DEEPSEEK_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL,
        )
