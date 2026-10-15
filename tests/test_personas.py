import asyncio

from app.engine.personas import (
    get_persona,
    list_personas,
    personalize_insight,
    prioritize_highlights,
)
from app.engine.pipeline import MatchPipeline
from app.models import Insight


def _first_goal_insight():
    pipeline = MatchPipeline(seed=20261015)
    result = pipeline.analyze_full()
    return Insight(**result["goals"][0])


def test_persona_registry():
    ids = {p.id for p in list_personas()}
    assert "studio-analyst" in ids
    assert "fan-home" in ids
    assert get_persona("does-not-exist").id  # falls back


def test_personalize_insight_language_and_depth():
    insight = _first_goal_insight()
    studio = personalize_insight(insight, get_persona("studio-analyst"))
    assert studio.show_factors and studio.show_evidence
    fan_es = personalize_insight(insight, get_persona("global-fan-es"))
    assert fan_es.language == "es"
    assert not fan_es.show_evidence


def test_prioritize_favorite_team_first():
    pipeline = MatchPipeline(seed=20261015)
    from app.engine.highlights import build_highlights

    hl = build_highlights(pipeline.events)
    home_fan = prioritize_highlights(hl, get_persona("fan-home"))
    assert home_fan[0].team_id == "HOME"


def test_recap_is_localized():
    async def run():
        return await MatchPipeline(seed=20261015).recap(persona_id="global-fan-es")

    text = asyncio.run(run())
    assert "Final:" in text or "Goles" in text
