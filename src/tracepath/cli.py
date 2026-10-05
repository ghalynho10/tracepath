"""The `tracepath` terminal command."""

import logging
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console

from tracepath import __version__
from tracepath.artifacts import (
    REVIEW_LOG,
    REVIEW_QUEUE,
    ensure_review_log,
    review_log_entries,
    write_graph_build,
    write_review_queue,
)
from tracepath.config import SettingsInvalid, load_neo4j_settings
from tracepath.extract.records import RecordError
from tracepath.graph import GraphUnavailable, connect, server_version
from tracepath.graph.load import GraphWriteFailed
from tracepath.graph.read import read_graph
from tracepath.pipeline import (
    ProvenanceMismatch,
    collapsed_links,
    graph_build,
    load,
    resolve_accepted,
    review_rows,
    unit_provenance,
)
from tracepath.rebuild import RebuildFailed, committed_units, partial_units, records_for_units
from tracepath.traverse.graph_slice import SliceError
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import StartNotInGraph, walk

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)

#: Who accepted what a load writes. Nothing is reviewed by hand yet (spec 0002), so
#: every accepted item was accepted by the three run agreement rule.
ACCEPTED_BY = "auto"


def _say(text: str) -> None:
    """Print one plain line to stdout: corpus text is never read as Rich markup."""
    console.print(text, markup=False, highlight=False, soft_wrap=True)


def _fail(message: str) -> NoReturn:
    """Print a failure to stderr and exit 1, with no traceback (spec 0004 AC-44)."""
    err_console.print("[red]✗[/red] ", end="")
    err_console.print(message, markup=False, highlight=False, soft_wrap=True)
    raise typer.Exit(code=1)


def _show_version(value: bool) -> None:
    if value:
        console.print(f"tracepath {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", help="Show debug logging."),
    version: bool = typer.Option(
        False, "--version", callback=_show_version, is_eager=True, help="Show the version."
    ),
) -> None:
    """Answer "why was this built this way?" from a project's decision records."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    # Only our own loggers; the driver's debug output is wire protocol noise.
    if debug:
        logging.getLogger("tracepath").setLevel(logging.DEBUG)


@app.command()
def status() -> None:
    """Check that the Neo4j graph store is reachable."""
    try:
        settings = load_neo4j_settings()
        driver = connect(settings)
    except (SettingsInvalid, GraphUnavailable) as exc:
        err_console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(code=1) from None
    with driver:
        version = server_version(driver, settings.database)
    console.print(f"[green]✓[/green] Neo4j {version} reachable at {settings.uri}")


@app.command()
def review_queue(
    root: str = typer.Option(".", "--root", help="The repository root to read and write."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
    model: str = typer.Option("claude-sonnet-5", "--model", help="The model the artifacts name."),
) -> None:
    """Rebuild the review queue from the committed run artifacts. No API call, no graph.

    Every held item needs somewhere durable to live, or AC-11c's promise that a held
    link sits in a file tracked in git is not true. The artifacts are the source of
    truth (spec 0001), so the queue is derived from them and never hand maintained.
    """
    base = Path(root)
    corpus_snapshot = base / snapshot
    try:
        results = committed_units(base, corpus_snapshot)
    except RebuildFailed as exc:
        err_console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(code=1) from None

    records = records_for_units(results, corpus_snapshot, commit)
    corpus = resolve_accepted(results, records)
    queued_at = max(a.extracted_at for r in results for a in r.artifacts)
    rows = review_rows(results, corpus.held, model, queued_at)

    write_review_queue(base, list(rows))
    ensure_review_log(base)
    console.print(
        f"[green]✓[/green] {len(rows)} held items from {len(results)} units "
        f"→ {REVIEW_QUEUE}, log at {REVIEW_LOG}"
    )


@app.command(name="load")
def load_graph(
    root: str = typer.Option(".", "--root", help="The repository root to read and write."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
) -> None:
    """Rebuild the graph from the committed run artifacts. No API call.

    Clears the graph, creates the constraints and loads every fully extracted unit,
    every write asserting its own row count, then writes `artifacts/graph-build.json`.
    """
    base = Path(root)
    corpus_snapshot = base / snapshot
    try:
        settings = load_neo4j_settings()
        results = committed_units(base, corpus_snapshot)
        records = records_for_units(results, corpus_snapshot, commit)
        corpus = resolve_accepted(results, records)
        provenances = [unit_provenance(result, ACCEPTED_BY) for result in results]
        manifest = graph_build(results, corpus, provenances, commit, review_log_entries(base))
        with connect(settings) as driver:
            written = load(
                driver,
                settings.database,
                records,
                results,
                corpus.resolution,
                commit,
                ACCEPTED_BY,
                clear_first=True,
            )
    except (
        SettingsInvalid,
        RebuildFailed,
        RecordError,
        ProvenanceMismatch,
        GraphUnavailable,
        GraphWriteFailed,
    ) as exc:
        _fail(str(exc))

    path = write_graph_build(base, manifest)
    _say(
        f"Loaded {len(results)} units: {written['records']} records, "
        f"{written['entities']} entities, {written['unresolved']} unresolved, "
        f"{written['links']} links written ({collapsed_links(corpus.resolution.links)} "
        "collapsed into an existing relationship), "
        f"{len(corpus.held)} links held across units."
    )
    versions = ", ".join(f"{v}: {n}" for v, n in manifest["prompt_versions"].items())
    _say(f"Units per prompt version: {versions}.")
    for partial in partial_units(base):
        _say(
            f"Not loaded: {partial.record} {partial.section} has {partial.settled_runs} "
            "settled runs of 3, so it is not extracted."
        )
    _say(f"Build manifest: {path.relative_to(base).as_posix()}")


@app.command()
def trace(
    start: str = typer.Argument(
        ..., help="A canonical id: an entity, such as 0012/AC-3, or a record."
    ),
) -> None:
    """Walk the chain from one item and print every step, each citing its record.

    Breadth first along the seven typed links, both ways, at most three hops. A Record
    or Unresolved node is printed and not expanded. Reads the graph only.
    """
    try:
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database)
        chain = walk(graph, start)
    except (SettingsInvalid, GraphUnavailable, SliceError, StartNotInGraph) as exc:
        _fail(str(exc))
    for line in render_chain(chain):
        _say(line)
