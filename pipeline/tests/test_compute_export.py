"""Compute and export on a small synthetic parliament with hand-checkable numbers.

Groups L (left) and R (right), 4 members each. 10 mapped votes on umwelt_ausgebaut in two
sessions: L always votes yes, R always no, except one R member who votes yes everywhere.
"""

import datetime as dt
import json
from pathlib import Path

import pytest

from politdrift.axes import Axis
from politdrift.compute import (
    BallotRow,
    compute_profiles,
    consistency,
    group_distance,
    scored_mappings,
    spearman,
)
from politdrift.export import run_export, validate_derived
from politdrift.models import (
    AxisAssignment,
    AxisMapping,
    Ballot,
    Decision,
    MappingSource,
    Membership,
    Person,
    Seat,
    Session,
    Vote,
    WindowKind,
)
from politdrift.scoring import WeightedPosition, position_score
from politdrift.store import Store

UMWELT = Axis.UMWELT_AUSGEBAUT
S1 = Session(
    session_id="1",
    body_id="nr",
    legislature=52,
    name="S1",
    start=dt.date(2024, 3, 1),
    end=dt.date(2024, 3, 20),
)
S2 = Session(
    session_id="2",
    body_id="nr",
    legislature=52,
    name="S2",
    start=dt.date(2024, 6, 1),
    end=dt.date(2024, 6, 20),
)
MEMBERS = {f"t:{g}{i}": g for g in "LR" for i in range(4)}
REBEL = "t:R0"
VOTES = list(range(100, 110))


def mapping(vid: int, *, reviewed: bool = True, direction: int = 1) -> AxisMapping:
    return AxisMapping(
        vote_id=vid,
        title=f"Vote {vid}",
        axes=[AxisAssignment(axis=UMWELT, direction=direction, weight=1.0)],  # type: ignore[arg-type]
        source=MappingSource.MANUAL,
        confidence=0.9,
        reviewed=reviewed,
        reviewed_by="tester" if reviewed else None,
        reviewed_at=dt.date(2026, 1, 1) if reviewed else None,
    )


def decision(pid: str) -> Decision:
    if pid == REBEL:
        return Decision.YES
    return Decision.YES if MEMBERS[pid] == "L" else Decision.NO


def rows() -> list[BallotRow]:
    return [
        BallotRow(vid, pid, decision(pid), g, "1" if vid < 105 else "2")
        for vid in VOTES
        for pid, g in MEMBERS.items()
    ]


def test_spearman() -> None:
    assert spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1)
    assert spearman([1, 2, 3], [30, 20, 10]) == pytest.approx(-1)
    assert spearman([1, 1, 1], [1, 2, 3]) is None
    assert spearman([1], [1]) is None


def test_position_score() -> None:
    assert position_score([WeightedPosition(1.0, 1, 1.0)] * 8).score == pytest.approx(100)
    assert position_score([WeightedPosition(0.0, 1, 1.0)] * 8).score == pytest.approx(50)
    assert position_score([WeightedPosition(1.0, 1, 1.0)] * 7).score is None
    with pytest.raises(ValueError, match="value"):
        position_score([WeightedPosition(1.5, 1, 1.0)])


def test_unreviewed_and_axisless_mappings_are_ignored() -> None:
    topic_only = AxisMapping(
        vote_id=1, title="t", topics=["x"], source=MappingSource.MANUAL, confidence=1
    )
    ms = scored_mappings([mapping(5), mapping(6, reviewed=False), topic_only])
    assert set(ms) == {5}


def test_windows_and_profiles() -> None:
    mappings = {vid: mapping(vid) for vid in VOTES}
    res = compute_profiles([S2, S1], 52, mappings, rows(), n_min=8)
    kinds = [w.kind for w in res.windows]
    assert kinds.count(WindowKind.SESSION) == 2
    assert kinds.count(WindowKind.ROLLING4) == 2
    assert kinds.count(WindowKind.LEGISLATURE) == 1
    assert res.current_window == "rolling4:2"
    # a session alone has 5 votes < n_min 8 -> null; the rolling window over both has 10
    assert res.persons["t:L1"]["session:1"][UMWELT].score is None
    assert res.persons["t:L1"]["rolling4:2"][UMWELT].score == pytest.approx(100)
    assert res.persons["t:R1"]["rolling4:2"][UMWELT].score == pytest.approx(0)
    assert res.persons[REBEL]["rolling4:2"][UMWELT].score == pytest.approx(100)
    # group R: 3 no, 1 yes per vote -> x = -0.5 -> score 25; n counts votes, not ballots
    r = res.groups["R"]["rolling4:2"][UMWELT]
    assert r.score == pytest.approx(25)
    assert r.n == 10
    assert res.groups["R"]["session:1"][UMWELT].score is None
    assert res.persons["t:L1"]["rolling4:2"][Axis.LAW_ORDER].n == 0


def test_group_distance() -> None:
    mappings = {vid: mapping(vid) for vid in VOTES}
    res = compute_profiles([S1, S2], 52, mappings, rows(), n_min=8)
    assert group_distance(res, REBEL, "R") == pytest.approx(75)
    assert group_distance(res, "t:R1", "R") == pytest.approx(25)
    assert group_distance(res, "t:R1", None) is None


