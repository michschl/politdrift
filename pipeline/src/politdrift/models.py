"""Pydantic models: the data contract of the pipeline (KONZEPT 4.2 and 2.2)."""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from politdrift.axes import Axis

Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")]
BodyId = Annotated[str, Field(pattern=r"^[a-z]{2}(?:_[a-z]{2})?$")]  # nr, sr, zh_kr, ...


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


# --- Core entities (DuckDB tables) ---------------------------------------------------------


class Level(StrEnum):
    FEDERAL = "federal"
    CANTONAL = "cantonal"


class Coverage(StrEnum):
    BALLOTS = "ballots"  # individual votes available
    AGGREGATE = "aggregate"  # only totals
    NONE = "none"  # no individual votes published


class Body(Strict):
    body_id: BodyId
    name: str
    level: Level
    source: str
    coverage: Coverage


class Legislature(Strict):
    body_id: BodyId
    legislature: int = Field(ge=1)
    start: dt.date
    end: dt.date | None = None


class Session(Strict):
    session_id: str
    body_id: BodyId
    legislature: int = Field(ge=1)
    name: str
    start: dt.date
    end: dt.date


class Person(Strict):
    person_id: str = Field(description="Stable id: '<source>:<source id>'", pattern=r"^[a-z]+:.+$")
    first_name: str
    last_name: str
    canton: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")


class Membership(Strict):
    person_id: str
    body_id: BodyId
    start: dt.date
    end: dt.date | None = None
    party: str | None = None
    parl_group: str | None = None
    seat: int | None = None


class Vote(Strict):
    vote_id: int
    body_id: BodyId
    session_id: str
    date: dt.datetime
    business: str | None = None
    title: str
    subject: str | None = None
    meaning_yes: str | None = None
    meaning_no: str | None = None
    result: str | None = None


class Decision(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"
    ABSENT = "absent"
    EXCUSED = "excused"
    PRESIDENT = "president"  # presiding, did not vote


class Ballot(Strict):
    vote_id: int
    person_id: str
    decision: Decision


# --- Axis mappings (data/mappings/<body>/<legislature>.yaml) -------------------------------


class MappingSource(StrEnum):
    SMARTVOTE = "smartvote"
    MANUAL = "manual"
    LLM = "llm"


class AxisAssignment(Strict):
    axis: Axis
    direction: Literal[-1, 1] = Field(description="+1: a yes vote points in axis direction")
    weight: float = Field(gt=0, le=1)


class AxisMapping(Strict):
    vote_id: int = Field(ge=1)
    business: str | None = Field(default=None, pattern=r"^\d{2}\.\d{3,4}$")
    title: str = Field(min_length=1)
    axes: list[AxisAssignment] = Field(default_factory=list[AxisAssignment], max_length=3)
    topics: list[Slug] = Field(default_factory=list[Slug])
    source: MappingSource
    confidence: float = Field(ge=0, le=1)
    contested: bool = False
    reviewed: bool = False
    reviewed_by: str | None = None
    reviewed_at: dt.date | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        axes = [a.axis for a in self.axes]
        if len(axes) != len(set(axes)):
            raise ValueError("an axis may be assigned only once per vote")
        if self.reviewed and (self.reviewed_by is None or self.reviewed_at is None):
            raise ValueError("reviewed mappings need reviewed_by and reviewed_at")
        if not self.reviewed and (self.reviewed_by is not None or self.reviewed_at is not None):
            raise ValueError("reviewed_by/reviewed_at set but reviewed is false")
        if not self.axes and not self.topics:
            raise ValueError("a mapping needs at least one axis or topic")
        return self


# --- Derived profiles ----------------------------------------------------------------------


class WindowKind(StrEnum):
    SESSION = "session"
    ROLLING4 = "rolling4"
    LEGISLATURE = "legislature"


class VotingProfileValue(Strict):
    person_id: str
    window: str
    window_kind: WindowKind
    axis: Axis
    score: float | None = Field(ge=0, le=100)
    n: int = Field(ge=0)


class ElectionProfileValue(Strict):
    person_id: str
    election: str
    axis: Axis
    score: float = Field(ge=0, le=100)
