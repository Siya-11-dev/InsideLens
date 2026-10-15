from __future__ import annotations

import math

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
GOAL_HALF_WIDTH_M = 3.66


def attack_dir(team_id: str) -> int:
    return 1 if team_id == "HOME" else -1


def goal_x(team_id: str) -> float:
    return 100.0 if team_id == "HOME" else 0.0


def to_meters(x: float, y: float) -> tuple[float, float]:
    return x * (PITCH_LENGTH_M / 100.0), y * (PITCH_WIDTH_M / 100.0)


def shot_distance(team_id: str, x: float, y: float) -> float:
    gx = goal_x(team_id)
    mx, my = to_meters(x, y)
    gmx, gmy = to_meters(gx, 50.0)
    return math.hypot(mx - gmx, my - gmy)


def shot_angle(distance: float) -> float:
    return 2.0 * math.atan2(GOAL_HALF_WIDTH_M, max(distance, 0.5))


def expected_goals(team_id: str, x: float, y: float) -> float:
    distance = shot_distance(team_id, x, y)
    angle = shot_angle(distance)
    xg = math.exp(-0.1 * distance) * min(1.0, angle / (math.pi / 4))
    return round(max(0.01, min(0.9, xg * 0.62)), 3)


def zone_of(team_id: str, x: float) -> str:
    d = attack_dir(team_id)
    own_x = x if d > 0 else 100 - x
    if own_x <= 33.33:
        return "defensive_third"
    if own_x <= 66.67:
        return "middle_third"
    return "attacking_third"


def flank_of(y: float) -> str:
    if y <= 33.33:
        return "left"
    if y >= 66.67:
        return "right"
    return "central"


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
