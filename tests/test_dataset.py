import json
from pathlib import Path

from app.data.simulator import MatchSimulator
from app.store.dataset import (
    FIELDS,
    build_event_dataset,
    export_dataset,
    to_csv,
    to_delta,
    to_jsonl,
)


def _meta_events(seed=20261015):
    sim = MatchSimulator(seed=seed)
    meta, events = sim.simulate()
    return meta, events


def test_dataset_row_schema():
    meta, events = _meta_events()
    rows = build_event_dataset(meta, events)
    assert len(rows) == len(events)
    assert set(rows[0].keys()) == set(FIELDS)


def test_dataset_engineered_features():
    meta, events = _meta_events()
    rows = build_event_dataset(meta, events)
    shots = [r for r in rows if r["is_shot"]]
    assert shots
    for r in shots:
        assert r["distance_to_goal"] != ""
        assert r["shot_angle"] != ""
    goals = [r for r in rows if r["is_goal"]]
    assert goals and all(r["is_on_target"] for r in goals)


def test_dataset_serialization():
    meta, events = _meta_events()
    rows = build_event_dataset(meta, events)
    jsonl = to_jsonl(rows)
    assert len(jsonl.splitlines()) == len(rows)
    json.loads(jsonl.splitlines()[0])
    csv_text = to_csv(rows)
    assert csv_text.splitlines()[0].startswith("match_id,")


def test_dataset_export_files(tmp_path: Path):
    meta, events = _meta_events()
    path, count = export_dataset(meta, events, "jsonl", tmp_path)
    assert path.exists() and count == len(events)
    path_csv, _ = export_dataset(meta, events, "csv", tmp_path)
    assert path_csv.exists()


def test_delta_export_degrades_gracefully(tmp_path: Path):
    meta, events = _meta_events()
    rows = build_event_dataset(meta, events)
    wrote_delta = to_delta(rows, tmp_path / "m.delta")
    assert isinstance(wrote_delta, bool)
    path, count = export_dataset(meta, events, "delta", tmp_path)
    assert path.exists() and count == len(events)

