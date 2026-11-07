"""Static JSON export to data/derived/ (KONZEPT 4.3). Deterministic: same input, same bytes."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from politdrift import __version__
from politdrift.compute import (
    BallotRow,
    ProfileResult,
    compute_profiles,
    consistency,
    drift_over_time,
    empty_profile,
    group_distance,
    scored_mappings,
)
from politdrift.export_models import (
    EXPORT_MODELS,
    GroupProfiles,
    GroupResult,
    Index,
    MappingRef,
    Meta,
    Parties,
    PersonBallot,
    PersonDetail,
    PersonSummary,
    Seats,
    Source,
    VoteDetail,
)
from politdrift.mappings import load_file
from politdrift.models import AxisMapping, Decision, Session
from politdrift.scoring import N_MIN
from politdrift.store import Store

SOURCES = [
    Source(name="Parlamentsdienste, parlament.ch", url="https://www.parlament.ch"),
    Source(
        name="Politdrift (Achsen-Zuordnungen)",
        url="https://github.com/michschl/politdrift",
        license="CC BY 4.0",
    ),
]


def slug(person_id: str) -> str:
    return person_id.replace(":", "-")


@dataclass
class ExportStats:
    persons: int
    votes: int
    mapped_votes: int
    warnings: list[str]


def load_mappings(mappings_dir: Path, body: str, legislature: int) -> list[AxisMapping]:
    path = mappings_dir / body / f"{legislature}.yaml"
    return load_file(path) if path.exists() else []


def _sessions(store: Store, body: str, legislature: int) -> list[Session]:
    rows = store.con.execute(
        'SELECT session_id, body_id, legislature, name, start, "end" FROM sessions '
        "WHERE body_id = ? AND legislature = ? ORDER BY start",
        [body, legislature],
    ).fetchall()
    return [
        Session(session_id=r[0], body_id=r[1], legislature=r[2], name=r[3], start=r[4], end=r[5])
        for r in rows
    ]


def load_ballots(store: Store, vote_ids: list[int]) -> list[BallotRow]:
    if not vote_ids:
        return []
    rows = store.con.execute(
        """SELECT b.vote_id, b.person_id, b.decision, b.parl_group, v.session_id
           FROM ballots b JOIN votes v USING (vote_id)
           WHERE b.vote_id IN (SELECT unnest(?::BIGINT[]))
           ORDER BY b.vote_id, b.person_id""",
        [vote_ids],
    ).fetchall()
    return [BallotRow(int(r[0]), r[1], Decision(r[2]), r[3], r[4]) for r in rows]


def _write(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _prune(directory: Path, keep: set[str]) -> None:
    if directory.is_dir():
        for f in directory.glob("*.json"):
            if f.name not in keep:
                f.unlink()


def _majority(counts: Counter[Decision]) -> Decision | None:
    y, n = counts[Decision.YES], counts[Decision.NO]
    if y == n:
        return None
    return Decision.YES if y > n else Decision.NO


def run_export(
    store: Store,
    mappings_dir: Path,
    out_dir: Path,
    body: str,
    legislature: int,
    *,
    today: dt.date | None = None,
    n_min: int = N_MIN,
) -> ExportStats:
    today = today or dt.datetime.now(dt.UTC).date()
    warnings: list[str] = []
    sessions = _sessions(store, body, legislature)
    all_mappings = load_mappings(mappings_dir, body, legislature)
    mapped = scored_mappings(all_mappings)
    session_ids = [s.session_id for s in sessions]
    known_votes = {
        int(r[0])
        for r in store.con.execute(
            "SELECT vote_id FROM votes WHERE session_id IN (SELECT unnest(?::TEXT[]))",
            [session_ids],
        ).fetchall()
    }
    for vid in sorted(set(mapped) - known_votes):
        warnings.append(f"mapping for vote {vid} has no vote in the cache (run fetch?)")
    mapped = {k: v for k, v in mapped.items() if k in known_votes}
    ballots = load_ballots(store, sorted(mapped))
    result = compute_profiles(sessions, legislature, mapped, ballots, n_min=n_min)

    base = out_dir / body / str(legislature)
    persons = _person_summaries(store, body, result, today)
    current = result.current_window

    _write(
        base / "index.json",
        Index(
            body=body,
            legislature=legislature,
            windows=result.windows,
            current_window=current,
            persons=persons,
        ),
    )
    _write(
        base / "parties.json",
        Parties(
            body=body,
            legislature=legislature,
            windows=result.windows,
            groups=[
                GroupProfiles(group=g, profiles=result.groups[g]) for g in sorted(result.groups)
            ],
        ),
    )

    by_person: dict[str, list[PersonBallot]] = defaultdict(list)
    by_vote: dict[int, list[BallotRow]] = defaultdict(list)
    for b in ballots:
        by_person[b.person_id].append(
            PersonBallot(vote_id=b.vote_id, decision=b.decision, parl_group=b.parl_group)
        )
        by_vote[b.vote_id].append(b)

    memberships = _memberships(store, body)
    written: set[str] = set()
    for p in persons:
        name = f"{p.slug}.json"
        _write(
            base / "persons" / name,
            PersonDetail(
                person=p,
                memberships=memberships.get(p.person_id, []),
                profiles=result.persons.get(p.person_id, {}),
                ballots=by_person.get(p.person_id, []),
            ),
        )
        written.add(name)
    _prune(base / "persons", written)

    written = set()
    for vid, m in sorted(mapped.items()):
        detail = _vote_detail(store, vid, mapped, by_vote[vid], result)
        if any(c.warning for c in detail.consistency):
            warnings.append(f"consistency warning for vote {vid} ({m.title})")
        _write(base / "votes" / f"{vid}.json", detail)
        written.add(f"{vid}.json")
    _prune(base / "votes", written)

    seat_rows = store.con.execute(
        "SELECT seat, person_id FROM seats WHERE body_id = ? ORDER BY seat", [body]
    ).fetchall()
    _write(base / "seats.json", Seats(body=body, seats={str(r[0]): r[1] for r in seat_rows}))

    latest = store.con.execute(
        "SELECT max(date) FROM votes WHERE session_id IN (SELECT unnest(?::TEXT[]))",
        [session_ids],
    ).fetchone()
    data_as_of = latest[0].replace(tzinfo=dt.UTC) if latest and latest[0] else None
    _write(
        out_dir / "meta.json",
        Meta(
            pipeline_version=__version__,
            body=body,
            legislature=legislature,
            data_as_of=data_as_of,
            sources=SOURCES,
            counts={
                "sessions": len(sessions),
                "votes": len(known_votes),
                "ballots": store.count("ballots"),
                "persons": len(persons),
                "mappings": len(all_mappings),
                "mappings_reviewed": sum(m.reviewed for m in all_mappings),
                "mapped_votes_in_profiles": len(mapped),
            },
            n_min=n_min,
        ),
    )
    write_schemas(out_dir / "schema")
    return ExportStats(
        persons=len(persons), votes=len(known_votes), mapped_votes=len(mapped), warnings=warnings
    )


def write_schemas(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, model in EXPORT_MODELS.items():
        schema: dict[str, Any] = model.model_json_schema()
        (directory / f"{name}.schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


def _memberships(store: Store, body: str) -> dict[str, list[dict[str, str | None]]]:
    rows = store.con.execute(
        'SELECT person_id, start, "end", party, parl_group FROM memberships '
        "WHERE body_id = ? ORDER BY person_id, start",
        [body],
    ).fetchall()
    out: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    for pid, start, end, party, group in rows:
        out[pid].append(
            {
                "start": start.isoformat(),
                "end": end.isoformat() if end else None,
                "party": party,
                "parl_group": group,
            }
        )
    return out


def _person_summaries(
    store: Store, body: str, result: ProfileResult, today: dt.date
) -> list[PersonSummary]:
    rows = store.con.execute(
        """WITH latest AS (
               SELECT *, row_number() OVER (PARTITION BY person_id ORDER BY start DESC) AS rn
               FROM memberships WHERE body_id = ?)
           SELECT p.person_id, p.first_name, p.last_name, p.canton,
                  l.party, l.parl_group, l."end", s.seat
           FROM persons p
           JOIN latest l ON l.person_id = p.person_id AND l.rn = 1
           LEFT JOIN seats s ON s.person_id = p.person_id AND s.body_id = ?
           ORDER BY p.last_name, p.first_name, p.person_id""",
        [body, body],
    ).fetchall()
    current = result.current_window
    out: list[PersonSummary] = []
    for pid, first, last, canton, party, group, end, seat in rows:
        profile = (result.persons.get(pid, {}).get(current) if current else None) or empty_profile()
        out.append(
            PersonSummary(
                person_id=pid,
                slug=slug(pid),
                first_name=first,
                last_name=last,
                canton=canton,
                party=party,
                parl_group=group,
                seat=seat,
                active=end is None or end >= today,
                profile=profile,
                group_distance=group_distance(result, pid, group),
                drift=drift_over_time(result, pid),
            )
        )
    return out


def _vote_detail(
    store: Store,
    vote_id: int,
    mappings: dict[int, AxisMapping],
    ballots: list[BallotRow],
    result: ProfileResult,
) -> VoteDetail:
    m = mappings[vote_id]
    row = store.con.execute(
        "SELECT session_id, date, business, title, subject, meaning_yes, meaning_no "
        "FROM votes WHERE vote_id = ?",
        [vote_id],
    ).fetchone()
    if row is None:
        raise ValueError(f"vote {vote_id} not in cache")
    counts: Counter[Decision] = Counter(b.decision for b in ballots)
    per_group: dict[str, Counter[Decision]] = defaultdict(Counter)
    for b in ballots:
        if b.parl_group:
            per_group[b.parl_group][b.decision] += 1
    majorities = {g: _majority(c) for g, c in per_group.items()}
    dissenters = [
        {
            "person_id": b.person_id,
            "group": b.parl_group,
            "decision": b.decision,
            "group_majority": majorities[b.parl_group],
        }
        for b in ballots
        if b.parl_group
        and majorities.get(b.parl_group) is not None
        and b.decision in (Decision.YES, Decision.NO)
        and b.decision is not majorities[b.parl_group]
    ]
    return VoteDetail.model_validate(
        {
            "vote_id": vote_id,
            "session_id": row[0],
            "date": row[1].replace(tzinfo=dt.UTC),
            "business": row[2],
            "title": row[3],
            "subject": row[4],
            "meaning_yes": row[5],
            "meaning_no": row[6],
            "counts": dict(sorted(counts.items())),
            "groups": [
                GroupResult(group=g, counts=dict(sorted(c.items())), majority=majorities[g])
                for g, c in sorted(per_group.items())
            ],
            "dissenters": dissenters,
            "axes": [
                MappingRef(axis=a.axis, direction=a.direction, weight=a.weight) for a in m.axes
            ],
            "topics": list(m.topics),
            "source": m.source,
            "confidence": m.confidence,
            "contested": m.contested,
            "reviewed_by": m.reviewed_by,
            "reviewed_at": m.reviewed_at,
            "note": m.note,
            "consistency": consistency(vote_id, mappings, result),
        }
    )


def validate_derived(out_dir: Path) -> list[str]:
    """Check every exported file against its model. Returns error messages."""
    errors: list[str] = []
    checks: list[tuple[Path, str]] = [(out_dir / "meta.json", "meta")]
    for leg_dir in sorted(p for p in out_dir.glob("*/*") if p.is_dir() and p.name.isdigit()):
        checks += [
            (leg_dir / "index.json", "index"),
            (leg_dir / "parties.json", "parties"),
            (leg_dir / "seats.json", "seats"),
        ]
        checks += [(f, "person") for f in sorted((leg_dir / "persons").glob("*.json"))]
        checks += [(f, "vote") for f in sorted((leg_dir / "votes").glob("*.json"))]
    for path, kind in checks:
        if not path.exists():
            errors.append(f"{path}: missing")
            continue
        try:
            EXPORT_MODELS[kind].model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as err:
            errors.append(f"{path}: {str(err).splitlines()[0]}")
    return errors
