from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMClient
from app.llm.local import LocalLLMClient


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "azure" and settings.azure_llm_ready:
        from app.llm.azure import AzureOpenAIClient

        return AzureOpenAIClient(settings)
    return LocalLLMClient()
