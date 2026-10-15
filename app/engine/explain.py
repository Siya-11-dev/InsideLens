from __future__ import annotations

from dataclasses import dataclass

from app.engine.analytics import MatchAnalytics
from app.engine.metrics import zone_of
from app.engine.patterns import _other
from app.models import (
    ActivePattern,
    EvidenceItem,
    EventType,
    Factor,
    Insight,
    MatchEvent,
    MatchMeta,
    Player,
)


@dataclass
class ExplanationContext:
    meta: MatchMeta
    analytics: MatchAnalytics
    events: list[MatchEvent]

    def team_short(self, team_id: str) -> str:
        if team_id == self.meta.home.id:
            return self.meta.home.short
        return self.meta.away.short

    def team_name(self, team_id: str) -> str:
        if team_id == self.meta.home.id:
            return self.meta.home.name
        return self.meta.away.name

    def player(self, team_id: str, player_id: int | None) -> Player | None:
        team = self.meta.home if team_id == self.meta.home.id else self.meta.away
        if player_id is None:
            return None
        for p in team.players:
            if p.id == player_id:
                return p
        return None


def _t(ev: MatchEvent) -> float:
    return ev.minute * 60 + ev.second


def _index_of(events: list[MatchEvent], ev: MatchEvent) -> int:
    for i, e in enumerate(events):
        if e.id == ev.id:
            return i
    return len(events) - 1


def _build_up(goal: MatchEvent, ctx: ExplanationContext, max_seconds: int = 80) -> list[MatchEvent]:
    i = _index_of(ctx.events, goal)
    team = goal.team_id
    seq: list[MatchEvent] = []
    end_t = _t(goal)
    for e in reversed(ctx.events[:i]):
        if end_t - _t(e) > max_seconds:
            break
        if e.type in (EventType.kickoff, EventType.halftime, EventType.fulltime):
            break
        if e.team_id == team:
            seq.append(e)
        elif e.type in (EventType.corner, EventType.free_kick):
            seq.append(e)
        elif e.type in (EventType.tackle, EventType.interception) and e.tags and "high_turnover" in e.tags:
            seq.append(e)
            break
        else:
            break
    seq.reverse()
    return seq


def explain_shot(event: MatchEvent, ctx: ExplanationContext) -> Insight:
    is_goal = event.type == EventType.goal
    goal = event
    team = goal.team_id or "HOME"
    opp = _other(team)
    seq = _build_up(goal, ctx)
    passes = [e for e in seq if e.type == EventType.pass_event and e.outcome == "complete"]
    carries = [e for e in seq if e.type == EventType.carry]
    turnovers = [e for e in seq if e.type in (EventType.tackle, EventType.interception)]
    setpiece = [e for e in seq if e.type in (EventType.corner, EventType.free_kick)]
    xg = goal.xg or 0.0
    shooter = ctx.player(team, goal.player_id)

    momentum = ctx.analytics.stats_for(team).momentum
    opp_stats = ctx.analytics.stats_for(opp)
    recent_opp_shots = [
        e
        for e in ctx.events
        if e.team_id == opp
        and e.type in (EventType.shot, EventType.save, EventType.goal)
        and _t(goal) - _t(e) <= 600
    ]

    raw: dict[str, float] = {
        "Build-up": min(1.0, len(passes) / 6.0) * 0.9 + min(1.0, len(carries) / 3.0) * 0.4,
        "Ball recovery": 0.75 if turnovers else 0.0,
        "Shot quality": min(1.0, xg * 3.0),
        "Momentum": min(1.0, max(0.0, momentum) / 8.0),
        "Set piece": 0.8 if setpiece else 0.0,
        "Opponent under pressure": min(1.0, len(recent_opp_shots) / 4.0),
        "Individual finish": (shooter.finishing if shooter else 0.6) * 0.7,
    }
    total = sum(raw.values()) or 1.0
    factors: list[Factor] = []
    for name, value in raw.items():
        if value <= 0:
            continue
        factors.append(
            Factor(
                name=name,
                weight=round(value / total, 3),
                direction="supports",
                detail=_factor_detail(name, passes, turnovers, setpiece, xg, momentum, recent_opp_shots, shooter),
            )
        )
    factors.sort(key=lambda f: f.weight, reverse=True)

    evidence: list[EvidenceItem] = [
        EvidenceItem(
            label="Build-up",
            detail=f"{len(passes)} completed passes and {len(carries)} carries in the {int(_t(goal)-_t(seq[0])) if seq else 0}s before the shot",
            event_ids=[e.id for e in seq][-8:],
            metric="passes",
            value=float(len(passes)),
        ),
        EvidenceItem(
            label="Chance quality",
            detail=f"Expected goals (xG) for this shot: {xg}",
            metric="xg",
            value=xg,
        ),
    ]
    if turnovers:
        t0 = turnovers[-1]
        evidence.append(
            EvidenceItem(
                label="Turnover won",
                detail=f"{ctx.team_short(team)} won possession in a high area (min {t0.minute})",
                event_ids=[t0.id],
                metric="high_turnover",
                value=1.0,
            )
        )
    if setpiece:
        evidence.append(
            EvidenceItem(
                label="Set piece",
                detail=f"Move originated from a {setpiece[-1].type.value.replace('_',' ')}",
                event_ids=[e.id for e in setpiece],
            )
        )
    evidence.append(
        EvidenceItem(
            label="Defensive record",
            detail=f"{ctx.team_short(opp)} had faced {len(recent_opp_shots)} shots in the previous 10 minutes",
            metric="opp_shots_10m",
            value=float(len(recent_opp_shots)),
        )
    )

    confidence = _clamp(0.42 + min(0.35, xg * 2.6) + min(0.15, len(seq) / 40.0), 0.4, 0.95)
    counterfactual = _goal_counterfactual(factors, seq, xg, ctx, team, opp, turns=turnovers)

    title = (
        f"Goal — {ctx.team_short(team)} ({goal.minute}')"
        if is_goal
        else f"Big chance — {ctx.team_short(team)} ({goal.minute}')"
    )
    if is_goal:
        claim = (
            f"{goal.player_name} scored for {ctx.team_short(team)} from a move worth {xg:.2f} xG "
            f"after {len(passes)} passes."
        )
        kind = "goal_explanation"
    else:
        claim = (
            f"{goal.player_name} ({ctx.team_short(team)}) carved out a {xg:.2f} xG chance that was "
            f"saved, after {len(passes)} passes."
        )
        kind = "chance_explanation"
    return Insight(
        id=f"goal-{goal.id}",
        kind=kind,
        minute=goal.minute,
        team_id=team,
        title=title,
        claim=claim,
        factors=factors,
        evidence=evidence,
        confidence=round(confidence, 2),
        counterfactual=counterfactual,
        facts={
            "player": goal.player_name or "the forward",
            "team": ctx.team_short(team),
            "opponent": ctx.team_short(opp),
            "minute": goal.minute,
            "xg": round(xg, 2),
            "passes": len(passes),
            "carries": len(carries),
            "top_factor": factors[0].name if factors else "",
        },
    )


