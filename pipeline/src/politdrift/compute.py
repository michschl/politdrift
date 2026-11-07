"""Profiles, drift and consistency checks (KONZEPT 2.2 rule 2, 2.3). No network, no files.

Only reviewed mappings with axes enter profiles (KONZEPT 2.2 rule 4).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from politdrift.axes import AXIS_ORDER, Axis
from politdrift.export_models import AxisValue, Consistency, Profile, Window
from politdrift.models import AxisMapping, Decision, Session, WindowKind
from politdrift.scoring import (
    N_MIN,
    WeightedBallot,
    WeightedPosition,
    axis_score,
    distance,
    position_score,
)

ROLLING = 4
MIN_GROUPS_FOR_CONSISTENCY = 4


@dataclass(frozen=True, slots=True)
class BallotRow:
    vote_id: int
    person_id: str
    decision: Decision
    parl_group: str | None
    session_id: str


@dataclass
class ProfileResult:
    windows: list[Window]
    persons: dict[str, dict[str, Profile]] = field(default_factory=dict[str, dict[str, Profile]])
    groups: dict[str, dict[str, Profile]] = field(default_factory=dict[str, dict[str, Profile]])
    positions: dict[tuple[int, str], float] = field(default_factory=dict[tuple[int, str], float])
    vote_session: dict[int, str] = field(default_factory=dict[int, str])

    @property
    def current_window(self) -> str | None:
        rolling = [w for w in self.windows if w.kind is WindowKind.ROLLING4]
        return rolling[-1].id if rolling else None

    @property
    def legislature_window(self) -> str | None:
        leg = [w for w in self.windows if w.kind is WindowKind.LEGISLATURE]
        return leg[0].id if leg else None


def build_windows(sessions: Sequence[Session], legislature: int) -> list[tuple[Window, set[str]]]:
    ordered = sorted(sessions, key=lambda s: s.start)
    out: list[tuple[Window, set[str]]] = []
    for s in ordered:
        out.append(
            (
                Window(
                    id=f"session:{s.session_id}",
                    kind=WindowKind.SESSION,
                    session_id=s.session_id,
                    label=s.name,
                    start=s.start,
                    end=s.end,
                ),
                {s.session_id},
            )
        )
    for i, s in enumerate(ordered):
        span = ordered[max(0, i - ROLLING + 1) : i + 1]
        out.append(
            (
                Window(
                    id=f"rolling4:{s.session_id}",
                    kind=WindowKind.ROLLING4,
                    session_id=s.session_id,
                    label=f"{span[0].name} \u2013 {s.name}" if len(span) > 1 else s.name,
                    start=span[0].start,
                    end=s.end,
                ),
                {x.session_id for x in span},
            )
        )
    if ordered:
        out.append(
            (
                Window(
                    id=f"legislature:{legislature}",
                    kind=WindowKind.LEGISLATURE,
                    session_id=ordered[-1].session_id,
                    label=f"Legislatur {legislature}",
                    start=ordered[0].start,
                    end=ordered[-1].end,
                ),
                {x.session_id for x in ordered},
            )
        )
    return out


def scored_mappings(mappings: Iterable[AxisMapping]) -> dict[int, AxisMapping]:
    """Reviewed mappings that carry at least one axis, keyed by vote id."""
    return {m.vote_id: m for m in mappings if m.reviewed and m.axes}


def empty_profile() -> Profile:
    return {axis: AxisValue(score=None, n=0) for axis in AXIS_ORDER}


def group_positions(ballots: Iterable[BallotRow]) -> dict[tuple[int, str], float]:
    """(vote_id, group) -> (yes - no) / (yes + no), only where the group cast yes/no votes."""
    yes: dict[tuple[int, str], int] = defaultdict(int)
    cast: dict[tuple[int, str], int] = defaultdict(int)
    for b in ballots:
        if b.parl_group and b.decision in (Decision.YES, Decision.NO):
            key = (b.vote_id, b.parl_group)
            cast[key] += 1
            yes[key] += b.decision is Decision.YES
    return {k: (2 * yes[k] - n) / n for k, n in cast.items() if n}


def _group_profile(per_axis: dict[Axis, list[WeightedPosition]], n_min: int) -> Profile:
    out: Profile = {}
    for axis in AXIS_ORDER:
        s = position_score(per_axis.get(axis, []), n_min=n_min)
        out[axis] = AxisValue(score=None if s.score is None else round(s.score, 2), n=s.n)
    return out


def _profile(per_axis: dict[Axis, list[WeightedBallot]], n_min: int) -> Profile:
    out: Profile = {}
    for axis in AXIS_ORDER:
        s = axis_score(per_axis.get(axis, []), n_min=n_min)
        out[axis] = AxisValue(score=None if s.score is None else round(s.score, 2), n=s.n)
    return out


def compute_profiles(
    sessions: Sequence[Session],
    legislature: int,
    mappings: dict[int, AxisMapping],
    ballots: Sequence[BallotRow],
    n_min: int = N_MIN,
) -> ProfileResult:
    windows = build_windows(sessions, legislature)
    result = ProfileResult(windows=[w for w, _ in windows])
    positions = group_positions(b for b in ballots if b.vote_id in mappings)
    vote_session = {b.vote_id: b.session_id for b in ballots}
    for window, session_ids in windows:
        by_person: dict[str, dict[Axis, list[WeightedBallot]]] = defaultdict(
            lambda: defaultdict(list)
        )
        by_group: dict[str, dict[Axis, list[WeightedPosition]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for b in ballots:
            if b.session_id not in session_ids:
                continue
            m = mappings.get(b.vote_id)
            if m is None:
                continue
            for a in m.axes:
                by_person[b.person_id][a.axis].append(
                    WeightedBallot(decision=b.decision, direction=a.direction, weight=a.weight)
                )
        for (vid, g), value in positions.items():
            if vote_session.get(vid) not in session_ids:
                continue
            for a in mappings[vid].axes:
                by_group[g][a.axis].append(
                    WeightedPosition(value=value, direction=a.direction, weight=a.weight)
                )
        for pid, per_axis in by_person.items():
            result.persons.setdefault(pid, {})[window.id] = _profile(per_axis, n_min)
        for g, per_axis in by_group.items():
            result.groups.setdefault(g, {})[window.id] = _group_profile(per_axis, n_min)
    result.positions = positions
    result.vote_session = vote_session
    return result


def scores(profile: Profile | None) -> dict[Axis, float | None]:
    return {a: v.score for a, v in (profile or {}).items()}


def group_distance(result: ProfileResult, person_id: str, group: str | None) -> float | None:
    """Fraktionsdrift: mean absolute axis distance to the group, current rolling window."""
    w = result.current_window
    if w is None or group is None:
        return None
    mine = result.persons.get(person_id, {}).get(w)
    theirs = result.groups.get(group, {}).get(w)
    if mine is None or theirs is None:
        return None
    d = distance(scores(mine), scores(theirs))
    return None if d is None else round(d, 2)


def drift_over_time(result: ProfileResult, person_id: str) -> float | None:
    """Mean absolute axis change between the first and the latest rolling window with data."""
    profiles = result.persons.get(person_id, {})
    rolling = [
        profiles[w.id]
        for w in result.windows
        if w.kind is WindowKind.ROLLING4
        and w.id in profiles
        and any(v.score is not None for v in profiles[w.id].values())
    ]
    if len(rolling) < 2:
        return None
    d = distance(scores(rolling[0]), scores(rolling[-1]))
    return None if d is None else round(d, 2)


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx * vy) ** 0.5


def consistency(
    vote_id: int,
    mappings: dict[int, AxisMapping],
    result: ProfileResult,
    n_min: int = N_MIN,
) -> list[Consistency]:
    """KONZEPT 2.2 rule 2, leave-one-out.

    For each axis of this vote: Spearman correlation between each group's position on this vote
    (in axis direction) and the group's legislature score on that axis computed from all *other*
    mapped votes. Negative with >= 4 groups -> warning. Without enough other votes: rho = null.
    """
    mapping = mappings[vote_id]
    groups = sorted({g for (vid, g) in result.positions if vid == vote_id})
    out: list[Consistency] = []
    for a in mapping.axes:
        xs: list[float] = []
        ys: list[float] = []
        for g in groups:
            others = [
                WeightedPosition(value=value, direction=x.direction, weight=x.weight)
                for (vid, gg), value in result.positions.items()
                if gg == g and vid != vote_id
                for x in mappings[vid].axes
                if x.axis is a.axis
            ]
            s = position_score(others, n_min=n_min)
            if s.score is None:
                continue
            xs.append(a.direction * result.positions[(vote_id, g)])
            ys.append(s.score)
        rho = spearman(xs, ys)
        out.append(
            Consistency(
                axis=a.axis,
                rho=None if rho is None else round(rho, 3),
                groups=len(xs),
                warning=rho is not None and len(xs) >= MIN_GROUPS_FOR_CONSISTENCY and rho < 0,
            )
        )
    return out
