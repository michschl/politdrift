"""Command line interface `politdrift` (KONZEPT 6.2)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

import typer

from politdrift import __version__
from politdrift.export import run_export, validate_derived
from politdrift.export_models import Index
from politdrift.fetch import run_fetch
from politdrift.mappings import validate_tree
from politdrift.sources.odata import ODataClient
from politdrift.sources.parlament import ParlamentSource
from politdrift.store import DEFAULT_PATH as DEFAULT_CACHE
from politdrift.store import Store

app = typer.Typer(
    name="politdrift",
    help="Politdrift data pipeline: fetch, classify, review, compute, export, validate.",
    no_args_is_help=True,
    add_completion=False,
)

BodyOpt = Annotated[str, typer.Option("--body", help="Parliament id, e.g. nr")]
LegislatureOpt = Annotated[int, typer.Option("--legislature", help="Legislature number, e.g. 52")]


@app.callback(invoke_without_command=True)
def _root(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit


CacheOpt = Annotated[Path, typer.Option("--cache", help="DuckDB cache file")]


@app.command()
def fetch(
    body: BodyOpt = "nr",
    legislature: LegislatureOpt = 52,
    cache: CacheOpt = DEFAULT_CACHE,
    concurrency: Annotated[int, typer.Option(min=1, max=8)] = 4,
    max_sessions: Annotated[
        int | None, typer.Option(help="Only the most recent N sessions (for testing)")
    ] = None,
) -> None:
    """Load persons, memberships, votes and ballots incrementally into the DuckDB cache."""
    with ODataClient() as client, Store(cache) as store:
        stats = run_fetch(
            ParlamentSource(client, body),
            store,
            legislature,
            concurrency=concurrency,
            max_sessions=max_sessions,
            log=typer.echo,
        )
        totals = {t: store.count(t) for t in ("persons", "sessions", "votes", "ballots")}
    typer.echo(
        f"fetched {stats.sessions_fetched} session(s), skipped {stats.sessions_skipped} "
        f"complete; new votes {stats.votes}, ballots {stats.ballots}"
    )
    typer.echo("cache totals: " + ", ".join(f"{k} {v}" for k, v in totals.items()))
    if stats.errors:
        for err in stats.errors:
            typer.secho(err, err=True, fg="red")
        raise typer.Exit(code=1)


@app.command()
def classify(
    body: BodyOpt = "nr",
    legislature: LegislatureOpt = 52,
    cache: CacheOpt = DEFAULT_CACHE,
    mappings: Annotated[Path, typer.Option("--mappings")] = Path("../data/mappings"),
    scope: Annotated[str, typer.Option(help="final | overall | motions | all")] = "final",
    limit: Annotated[int, typer.Option(min=1, help="Maximum number of new proposals")] = 20,
    model: Annotated[str | None, typer.Option(help="Overrides POLITDRIFT_LLM_MODEL")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print, do not write")] = False,
) -> None:
    """Propose axis mappings for unmapped votes with an LLM (source: llm, reviewed: false)."""
    from politdrift import mapping_io
    from politdrift.classify import LLMConfig, classify_votes, openai_compatible, select_votes

    path = mappings / body / f"{legislature}.yaml"
    existing = mapping_io.vote_ids(mapping_io.load(path))
    config = LLMConfig.from_env(model)
    with Store(cache) as store:
        session_ids = [
            r[0]
            for r in store.con.execute(
                "SELECT session_id FROM sessions WHERE body_id = ? AND legislature = ?",
                [body, legislature],
            ).fetchall()
        ]
        votes = select_votes(store, session_ids, existing, scope, limit)
    if not votes:
        typer.echo("no unmapped votes in this scope")
        return
    typer.echo(f"classifying {len(votes)} vote(s) with {config.model}")
    result = classify_votes(votes, openai_compatible(config), config.model, log=typer.echo)
    for err in result.errors:
        typer.secho(err, err=True, fg="yellow")
    if dry_run:
        return
    added = mapping_io.append(path, result.mappings)
    typer.secho(f"added {added} proposal(s) to {path} (reviewed: false)", fg="green")


@app.command()
def review(
    body: BodyOpt = "nr",
    legislature: LegislatureOpt = 52,
    cache: CacheOpt = DEFAULT_CACHE,
    mappings: Annotated[Path, typer.Option("--mappings")] = Path("../data/mappings"),
    reviewer: Annotated[str, typer.Option(help="GitHub handle stored as reviewed_by")] = "michschl",
    from_file: Annotated[
        Path | None,
        typer.Option(
            "--from",
            help="Import decisions made elsewhere (JSON list of {vote_id, action, ...})",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
) -> None:
    """Accept, edit or reject proposed mappings, one by one. Saves after every decision."""
    import datetime as dt

    import yaml
    from pydantic import TypeAdapter

    from politdrift import mapping_io
    from politdrift.review import (
        Action,
        Decision,
        apply,
        describe,
        edit_text,
        import_decisions,
        pending,
        replace_with,
    )

    path = mappings / body / f"{legislature}.yaml"
    data = mapping_io.load(path)
    if from_file is not None:
        decisions = TypeAdapter(list[Decision]).validate_json(from_file.read_bytes())
        applied, messages = import_decisions(list(data), decisions, reviewer, dt.date.today())
        for m in messages:
            typer.secho(m, err=True, fg="yellow")
        if applied:
            mapping_io.save(path, data)
        typer.secho(
            f"{applied} decision(s) applied, {len(pending(list(data)))} still pending", fg="green"
        )
        return
    todo = pending(list(data))
    if not todo:
        typer.echo("nothing to review")
        return
    store = Store(cache) if cache.exists() else None
    today = dt.date.today()
    done = 0
    try:
        for i, node in enumerate(todo, start=1):
            typer.echo(f"\n[{i}/{len(todo)}]")
            typer.echo(describe(node, store))
            while True:
                choice = (
                    typer.prompt(
                        "[a]nnehmen, [b]earbeiten, [k]eine Achse, [s]überspringen, [q]uit",
                        default="s",
                    )
                    .strip()
                    .lower()
                )
                try:
                    action = Action(choice[:1])
                except ValueError:
                    continue
                break
            if action is Action.QUIT:
                break
            if action is Action.SKIP:
                continue
            try:
                if action is Action.EDIT:
                    draft = yaml.safe_dump(dict(node), allow_unicode=True, sort_keys=False)
                    text = edit_text(draft)
                    if text is None:
                        continue
                    replace_with(node, yaml.safe_load(text), reviewer, today)
                else:
                    apply(node, action, reviewer, today)
            except ValueError as err:
                typer.secho(f"nicht gespeichert: {err}", fg="red")
                continue
            mapping_io.save(path, data)
            done += 1
    finally:
        if store is not None:
            store.close()
    typer.secho(f"{done} reviewed, {len(todo) - done} still pending", fg="green")


MappingsOpt = Annotated[Path, typer.Option("--mappings", help="Mapping root directory")]
OutOpt = Annotated[Path, typer.Option("--out", help="Export directory")]
DEFAULT_MAPPINGS = Path("../data/mappings")
DEFAULT_OUT = Path("../data/derived")


@app.command()
def compute(
    body: BodyOpt = "nr",
    legislature: LegislatureOpt = 52,
    cache: CacheOpt = DEFAULT_CACHE,
    mappings: MappingsOpt = DEFAULT_MAPPINGS,
    include_pending: Annotated[
        bool,
        typer.Option(
            "--include-pending",
            help="Review aid: treat unreviewed proposals as reviewed for the consistency check",
        ),
    ] = False,
) -> None:
    """Compute profiles from reviewed mappings and report coverage (no files written)."""
    with Store(cache) as store, tempfile.TemporaryDirectory() as tmp:
        stats = run_export(
            store, mappings, Path(tmp), body, legislature, include_pending=include_pending
        )
        index = Index.model_validate_json(
            (Path(tmp) / body / str(legislature) / "index.json").read_text()
        )
    scored = [p for p in index.persons if any(v.score is not None for v in p.profile.values())]
    typer.echo(
        f"{stats.persons} persons, {stats.votes} votes, {stats.mapped_votes} mapped votes in "
        f"profiles; {len(scored)} persons with at least one axis score "
        f"(window {index.current_window})"
    )
    for w in stats.warnings:
        typer.secho(w, err=True, fg="yellow")


@app.command()
def export(
    body: BodyOpt = "nr",
    legislature: LegislatureOpt = 52,
    cache: CacheOpt = DEFAULT_CACHE,
    mappings: MappingsOpt = DEFAULT_MAPPINGS,
    out: OutOpt = DEFAULT_OUT,
) -> None:
    """Write static JSON to data/derived/ (KONZEPT 4.3)."""
    with Store(cache) as store:
        stats = run_export(store, mappings, out, body, legislature)
    for w in stats.warnings:
        typer.secho(w, err=True, fg="yellow")
    errors = validate_derived(out)
    for e in errors:
        typer.secho(e, err=True, fg="red")
    if errors:
        raise typer.Exit(code=1)
    typer.secho(
        f"exported {stats.persons} persons, {stats.mapped_votes} mapped votes to {out}",
        fg="green",
    )


@app.command()
def validate(
    path: Annotated[
        Path, typer.Argument(help="Mapping root directory", exists=True, file_okay=False)
    ] = Path("../data/mappings"),
    derived: Annotated[
        Path | None, typer.Option("--derived", help="Also validate exported JSON in this dir")
    ] = None,
) -> None:
    """Check mapping YAML (and optionally the export) against the schema."""
    report = validate_tree(path)
    if derived is not None:
        report.errors += validate_derived(derived)
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