def test_consistency_leave_one_out() -> None:
    # four groups of 4; yes votes per group in axis direction: A 4, B 3, C 1, D 0
    yes_count = {"A": 4, "B": 3, "C": 1, "D": 0}

    def ballots(vid: int, flip: bool) -> list[BallotRow]:
        out: list[BallotRow] = []
        for g, n_yes in yes_count.items():
            k = 4 - n_yes if flip else n_yes
            for i in range(4):
                d = Decision.YES if i < k else Decision.NO
                out.append(BallotRow(vid, f"t:{g}{i}", d, g, "1"))
        return out

    regular = list(range(1, 11))
    bs = [b for vid in regular for b in ballots(vid, flip=False)] + ballots(99, flip=True)
    mappings = {vid: mapping(vid) for vid in [*regular, 99]}
    res = compute_profiles([S1], 52, mappings, bs, n_min=8)
    ok = consistency(1, mappings, res, n_min=8)[0]
    bad = consistency(99, mappings, res, n_min=8)[0]
    assert ok.groups == 4
    assert ok.rho is not None and ok.rho > 0 and not ok.warning
    assert bad.rho is not None and bad.rho < 0 and bad.warning
    # with fewer than n_min other votes there is no reference profile -> no verdict
    few = {vid: mapping(vid) for vid in [1, 99]}
    res_few = compute_profiles([S1], 52, few, ballots(1, False) + ballots(99, True), n_min=8)
    assert consistency(99, few, res_few, n_min=8)[0].rho is None


@pytest.fixture
def store() -> Store:
    s = Store(":memory:")
    s.put_sessions([S1, S2])
    s.put_persons(
        Person(person_id=p, first_name=p[-2:], last_name=f"Name {p}", canton="BE") for p in MEMBERS
    )
    s.put_memberships(
        Membership(person_id=p, body_id="nr", start=dt.date(2023, 12, 4), parl_group=g, party=g)
        for p, g in MEMBERS.items()
    )
    s.put_seats(Seat(body_id="nr", seat=i + 1, person_id=p) for i, p in enumerate(MEMBERS))
    s.put_votes(
        Vote(
            vote_id=vid,
            body_id="nr",
            session_id="1" if vid < 105 else "2",
            date=dt.datetime(2024, 3 if vid < 105 else 6, 2, 10, tzinfo=dt.UTC),
            business="24.001",
            title=f"Vote {vid}",
        )
        for vid in VOTES
    )
    s.put_ballots(
        Ballot(
            vote_id=r.vote_id, person_id=r.person_id, decision=r.decision, parl_group=r.parl_group
        )
        for r in rows()
    )
    return s


def write_mappings(root: Path, items: list[AxisMapping]) -> Path:
    path = root / "mappings" / "nr" / "52.yaml"
    path.parent.mkdir(parents=True)
    import yaml

    path.write_text(yaml.safe_dump([m.model_dump(mode="json") for m in items]), encoding="utf-8")
    return root / "mappings"


def test_export_end_to_end(store: Store, tmp_path: Path) -> None:
    mappings_dir = write_mappings(
        tmp_path,
        [mapping(v) for v in VOTES] + [mapping(999)],  # 999 is not in the cache
    )
    out = tmp_path / "derived"
    stats = run_export(store, mappings_dir, out, "nr", 52, today=dt.date(2024, 7, 1))
    assert stats.mapped_votes == 10
    assert any("999" in w for w in stats.warnings)
    assert validate_derived(out) == []

    index = json.loads((out / "nr/52/index.json").read_text())
    rebel = next(p for p in index["persons"] if p["person_id"] == REBEL)
    assert rebel["profile"][UMWELT.value]["score"] == pytest.approx(100)
    assert rebel["group_distance"] == pytest.approx(75)
    assert len(rebel["profile"]) == 8
    assert (out / "nr/52/persons/t-R0.json").exists()
    vote = json.loads((out / "nr/52/votes/100.json").read_text())
    assert [d["person_id"] for d in vote["dissenters"]] == [REBEL]
    assert {g["group"]: g["majority"] for g in vote["groups"]} == {"L": "yes", "R": "no"}
    assert (out / "schema/person.schema.json").exists()
    meta = json.loads((out / "meta.json").read_text())
    assert meta["counts"]["mapped_votes_in_profiles"] == 10

    # deterministic and pruning: second export with fewer mappings, identical bytes elsewhere
    before = (out / "nr/52/parties.json").read_bytes()
    run_export(store, mappings_dir, out, "nr", 52, today=dt.date(2024, 7, 1))
    assert (out / "nr/52/parties.json").read_bytes() == before
    write_mappings(tmp_path / "second", [mapping(v) for v in VOTES[:9]])
    run_export(store, tmp_path / "second" / "mappings", out, "nr", 52, today=dt.date(2024, 7, 1))
    assert not (out / "nr/52/votes/109.json").exists()


def test_validate_derived_reports_broken_files(store: Store, tmp_path: Path) -> None:
    out = tmp_path / "derived"
    run_export(store, write_mappings(tmp_path, [mapping(100)]), out, "nr", 52)
    (out / "nr/52/votes/100.json").write_text('{"vote_id": "x"}')
    errors = validate_derived(out)
    assert len(errors) == 1 and "votes/100.json" in errors[0]
