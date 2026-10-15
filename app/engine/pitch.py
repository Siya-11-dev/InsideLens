from __future__ import annotations

from app.models import Player, PitchPlayer, Team

_ROLE_PUSH: dict[str, float] = {
    "striker": 1.25,
    "right_winger": 1.15,
    "left_winger": 1.15,
    "attacking_midfielder": 1.1,
    "right_midfielder": 0.95,
    "left_midfielder": 0.95,
    "central_midfielder": 0.9,
    "defensive_midfielder": 0.75,
    "right_back": 0.7,
    "left_back": 0.7,
    "centre_back": 0.45,
    "goalkeeper": 0.0,
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _move(player: Player, ball_x: float, ball_y: float, in_possession: bool, attack_dir: int) -> tuple[float, float]:
    if player.position == "GK":
        own_x = 4.0 if attack_dir > 0 else 96.0
        return own_x, _clamp(50.0 + (ball_y - 50.0) * 0.25, 40.0, 60.0)

    push = _ROLE_PUSH.get(player.role, 0.7)
    x = player.x * 0.74 + ball_x * 0.26
    y = player.y * 0.68 + ball_y * 0.32
    shift = (7.5 * push) if in_possession else (-4.0 * push)
    x += shift * attack_dir
    return _clamp(x, 2.0, 98.0), _clamp(y, 3.0, 97.0)


def positions_frame(
    home: Team,
    away: Team,
    ball_x: float,
    ball_y: float,
    possession_team: str | None,
) -> list[PitchPlayer]:
    frame: list[PitchPlayer] = []
    for team, attack_dir in ((home, 1), (away, -1)):
        in_possession = team.id == possession_team
        for player in team.players:
            x, y = _move(player, ball_x, ball_y, in_possession, attack_dir)
            frame.append(
                PitchPlayer(
                    id=player.id,
                    team_id=team.id,
                    number=player.number,
                    name=player.name,
                    position=player.position,
                    x=round(x, 1),
                    y=round(y, 1),
                )
            )
    return frame
