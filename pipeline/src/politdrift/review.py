"""Review workflow for mapping proposals (KONZEPT 2.4): accept, edit, no axis, skip."""

# ruamel.yaml ships incomplete type information.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import datetime as dt
import os
import shlex
import subprocess
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from politdrift.models import AxisMapping
from politdrift.store import Store


class Action(StrEnum):
    ACCEPT = "a"
    NO_AXIS = "k"
    SKIP = "s"
    QUIT = "q"
    EDIT = "b"


def pending(data: list[Any]) -> list[CommentedMap]:
    return [e for e in data if isinstance(e, CommentedMap) and not e.get("reviewed", False)]


def apply(node: CommentedMap, action: Action, reviewer: str, today: dt.date) -> None:
    """Mutate a mapping node in place for ACCEPT or NO_AXIS; validates the result."""
    if action is Action.NO_AXIS:
        node["axes"] = []
        if not node.get("topics"):
            node["topics"] = ["kein_achsenbezug"]
    elif action is not Action.ACCEPT:
        raise ValueError(f"apply() handles accept and no-axis, not {action}")
    node["reviewed"] = True
    node["reviewed_by"] = reviewer
    node["reviewed_at"] = today
    AxisMapping.model_validate(dict(node))


def replace_with(node: CommentedMap, edited: dict[str, Any], reviewer: str, today: dt.date) -> None:
    """Replace a node's content with an edited version (vote_id must stay), mark reviewed."""
    if int(edited.get("vote_id", -1)) != int(node["vote_id"]):
        raise ValueError("vote_id must not change while editing")
    edited = {**edited, "reviewed": True, "reviewed_by": reviewer, "reviewed_at": today}
    if edited.get("source") == "llm":
        edited["source"] = "manual" if edited.get("axes") != node.get("axes") else "llm"
    AxisMapping.model_validate(edited)
    for key in list(node.keys()):
        if key not in edited:
            del node[key]
    for key, value in edited.items():
        node[key] = value


def describe(node: CommentedMap, store: Store | None) -> str:
    vid = int(node["vote_id"])
    lines = [f"── Abstimmung {vid}: {node.get('title', '')}"]
    if store is not None:
        row = store.con.execute(
            "SELECT business, date, meaning_yes, meaning_no FROM votes WHERE vote_id = ?", [vid]
        ).fetchone()
        if row:
            lines.append(f"   Geschäft {row[0]} · {row[1]:%d.%m.%Y}")
            lines.append(f"   Ja:   {row[2] or '-'}")
            lines.append(f"   Nein: {row[3] or '-'}")
        groups = store.con.execute(
            """SELECT parl_group,
                      count(*) FILTER (WHERE decision = 'yes'),
                      count(*) FILTER (WHERE decision = 'no')
               FROM ballots WHERE vote_id = ? AND parl_group IS NOT NULL
               GROUP BY 1 ORDER BY 1""",
            [vid],
        ).fetchall()
        if groups:
            lines.append(
                "   Fraktionen (Ja/Nein): " + "  ".join(f"{g} {y}/{n}" for g, y, n in groups)
            )
    axes = node.get("axes") or []
    lines.append("   Vorschlag:")
    if not axes:
        lines.append("     (keine Achse)")
    for a in axes:
        arrow = "Ja → hoch" if int(a["direction"]) > 0 else "Ja → tief"
        lines.append(f"     {a['axis']:<22} {arrow}  Gewicht {a['weight']}")
    topics = ", ".join(node.get("topics") or []) or "-"
    contested = "ja" if node.get("contested") else "nein"
    lines.append(
        f"   Themen: {topics} · Konfidenz {node.get('confidence')} · umstritten: {contested}"
    )
    if node.get("note"):
        lines.append(f"   Begründung: {node['note']}")
    return "\n".join(lines)


def edit_text(text: str) -> str | None:
    """Open $VISUAL/$EDITOR (fallback: nano) on text; None if the file was left unchanged."""
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        path = Path(fh.name)
    try:
        subprocess.run([*shlex.split(editor), str(path)], check=True)  # noqa: S603
        edited = path.read_text(encoding="utf-8")
    finally:
        path.unlink(missing_ok=True)
    return None if edited == text else edited
