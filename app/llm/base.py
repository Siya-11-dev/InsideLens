from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import Insight


class LLMClient(ABC):
    name: str = "local"

    @abstractmethod
    async def narrate(self, insight: Insight) -> str:
        ...

    @abstractmethod
    async def translate(self, text: str, target_lang: str) -> str | None:
        ...

    async def compose(self, system: str, user: str) -> str | None:
        return None
