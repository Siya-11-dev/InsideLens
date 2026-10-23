from __future__ import annotations

import random
from dataclasses import dataclass

from app.data.teams import (
    DEFAULT_AWAY,
    DEFAULT_HOME,
    club_strength,
    away_team,
    get_club,
    home_team,
    venue_for,
)
from app.engine.metrics import (
    attack_dir,
    clamp,
    expected_goals,
    flank_of,
    goal_x,
    zone_of,
)
from app.models import (
    EventType,
    MatchEvent,
    MatchMeta,
    Player,
    PressureLevel,
    Team,
)


ATTACK_ROLES = ["striker", "right_winger", "left_winger", "attacking_midfielder"]


@dataclass
class _Chain:
    team_id: str
    start_minute: int
    passes: int = 0
    carry_meters: float = 0.0
    high_turnover: bool = False
    events: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []


class MatchSimulator:
    def __init__(
        self,
        seed: int = 20261015,
        home_club: str | None = None,
        away_club: str | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.home_club = get_club(home_club or DEFAULT_HOME)
        self.away_club = get_club(away_club or DEFAULT_AWAY)
        self.home = home_team(self.home_club.id)
        self.away = away_team(self.away_club.id)
        self.teams: dict[str, Team] = {"HOME": self.home, "AWAY": self.away}
        home_rating = club_strength(self.home_club.id) + 0.06
        away_rating = club_strength(self.away_club.id)
        self.strength = {
            "HOME": min(0.78, home_rating),
            "AWAY": min(0.78, away_rating),
        }
        self.event_id = 0
        self.ball_x = 50.0
        self.ball_y = 50.0
        self.pos_team = "HOME"
        self.score = {"HOME": 0, "AWAY": 0}
        self.events: list[MatchEvent] = []
        self.halftime_done = False

    # -- helpers ---------------------------------------------------------
    def _other(self, team_id: str) -> str:
        return "AWAY" if team_id == "HOME" else "HOME"

    def _pick_player(
        self,
        team: Team,
        ball_x: float,
        ball_y: float,
        prefer: list[str],
        skill: str,
        restrict: bool = False,
    ) -> Player:
        outfield = [p for p in team.players if p.position != "GK"]
        candidates = outfield
        if restrict:
            candidates = [p for p in outfield if p.role in prefer] or outfield
        weights: list[float] = []
        for p in candidates:
            dist = ((p.x - ball_x) ** 2 + (p.y - ball_y) ** 2) ** 0.5
            proximity = max(0.0, 1.0 - dist / 50.0) ** 2
            role_bonus = 2.2 if p.role in prefer else 0.0
            w = 0.05 + 1.1 * proximity + role_bonus + getattr(p, skill) * 1.0
            weights.append(w)
        return self.rng.choices(candidates, weights=weights, k=1)[0]

    def _emit(
        self,
        minute: int,
        second: int,
        team_id: str | None,
        event_type: EventType,
        x: float,
        y: float,
        player: Player | None = None,
        **kwargs,
    ) -> MatchEvent:
        self.event_id += 1
        ev = MatchEvent(
            id=self.event_id,
            minute=minute,
            second=second,
            team_id=team_id,
            player_id=player.id if player else None,
            player_name=player.name if player else None,
            type=event_type,
            x=round(x, 1),
            y=round(y, 1),
            **kwargs,
        )
        self.events.append(ev)
        return ev

    def _pressure_for(self, team_id: str, adv: float) -> PressureLevel:
        opp = self._other(team_id)
        opp_team = self.teams[opp]
        press = sum(p.pressing for p in opp_team.players if p.position != "GK") / 10.0
        contested = clamp(adv / 100.0)
        score = press * 0.6 + contested * 0.6 + self.rng.uniform(-0.15, 0.15)
        if score > 0.85:
            return PressureLevel.high
        if score > 0.62:
            return PressureLevel.medium
        if score > 0.4:
            return PressureLevel.low
        return PressureLevel.none

    # -- main loop -------------------------------------------------------
    def simulate(self) -> tuple[MatchMeta, list[MatchEvent]]:
        self._emit(0, 0, None, EventType.kickoff, 50, 50, description="Kick-off")
        t = 0
        while t < 5400:
            t += self.rng.randint(2, 6)
            if t > 5400:
                t = 5400
            minute = min(90, t // 60)
            second = t % 60
            if minute >= 45 and not self.halftime_done:
                self.halftime_done = True
                self._emit(45, 0, None, EventType.halftime, 50, 50, description="Half-time")
                self.pos_team = "AWAY"
                self.ball_x, self.ball_y = 50.0, 50.0
                continue
            self._tick(minute, second)
        self._emit(90, 0, None, EventType.fulltime, 50, 50, description="Full-time")
        meta = MatchMeta(
            match_id=f"{self.home.short}-{self.away.short}-2026",
            home=self.home,
            away=self.away,
            venue=venue_for(self.home_club.id),
            competition="Premier League (synthetic feed)",
        )
        return meta, self.events

    def _last_type(self) -> EventType | None:
        return self.events[-1].type if self.events else None

    def _tick(self, minute: int, second: int) -> None:
        team = self.pos_team
        team_obj = self.teams[team]
        d = attack_dir(team)
        own_x = self.ball_x if d > 0 else 100 - self.ball_x
        adv = own_x
        under = self._pressure_for(team, adv)

        progress_bias = self.strength[team]
        shot_threshold = 0.015 + 0.065 * (max(0.0, adv - 75) / 25.0)

        pressure_mult = {
            PressureLevel.none: 0.75,
            PressureLevel.low: 0.9,
            PressureLevel.medium: 1.12,
            PressureLevel.high: 1.4,
        }[under]

        if adv > 75 and self.rng.random() < shot_threshold:
            self._shot(minute, second, team, under)
            return

        turnover = clamp(0.09 * pressure_mult * (1.15 - progress_bias))
        if self.rng.random() < turnover:
            self._turnover(minute, second, team, under)
            return

        if self.rng.random() < 0.3:
            self._carry(minute, second, team)
        else:
            self._pass(minute, second, team, under)

    def _pass(self, minute: int, second: int, team: str, under: PressureLevel) -> None:
        team_obj = self.teams[team]
        d = attack_dir(team)
        passer = self._pick_player(
            team_obj, self.ball_x, self.ball_y, ["central_midfielder", "defensive_midfielder", "attacking_midfielder", "goalkeeper"], "passing"
        )
        aim_x = clamp(self.ball_x + d * self.rng.uniform(6, 22), 2, 98)
        aim_y = clamp(self.ball_y + self.rng.gauss(0, 12), 3, 97)
        receiver = self._pick_player(team_obj, aim_x, aim_y, [], "passing")
        end_x = gen_x = clamp(aim_x + self.rng.gauss(0, 4), 2, 98)
        end_y = clamp(aim_y + self.rng.gauss(0, 5), 3, 97)

        accuracy = clamp(0.62 + passer.passing * 0.35 - pressure_mult_val(under) * 0.12)
        complete = self.rng.random() < accuracy
        outcome = "complete" if complete else "incomplete"
        self._emit(
            minute,
            second,
            team,
            EventType.pass_event,
            self.ball_x,
            self.ball_y,
            player=passer,
            end_x=gen_x,
            end_y=end_y,
            outcome=outcome,
            under_pressure=under,
            description=f"{passer.name} {'finds' if complete else 'mistimes a pass to'} {receiver.name}",
        )
        if complete:
            self.ball_x, self.ball_y = end_x, end_y
        else:
            self.pos_team = self._other(team)
            self.ball_x, self.ball_y = end_x, end_y

    def _carry(self, minute: int, second: int, team: str) -> None:
        team_obj = self.teams[team]
        d = attack_dir(team)
        player = self._pick_player(team_obj, self.ball_x, self.ball_y, ATTACK_ROLES, "pace", restrict=True)
        dist = self.rng.uniform(3, 12) * (0.7 + player.pace * 0.6)
        end_x = clamp(self.ball_x + d * dist, 3, 97)
        end_y = clamp(self.ball_y + self.rng.gauss(0, 7), 3, 97)
        self._emit(
            minute,
            second,
            team,
            EventType.carry,
            self.ball_x,
            self.ball_y,
            player=player,
            end_x=end_x,
            end_y=end_y,
            outcome="complete",
            description=f"{player.name} drives forward",
        )
        self.ball_x, self.ball_y = end_x, end_y

    def _turnover(self, minute: int, second: int, team: str, under: PressureLevel) -> None:
        opp = self._other(team)
        opp_team = self.teams[opp]
        d = attack_dir(team)
        own_x = self.ball_x if d > 0 else 100 - self.ball_x
        center = ["defensive_midfielder", "centre_back", "central_midfielder"]
        defender = self._pick_player(opp_team, self.ball_x, self.ball_y, center, "pressing")
        forced_high = own_x > 60
        if under in (PressureLevel.high, PressureLevel.medium) or forced_high:
            etype = EventType.tackle if self.rng.random() < 0.5 else EventType.interception
            tags = ["high_turnover"] if forced_high else []
            self._emit(
                minute,
                second,
                opp,
                etype,
                self.ball_x,
                self.ball_y,
                player=defender,
                outcome="won",
                tags=tags,
                description=f"{defender.name} wins it back for {opp_team.short}",
            )
        else:
            self._emit(
                minute,
                second,
                opp,
                EventType.pressure,
                self.ball_x,
                self.ball_y,
                player=defender,
                outcome="applied",
                description=f"{defender.name} closes down",
            )
        self.pos_team = opp

    def _shot(self, minute: int, second: int, team: str, under: PressureLevel) -> None:
        team_obj = self.teams[team]
        shooter = self._pick_player(team_obj, self.ball_x, self.ball_y, ATTACK_ROLES, "finishing", restrict=True)
        xg = expected_goals(team, self.ball_x, self.ball_y)
        finishing_bonus = 0.55 + shooter.finishing * 0.2
        roll = self.rng.random()
        body = "right foot" if self.rng.random() < 0.7 else "left foot"
        big_chance = xg >= 0.2
        key = ["key_moment"] if big_chance else []

        if roll < xg * finishing_bonus:
            self.score[team] += 1
            self._emit(
                minute,
                second,
                team,
                EventType.goal,
                self.ball_x,
                self.ball_y,
                player=shooter,
                end_x=goal_x(team),
                end_y=50 + self.rng.gauss(0, 4),
                xg=xg,
                xg_delta=xg,
                outcome="goal",
                under_pressure=under,
                body_part=body,
                tags=["goal", "key_moment"],
                description=f"GOAL! {shooter.name} scores for {team_obj.short}",
            )
            self._restart(team)
            return
        if roll < xg * finishing_bonus + 0.26:
            self._emit(
                minute,
                second,
                team,
                EventType.save,
                self.ball_x,
                self.ball_y,
                player=shooter,
                xg=xg,
                xg_delta=xg,
                outcome="saved",
                under_pressure=under,
                body_part=body,
                tags=key + ["on_target"],
                description=f"{shooter.name} forces a save",
            )
            self._corner_or_restart(team, minute, second)
            return
        if roll < xg * finishing_bonus + 0.52:
            self._emit(
                minute,
                second,
                team,
                EventType.shot,
                self.ball_x,
                self.ball_y,
                player=shooter,
                xg=xg,
                xg_delta=xg,
                outcome="blocked",
                under_pressure=under,
                body_part=body,
                tags=key + ["blocked"],
                description=f"{shooter.name}'s effort is blocked",
            )
            self._corner_or_restart(team, minute, second)
            return
        self._emit(
            minute,
            second,
            team,
            EventType.shot,
            self.ball_x,
            self.ball_y,
            player=shooter,
            xg=xg,
            xg_delta=xg,
            outcome="off_target",
            under_pressure=under,
            body_part=body,
            tags=key + ["off_target"],
            description=f"{shooter.name} shoots off target",
        )
        self._restart(self._other(team))

    def _corner_or_restart(self, team: str, minute: int, second: int) -> None:
        if self.rng.random() < 0.45:
            corner_x = 100.0 if attack_dir(team) > 0 else 0.0
            corner_y = 2.0 if self.rng.random() < 0.5 else 98.0
            self._emit(
                minute,
                second,
                team,
                EventType.corner,
                corner_x,
                corner_y,
                end_x=goal_x(self._other(team)),
                end_y=50.0,
                tags=["set_piece"],
                description=f"Corner for {self.teams[team].short}",
            )
            self._resolve_corner(team, minute, second)
        else:
            self._restart(self._other(team))

    def _resolve_corner(self, team: str, minute: int, second: int) -> None:
        team_obj = self.teams[team]
        d = attack_dir(team)
        origin_x = goal_x(team) - d * 4.0
        roll = self.rng.random()
        if roll < 0.08:
            scorer = self._pick_player(team_obj, goal_x(team), 50.0, ["centre_back"], "finishing", restrict=True)
            xg = round(self.rng.uniform(0.08, 0.28), 2)
            self.score[team] += 1
            self._emit(
                minute,
                second,
                team,
                EventType.goal,
                origin_x,
                50.0,
                player=scorer,
                end_x=goal_x(team),
                end_y=50 + self.rng.gauss(0, 3),
                xg=xg,
                xg_delta=xg,
                outcome="goal",
                body_part="header",
                tags=["goal", "key_moment", "set_piece"],
                description=f"GOAL! {scorer.name} heads home from the corner",
            )
            self._restart(self._other(team))
            return
        if roll < 0.22:
            scorer = self._pick_player(team_obj, goal_x(team), 50.0, ["centre_back", "striker"], "finishing", restrict=True)
            xg = round(self.rng.uniform(0.05, 0.20), 2)
            self._emit(
                minute,
                second,
                team,
                EventType.save,
                origin_x,
                50.0,
                player=scorer,
                xg=xg,
                xg_delta=xg,
                outcome="saved",
                body_part="header",
                tags=["set_piece", "on_target"],
                description=f"{scorer.name}'s header from the corner is kept out",
            )
            self._restart(self._other(team))
            return
        self.ball_x, self.ball_y = 88.0 if d > 0 else 12.0, 50.0
        self.pos_team = team

    def _restart(self, team: str) -> None:
        self.pos_team = team
        if team == "HOME":
            self.ball_x, self.ball_y = 30.0, 50.0
        else:
            self.ball_x, self.ball_y = 70.0, 50.0


def pressure_mult_val(under: PressureLevel) -> float:
    return {
        PressureLevel.none: 0.0,
        PressureLevel.low: 0.3,
        PressureLevel.medium: 0.6,
        PressureLevel.high: 1.0,
    }[under]