def _factor_detail(name, passes, turnovers, setpiece, xg, momentum, opp_shots, shooter) -> str:
    if name == "Build-up":
        return f"{len(passes)} completed passes in the sequence"
    if name == "Ball recovery":
        return "Start of the move came from a high turnover"
    if name == "Shot quality":
        return f"Shot carried {xg:.2f} xG"
    if name == "Momentum":
        return f"Attacking momentum was {momentum:.1f} at the time"
    if name == "Set piece":
        return "Chance originated from a set piece"
    if name == "Opponent under pressure":
        return f"Opponent had faced {len(opp_shots)} shots in 10 minutes"
    if name == "Individual finish":
        return f"{shooter.name if shooter else 'Forward'} conversion profile"
    return name


def _goal_counterfactual(factors, seq, xg, ctx, team, opp, turns) -> str:
    names = [f.name for f in factors]
    if turns:
        t0 = turns[-1]
        return (
            f"Counterfactual: had {ctx.team_short(opp)} cleared the ball at minute {t0.minute} "
            f"instead of conceding the turnover, the move would not have started."
        )
    if xg >= 0.25:
        return (
            f"Counterfactual: if {ctx.team_short(opp)}'s defensive line had compressed the space faster, "
            f"this chance's xG would fall from {xg:.2f} to approximately {xg*0.35:.2f}."
        )
    if "Set piece" in names:
        return (
            f"Counterfactual: had {ctx.team_short(opp)} defended the first contact from the set piece, "
            f"the chance would likely not develop."
        )
    if len(seq) >= 8:
        return (
            f"Counterfactual: if {ctx.team_short(opp)} had won the ball back inside the first "
            f"{max(2, len(seq)//2)} passes, the move would not have reached the box."
        )
    return (
        f"Counterfactual: with tighter pressing on the ball carrier, {ctx.team_short(team)}'s "
        f"expected goals on this move would drop materially."
    )


