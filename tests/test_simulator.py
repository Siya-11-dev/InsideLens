from app.data.simulator import ATTACK_ROLES, MatchSimulator
from app.models import EventType


def test_simulator_produces_ordered_events():
    sim = MatchSimulator(seed=1)
    _, events = sim.simulate()
    assert len(events) > 400
    times = [e.minute * 60 + e.second for e in events]
    assert times == sorted(times)
    assert events[0].type == EventType.kickoff
    assert events[-1].type == EventType.fulltime


def test_halftime_emitted_once():
    sim = MatchSimulator(seed=7)
    _, events = sim.simulate()
    halftimes = [e for e in events if e.type == EventType.halftime]
    assert len(halftimes) == 1
    assert halftimes[0].minute == 45


def test_scoreline_is_realistic():
    for seed in (1, 7, 42, 99, 123, 555):
        sim = MatchSimulator(seed=seed)
        _, events = sim.simulate()
        goals = [e for e in events if e.type == EventType.goal]
        assert len(goals) <= 9
        assert sim.score["HOME"] + sim.score["AWAY"] == len(goals)


def test_xg_within_bounds():
    sim = MatchSimulator(seed=3)
    _, events = sim.simulate()
    for e in events:
        if e.xg is not None:
            assert 0.0 < e.xg <= 0.9


def test_shots_and_goals_only_from_attack_roles():
    for seed in (1, 7, 42, 99, 123, 555):
        sim = MatchSimulator(seed=seed)
        meta, events = sim.simulate()
        roles = {
            "HOME": {p.id: p.role for p in meta.home.players},
            "AWAY": {p.id: p.role for p in meta.away.players},
        }
        for e in events:
            set_piece = "set_piece" in (e.tags or [])
            if e.type in (EventType.shot, EventType.save, EventType.goal) and e.player_id and not set_piece:
                assert roles[e.team_id][e.player_id] in ATTACK_ROLES


def test_defenders_score_from_set_pieces():
    found = 0
    for seed in range(1, 60):
        sim = MatchSimulator(seed=seed)
        meta, events = sim.simulate()
        roles = {
            "HOME": {p.id: p.role for p in meta.home.players},
            "AWAY": {p.id: p.role for p in meta.away.players},
        }
        for e in events:
            if e.type == EventType.goal and e.player_id and roles[e.team_id][e.player_id] not in ATTACK_ROLES:
                assert "set_piece" in (e.tags or [])
                assert e.body_part == "header"
                found += 1
    assert found >= 1


def test_pick_player_prefers_role_near_ball():
    sim = MatchSimulator(seed=5, home_club="ARS")
    home = sim.teams["HOME"]
    picks = [sim._pick_player(home, 88.0, 50.0, ATTACK_ROLES, "finishing", restrict=True) for _ in range(400)]
    roles = {p.role for p in picks}
    assert roles <= set(ATTACK_ROLES)
