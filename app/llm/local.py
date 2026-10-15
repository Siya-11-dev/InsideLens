from __future__ import annotations

from app.engine import narrative
from app.llm.base import LLMClient
from app.models import Insight


class LocalLLMClient(LLMClient):
    name = "local-template"

    async def narrate(self, insight: Insight) -> str:
        return narrative.render_narrative(insight, "en")

    async def translate(self, text: str, target_lang: str) -> str | None:
        return None
