"""Round-trip editing of mapping YAML, preserving comments and order (ruamel.yaml)."""

# ruamel.yaml ships incomplete type information.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from politdrift.models import AxisMapping

_FIELD_ORDER = [
    "vote_id", "business", "title", "axes", "topics", "source", "confidence",
    "contested", "reviewed", "reviewed_by", "reviewed_at", "note",
]  # fmt: skip


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 100
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def load(path: Path) -> CommentedSeq:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return CommentedSeq()
    data: Any = _yaml().load(path)
    if not isinstance(data, list):
        raise ValueError(f"{path}: top level must be a list")
    return cast(CommentedSeq, data)


def _dedent_top_level(text: str) -> str:
    """Put the top-level dashes at column 0 and drop trailing spaces.

    ruamel indents the top-level sequence like nested ones, and it can leave a space before a
    line break when it folds a long plain scalar. YAML ignores that space in flow scalars, but
    editors honouring .editorconfig would strip it and create noise in review diffs.
    """
    return "\n".join(
        (line[2:] if line.startswith("  ") else line).rstrip() for line in text.split("\n")
    )


def save(path: Path, data: CommentedSeq) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        _yaml().dump(data, fh, transform=_dedent_top_level)


def to_node(m: AxisMapping) -> CommentedMap:
    raw: dict[str, Any] = m.model_dump(mode="json", exclude_none=True)
    node = CommentedMap()
    for key in _FIELD_ORDER:
        if key in raw:
            node[key] = raw[key]
    return node


def vote_ids(data: CommentedSeq) -> set[int]:
    return {int(cast(dict[str, Any], e)["vote_id"]) for e in data}


def append(path: Path, mappings: Iterable[AxisMapping]) -> int:
    """Append mappings whose vote_id is not yet in the file. Returns the number added."""
    data = load(path)
    known = vote_ids(data)
    added = 0
    for m in mappings:
        if m.vote_id in known:
            continue
        data.append(to_node(m))
        known.add(m.vote_id)
        added += 1
    if added:
        save(path, data)
    return added
