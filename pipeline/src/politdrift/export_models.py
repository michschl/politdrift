"""Contract of the static export in data/derived/ (KONZEPT 4.3).

The web app reads these files; `politdrift validate --derived` checks them, and
`politdrift export` writes the JSON Schema next to the data (data/derived/schema/).
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from politdrift.axes import Axis
from politdrift.models import Decision, MappingSource, WindowKind

SCHEMA_VERSION = 1


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AxisValue(Out):
    score: float | None = Field(ge=0, le=100, description="0..100, null = too little data")
    n: int = Field(ge=0, description="Number of mapped, cast votes in the window")


Profile = dict[Axis, AxisValue]


class Window(Out):
    id: str = Field(description="session:<id>, rolling4:<last session id> or legislature:<n>")
    kind: WindowKind
    session_id: str | None = Field(description="Last session in the window")
    label: str
    start: dt.date
    end: dt.date


class Source(Out):
    name: str
    url: str
    license: str | None = None


class Meta(Out):
    schema_version: Literal[1] = SCHEMA_VERSION
    pipeline_version: str
    body: str
    legislature: int
    data_as_of: dt.datetime | None = Field(description="Time of the latest vote in the cache")
    sources: list[Source]
    counts: dict[str, int]
    n_min: int


class PersonSummary(Out):
    person_id: str
    slug: str
    first_name: str
    last_name: str
    canton: str | None
    party: str | None
    parl_group: str | None
    seat: int | None
    active: bool
    profile: Profile = Field(description="Rolling window over the last 4 sessions")
    group_distance: float | None = Field(
        ge=0, le=100, description="Fraktionsdrift: mean |person - group| over axes"
    )
    drift: float | None = Field(
        ge=0, le=100, description="Mean axis change between first and latest rolling window"
    )


class Index(Out):
    body: str
    legislature: int
    windows: list[Window]
    current_window: str | None
    persons: list[PersonSummary]


class GroupProfiles(Out):
    group: str
    profiles: dict[str, Profile] = Field(description="window id -> profile")


class Parties(Out):
    body: str
    legislature: int
    windows: list[Window]
    groups: list[GroupProfiles]


class PersonBallot(Out):
    vote_id: int
    decision: Decision
    parl_group: str | None


class PersonDetail(Out):
    person: PersonSummary
    memberships: list[dict[str, str | None]]
    profiles: dict[str, Profile] = Field(description="window id -> profile")
    ballots: list[PersonBallot] = Field(description="Ballots on mapped votes only")


class MappingRef(Out):
    axis: Axis
    direction: Literal[-1, 1]
    weight: float


class Consistency(Out):
    axis: Axis
    rho: float | None = Field(description="Spearman rank correlation, group yes-share vs profile")
    groups: int
    warning: bool


class GroupResult(Out):
    group: str
    counts: dict[Decision, int]
    majority: Decision | None


class Dissenter(Out):
    person_id: str
    group: str
    decision: Decision
    group_majority: Decision


class VoteDetail(Out):
    vote_id: int
    session_id: str
    date: dt.datetime
    business: str | None
    title: str
    subject: str | None
    meaning_yes: str | None
    meaning_no: str | None
    counts: dict[Decision, int]
    groups: list[GroupResult]
    dissenters: list[Dissenter]
    axes: list[MappingRef]
    topics: list[str]
    source: MappingSource
    confidence: float
    contested: bool
    reviewed_by: str | None
    reviewed_at: dt.date | None
    note: str | None
    consistency: list[Consistency]


class Seats(Out):
    body: str
    seats: dict[str, str] = Field(description="seat number -> person_id")


EXPORT_MODELS: dict[str, type[Out]] = {
    "meta": Meta,
    "index": Index,
    "parties": Parties,
    "person": PersonDetail,
    "vote": VoteDetail,
    "seats": Seats,
}
