"""Adapter for the federal parliament (Parlamentsdienste, ws.parlament.ch). KONZEPT 3.1.

Field names were verified against https://ws.parlament.ch/odata.svc/$metadata on 2026-11-07.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from politdrift.models import Ballot, Decision, Legislature, Membership, Person, Seat, Session, Vote
from politdrift.sources.odata import ODataClient, Row, parse_date

SOURCE = "parlch"
COUNCIL_IDS = {"nr": 1, "sr": 2}


def person_id(person_number: int) -> str:
    return f"{SOURCE}:{person_number}"


def decision_from_text(text: str) -> Decision:
    """Map DecisionText (German) to a Decision. Codes are deliberately not used (KONZEPT 3.1).

    Unknown texts raise, so a change at the source stops the pipeline instead of silently
    distorting profiles.
    """
    t = text.strip()
    if t == "Ja":
        return Decision.YES
    if t == "Nein":
        return Decision.NO
    if t == "Enthaltung":
        return Decision.ABSTAIN
    if t == "Hat nicht teilgenommen":
        return Decision.ABSENT
    if t.startswith("Entschuldigt"):
        return Decision.EXCUSED
    if "Präsident" in t:
        return Decision.PRESIDENT
    raise ValueError(f"unknown DecisionText: {text!r}")


def _date(value: str | None) -> dt.date | None:
    d = parse_date(value)
    return d.date() if d else None


def _req_date(value: str | None) -> dt.date:
    d = _date(value)
    if d is None:
        raise ValueError("missing date")
    return d


@dataclass(frozen=True)
class MemberRecord:
    person: Person
    membership: Membership


class ParlamentSource:
    def __init__(self, client: ODataClient, body: str = "nr") -> None:
        if body not in COUNCIL_IDS:
            raise ValueError(f"unsupported body: {body}")
        self.client = client
        self.body = body

    # --- structure -------------------------------------------------------------------------

    def legislature(self, number: int) -> Legislature:
        rows = list(self.client.query("LegislativePeriod", f"LegislativePeriodNumber eq {number}"))
        if not rows:
            raise ValueError(f"legislature {number} not found")
        r = rows[0]
        return Legislature(
            body_id=self.body,
            legislature=number,
            start=_req_date(r["StartDate"]),
            end=_date(r.get("EndDate")),
        )

    def sessions(self, legislature: int) -> list[Session]:
        rows = self.client.query("Session", f"LegislativePeriodNumber eq {legislature}")
        out = [
            Session(
                session_id=str(r["ID"]),
                body_id=self.body,
                legislature=legislature,
                name=r["SessionName"],
                start=_req_date(r["StartDate"]),
                end=_req_date(r["EndDate"]),
            )
            for r in rows
        ]
        return sorted(out, key=lambda s: s.start)

    # --- people ----------------------------------------------------------------------------

    def members(self, since: dt.date) -> list[MemberRecord]:
        council = COUNCIL_IDS[self.body]
        cutoff = f"datetime'{since.isoformat()}T00:00:00'"
        rows = self.client.query(
            "MemberCouncilHistory",
            f"Council eq {council} and (DateLeaving eq null or DateLeaving ge {cutoff})",
        )
        return [self._member(r) for r in rows]

    def _member(self, r: Row) -> MemberRecord:
        pid = person_id(int(r["PersonNumber"]))
        return MemberRecord(
            person=Person(
                person_id=pid,
                first_name=r["FirstName"],
                last_name=r["LastName"],
                canton=r.get("CantonAbbreviation"),
            ),
            membership=Membership(
                person_id=pid,
                body_id=self.body,
                start=_req_date(r["DateJoining"]),
                end=_date(r.get("DateLeaving")),
                party=r.get("PartyAbbreviation"),
                parl_group=r.get("ParlGroupAbbreviation"),
            ),
        )

    def seats(self) -> list[Seat]:
        if self.body != "nr":
            return []
        rows = self.client.query("SeatOrganisationNr", "SeatNumber gt 0")
        return [
            Seat(
                body_id=self.body, seat=int(r["SeatNumber"]), person_id=person_id(r["PersonNumber"])
            )
            for r in rows
        ]

    # --- votes -----------------------------------------------------------------------------

    def votes(self, session_id: str) -> list[Vote]:
        rows = self.client.query("Vote", f"IdSession eq {int(session_id)}")
        out: list[Vote] = []
        for r in rows:
            end = parse_date(r["VoteEnd"])
            if end is None:
                continue
            out.append(
                Vote(
                    vote_id=int(r["ID"]),
                    body_id=self.body,
                    session_id=session_id,
                    date=end,
                    business=r.get("BusinessShortNumber") or None,
                    title=r.get("BusinessTitle") or "",
                    subject=r.get("Subject") or None,
                    meaning_yes=r.get("MeaningYes") or None,
                    meaning_no=r.get("MeaningNo") or None,
                )
            )
        return out

    def ballots(self, vote_id: int) -> list[Ballot]:
        rows = self.client.query(
            "Voting",
            f"IdVote eq {vote_id}",
            select=["ID", "IdVote", "PersonNumber", "DecisionText", "ParlGroupCode"],
        )
        return [
            Ballot(
                vote_id=int(r["IdVote"]),
                person_id=person_id(int(r["PersonNumber"])),
                decision=decision_from_text(r["DecisionText"]),
                parl_group=r.get("ParlGroupCode") or None,
            )
            for r in rows
        ]
