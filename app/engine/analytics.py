from __future__ import annotations

from collections import deque

from app.engine.metrics import (
    attack_dir,
    clamp,
    flank_of,
    zone_of,
)
from app.models import (
    ActivePattern,
    EventType,
    MatchEvent,
    MomentumPoint,
    TeamStats,
)


class MatchAnalytics:
    def __init__(self) -> None:
        self.home = TeamStats()
        self.away = TeamStats()
        self.momentum: list[MomentumPoint] = []
        self._ema = {"HOME": 0.0, "AWAY": 0.0}
        self._attacking_threat_total = {"HOME": 0.0, "AWAY": 0.0}
        self._flank_events: dict[str, dict[str, int]] = {
            "HOME": {"left": 0, "central": 0, "right": 0},
            "AWAY": {"left": 0, "central": 0, "right": 0},
        }
        self._final_third: dict[str, int] = {"HOME": 0, "AWAY": 0}
        self._recent_final_third: deque[tuple[int, str]] = deque(maxlen=200)
        self._last_time = 0.0
        self._last_team = "HOME"
        self._possession: dict[str, float] = {"HOME": 0.0, "AWAY": 0.0}
        self._press_events: dict[str, list[int]] = {"HOME": [], "AWAY": []}
        self._minute_buckets: dict[int, dict[str, float]] = {}
        self.current_minute = 0

    def _stats(self, team_id: str) -> TeamStats:
        return self.home if team_id == "HOME" else self.away

    def _time_of(self, ev: MatchEvent) -> float:
        return ev.minute * 60 + ev.second

    def consume(self, ev: MatchEvent) -> None:
        t = self._time_of(ev)
        dt = max(0.0, t - self._last_time)
        if dt > 0:
            self._possession[self._last_team] += dt
        if ev.team_id:
            self._last_team = ev.team_id
        self._last_time = t
        self.current_minute = ev.minute

        if ev.team_id:
            self._apply(ev)
        if ev.minute != (self.momentum[-1].minute if self.momentum else -1):
            self._snapshot_momentum(ev.minute)

    def _apply(self, ev: MatchEvent) -> None:
        team = ev.team_id
        assert team is not None
        stats = self._stats(team)
        threat = self._threat(ev)

        if ev.type == EventType.pass_event:
            stats.passes += 1
            if ev.outcome == "complete":
                stats.passes_completed += 1
        if ev.type in (EventType.shot, EventType.save, EventType.goal):
            stats.shots += 1
            if ev.type in (EventType.save, EventType.goal):
                stats.shots_on_target += 1
            if ev.type == EventType.goal:
                stats.goals += 1
            stats.xg += ev.xg_delta or 0.0
        elif ev.type == EventType.pressure:
            stats.pressures += 1
        if "high_turnover" in ev.tags:
            stats.high_turnovers += 1
        if "set_piece" in ev.tags:
            self._press_events[team].append(ev.minute)

        if zone_of(team, ev.x) == "attacking_third" or (
            ev.end_x is not None and zone_of(team, ev.end_x) == "attacking_third"
        ):
            stats.final_third_entries += 1
            self._final_third[team] += 1
            self._recent_final_third.append((ev.minute, team))
        if zone_of(team, ev.x) in ("attacking_third", "middle_third"):
            self._flank_events[team][flank_of(ev.y)] += 1

        self._update_momentum(team, threat)

    def _update_momentum(self, team: str, threat: float) -> None:
        alpha = 0.09
        other = "AWAY" if team == "HOME" else "HOME"
        self._ema[team] = self._ema[team] * (1 - alpha) + threat * alpha
        self._ema[other] = self._ema[other] * (1 - alpha)

    def _snapshot_momentum(self, minute: int) -> None:
        self.momentum.append(
            MomentumPoint(
                minute=minute,
                home=round(self._ema["HOME"] * 100, 2),
                away=round(self._ema["AWAY"] * 100, 2),
            )
        )

    def _threat(self, ev: MatchEvent) -> float:
        if ev.type == EventType.goal:
            return 1.0
        if ev.type == EventType.save:
            return 0.72
        if ev.type == EventType.shot:
            return 0.4 if ev.outcome != "off_target" else 0.3
        if ev.type in (EventType.tackle, EventType.interception):
            return 0.3 if "high_turnover" in ev.tags else 0.14
        if ev.type == EventType.pressure:
            return 0.08
        if ev.type == EventType.corner:
            return 0.22
        if ev.type in (EventType.pass_event, EventType.carry):
            team = ev.team_id or "HOME"
            z = zone_of(team, ev.x)
            danger = {"attacking_third": 0.18, "middle_third": 0.05, "defensive_third": 0.015}[z]
            return danger
        return 0.02

    def stats_for(self, team_id: str) -> TeamStats:
        return self._stats(team_id)

    def snapshot(self) -> tuple[TeamStats, TeamStats]:
        self._finalise()
        return self.home, self.away

    def _finalise(self) -> None:
        total = self._possession["HOME"] + self._possession["AWAY"]
        if total > 0:
            self.home.possession = round(100 * self._possession["HOME"] / total, 1)
            self.away.possession = round(100 * self._possession["AWAY"] / total, 1)
        for tid in ("HOME", "AWAY"):
            s = self._stats(tid)
            s.pass_accuracy = round(100 * s.passes_completed / s.passes, 1) if s.passes else 0.0
            s.xg = round(s.xg, 2)
            s.momentum = round(self._ema[tid] * 100, 2)
        tilt_total = self._final_third["HOME"] + self._final_third["AWAY"]
        if tilt_total > 0:
            self.home.field_tilt = round(100 * self._final_third["HOME"] / tilt_total, 1)
            self.away.field_tilt = round(100 * self._final_third["AWAY"] / tilt_total, 1)
        minute = max(1, self.current_minute)
        for tid in ("HOME", "AWAY"):
            high = sum(1 for (m, t) in self._recent_final_third if t == tid and m > minute - 15)
            self._stats(tid).press_intensity = round(high / min(15, minute), 2)

    def possession_team(self) -> str:
        return self._last_team

    def flank_share(self, team_id: str) -> dict[str, float]:
        counts = self._flank_events[team_id]
        total = sum(counts.values()) or 1
        return {k: round(100 * v / total, 1) for k, v in counts.items()}

    def recent(self, events: list[MatchEvent], window_seconds: int = 420) -> list[MatchEvent]:
        if not events:
            return []
        cutoff = events[-1].minute * 60 + events[-1].second - window_seconds
        return [e for e in events if self._time_of(e) >= cutoff]
