from app.data.simulator import MatchSimulator
from app.engine.analytics import MatchAnalytics
from app.engine.explain import ExplanationContext, explain_pattern, explain_shot
from app.engine.patterns import detect
from app.models import EventType


def _ctx(seed=20261015):
    sim = MatchSimulator(seed=seed)
    meta, events = sim.simulate()
    an = MatchAnalytics()
    for e in events:
        an.consume(e)
    an.snapshot()
    return ExplanationContext(meta=meta, analytics=an, events=events)


def test_pattern_detection_returns_valid_shapes():
    ctx = _ctx()
    pats = detect(ctx.analytics, ctx.events, {"HOME": "NCB", "AWAY": "RIV"})
    assert isinstance(pats, list)
    for p in pats:
        assert 0.0 <= p.strength <= 1.0
        assert p.team_id in ("HOME", "AWAY")


def test_goal_insight_is_explainable():
    ctx = _ctx()
    goals = [e for e in ctx.events if e.type == EventType.goal]
    assert goals
    ins = explain_shot(goals[0], ctx)
    assert ins.kind == "goal_explanation"
    assert ins.factors and all(0 < f.weight <= 1 for f in ins.factors)
    assert ins.evidence
    assert 0.4 <= ins.confidence <= 0.95
    assert ins.counterfactual
    assert "xg" in ins.facts


def test_pattern_insight_has_evidence():
    ctx = _ctx()
    pats = detect(ctx.analytics, ctx.events, {"HOME": "NCB", "AWAY": "RIV"})
    assert pats
    ins = explain_pattern(pats[0], ctx)
    assert ins.kind == "tactical_pattern"
    assert ins.factors
    assert ins.confidence > 0
