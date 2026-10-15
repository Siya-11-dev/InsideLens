from __future__ import annotations

from app.engine.analytics import MatchAnalytics
from app.engine.metrics import attack_dir, zone_of
from app.models import ActivePattern, EventType, MatchEvent


def _time_of(ev: MatchEvent) -> float:
    return ev.minute * 60 + ev.second


def _own_frame(team_id: str, x: float) -> float:
    return x if attack_dir(team_id) > 0 else 100 - x


def _other(team_id: str) -> str:
    return "AWAY" if team_id == "HOME" else "HOME"


def _count(events: list[MatchEvent], team_id: str, predicate) -> int:
    return sum(1 for e in events if e.team_id == team_id and predicate(e))


def detect(
    analytics: MatchAnalytics,
    events: list[MatchEvent],
    shorts: dict[str, str] | None = None,
) -> list[ActivePattern]:
    shorts = shorts or {"HOME": "HOME", "AWAY": "AWAY"}
    if not events:
        return []
    window = analytics.recent(events, 420)
    if not window:
        return []
    now_minute = events[-1].minute
    patterns: list[ActivePattern] = []

    for team in ("HOME", "AWAY"):
        opp = _other(team)
        team_window = [e for e in window if e.team_id == team]
        opp_window = [e for e in window if e.team_id == opp]

        high_wins = _count(window, team, lambda e: "high_turnover" in e.tags)
        pressures = _count(window, team, lambda e: e.type == EventType.pressure)
        if high_wins >= 2 or (high_wins >= 1 and pressures >= 3):
            strength = min(1.0, 0.25 * high_wins + 0.08 * pressures)
            since = _first_minute(window, team, lambda e: "high_turnover" in e.tags, now_minute)
            patterns.append(
                ActivePattern(
                    key="high_press",
                    label=f"{shorts.get(team, team)} pressing high",
                    team_id=team,
                    strength=round(strength, 2),
                    since_minute=since,
                )
            )

        deep_events = _count(
            window, team, lambda e: _own_frame(team, e.x) < 42 and e.type in (EventType.pass_event, EventType.carry)
        )
        opp_final = _count(
            window, opp, lambda e: zone_of(opp, e.x) == "attacking_third"
        )
        if opp_final >= 6 and deep_events >= 5:
            strength = min(1.0, 0.06 * opp_final + 0.03 * deep_events)
            patterns.append(
                ActivePattern(
                    key="low_block",
                    label=f"{shorts.get(team, team)} dropping into a low block",
                    team_id=team,
                    strength=round(strength, 2),
                    since_minute=max(0, now_minute - 7),
                )
            )

        entries_recent = _count(
            [e for e in window if _time_of(e) >= _time_of(events[-1]) - 300],
            team,
            lambda e: zone_of(team, e.x) == "attacking_third",
        )
        if entries_recent >= 5:
            strength = min(1.0, 0.12 * entries_recent)
            patterns.append(
                ActivePattern(
                    key="sustained_pressure",
                    label=f"{shorts.get(team, team)} building sustained pressure",
                    team_id=team,
                    strength=round(strength, 2),
                    since_minute=max(0, now_minute - 5),
                )
            )

        flanks = analytics.flank_share(team)
        for side in ("left", "right"):
            if flanks.get(side, 0) >= 54 and len(team_window) >= 25:
                patterns.append(
                    ActivePattern(
                        key=f"{side}_overload",
                        label=f"{shorts.get(team, team)} overloading the {side}",
                        team_id=team,
                        strength=round(min(1.0, (flanks[side] - 50) / 25.0), 2),
                        since_minute=max(0, now_minute - 10),
                    )
                )

        corners = _count(window, team, lambda e: e.type == EventType.corner)
        if corners >= 2:
            patterns.append(
                ActivePattern(
                    key="set_piece_threat",
                    label=f"{shorts.get(team, team)} threatening from set pieces",
                    team_id=team,
                    strength=round(min(1.0, 0.2 * corners), 2),
                    since_minute=_first_minute(window, team, lambda e: e.type == EventType.corner, now_minute),
                )
            )

        if _has_transition(team, window):
            patterns.append(
                ActivePattern(
                    key="counter_attack",
                    label=f"{shorts.get(team, team)} threatening in transition",
                    team_id=team,
                    strength=0.6,
                    since_minute=max(0, now_minute - 6),
                )
            )

    return patterns


def _has_transition(team_id: str, window: list[MatchEvent]) -> bool:
    for i, e in enumerate(window):
        if e.team_id != team_id:
            continue
        if e.type in (EventType.tackle, EventType.interception) and _own_frame(team_id, e.x) < 50:
            start_t = _time_of(e)
            for nxt in window[i + 1 : i + 8]:
                if nxt.team_id != team_id:
                    break
                if _time_of(nxt) - start_t > 35:
                    break
                if zone_of(team_id, nxt.x) == "attacking_third":
                    return True
    return False


def _first_minute(events, team_id, predicate, default: int) -> int:
    for e in events:
        if e.team_id == team_id and predicate(e):
            return e.minute
    return default
