"""Loading and validating axis mappings from data/mappings/<body>/<legislature>.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import TypeAdapter, ValidationError

from politdrift.models import AxisMapping

_FILE_RE = re.compile(r"^\d+\.ya?ml$")
_BODY_RE = re.compile(r"^[a-z]{2}(?:_[a-z]{2})?$")
_ADAPTER = TypeAdapter(list[AxisMapping])


@dataclass
class ValidationReport:
    files: int = 0
    mappings: int = 0
    reviewed: int = 0
    errors: list[str] = field(default_factory=list[str])

    @property
    def ok(self) -> bool:
        return not self.errors


def _format_error(path: Path, err: ValidationError, raw: list[Any]) -> list[str]:
    out: list[str] = []
    for e in err.errors():
        loc = e["loc"]
        prefix = str(path)
        if loc and isinstance(loc[0], int) and loc[0] < len(raw):
            item: Any = raw[loc[0]]
            vote: object = (
                cast(dict[str, Any], item).get("vote_id", "?") if isinstance(item, dict) else "?"
            )
            prefix += f" [#{loc[0]} vote_id={vote}]"
            loc = loc[1:]
        where = ".".join(str(x) for x in loc) or "<entry>"
        out.append(f"{prefix} {where}: {e['msg']}")
    return out


def load_file(path: Path) -> list[AxisMapping]:
    """Parse one mapping file. Raises ValueError with readable messages on any problem."""
    with path.open(encoding="utf-8") as fh:
        raw: Any = yaml.safe_load(fh)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{path}: top level must be a list of mappings")
    items: list[Any] = list(raw)  # pyright: ignore[reportUnknownArgumentType]
    try:
        mappings = _ADAPTER.validate_python(items)
    except ValidationError as err:
        raise ValueError("\n".join(_format_error(path, err, items))) from err
    seen: set[int] = set()
    dupes: set[int] = set()
    for m in mappings:
        (dupes if m.vote_id in seen else seen).add(m.vote_id)
    if dupes:
        raise ValueError(f"{path}: duplicate vote_id {', '.join(map(str, sorted(dupes)))}")
    return mappings


def validate_tree(root: Path) -> ValidationReport:
    """Validate every mapping file below root (layout: <body>/<legislature>.yaml)."""
    report = ValidationReport()
    if not root.is_dir():
        report.errors.append(f"{root}: not a directory")
        return report
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.name.startswith("."):
            continue
        rel = path.relative_to(root)
        if len(rel.parts) != 2 or not _BODY_RE.match(rel.parts[0]) or not _FILE_RE.match(path.name):
            report.errors.append(f"{path}: expected <body>/<legislature>.yaml, e.g. nr/52.yaml")
            continue
        report.files += 1
        try:
            mappings = load_file(path)
        except (ValueError, yaml.YAMLError) as err:
            report.errors.append(str(err))
            continue
        report.mappings += len(mappings)
        report.reviewed += sum(m.reviewed for m in mappings)
    return report
