"""Incremental fetch of one parliament and legislature into the DuckDB cache (KONZEPT 6.2)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from politdrift.models import Body, Coverage, Level
from politdrift.sources.parlament import ParlamentSource
from politdrift.store import Store

BODIES = {
    "nr": Body(
        body_id="nr",
        name="Nationalrat",
        level=Level.FEDERAL,
        source="Parlamentsdienste, parlament.ch",
        coverage=Coverage.BALLOTS,
    ),
}


@dataclass
class FetchStats:
    sessions_total: int = 0
    sessions_fetched: int = 0
    sessions_skipped: int = 0
    votes: int = 0
    ballots: int = 0
    persons: int = 0
    errors: list[str] = field(default_factory=list[str])


def run_fetch(
    source: ParlamentSource,
    store: Store,
    legislature: int,
    *,
    concurrency: int = 4,
    max_sessions: int | None = None,
    today: dt.date | None = None,
    log: Callable[[str], None] = print,
) -> FetchStats:
    today = today or dt.datetime.now(dt.UTC).date()
    stats = FetchStats()
    body = BODIES[source.body]
    store.put_bodies([body])

    leg = source.legislature(legislature)
    store.put_legislatures([leg])

    members = source.members(since=leg.start)
    store.put_persons({m.person.person_id: m.person for m in members}.values())
    store.put_memberships(m.membership for m in members)
    stats.persons = len({m.person.person_id for m in members})
    store.put_seats(source.seats())
    log(f"members: {stats.persons} persons, {len(members)} memberships")

    sessions = [s for s in source.sessions(legislature) if s.start <= today]
    store.put_sessions(sessions)
    stats.sessions_total = len(sessions)
    if max_sessions is not None:
        sessions = sessions[-max_sessions:]

    for s in sessions:
        finished = s.end < today
        known = store.con.execute(
            "SELECT count(*) FROM votes WHERE session_id = ?", [s.session_id]
        ).fetchone()
        has_votes = bool(known and known[0])
        if finished and has_votes and not store.vote_ids_without_ballots(s.session_id):
            stats.sessions_skipped += 1
            continue

        votes = source.votes(s.session_id)
        store.put_votes(votes)
        stats.votes += len(votes)
        missing = store.vote_ids_without_ballots(s.session_id)
        log(f"{s.name}: {len(votes)} votes, fetching ballots for {len(missing)}")

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(source.ballots, vid): vid for vid in missing}
            for fut in as_completed(futures):
                vid = futures[fut]
                try:
                    ballots = fut.result()
                except Exception as err:  # keep going, report at the end
                    stats.errors.append(f"vote {vid}: {err}")
                    continue
                stats.ballots += store.put_ballots(ballots)
        stats.sessions_fetched += 1

    return stats
