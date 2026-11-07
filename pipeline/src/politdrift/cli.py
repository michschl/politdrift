"""Command line interface `politdrift` (KONZEPT 6.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from politdrift import __version__
from politdrift.mappings import validate_tree

app = typer.Typer(
    name="politdrift",
    help="Politdrift data pipeline: fetch, classify, review, compute, export, validate.",
    no_args_is_help=True,
    add_completion=False,
)

BodyOpt = Annotated[str, typer.Option("--body", help="Parliament id, e.g. nr")]
LegislatureOpt = Annotated[int, typer.Option("--legislature", help="Legislature number, e.g. 52")]


def _not_implemented(command: str, phase: str) -> None:
    typer.secho(f"`{command}` is not implemented yet ({phase}).", err=True, fg="yellow")
    raise typer.Exit(code=2)


@app.callback(invoke_without_command=True)
def _root(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit


@app.command()
def fetch(body: BodyOpt = "nr", legislature: LegislatureOpt = 52) -> None:
    """Load persons, memberships, votes and ballots incrementally into the DuckDB cache."""
    _not_implemented("fetch", "phase 2")


@app.command()
def classify(body: BodyOpt = "nr", legislature: LegislatureOpt = 52) -> None:
    """Propose axis mappings for unmapped votes with an LLM (source: llm, reviewed: false)."""
    _not_implemented("classify", "phase 2")


@app.command()
def review(body: BodyOpt = "nr", legislature: LegislatureOpt = 52) -> None:
    """Accept, edit or reject proposed mappings."""
    _not_implemented("review", "phase 2")


@app.command()
def compute(body: BodyOpt = "nr", legislature: LegislatureOpt = 52) -> None:
    """Compute voting profiles, Fraktionsdrift and drift series from reviewed mappings."""
    _not_implemented("compute", "phase 2")


@app.command()
def export(body: BodyOpt = "nr", legislature: LegislatureOpt = 52) -> None:
    """Write static JSON to data/derived/ (KONZEPT 4.3)."""
    _not_implemented("export", "phase 2")


@app.command()
def validate(
    path: Annotated[
        Path, typer.Argument(help="Mapping root directory", exists=True, file_okay=False)
    ] = Path("../data/mappings"),
) -> None:
    """Check mapping YAML against the schema: axis keys, directions, required fields, review."""
    report = validate_tree(path)
    for err in report.errors:
        typer.secho(err, err=True, fg="red")
    summary = (
        f"{report.files} file(s), {report.mappings} mapping(s), "
        f"{report.reviewed} reviewed, {len(report.errors)} error(s)"
    )
    if not report.ok:
        typer.secho(summary, err=True, fg="red")
        raise typer.Exit(code=1)
    typer.secho(summary, fg="green")
