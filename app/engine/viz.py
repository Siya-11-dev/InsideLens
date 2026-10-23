from __future__ import annotations

from app.engine.metrics import zone_of
from app.models import EventType, MatchEvent


def heatmap(
    events: list[MatchEvent],
    bins_x: int = 12,
    bins_y: int = 8,
    team_id: str | None = None,
    kind: str | None = None,
) -> dict:
    grid = [[0 for _ in range(bins_x)] for _ in range(bins_y)]
    total = 0
    for ev in events:
        if team_id and ev.team_id != team_id:
            continue
        if kind and ev.type.value != kind:
            continue
        ix = min(bins_x - 1, max(0, int(ev.x / 100.0 * bins_x)))
        iy = min(bins_y - 1, max(0, int(ev.y / 100.0 * bins_y)))
        grid[iy][ix] += 1
        total += 1
    return {"bins_x": bins_x, "bins_y": bins_y, "total": total, "grid": grid}


def pass_network(events: list[MatchEvent], team_id: str | None = None) -> dict:
    nodes: dict[int, dict] = {}
    for ev in events:
        if team_id and ev.team_id != team_id:
            continue
        if ev.player_id is None:
            continue
        node = nodes.setdefault(
            ev.player_id,
            {"id": ev.player_id, "name": ev.player_name, "x": 0.0, "y": 0.0, "events": 0, "passes": 0},
        )
        node["x"] += ev.x
        node["y"] += ev.y
        node["events"] += 1

    edges: dict[tuple[int, int], int] = {}
    for i, ev in enumerate(events):
        if ev.type != EventType.pass_event:
            continue
        if team_id and ev.team_id != team_id:
            continue
        if ev.player_id is None or ev.outcome != "complete":
            continue
        receiver = None
        for j in range(i + 1, len(events)):
            nxt = events[j]
            if nxt.team_id != ev.team_id:
                break
            if nxt.player_id is not None and nxt.player_id != ev.player_id:
                receiver = nxt.player_id
                break
        if receiver is None:
            continue
        key = (ev.player_id, receiver)
        edges[key] = edges.get(key, 0) + 1
        if ev.player_id in nodes:
            nodes[ev.player_id]["passes"] += 1

    for node in nodes.values():
        if node["events"]:
            node["x"] = round(node["x"] / node["events"], 1)
            node["y"] = round(node["y"] / node["events"], 1)
        del node["events"]

    return {
        "nodes": list(nodes.values()),
        "edges": [{"from": a, "to": b, "passes": c} for (a, b), c in edges.items()],
    }


def expected_threat(events: list[MatchEvent]) -> dict:
    threat_value = {"defensive_third": 0.01, "middle_third": 0.05, "attacking_third": 0.12}
    home = 0.0
    away = 0.0
    scored: list[tuple[float, MatchEvent]] = []
    for ev in events:
        if ev.team_id not in ("HOME", "AWAY"):
            continue
        if ev.type in (EventType.shot, EventType.save, EventType.goal):
            threat = ev.xg if ev.xg is not None else (ev.xg_delta or 0.1)
        else:
            threat = threat_value.get(zone_of(ev.team_id, ev.x), 0.05)
            if ev.type == EventType.pass_event and ev.outcome == "complete" and ev.end_x is not None:
                threat = threat_value.get(zone_of(ev.team_id, ev.end_x), 0.05)
        if ev.team_id == "HOME":
            home += threat
        else:
            away += threat
        scored.append((float(threat), ev))
    top = sorted(scored, key=lambda t: t[0], reverse=True)[:5]
    return {
        "home": round(home, 2),
        "away": round(away, 2),
        "top": [
            {
                "minute": ev.minute,
                "player": ev.player_name,
                "team_id": ev.team_id,
                "threat": round(t, 3),
                "type": ev.type.value,
            }
            for t, ev in top
        ],
    }
