from __future__ import annotations

from app.engine import narrative
from app.llm.base import LLMClient
from app.llm.translator import get_translator
from app.models import Insight

_MAX_TRANSLATED = 6


async def localize(insight: Insight, llm: LLMClient) -> Insight:
    insight.narrative = await llm.narrate(insight)
    insight.model = llm.name
    translator = get_translator()
    translations: dict[str, str] = {"en": insight.narrative}
    for code in narrative.LANGUAGES:
        if code == "en":
            continue
        if len(translations) >= _MAX_TRANSLATED:
            break
        translated = await translator.translate(insight.narrative, code)
        if translated is None:
            translated = await llm.translate(insight.narrative, code)
        translations[code] = translated or narrative.render_narrative(insight, code)
    insight.translations = translations
    return insight
