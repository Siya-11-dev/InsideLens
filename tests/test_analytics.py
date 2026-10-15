from app.data.simulator import MatchSimulator
from app.engine.analytics import MatchAnalytics
from app.models import EventType


def _run(seed=20261015):
    sim = MatchSimulator(seed=seed)
    _, events = sim.simulate()
    an = MatchAnalytics()
    for e in events:
        an.consume(e)
    return an, events


def test_possession_sums_to_100():
    an, _ = _run()
    home, away = an.snapshot()
    assert abs((home.possession + away.possession) - 100.0) < 0.2


def test_goal_count_matches_events():
    an, events = _run()
    home, away = an.snapshot()
    goals = sum(1 for e in events if e.type == EventType.goal)
    assert home.goals + away.goals == goals


def test_momentum_series_grows_with_time():
    an, _ = _run()
    an.snapshot()
    assert len(an.momentum) >= 80
    assert an.momentum[-1].minute >= 88


def test_field_tilt_sums_to_100():
    an, _ = _run()
    home, away = an.snapshot()
    if home.field_tilt or away.field_tilt:
        assert abs((home.field_tilt + away.field_tilt) - 100.0) < 0.5
