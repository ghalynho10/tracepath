"""The `tracepath` terminal command."""

import logging
from pathlib import Path

import typer
from rich.console import Console

from tracepath import __version__
from tracepath.artifacts import REVIEW_LOG, REVIEW_QUEUE, ensure_review_log, write_review_queue
from tracepath.config import SettingsInvalid, load_neo4j_settings
from tracepath.graph import GraphUnavailable, connect, server_version
from tracepath.pipeline import resolve_accepted, review_rows
from tracepath.rebuild import RebuildFailed, committed_units, records_for_units

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)


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
