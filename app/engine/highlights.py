from __future__ import annotations

from app.engine.metrics import expected_goals
from app.models import EventType, Highlight, MatchEvent


def _late_bonus(minute: int) -> float:
    if minute >= 85:
        return 12.0
    if minute >= 75:
        return 8.0
    if minute >= 45:
        return 4.0
    return 0.0


def _excitement(ev: MatchEvent) -> tuple[float, str] | None:
    team = ev.team_id or "HOME"
    xg = ev.xg if ev.xg is not None else expected_goals(team, ev.x, ev.y)
    late = _late_bonus(ev.minute)

    if ev.type == EventType.goal:
        return min(100.0, 70 + xg * 40 + late), f"Goal worth {xg:.2f} xG"
    if ev.type == EventType.save and xg >= 0.25:
        return min(95.0, 55 + xg * 45 + late), f"Big chance saved ({xg:.2f} xG)"
    if ev.type == EventType.shot and xg >= 0.15:
        return min(80.0, 35 + xg * 50 + late), f"Chance ({xg:.2f} xG)"
    if "high_turnover" in ev.tags:
        return 30.0 + late, "High turnover in a dangerous area"
    if ev.type == EventType.corner:
        return 20.0 + late, "Set-piece opportunity"
    return None


def build_highlights(events: list[MatchEvent], limit: int = 12) -> list[Highlight]:
    scored: list[Highlight] = []
    for ev in events:
        result = _excitement(ev)
        if result is None:
            continue
        excitement, reason = result
        scored.append(
            Highlight(
                id=f"hl-{ev.id}",
                minute=ev.minute,
                team_id=ev.team_id,
                event_ids=[ev.id],
                kind=ev.type.value,
                title=_title(ev),
                description=ev.description or _title(ev),
                excitement=round(excitement, 1),
                reason=reason,
            )
        )
    scored.sort(key=lambda h: (h.excitement, h.minute), reverse=True)
    return scored[:limit]


def _title(ev: MatchEvent) -> str:
    label = {
        EventType.goal: "Goal",
        EventType.save: "Big save",
        EventType.shot: "Shot",
        EventType.corner: "Corner",
    }.get(ev.type, ev.type.value.title())
    who = ev.player_name or ""
    return f"{label} — {who}".strip(" —")
