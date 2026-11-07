"""Scoring (KONZEPT 2.3). Pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from politdrift.axes import Axis
from politdrift.models import Decision

N_MIN = 8
"""Minimum number of mapped, cast votes per axis and window; below that the score is None."""


@dataclass(frozen=True, slots=True)
class WeightedBallot:
    """One ballot of one person on one vote, already resolved for a single axis."""

    decision: Decision
    direction: int  # +1 or -1
    weight: float


@dataclass(frozen=True, slots=True)
class AxisScore:
    score: float | None
    n: int


def ballot_value(decision: Decision) -> int:
    """s(p,v): +1 yes, -1 no, 0 otherwise (abstention/absence do not count)."""
    if decision is Decision.YES:
        return 1
    if decision is Decision.NO:
        return -1
    return 0


def axis_score(ballots: Iterable[WeightedBallot], n_min: int = N_MIN) -> AxisScore:
    """S(p,a,w) normalised to 0..100.

    S = sum(w * d * s) / sum(w * |s|);  score = (S + 1) / 2 * 100.
    Returns score None if fewer than n_min cast votes are mapped to the axis.
    """
    num = 0.0
    den = 0.0
    n = 0
    for b in ballots:
        if b.direction not in (-1, 1):
            raise ValueError(f"direction must be -1 or 1, got {b.direction}")
        s = ballot_value(b.decision)
        if s == 0:
            continue
        num += b.weight * b.direction * s
        den += b.weight
        n += 1
    if n < n_min or den == 0:
        return AxisScore(score=None, n=n)
    return AxisScore(score=(num / den + 1) / 2 * 100, n=n)


def coverage(soll: Mapping[Axis, float | None], ist: Mapping[Axis, float | None]) -> float | None:
    """Deckungsgrad: 100 - mean(|soll_a - ist_a|) over axes where both values exist."""
    diffs = [
        abs(s - i) for axis, s in soll.items() if s is not None and (i := ist.get(axis)) is not None
    ]
    if not diffs:
        return None
    return 100 - sum(diffs) / len(diffs)


def drift(
    before: Mapping[Axis, float | None], after: Mapping[Axis, float | None]
) -> dict[Axis, float]:
    """Per-axis change between two windows (after - before), axes with both values only."""
    return {
        axis: a - b
        for axis, a in after.items()
        if a is not None and (b := before.get(axis)) is not None
    }


def distance(a: Mapping[Axis, float | None], b: Mapping[Axis, float | None]) -> float | None:
    """Mean absolute axis distance; used for Fraktionsdrift (person vs. parliamentary group)."""
    c = coverage(a, b)
    return None if c is None else 100 - c
