import asyncio
import json

from app.config import Settings
from app.data.sources import (
    EventHubSource,
    ReplaySource,
    SyntheticSource,
    default_feed_meta,
    get_source,
    normalize_event,
)
from app.engine.pipeline import MatchPipeline
from app.models import EventType


def test_normalize_event_maps_fields():
    ev = normalize_event(
        {
            "id": 7,
            "minute": 12,
            "second": 30,
            "team_id": "HOME",
            "type": "goal",
            "x": 88,
            "y": 50,
            "xg": 0.4,
            "under_pressure": "high",
            "tags": ["big_chance"],
        }
    )
    assert ev.type == EventType.goal
    assert ev.team_id == "HOME"
    assert ev.xg == 0.4
    assert ev.under_pressure.value == "high"


def test_normalize_event_unknown_type_defaults_to_pass():
    ev = normalize_event({"type": "who_knows", "id": 1})
    assert ev.type == EventType.pass_event


def test_synthetic_source_streams_all_events():
    source = SyntheticSource(seed=20261015)
    events = asyncio.run(_collect(source))
    assert len(events) == len(source.events)
    assert source.realtime is False


def test_replay_source_roundtrip(tmp_path):
    source = SyntheticSource(seed=20261015)
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(ev.model_dump(mode="json")) for ev in source.events),
        encoding="utf-8",
    )
    replay = ReplaySource.from_jsonl(str(path), default_feed_meta())
    assert len(replay.events) == len(source.events)
    assert replay.realtime is True


def test_eventhub_source_is_lazy_and_configured():
    source = EventHubSource("Endpoint=sb://x", "hub", "$Default")
    assert source.realtime is True
    assert source.meta.match_id == "LIVE-FEED"


def test_get_source_defaults_to_synthetic():
    source = get_source(Settings())
    assert isinstance(source, SyntheticSource)


def test_pipeline_accepts_replay_source():
    synthetic = SyntheticSource(seed=20261015)
    replay = ReplaySource(synthetic.meta, synthetic.events)
    pipeline = MatchPipeline(source=replay)
    result = pipeline.analyze_full()
    expected = MatchPipeline(seed=20261015).analyze_full()["score"]
    assert result["score"] == expected
    assert result["match"]["home"]["short"] == synthetic.meta.home.short


async def _collect(source):
    out = []
    async for ev in source.stream_events():
        out.append(ev)
    return out
