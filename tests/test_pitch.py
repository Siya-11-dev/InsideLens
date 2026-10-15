from app.data.teams import home_team, away_team
from app.engine.pitch import positions_frame


def test_positions_frame_has_22_players():
    home = home_team("MUN")
    away = away_team("MCI")
    frame = positions_frame(home, away, 50.0, 50.0, "HOME")
    assert len(frame) == 22
    assert sum(1 for p in frame if p.team_id == "HOME") == 11
    assert sum(1 for p in frame if p.team_id == "AWAY") == 11


def test_positions_within_pitch():
    home = home_team("ARS")
    away = away_team("TOT")
    frame = positions_frame(home, away, 80.0, 10.0, "HOME")
    for p in frame:
        assert 0.0 <= p.x <= 100.0
        assert 0.0 <= p.y <= 100.0


def test_goalkeepers_stay_near_own_goal():
    home = home_team("MUN")
    away = away_team("MCI")
    frame = positions_frame(home, away, 90.0, 50.0, "AWAY")
    home_gk = next(p for p in frame if p.team_id == "HOME" and p.position == "GK")
    away_gk = next(p for p in frame if p.team_id == "AWAY" and p.position == "GK")
    assert home_gk.x < 10
    assert away_gk.x > 90


def test_possession_team_is_higher_up_pitch():
    home = home_team("MUN")
    away = away_team("MCI")
    with_ball = positions_frame(home, away, 50.0, 50.0, "HOME")
    without_ball = positions_frame(home, away, 50.0, 50.0, "AWAY")
    home_in = sum(p.x for p in with_ball if p.team_id == "HOME") / 11
    home_out = sum(p.x for p in without_ball if p.team_id == "HOME") / 11
    away_in = sum(p.x for p in without_ball if p.team_id == "AWAY") / 11
    away_out = sum(p.x for p in with_ball if p.team_id == "AWAY") / 11
    assert home_in > home_out
    assert away_in < away_out


def test_pipeline_state_includes_players():
    from app.engine.pipeline import MatchPipeline

    pipeline = MatchPipeline(seed=1, home_team="LIV", away_team="CHE")
    state = pipeline._state(pipeline.events[0])
    assert len(state.players) == 22
    assert all(p.team_id in ("HOME", "AWAY") for p in state.players)
