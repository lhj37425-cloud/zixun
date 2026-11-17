"""DeepSeek（OpenAI 兼容）客户端，以及测试用的假客户端。"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from daily_dissect.llm.config import LLMConfig


class LLMError(Exception):
    """调用模型失败。"""


class LLMClient(Protocol):
    def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        """发一次请求，返回解析后的 JSON 对象。"""

    @property
    def call_count(self) -> int: ...

    @property
    def model(self) -> str: ...


def _strip_code_fence(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


class DeepSeekClient:
    def __init__(self, config: LLMConfig, *, timeout: float = 60.0):
        if not config.enabled:
            raise ValueError("没有配置 DEEPSEEK_API_KEY")
        self._config = config
        self._timeout = timeout
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def model(self) -> str:
        return self._config.model

    def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        url = f"{self._config.base_url}/chat/completions"
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            self._call_count += 1
            return json.loads(_strip_code_fence(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LLMError(str(error) or error.__class__.__name__) from error


class FakeLLMClient:
    """测试用：按预定顺序返回 JSON，并记下调用次数。"""

    def __init__(
        self,
        responses: list[dict[str, Any] | LLMError],
        *,
        model: str = "fake-model",
    ):
        self._responses = list(responses)
        self._call_count = 0
        self._model = model
        self.calls: list[tuple[str, str]] = []

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def model(self) -> str:
        return self._model

    def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        if self._call_count >= len(self._responses):
            raise LLMError("假模型没有更多预设回答了")
        self.calls.append((system, user))
        result = self._responses[self._call_count]
        self._call_count += 1
        if isinstance(result, LLMError):
            raise result
        return result
