"""调用 DeepSeek，以及没 Key / 失败时的关键词兜底。"""

from daily_dissect.llm.client import DeepSeekClient, FakeLLMClient, LLMError
from daily_dissect.llm.config import LLMConfig
from daily_dissect.llm.pipeline import DayLLMResult, run_day_llm
from daily_dissect.llm.types import (
    NewsBlurb,
    NewsGroupScore,
    ProjectBlurb,
    ProjectScore,
)

__all__ = [
    "DayLLMResult",
    "DeepSeekClient",
    "FakeLLMClient",
    "LLMConfig",
    "LLMError",
    "NewsBlurb",
    "NewsGroupScore",
    "ProjectBlurb",
    "ProjectScore",
    "run_day_llm",
]