def explain_pattern(pattern: ActivePattern, ctx: ExplanationContext) -> Insight:
    team = pattern.team_id
    opp = _other(team)
    window = ctx.analytics.recent(ctx.events, 420)
    team_window = [e for e in window if e.team_id == team]
    opp_window = [e for e in window if e.team_id == opp]

    factors: list[Factor] = []
    evidence: list[EvidenceItem] = []
    counterfactual = ""
    confidence = 0.5

    if pattern.key == "high_press":
        turnovers = [e for e in team_window if "high_turnover" in e.tags]
        pressures = [e for e in team_window if e.type == EventType.pressure]
        opp_acc = ctx.analytics.stats_for(opp).pass_accuracy
        factors = [
            Factor(name="High turnovers", weight=0.5, direction="supports", detail=f"{len(turnovers)} recoveries in opponent half"),
            Factor(name="Pressing volume", weight=0.3, direction="supports", detail=f"{len(pressures)} pressures applied"),
            Factor(name="Opponent pass accuracy", weight=0.2, direction="supports", detail=f"{ctx.team_short(opp)} completing {opp_acc}% of passes"),
        ]
        evidence = [
            EvidenceItem(label="Regains", detail=f"{len(turnovers)} high turnovers in the last 7 minutes", event_ids=[e.id for e in turnovers][-6:], metric="high_turnovers", value=float(len(turnovers))),
        ]
        counterfactual = (
            f"Counterfactual: if {ctx.team_short(team)} dropped their line 10 metres, "
            f"{ctx.team_short(opp)} would regain time on the ball and turnovers would fall."
        )
        confidence = _clamp(0.45 + 0.1 * len(turnovers), 0.4, 0.9)
    elif pattern.key == "low_block":
        opp_final = [e for e in opp_window if zone_of(opp, e.x) == "attacking_third"]
        deep = [e for e in team_window if e.type in (EventType.pass_event, EventType.carry)]
        factors = [
            Factor(name="Opponent territory", weight=0.55, direction="supports", detail=f"{len(opp_final)} touches in the final third"),
            Factor(name="Deep defending", weight=0.45, direction="supports", detail=f"{len(deep)} passes inside own half"),
        ]
        evidence = [EvidenceItem(label="Territorial pressure", detail=f"{ctx.team_short(opp)} camped in the attacking third", event_ids=[e.id for e in opp_final][-6:])]
        counterfactual = (
            f"Counterfactual: if {ctx.team_short(team)} pushed their defensive line higher, "
            f"they could turn defence into a counter-attacking platform."
        )
        confidence = _clamp(0.45 + 0.05 * len(opp_final), 0.4, 0.9)
    elif pattern.key == "sustained_pressure":
        entries = [e for e in team_window if zone_of(team, e.x) == "attacking_third"]
        factors = [Factor(name="Final-third entries", weight=1.0, direction="supports", detail=f"{len(entries)} entries in the last 5 minutes")]
        evidence = [EvidenceItem(label="Pressure phase", detail=f"{ctx.team_short(team)} repeatedly reaching the final third", event_ids=[e.id for e in entries][-8:])]
        counterfactual = f"Counterfactual: a single clearance would reset {ctx.team_short(team)}'s pressure phase."
        confidence = _clamp(0.4 + 0.06 * len(entries), 0.4, 0.9)
    elif pattern.key.endswith("_overload"):
        side = pattern.key.replace("_overload", "")
        share = ctx.analytics.flank_share(team).get(side, 0)
        factors = [Factor(name=f"{side.title()} overload", weight=1.0, direction="supports", detail=f"{share}% of attacks down the {side}")]
        side_events = [e for e in team_window if (e.y <= 33.33 if side == "left" else e.y >= 66.67)]
        evidence = [EvidenceItem(label="Flank bias", detail=f"{share}% of attacking actions down the {side}", event_ids=[e.id for e in side_events][-8:], metric="flank_share", value=share)]
        counterfactual = f"Counterfactual: if {ctx.team_short(opp)} shifted their block to the {side}, space would open on the opposite flank."
        confidence = _clamp(0.4 + share / 400.0, 0.4, 0.9)
    elif pattern.key == "set_piece_threat":
        corners = [e for e in team_window if e.type == EventType.corner]
        factors = [Factor(name="Set-piece volume", weight=1.0, direction="supports", detail=f"{len(corners)} corners in the window")]
        evidence = [EvidenceItem(label="Set pieces", detail=f"{len(corners)} corners delivered", event_ids=[e.id for e in corners], metric="corners", value=float(len(corners)))]
        counterfactual = f"Counterfactual: better first-contact defending would neutralise this threat."
        confidence = _clamp(0.4 + 0.1 * len(corners), 0.4, 0.9)
    else:
        factors = [Factor(name="Transition speed", weight=0.6, direction="supports", detail="Ball won deep and moved forward quickly"), Factor(name="Directness", weight=0.4, direction="supports", detail="Few passes before reaching the final third")]
        evidence = [EvidenceItem(label="Transitions", detail="Recent transitions from defence into attack", event_ids=[e.id for e in team_window][-6:])]
        counterfactual = f"Counterfactual: keeping a rest-defence structure would slow these transitions."
        confidence = 0.55

    return Insight(
        id=f"pattern-{pattern.key}-{team}-{pattern.since_minute}",
        kind="tactical_pattern",
        minute=ctx.events[-1].minute if ctx.events else pattern.since_minute,
        team_id=team,
        title=pattern.label,
        claim=f"{pattern.label} — detected with strength {pattern.strength:.2f}.",
        factors=factors,
        evidence=evidence,
        confidence=round(confidence, 2),
        counterfactual=counterfactual,
        facts={
            "pattern_key": pattern.key,
            "team": ctx.team_short(team),
            "opponent": ctx.team_short(opp),
            "strength": round(pattern.strength, 2),
            "minute": ctx.events[-1].minute if ctx.events else pattern.since_minute,
            "top_factor": factors[0].name if factors else "",
        },
    )


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
