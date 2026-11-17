"""从 .env 读取 DeepSeek 配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

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
    def from_env(cls, *, dotenv_path: str | None = None) -> LLMConfig:
        load_dotenv(dotenv_path)
        return cls(
            api_key=(os.getenv("DEEPSEEK_API_KEY") or "").strip(),
            base_url=(os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            model=(os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        )
