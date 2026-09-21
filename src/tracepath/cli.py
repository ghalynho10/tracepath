"""The `tracepath` terminal command."""

import logging

import typer
from rich.console import Console

from tracepath import __version__
from tracepath.config import SettingsInvalid, load_neo4j_settings
from tracepath.graph import GraphUnavailable, connect, server_version

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
