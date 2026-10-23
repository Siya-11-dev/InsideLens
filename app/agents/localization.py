from __future__ import annotations

from app.agents.base import Agent
from app.llm.factory import get_llm


class LocalizationAgent(Agent):
    name = "localization"
    role = "Translates text to the target language"

    async def run(self, context, task):
        text = context.get("text", "")
        lang = context.get("language", "en")
        if lang == "en" or not text:
            return {"agent": self.name, "text": text, "language": lang}
        llm = get_llm()
        translated = await llm.translate(text, lang)
        return {"agent": self.name, "text": translated or text, "language": lang}
