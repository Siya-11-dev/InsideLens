from __future__ import annotations

import asyncio
from typing import AsyncIterator

from app.config import get_settings
from app.data.sources import EventSource, SyntheticSource
from app.engine import highlights as highlights_engine
from app.engine import narrative
from app.engine import patterns as pattern_engine
from app.engine import personas as persona_engine
from app.engine.analytics import MatchAnalytics
from app.engine.explain import ExplanationContext, explain_pattern, explain_shot
from app.engine.i18n import localize
from app.engine.narrative import LANGUAGES as codes
from app.engine.pitch import positions_frame
from app.llm.factory import get_llm
from app.models import (
    ActivePattern,
    EventType,
    Insight,
    MatchEvent,
    MatchState,
)
from app.store.dataset import export_dataset
from app.store.factory import get_repository


class MatchPipeline:
    def __init__(
        self,
        seed: int | None = None,
        source: EventSource | None = None,
        home_team: str | None = None,
        away_team: str | None = None,
    ) -> None:
        self.settings = get_settings()
        self.seed = seed if seed is not None else self.settings.match_seed
        self.source = source or SyntheticSource(
            self.seed,
            home_club=home_team or self.settings.home_team,
            away_club=away_team or self.settings.away_team,
        )
        self.meta = self.source.meta
        self.events: list[MatchEvent] = list(getattr(self.source, "events", []))
        self._received: list[MatchEvent] = []
        self.analytics = MatchAnalytics()
        self.llm = get_llm()
        self.repository = get_repository()
        self.insights: list[Insight] = []
        self.current_patterns: list[ActivePattern] = []
        self._pattern_cooldown: dict[tuple[str, str], int] = {}
        self._last_minute = -1
        self._analyzed = False
        self._ctx = ExplanationContext(meta=self.meta, analytics=self.analytics, events=self._received)

    @property
    def shorts(self) -> dict[str, str]:
        return {self.meta.home.id: self.meta.home.short, self.meta.away.id: self.meta.away.short}

    @property
    def _analysis_events(self) -> list[MatchEvent]:
        return self.events if self.events else self._received

    def init_frame(self) -> dict:
        return {
            "type": "match_init",
            "match": self.meta.model_dump(),
            "languages": list(codes),
            "personas": [p.model_dump() for p in persona_engine.list_personas()],
            "llm": self.llm.name,
            "translator": "azure" if self.settings.azure_translator_ready else "local",
            "store": self.repository.name,
            "source": type(self.source).__name__,
            "realtime": self.source.realtime,
            "stream_speed": self.settings.stream_speed,
        }

    def _state(self, ev: MatchEvent) -> MatchState:
        home, away = self.analytics.snapshot()
        phase = "first_half" if ev.minute < 45 else "second_half"
        ball_x = ev.end_x if ev.end_x is not None else ev.x
        ball_y = ev.end_y if ev.end_y is not None else ev.y
        possession = ev.team_id or self.analytics.possession_team()
        return MatchState(
            match_id=self.meta.match_id,
            minute=ev.minute,
            second=ev.second,
            phase=phase,
            home=home,
            away=away,
            momentum=self.analytics.momentum,
            patterns=self.current_patterns,
            last_event=ev,
            ball=(ball_x, ball_y),
            possession_team=possession,
            players=positions_frame(self.meta.home, self.meta.away, ball_x, ball_y, possession),
        )

    def _detect_patterns(self, ev: MatchEvent) -> list[Insight]:
        self.current_patterns = pattern_engine.detect(self.analytics, self._received, self.shorts)
        produced: list[Insight] = []
        for p in self.current_patterns:
            if p.strength < 0.45:
                continue
            key = (p.key, p.team_id)
            if ev.minute - self._pattern_cooldown.get(key, -999) >= 20:
                self._pattern_cooldown[key] = ev.minute
                produced.append(explain_pattern(p, self._ctx))
        return produced

    async def _emit_pending(
        self, pending: list[Insight], persona_id: str | None
    ) -> AsyncIterator[dict]:
        persona = persona_engine.get_persona(persona_id) if persona_id else None
        for insight in pending:
            await localize(insight, self.llm)
            if persona:
                insight.narrative = insight.translations.get(persona.language) or insight.narrative
            self.insights.append(insight)
            try:
                self.repository.save_many(self.meta.match_id, [insight])
            except Exception:
                pass
            yield {"type": "insight", "insight": insight.model_dump()}

    async def stream(
        self, speed: float | None = None, persona_id: str | None = None
    ) -> AsyncIterator[dict]:
        speed = speed or self.settings.stream_speed
        yield self.init_frame()
        await asyncio.sleep(0.05)

        batch: list[MatchEvent] = []
        pending: list[Insight] = []
        last_flush_t = 0.0
        last_ev: MatchEvent | None = None

        async for ev in self.source.stream_events():
            self.analytics.consume(ev)
            self._received.append(ev)
            batch.append(ev)
            last_ev = ev

            if ev.type == EventType.goal:
                pending.append(explain_shot(ev, self._ctx))
            elif ev.type == EventType.save and (ev.xg or 0) >= 0.3:
                pending.append(explain_shot(ev, self._ctx))

            minute_changed = ev.minute != self._last_minute
            if minute_changed and ev.minute > 0:
                pending.extend(self._detect_patterns(ev))
            self._last_minute = ev.minute

            if minute_changed or len(batch) >= 18:
                yield {"type": "tick", "state": self._state(ev).model_dump()}
                async for frame in self._emit_pending(pending, persona_id):
                    yield frame
                pending = []
                batch = []
                if not self.source.realtime:
                    t = ev.minute * 60 + ev.second
                    dt = max(0.0, t - last_flush_t)
                    last_flush_t = t
                    await asyncio.sleep(max(0.01, dt / speed))

        if last_ev is not None and (pending or batch):
            yield {"type": "tick", "state": self._state(last_ev).model_dump()}
            async for frame in self._emit_pending(pending, persona_id):
                yield frame

        home, away = self.analytics.snapshot()
        events = self._analysis_events
        end_state = self._state(events[-1]) if events else None
        highlights = highlights_engine.build_highlights(events, limit=12)
        yield {
            "type": "end",
            "state": end_state.model_dump() if end_state else None,
            "summary": {
                "score": f"{home.goals}-{away.goals}",
                "insights": len(self.insights),
                "highlights": [h.model_dump() for h in highlights],
                "top_insights": [i.model_dump() for i in self.insights[-8:]],
            },
        }
        await self.source.aclose()

    def _ensure_analyzed(self) -> None:
        if self._analyzed:
            return
        events = self._analysis_events
        if not events:
            raise RuntimeError("No events available for analysis; stream the source first.")
        if self.events:
            self._received[:] = self.events
        for ev in events:
            self.analytics.consume(ev)
        self.current_patterns = pattern_engine.detect(self.analytics, events, self.shorts)
        self._analyzed = True

    def analyze_full(self) -> dict:
        self._ensure_analyzed()
        events = self._analysis_events
        home, away = self.analytics.snapshot()
        pattern_insights = [explain_pattern(p, self._ctx) for p in self.current_patterns[:10]]
        goal_insights = [explain_shot(e, self._ctx) for e in events if e.type == EventType.goal]
        highlights = highlights_engine.build_highlights(events, limit=12)
        return {
            "match": self.meta.model_dump(),
            "state": self._state(events[-1]).model_dump(),
            "goals": [i.model_dump() for i in goal_insights],
            "patterns": [i.model_dump() for i in pattern_insights],
            "highlights": [h.model_dump() for h in highlights],
            "score": f"{home.goals}-{away.goals}",
        }

    def highlights(self, persona_id: str | None = None) -> list[dict]:
        items = highlights_engine.build_highlights(self._analysis_events, limit=12)
        if persona_id:
            items = persona_engine.prioritize_highlights(items, persona_engine.get_persona(persona_id))
        return [h.model_dump() for h in items]

    def personalized_insights(self, persona_id: str) -> list[dict]:
        persona = persona_engine.get_persona(persona_id)
        result = self.analyze_full()
        out: list[dict] = []
        for group in ("goals", "patterns"):
            for item in result[group]:
                view = persona_engine.personalize_insight(Insight(**item), persona)
                out.append(view.model_dump())
        return out

    async def recap(self, persona_id: str | None = None) -> str:
        result = self.analyze_full()
        persona = persona_engine.get_persona(persona_id) if persona_id else None
        lang = persona.language if persona else "en"
        local = narrative.match_recap(
            self.meta,
            result["state"]["home"],
            result["state"]["away"],
            result["goals"],
            result["patterns"],
            lang=lang,
        )
        scorers = ", ".join(
            f"{g['facts'].get('player')} {g['facts'].get('minute')}'" for g in result["goals"]
        )
        system = "You are a football broadcast writer. Produce a concise, engaging full-time recap."
        user = (
            f"Final score {result['score']}. Goals by: {scorers}. "
            f"Tactical patterns observed: {', '.join(p['title'] for p in result['patterns'][:5])}. "
            "Write 3-4 sentences."
        )
        generated = await self.llm.compose(system, user)
        if generated:
            if lang != "en":
                translated = await self.llm.translate(generated, lang)
                return translated or generated
            return generated
        if persona:
            return await persona_engine.personalize_recap(local, persona, self.llm)
        return local

    def export(self, fmt: str = "jsonl", upload: bool = False) -> dict:
        from pathlib import Path

        path, rows = export_dataset(self.meta, self._analysis_events, fmt, Path(self.settings.export_dir))
        uploaded = False
        if upload and hasattr(self.repository, "upload_file"):
            remote = f"datasets/{path.name}"
            uploaded = self.repository.upload_file(str(path), remote)
        return {
            "path": str(path),
            "rows": rows,
            "format": path.suffix.lstrip("."),
            "uploaded": uploaded,
        }

    def persist_analysis(self) -> int:
        result = self.analyze_full()
        insights = [Insight(**g) for g in result["goals"]] + [Insight(**p) for p in result["patterns"]]
        return self.repository.save_many(self.meta.match_id, insights)

    def heatmap(self, team_id: str | None = None, bins_x: int = 12, bins_y: int = 8, kind: str | None = None) -> dict:
        from app.engine import viz

        return viz.heatmap(self._analysis_events, bins_x=bins_x, bins_y=bins_y, team_id=team_id, kind=kind)

    def pass_network(self, team_id: str | None = None) -> dict:
        from app.engine import viz

        return viz.pass_network(self._analysis_events, team_id=team_id)

    def expected_threat(self) -> dict:
        from app.engine import viz

        return viz.expected_threat(self._analysis_events)
