from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable

from app.data.simulator import MatchSimulator
from app.data.teams import away_team, home_team
from app.models import EventType, MatchEvent, MatchMeta


def _opt_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _opt_int(value) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def normalize_event(data: dict) -> MatchEvent:
    raw_type = str(data.get("type", "pass")).lower()
    try:
        event_type = EventType(raw_type)
    except ValueError:
        event_type = EventType.pass_event
    pressure = str(data.get("under_pressure", "none"))
    return MatchEvent(
        id=_opt_int(data.get("id") or data.get("event_id")) or 0,
        minute=int(data.get("minute", 0) or 0),
        second=int(data.get("second", 0) or 0),
        team_id=data.get("team_id") or None,
        player_id=_opt_int(data.get("player_id")),
        player_name=data.get("player_name") or None,
        type=event_type,
        x=float(data.get("x", 50) or 50),
        y=float(data.get("y", 50) or 50),
        end_x=_opt_float(data.get("end_x")),
        end_y=_opt_float(data.get("end_y")),
        xg=_opt_float(data.get("xg")),
        xg_delta=_opt_float(data.get("xg_delta")),
        outcome=data.get("outcome") or None,
        under_pressure=pressure if pressure in {"none", "low", "medium", "high"} else "none",
        body_part=data.get("body_part") or None,
        tags=list(data.get("tags", []) or []),
        description=data.get("description", "") or "",
    )


def default_feed_meta(
    match_id: str = "LIVE-FEED",
    home_club: str | None = None,
    away_club: str | None = None,
) -> MatchMeta:
    return MatchMeta(
        match_id=match_id,
        home=home_team(home_club),
        away=away_team(away_club),
        venue="Live feed",
        competition="Premier League (live)",
    )


class EventSource(ABC):
    meta: MatchMeta
    realtime: bool = False

    @abstractmethod
    async def stream_events(self) -> AsyncIterator[MatchEvent]:
        ...

    async def aclose(self) -> None:
        return None


class SyntheticSource(EventSource):
    realtime = False

    def __init__(
        self,
        seed: int | None = None,
        home_club: str | None = None,
        away_club: str | None = None,
    ) -> None:
        simulator = MatchSimulator(
            seed if seed is not None else 20261015,
            home_club=home_club,
            away_club=away_club,
        )
        self.meta, self.events = simulator.simulate()

    async def stream_events(self) -> AsyncIterator[MatchEvent]:
        for ev in self.events:
            yield ev


class ReplaySource(EventSource):
    realtime = True

    def __init__(self, meta: MatchMeta, events: list[MatchEvent]) -> None:
        self.meta = meta
        self.events = events

    @classmethod
    def from_jsonl(cls, path: str, meta: MatchMeta | None = None) -> "ReplaySource":
        events: list[MatchEvent] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(normalize_event(json.loads(line)))
        return cls(meta or default_feed_meta(), events)

    async def stream_events(self) -> AsyncIterator[MatchEvent]:
        for ev in self.events:
            yield ev


class EventHubSource(EventSource):
    """Consumes a live feed from Azure Event Hubs (lazy dependency)."""

    realtime = True

    def __init__(
        self,
        connection_string: str,
        eventhub_name: str,
        consumer_group: str = "$Default",
        meta: MatchMeta | None = None,
        normalizer: Callable[[dict], MatchEvent] = normalize_event,
    ) -> None:
        self.connection_string = connection_string
        self.eventhub_name = eventhub_name
        self.consumer_group = consumer_group
        self.meta = meta or default_feed_meta()
        self.normalizer = normalizer

    @classmethod
    def from_settings(cls, settings) -> "EventHubSource":
        return cls(
            settings.eventhub_connection,
            settings.eventhub_name,
            settings.eventhub_consumer_group,
            meta=default_feed_meta(
                "LIVE-FEED", settings.home_team, settings.away_team
            ),
        )

    async def stream_events(self) -> AsyncIterator[MatchEvent]:
        from azure.eventhub.aio import EventHubConsumerClient

        client = EventHubConsumerClient.from_connection_string(
            self.connection_string,
            consumer_group=self.consumer_group,
            eventhub_name=self.eventhub_name,
        )
        queue: list[MatchEvent] = []

        async def on_event(partition_context, event) -> None:
            if event is None:
                return
            try:
                payload = json.loads(event.body_as_str())
            except Exception:
                return
            queue.append(self.normalizer(payload))
            await partition_context.update_checkpoint(event)

        async with client:
            receiver = client.receive(on_event=on_event, starting_position="-1")
            async with receiver:
                while True:
                    if queue:
                        yield queue.pop(0)
                    else:
                        import asyncio

                        await asyncio.sleep(0.05)


def get_source(
    settings,
    seed: int | None = None,
    home_club: str | None = None,
    away_club: str | None = None,
) -> EventSource:
    if settings.data_source == "eventhub" and settings.eventhub_connection:
        return EventHubSource.from_settings(settings)
    return SyntheticSource(
        seed,
        home_club=home_club or settings.home_team,
        away_club=away_club or settings.away_team,
    )
