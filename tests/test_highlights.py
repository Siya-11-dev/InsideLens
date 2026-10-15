from app.data.simulator import MatchSimulator
from app.engine.highlights import build_highlights


def _events(seed=20261015):
    sim = MatchSimulator(seed=seed)
    _, events = sim.simulate()
    return events


def test_highlights_ranked_by_excitement():
    hl = build_highlights(_events())
    assert hl
    assert hl == sorted(hl, key=lambda h: (h.excitement, h.minute), reverse=True)
    assert all(0 < h.excitement <= 100 for h in hl)


def test_goals_appear_in_highlights():
    events = _events()
    hl = build_highlights(events, limit=50)
    types = {h.kind for h in hl}
    assert "goal" in types


def test_highlight_limit():
    hl = build_highlights(_events(), limit=5)
    assert len(hl) <= 5
