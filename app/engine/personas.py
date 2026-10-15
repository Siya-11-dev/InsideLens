from __future__ import annotations

from app.engine import narrative
from app.llm.base import LLMClient
from app.llm.translator import get_translator
from app.models import Highlight, Insight, Persona, PersonalizedInsight

PERSONAS: dict[str, Persona] = {
    "studio-analyst": Persona(
        id="studio-analyst",
        name="Studio analyst",
        description="Deep, stat-heavy tactical breakdown for the broadcast studio.",
        role="studio",
        language="en",
        tone="analytical",
        verbosity="deep",
        stat_bias=0.9,
    ),
    "broadcast-hype": Persona(
        id="broadcast-hype",
        name="Broadcast commentator",
        description="Punchy, energetic lines for live commentary.",
        role="broadcaster",
        language="en",
        tone="hype",
        verbosity="standard",
        stat_bias=0.4,
    ),
    "fan-home": Persona(
        id="fan-home",
        name="Home fan",
        description="Brief, emotional updates focused on the home side.",
        role="fan",
        language="en",
        tone="hype",
        verbosity="brief",
        stat_bias=0.3,
        favorite_team="HOME",
    ),
    "fan-away": Persona(
        id="fan-away",
        name="Away fan",
        description="Brief, emotional updates focused on the away side.",
        role="fan",
        language="en",
        tone="hype",
        verbosity="brief",
        stat_bias=0.3,
        favorite_team="AWAY",
    ),
    "global-fan-es": Persona(
        id="global-fan-es",
        name="Aficionado (ES)",
        description="Spanish-language fan experience.",
        role="fan",
        language="es",
        tone="neutral",
        verbosity="standard",
        stat_bias=0.4,
    ),
    "global-fan-zu": Persona(
        id="global-fan-zu",
        name="Umlandeli (ZU)",
        description="isiZulu-language fan experience.",
        role="fan",
        language="zu",
        tone="neutral",
        verbosity="standard",
        stat_bias=0.4,
    ),
    "global-fan-ar": Persona(
        id="global-fan-ar",
        name="مشجع (AR)",
        description="Arabic-language fan experience.",
        role="fan",
        language="ar",
        tone="neutral",
        verbosity="standard",
        stat_bias=0.4,
    ),
}


def list_personas() -> list[Persona]:
    return list(PERSONAS.values())


def get_persona(persona_id: str | None) -> Persona:
    if persona_id and persona_id in PERSONAS:
        return PERSONAS[persona_id]
    return PERSONAS["broadcast-hype"]


def _tone_headline(title: str, tone: str) -> str:
    if tone == "hype":
        return f"{title} — what a moment!"
    if tone == "analytical":
        return f"{title} — analysis"
    return title


def personalize_insight(insight: Insight, persona: Persona) -> PersonalizedInsight:
    lang = persona.language
    body = (
        insight.translations.get(lang)
        or narrative.render_narrative(insight, lang)
        or insight.narrative
        or insight.claim
    )
    headline = _tone_headline(
        narrative.render_title(insight, lang) or insight.title, persona.tone
    )

    pieces: list[str] = [body]
    show_factors = persona.verbosity == "deep" or persona.stat_bias >= 0.7
    show_evidence = persona.verbosity == "deep"

    if persona.verbosity == "deep":
        top = sorted(insight.factors, key=lambda f: f.weight, reverse=True)[:2]
        if top:
            factors_txt = "; ".join(
                f"{narrative.factor_label(f.name, lang)} ({round(f.weight * 100)}%)" for f in top
            )
            pieces.append(f"Key factors: {factors_txt}.")
        pieces.append(
            f"Confidence {round(insight.confidence * 100)}% · {len(insight.evidence)} evidence items."
        )
    if persona.stat_bias >= 0.7 and "xg" in insight.facts:
        pieces.append(f"xG: {insight.facts['xg']}.")

    return PersonalizedInsight(
        insight_id=insight.id,
        persona_id=persona.id,
        language=lang,
        headline=headline,
        body=" ".join(pieces),
        show_factors=show_factors,
        show_evidence=show_evidence,
        tone=persona.tone,
    )


def prioritize_highlights(highlights: list[Highlight], persona: Persona) -> list[Highlight]:
    if not persona.favorite_team:
        return highlights
    return sorted(
        highlights,
        key=lambda h: (h.team_id == persona.favorite_team, h.excitement),
        reverse=True,
    )


async def personalize_recap(recap: str, persona: Persona, llm: LLMClient) -> str:
    text = recap
    if persona.language != "en":
        translated = await get_translator().translate(recap, persona.language)
        if translated is None:
            translated = await llm.translate(recap, persona.language)
        if translated:
            text = translated
    if persona.tone == "hype":
        return f"{text}"
    if persona.tone == "analytical":
        return f"{text}"
    return text
