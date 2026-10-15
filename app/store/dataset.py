from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from app.engine.metrics import flank_of, shot_angle, shot_distance, zone_of
from app.models import EventType, MatchEvent, MatchMeta

SHOT_TYPES = {EventType.shot, EventType.save, EventType.goal}
ON_TARGET_TYPES = {EventType.save, EventType.goal}
PRESSURE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}

FIELDS = [
    "match_id",
    "event_id",
    "event_index",
    "minute",
    "second",
    "t_seconds",
    "team_id",
    "player_id",
    "player_name",
    "type",
    "outcome",
    "x",
    "y",
    "end_x",
    "end_y",
    "xg",
    "under_pressure",
    "pressure_score",
    "body_part",
    "zone",
    "flank",
    "distance_to_goal",
    "shot_angle",
    "is_shot",
    "is_on_target",
    "is_goal",
    "is_high_turnover",
    "n_tags",
]


def build_event_row(meta: MatchMeta, ev: MatchEvent, index: int) -> dict:
    team = ev.team_id
    is_shot = ev.type in SHOT_TYPES
    distance = None
    angle = None
    zone = None
    flank = None
    if team:
        zone = zone_of(team, ev.x)
        flank = flank_of(ev.y)
        if is_shot:
            distance = round(shot_distance(team, ev.x, ev.y), 2)
            angle = round(shot_angle(distance), 3)
    return {
        "match_id": meta.match_id,
        "event_id": ev.id,
        "event_index": index,
        "minute": ev.minute,
        "second": ev.second,
        "t_seconds": ev.minute * 60 + ev.second,
        "team_id": team or "",
        "player_id": ev.player_id if ev.player_id is not None else "",
        "player_name": ev.player_name or "",
        "type": ev.type.value,
        "outcome": ev.outcome or "",
        "x": ev.x,
        "y": ev.y,
        "end_x": ev.end_x if ev.end_x is not None else "",
        "end_y": ev.end_y if ev.end_y is not None else "",
        "xg": ev.xg if ev.xg is not None else "",
        "under_pressure": ev.under_pressure.value,
        "pressure_score": PRESSURE_ORDER.get(ev.under_pressure.value, 0),
        "body_part": ev.body_part or "",
        "zone": zone or "",
        "flank": flank or "",
        "distance_to_goal": distance if distance is not None else "",
        "shot_angle": angle if angle is not None else "",
        "is_shot": int(is_shot),
        "is_on_target": int(ev.type in ON_TARGET_TYPES),
        "is_goal": int(ev.type == EventType.goal),
        "is_high_turnover": int("high_turnover" in ev.tags),
        "n_tags": len(ev.tags),
    }


def build_event_dataset(meta: MatchMeta, events: list[MatchEvent]) -> list[dict]:
    return [build_event_row(meta, ev, i) for i, ev in enumerate(events)]


def to_jsonl(rows: list[dict]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def to_parquet(rows: list[dict], path: Path) -> bool:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception:
        return False
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)
    return True


def to_delta(rows: list[dict], path: Path) -> bool:
    try:
        import pyarrow as pa
        from deltalake import write_deltalake
    except Exception:
        return False
    table = pa.Table.from_pylist(rows)
    write_deltalake(str(path), table, mode="overwrite")
    return True


def export_dataset(
    meta: MatchMeta, events: list[MatchEvent], fmt: str, out_dir: Path
) -> tuple[Path, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_event_dataset(meta, events)
    fmt = fmt.lower()
    if fmt == "delta":
        path = out_dir / f"{meta.match_id}.delta"
        if to_delta(rows, path):
            return path, len(rows)
        fmt = "parquet"
    if fmt == "parquet":
        path = out_dir / f"{meta.match_id}.parquet"
        if to_parquet(rows, path):
            return path, len(rows)
        fmt = "jsonl"
    if fmt == "csv":
        path = out_dir / f"{meta.match_id}.csv"
        path.write_text(to_csv(rows), encoding="utf-8")
    else:
        path = out_dir / f"{meta.match_id}.jsonl"
        path.write_text(to_jsonl(rows), encoding="utf-8")
    return path, len(rows)
