"""Record a small, real sample of ws.parlament.ch responses as test fixtures.

Run from pipeline/: uv run python scripts/record_parlament_fixtures.py
Tests never touch the network; they replay these files (KONZEPT 6.2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

BASE = "https://ws.parlament.ch/odata.svc"
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "parlament"
SESSION = 5215  # Herbstsession 2026
N_VOTES = 3


def get(entity: str, filter_: str, **extra: str) -> list[dict[str, Any]]:
    params = {"$format": "json", "$filter": f"Language eq 'DE' and ({filter_})", **extra}
    r = httpx.get(f"{BASE}/{entity}", params=params, timeout=120)
    r.raise_for_status()
    d = r.json()["d"]
    return d["results"] if isinstance(d, dict) else d


def save(name: str, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row.pop("__metadata", None)
        for k in [k for k, v in row.items() if isinstance(v, dict)]:
            row.pop(k)
    (OUT / f"{name}.json").write_text(
        json.dumps({"d": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save("LegislativePeriod", get("LegislativePeriod", "LegislativePeriodNumber eq 52"))
    sessions = get("Session", "LegislativePeriodNumber eq 52", **{"$orderby": "ID"})
    save("Session", [s for s in sessions if s["ID"] in (5214, SESSION)])
    members = get(
        "MemberCouncilHistory",
        "Council eq 1 and (DateLeaving eq null or DateLeaving ge datetime'2023-12-04T00:00:00')",
        **{"$orderby": "ID"},
    )
    left = [m for m in members if m["DateLeaving"]][:2]
    no_group = [m for m in members if not m["ParlGroupAbbreviation"]][:1]
    regular = [m for m in members if m["ParlGroupAbbreviation"] and not m["DateLeaving"]][:3]
    save("MemberCouncilHistory", left + no_group + regular)
    save("SeatOrganisationNr", get("SeatOrganisationNr", "SeatNumber gt 0", **{"$top": "5"}))
    votes = get("Vote", f"IdSession eq {SESSION}", **{"$orderby": "ID", "$top": str(N_VOTES)})
    save("Vote", votes)
    ballots: list[dict[str, Any]] = []
    for v in votes:
        ballots += get(
            "Voting",
            f"IdVote eq {v['ID']}",
            **{"$select": "ID,IdVote,PersonNumber,DecisionText,ParlGroupCode", "$orderby": "ID"},
        )
    save("Voting", ballots)


if __name__ == "__main__":
    main()
