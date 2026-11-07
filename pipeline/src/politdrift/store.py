"""DuckDB cache for raw and normalized data (KONZEPT 4.2). Not committed; lives in .cache/."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import duckdb

from politdrift.models import Ballot, Body, Legislature, Membership, Person, Seat, Session, Vote

DEFAULT_PATH = Path(".cache/politdrift.duckdb")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bodies (
    body_id TEXT PRIMARY KEY, name TEXT, level TEXT, source TEXT, coverage TEXT);
CREATE TABLE IF NOT EXISTS legislatures (
    body_id TEXT, legislature INTEGER, start DATE, "end" DATE,
    PRIMARY KEY (body_id, legislature));
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY, body_id TEXT, legislature INTEGER, name TEXT,
    start DATE, "end" DATE);
CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, canton TEXT);
CREATE TABLE IF NOT EXISTS memberships (
    person_id TEXT, body_id TEXT, start DATE, "end" DATE, party TEXT, parl_group TEXT,
    seat INTEGER, PRIMARY KEY (person_id, body_id, start));
CREATE TABLE IF NOT EXISTS seats (
    body_id TEXT, seat INTEGER, person_id TEXT, PRIMARY KEY (body_id, seat));
CREATE TABLE IF NOT EXISTS votes (
    vote_id BIGINT PRIMARY KEY, body_id TEXT, session_id TEXT, date TIMESTAMP,  -- UTC
    business TEXT, title TEXT, subject TEXT, meaning_yes TEXT, meaning_no TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS ballots (
    vote_id BIGINT, person_id TEXT, decision TEXT, parl_group TEXT,
    PRIMARY KEY (vote_id, person_id));
"""


class Store:
    def __init__(self, path: Path | str = DEFAULT_PATH) -> None:
        path = Path(path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path))
        self.con.execute(SCHEMA)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _upsert(self, table: str, rows: Sequence[dict[str, Any]]) -> int:
        """Bulk upsert via a temporary NDJSON file (executemany is ~2 ms per row)."""
        if not rows:
            return 0
        types = {
            name: dtype
            for name, dtype in self.con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? ORDER BY ordinal_position",
                [table],
            ).fetchall()
        }
        cols = [c for c in rows[0] if c in types]
        spec = "{" + ", ".join(f"'{c}': '{types[c]}'" for c in cols) + "}"
        quoted = ", ".join(f'"{c}"' for c in cols)
        with tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False) as fh:
            for r in rows:
                fh.write(json.dumps({c: r[c] for c in cols}, default=str))
                fh.write("\n")
            tmp = fh.name
        try:
            self.con.execute(
                f"INSERT OR REPLACE INTO {table} ({quoted}) "  # noqa: S608
                f"SELECT {quoted} FROM read_json(?, format='newline_delimited', columns={spec})",
                [tmp],
            )
        finally:
            Path(tmp).unlink(missing_ok=True)
        return len(rows)

    def put_bodies(self, items: Iterable[Body]) -> int:
        return self._upsert("bodies", [i.model_dump(mode="json") for i in items])

    def put_legislatures(self, items: Iterable[Legislature]) -> int:
        return self._upsert("legislatures", [i.model_dump(mode="json") for i in items])

    def put_sessions(self, items: Iterable[Session]) -> int:
        return self._upsert("sessions", [i.model_dump(mode="json") for i in items])

    def put_persons(self, items: Iterable[Person]) -> int:
        return self._upsert("persons", [i.model_dump(mode="json") for i in items])

    def put_memberships(self, items: Iterable[Membership]) -> int:
        return self._upsert("memberships", [i.model_dump(mode="json") for i in items])

    def put_seats(self, items: Iterable[Seat]) -> int:
        return self._upsert("seats", [i.model_dump(mode="json") for i in items])

    def put_votes(self, items: Iterable[Vote]) -> int:
        return self._upsert("votes", [i.model_dump(mode="json") for i in items])

    def put_ballots(self, items: Iterable[Ballot]) -> int:
        return self._upsert("ballots", [i.model_dump(mode="json") for i in items])

    def vote_ids_without_ballots(self, session_id: str) -> list[int]:
        rows = self.con.execute(
            """SELECT v.vote_id FROM votes v
               WHERE v.session_id = ?
                 AND NOT EXISTS (SELECT 1 FROM ballots b WHERE b.vote_id = v.vote_id)
               ORDER BY v.vote_id""",
            [session_id],
        ).fetchall()
        return [int(r[0]) for r in rows]

    def count(self, table: str) -> int:
        row = self.con.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
        return int(row[0]) if row else 0
