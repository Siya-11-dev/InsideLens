from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    kickoff = "kickoff"
    pass_event = "pass"
    carry = "carry"
    shot = "shot"
    save = "save"
    goal = "goal"
    tackle = "tackle"
    interception = "interception"
    clearance = "clearance"
    pressure = "pressure"
    foul = "foul"
    card = "card"
    corner = "corner"
    free_kick = "free_kick"
    substitution = "substitution"
    offside = "offside"
    halftime = "halftime"
    fulltime = "fulltime"


class PressureLevel(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"


class Player(BaseModel):
    id: int
    name: str
    number: int
    position: str
    role: str
    x: float
    y: float
    finishing: float = 0.5
    passing: float = 0.5
    pressing: float = 0.5
    pace: float = 0.5


class Team(BaseModel):
    id: str
    name: str
    short: str
    color: str
    formation: str
    players: list[Player]


class MatchEvent(BaseModel):
    id: int
    minute: int
    second: int
    team_id: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    type: EventType
    x: float
    y: float
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    xg: Optional[float] = None
    xg_delta: Optional[float] = None
    outcome: Optional[str] = None
    under_pressure: PressureLevel = PressureLevel.none
    body_part: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""


class Factor(BaseModel):
    name: str
    weight: float
    direction: str
    detail: str


class EvidenceItem(BaseModel):
    label: str
    detail: str
    event_ids: list[int] = Field(default_factory=list)
    metric: Optional[str] = None
    value: Optional[float] = None


class Insight(BaseModel):
    id: str
    kind: str
    minute: int
    team_id: Optional[str] = None
    title: str
    claim: str
    narrative: str = ""
    factors: list[Factor] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: float = 0.5
    counterfactual: Optional[str] = None
    model: str = "local"
    facts: dict[str, float | int | str] = Field(default_factory=dict)
    translations: dict[str, str] = Field(default_factory=dict)


class TeamStats(BaseModel):
    possession: float = 0.0
    shots: int = 0
    shots_on_target: int = 0
    goals: int = 0
    xg: float = 0.0
    passes: int = 0
    passes_completed: int = 0
    pass_accuracy: float = 0.0
    pressures: int = 0
    high_turnovers: int = 0
    final_third_entries: int = 0
    field_tilt: float = 0.0
    press_intensity: float = 0.0
    momentum: float = 0.0


class MomentumPoint(BaseModel):
    minute: int
    home: float
    away: float


class ActivePattern(BaseModel):
    key: str
    label: str
    team_id: str
    strength: float
    since_minute: int


class PitchPlayer(BaseModel):
    id: int
    team_id: str
    number: int
    name: str
    position: str
    x: float
    y: float


class MatchState(BaseModel):
    match_id: str
    minute: int
    second: int
    phase: str = "first_half"
    home: TeamStats = Field(default_factory=TeamStats)
    away: TeamStats = Field(default_factory=TeamStats)
    momentum: list[MomentumPoint] = Field(default_factory=list)
    patterns: list[ActivePattern] = Field(default_factory=list)
    last_event: Optional[MatchEvent] = None
    ball: tuple[float, float] = (50.0, 50.0)
    possession_team: Optional[str] = None
    players: list[PitchPlayer] = Field(default_factory=list)


class MatchMeta(BaseModel):
    match_id: str
    home: Team
    away: Team
    venue: str
    competition: str


class Highlight(BaseModel):
    id: str
    minute: int
    team_id: Optional[str] = None
    event_ids: list[int] = Field(default_factory=list)
    kind: str
    title: str
    description: str
    excitement: float
    reason: str


class Persona(BaseModel):
    id: str
    name: str
    description: str
    role: str = "fan"
    language: str = "en"
    tone: str = "neutral"
    verbosity: str = "standard"
    stat_bias: float = 0.5
    favorite_team: Optional[str] = None


class PersonalizedInsight(BaseModel):
    insight_id: str
    persona_id: str
    language: str
    headline: str
    body: str
    show_factors: bool
    show_evidence: bool
    tone: str

