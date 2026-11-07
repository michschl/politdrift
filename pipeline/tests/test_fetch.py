import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest

from politdrift.fetch import run_fetch
from politdrift.models import Decision
from politdrift.sources import odata
from politdrift.sources.odata import ODataClient, ODataError, parse_date
from politdrift.sources.parlament import ParlamentSource, decision_from_text
from politdrift.store import Store

FIX = Path(__file__).parent / "fixtures" / "parlament"


def quiet(_: str) -> None:
    pass


def no_sleep(_: float) -> None:
    pass


def rows(entity: str) -> list[dict[str, Any]]:
    return json.loads((FIX / f"{entity}.json").read_text(encoding="utf-8"))["d"]


def replay(request: httpx.Request) -> httpx.Response:
    """Serve recorded fixtures, applying the few filters the adapter uses."""
    entity = request.url.path.rsplit("/", 1)[-1]
    flt = request.url.params.get("$filter", "")
    assert "Language eq 'DE'" in flt, "every query must filter on language"
    data = rows(entity)
    if m := re.search(r"IdSession eq (\d+)", flt):
        data = [r for r in data if r["IdSession"] == int(m.group(1))]
    if m := re.search(r"IdVote eq (\d+)", flt):
        data = [r for r in data if r["IdVote"] == int(m.group(1))]
    return httpx.Response(200, json={"d": data})


@pytest.fixture
def source() -> ParlamentSource:
    client = ODataClient(client=httpx.Client(transport=httpx.MockTransport(replay)), min_interval=0)
    return ParlamentSource(client, "nr")


def test_parse_date() -> None:
    assert parse_date("/Date(1790021728541)/") == dt.datetime(
        2026, 9, 21, 20, 15, 28, 541000, tzinfo=dt.UTC
    )
    assert parse_date("/Date(1790021728540+0120)/") is not None
    assert parse_date(None) is None
    with pytest.raises(ValueError, match="OData date"):
        parse_date("2026-01-01")


@pytest.mark.parametrize(
    ("text", "decision"),
    [
        ("Ja", Decision.YES),
        ("Nein", Decision.NO),
        ("Enthaltung", Decision.ABSTAIN),
        ("Hat nicht teilgenommen", Decision.ABSENT),
        ("Entschuldigt gemäss Art. 57 Abs. 4", Decision.EXCUSED),
        ("Die Präsidentin/der Präsident stimmt nicht", Decision.PRESIDENT),
    ],
)
def test_decision_from_text(text: str, decision: Decision) -> None:
    assert decision_from_text(text) is decision


def test_unknown_decision_text_raises() -> None:
    with pytest.raises(ValueError, match="unknown DecisionText"):
        decision_from_text("Vielleicht")


def test_every_recorded_decision_maps() -> None:
    for r in rows("Voting"):
        decision_from_text(r["DecisionText"])


def test_source_adapter(source: ParlamentSource) -> None:
    leg = source.legislature(52)
    assert leg.start == dt.date(2023, 12, 4)
    sessions = source.sessions(52)
    assert [s.session_id for s in sessions] == ["5214", "5215"]
    members = source.members(since=leg.start)
    assert len(members) == 6
    assert all(m.person.person_id.startswith("parlch:") for m in members)
    assert any(m.membership.end is not None for m in members)
    assert any(m.membership.parl_group is None for m in members)
    votes = source.votes("5215")
    assert len(votes) == 3
    assert all(v.date.tzinfo is not None for v in votes)
    ballots = source.ballots(votes[0].vote_id)
    assert len(ballots) == 200
    assert {b.vote_id for b in ballots} == {votes[0].vote_id}
    assert len(source.seats()) == 5


def test_run_fetch_is_incremental(source: ParlamentSource) -> None:
    store = Store(":memory:")
    today = dt.date(2026, 10, 10)  # Herbstsession 2026 ends on 2026-10-02
    first = run_fetch(source, store, 52, today=today, log=quiet)
    assert first.errors == []
    assert first.sessions_fetched == 2
    assert store.count("votes") == 3
    assert store.count("ballots") == 600
    assert store.count("persons") == first.persons > 0

    second = run_fetch(source, store, 52, today=today, log=quiet)
    # 5215 is finished and complete -> skipped; 5214 has no votes in the sample -> re-checked
    assert second.sessions_skipped == 1
    assert second.ballots == 0
    assert store.count("ballots") == 600


def test_future_sessions_are_ignored(source: ParlamentSource) -> None:
    store = Store(":memory:")
    stats = run_fetch(source, store, 52, today=dt.date(2026, 7, 1), log=quiet)
    assert stats.sessions_total == 1  # Herbstsession 2026 has not started yet
    assert store.count("votes") == 0


def test_client_retries_server_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(odata.time, "sleep", no_sleep)
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"error": "boom"})
        return replay(request)

    client = ODataClient(client=httpx.Client(transport=httpx.MockTransport(flaky)), min_interval=0)
    assert len(list(client.query("Session", "LegislativePeriodNumber eq 52"))) == 2
    assert calls["n"] == 2


def unavailable(_: httpx.Request) -> httpx.Response:
    return httpx.Response(503)


def test_client_gives_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(odata.time, "sleep", no_sleep)
    client = ODataClient(
        client=httpx.Client(transport=httpx.MockTransport(unavailable)),
        min_interval=0,
        retries=2,
    )
    with pytest.raises(ODataError, match="failed after retries"):
        list(client.query("Session", "LegislativePeriodNumber eq 52"))


def test_client_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(odata, "PAGE_SIZE", 2)
    seen: list[str] = []

    def paged(request: httpx.Request) -> httpx.Response:
        skip = int(request.url.params["$skip"])
        seen.append(request.url.params["$skip"])
        data = [{"ID": i} for i in range(5)][skip : skip + 2]
        return httpx.Response(200, json={"d": {"results": data}})

    client = ODataClient(client=httpx.Client(transport=httpx.MockTransport(paged)), min_interval=0)
    assert [r["ID"] for r in client.query("Vote", "IdSession eq 1")] == [0, 1, 2, 3, 4]
    assert seen == ["0", "2", "4"]


def test_store_upsert_is_idempotent(source: ParlamentSource) -> None:
    store = Store(":memory:")
    ballots = source.ballots(source.votes("5215")[0].vote_id)
    store.put_ballots(ballots)
    store.put_ballots(ballots)
    assert store.count("ballots") == 200
