from app.data.teams import (
    CLUB_ORDER,
    DEFAULT_AWAY,
    DEFAULT_HOME,
    PL_CLUBS,
    get_club,
    list_clubs,
    venue_for,
)
from app.data.simulator import MatchSimulator


def test_twenty_clubs_present():
    assert len(PL_CLUBS) == 20
    assert len(CLUB_ORDER) == 20
    assert DEFAULT_HOME == "MUN" and DEFAULT_AWAY == "MCI"


def test_2026_27_club_set():
    assert set(CLUB_ORDER) == {
        "ARS", "AVL", "BOU", "BRE", "BHA", "CHE", "COV", "CRY", "EVE", "FUL",
        "HUL", "IPS", "LEE", "LIV", "MCI", "MUN", "NEW", "NFO", "SUN", "TOT",
    }
    for promoted in ("COV", "HUL", "IPS"):
        assert promoted in PL_CLUBS
    for relegated in ("LEI", "SOU", "WHU", "WOL"):
        assert relegated not in PL_CLUBS


def test_every_club_has_valid_eleven():
    for club in PL_CLUBS.values():
        assert len(club.players) == 11
        for name, number in club.players:
            assert name and 0 <= number <= 99


def test_formation_slots_match_player_counts():
    for club in PL_CLUBS.values():
        counts = [int(part) for part in club.formation.split("-")]
        assert sum(counts) + 1 == len(club.players)


def test_list_clubs_shape():
    clubs = list_clubs()
    assert clubs[0]["id"] == "ARS"
    assert all({"id", "name", "short", "color", "formation"} <= set(c) for c in clubs)


def test_venue_lookup():
    assert venue_for("MUN") == "Old Trafford"
    assert venue_for("mci") == "Etihad Stadium"
    assert venue_for("COV") == "Coventry Building Society Arena"


def test_build_team_roles_and_positions():
    from app.data.teams import home_team

    team = home_team("MUN")
    assert team.players[0].position == "GK"
    roles = {p.role for p in team.players}
    assert "striker" in roles
    assert len(team.players) == 11


def test_role_overrides_fix_striker_labels():
    from app.data.teams import home_team

    roles = {p.name: p.role for p in home_team("LIV").players}
    assert roles["A. Isak"] == "striker"
    assert roles["C. Gakpo"] == "left_winger"
    tot = {p.name: p.role for p in home_team("TOT").players}
    assert tot["O. Marmoush"] == "striker"


def test_simulator_uses_selected_clubs():
    sim = MatchSimulator(seed=1, home_club="ARS", away_club="TOT")
    meta, _ = sim.simulate()
    assert meta.home.name == "Arsenal"
    assert meta.away.name == "Tottenham Hotspur"
    assert meta.match_id == "ARS-TOT-2026"
    assert meta.venue == "Emirates Stadium"


def test_unknown_club_defaults_gracefully():
    assert get_club("ZZZ").id == DEFAULT_HOME
