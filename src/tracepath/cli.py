"""The `tracepath` terminal command."""

import logging
import math
from pathlib import Path
from typing import Annotated, NoReturn

import anthropic
import typer
from rich.console import Console

from tracepath import __version__
from tracepath.artifacts import (
    REVIEW_LOG,
    REVIEW_QUEUE,
    ArtifactCollisionError,
    ensure_review_log,
    now_utc,
    review_log_entries,
    write_graph_build,
    write_review_queue,
)
from tracepath.config import SettingsInvalid, load_anthropic_settings, load_neo4j_settings
from tracepath.extract.address import UnitAddressError, resolve_address, resolve_addresses
from tracepath.extract.client import build_client, system_prompt
from tracepath.extract.cost import (
    CALIBRATION_ADDRESS,
    EstimateUnavailable,
    UnitCount,
    check_calibration,
    estimate,
    estimate_lines,
)
from tracepath.extract.examples import ExampleError
from tracepath.extract.metered import (
    Plan,
    ResumeRefused,
    RunPlan,
    calls_through,
    count_input,
    first_collision,
    fresh_runs,
    provenance_mismatch,
    resume_preflight,
    resume_runs,
    run_metered,
    summary_lines,
)
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
from tracepath.rebuild import (
    RebuildFailed,
    committed_units,
    partial_units,
    records_for_units,
    settled_run_counts,
    unit_passes,
)
from tracepath.report import (
    EVAL_FILE,
    EvalEntryUnusable,
    holding_units,
    read_question,
    report_lines,
    score,
)
from tracepath.traverse.graph_slice import SliceError
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import Chain, StartNotInGraph, walk

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
        manifest = graph_build(
            results, corpus, provenances, commit, review_log_entries(base), unit_passes(base)
        )
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
    start: str | None = typer.Argument(
        None, help="A canonical id: an entity, such as 0012/AC-3, or a record."
    ),
    eval_question: int | None = typer.Option(
        None,
        "--eval",
        help="Score the chain of eval question N; its start comes from the eval set.",
    ),
    eval_file: str = typer.Option(
        str(EVAL_FILE), "--eval-file", help="The eval set, relative to --root."
    ),
    root: str = typer.Option(".", "--root", help="The repository root to read."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
) -> None:
    """Walk the chain from one item and print every step, each citing its record.

    Breadth first along the seven typed links, both ways, at most three hops. A Record
    or Unresolved node is printed and not expanded. With `--eval N`, the start is
    question N's first trace entry, and the chain is then scored against its expected
    items. The walk never reads the eval set; only the scoring after it does.
    """
    if (start is None) == (eval_question is None):
        _fail("give one START id or --eval N, not both and not neither.")
    base = Path(root)
    try:
        question = (
            read_question(base / eval_file, eval_question) if eval_question is not None else None
        )
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database)
    except (EvalEntryUnusable, SettingsInvalid, GraphUnavailable, SliceError) as exc:
        _fail(str(exc))

    begin = question.start if question is not None else str(start)
    chain: Chain | None
    try:
        chain = walk(graph, begin)
    except StartNotInGraph as exc:
        if question is None:
            _fail(str(exc))
        chain, missing = None, str(exc)
    if chain is not None:
        for line in render_chain(chain):
            _say(line)
    if question is None:
        return

    corpus_snapshot = base / snapshot
    try:
        results = committed_units(base, corpus_snapshot)
        corpus = resolve_accepted(results, records_for_units(results, corpus_snapshot, commit))
        split = holding_units(corpus_snapshot, (item.file for item in question.items))
    except (RebuildFailed, RecordError, OSError) as exc:
        _fail(str(exc))
    report = score(question, chain, results, corpus, settled_run_counts(base), split)
    if chain is not None:
        _say("")
    for line in report_lines(report):
        _say(line)
    if chain is None:
        _fail(missing)


@app.command()
def extract(
    units: Annotated[
        list[str],
        typer.Argument(
            help='Unit addresses, RECORD:SECTION, e.g. 0002:Requirements "0007:Feature design".'
        ),
    ],
    ceiling: float | None = typer.Option(
        None, "--ceiling", help="The most this command may spend, in USD. Required."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Count and price only: no extraction call is made."
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Complete units whose one pass was cut short, owed runs only."
    ),
    root: str = typer.Option(".", "--root", help="The repository root to write artifacts under."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
) -> None:
    """Extract units with the model, three runs each, every attempt written as it settles.

    Spends API credit unless `--dry-run`. Prints a measured estimate first, refuses to
    start when the ceiling cannot cover one call's bound, and stops before any call
    that its bound could carry past the ceiling. `--resume` completes units cut short.
    """
    if ceiling is None:
        _fail("--ceiling USD is required: the most this command may spend.")
    if not (math.isfinite(ceiling) and ceiling > 0):
        _fail(f"--ceiling USD must be a finite number above 0, not {ceiling}.")
    base = Path(root)
    corpus_snapshot = base / snapshot
    # The order spec 0004 sets: the prompt (AC-3), the units, the counts, the
    # collision or resume checks, the ceiling against the bound (AC-8), then calls.
    try:
        system_prompt()
        targets = resolve_addresses(corpus_snapshot, units)
        calibration = resolve_address(corpus_snapshot, CALIBRATION_ADDRESS)
        settings = load_anthropic_settings()
    except (UnitAddressError, ExampleError, SettingsInvalid) as exc:
        _fail(str(exc))

    client = build_client(settings)
    try:
        check_calibration(count_input(client, settings, calibration.unit))
        counted = {t.address: count_input(client, settings, t.unit) for t in targets}
    except EstimateUnavailable as exc:
        _fail(str(exc))
    except anthropic.APIError as exc:
        _fail(f"the token count endpoint failed, so nothing is priced ({exc})")

    runs: dict[str, tuple[RunPlan, ...]] = {}
    collisions: list[tuple[str, Path]] = []
    if resume:
        refused: list[str] = []
        for target in targets:
            try:
                runs[target.address] = resume_runs(base, target, settings.runs_per_unit)
            except ResumeRefused as exc:
                refused.append(str(exc))
        if refused:
            _fail("--resume refuses, before any call: " + "; ".join(refused))
        mismatched = [
            found
            for target in targets
            if (found := provenance_mismatch(base, target, settings, commit)) is not None
        ]
        if mismatched:
            _fail("--resume refuses, before any call: " + "; ".join(mismatched))
    else:
        for target in targets:
            runs[target.address] = fresh_runs(settings.runs_per_unit)
            path = first_collision(base, target, settings.runs_per_unit)
            if path is not None:
                collisions.append((target.address, path))
        if collisions and not dry_run:
            _fail(f"an artifact already exists at {collisions[0][1]}")

    try:
        priced = estimate(
            [
                UnitCount(t.address, t.unit.section, counted[t.address], len(runs[t.address]))
                for t in targets
            ]
        )
    except EstimateUnavailable as exc:
        _fail(str(exc))
    plans = [
        Plan(target=t, runs=runs[t.address], bound=unit.bound_usd)
        for t, unit in zip(targets, priced.units, strict=True)
    ]
    for line in estimate_lines(priced, ceiling):
        _say(line)
    if resume:
        for plan in plans:
            owed = ", ".join(f"run {r.run} from attempt {r.first_attempt}" for r in plan.runs)
            _say(f"  {plan.target.address} resume: {owed}.")
    if dry_run:
        for address, path in collisions:
            _say(f"{address}: a real run would refuse it at the collision check ({path} exists).")
        if ceiling < priced.largest_bound_usd:
            _say(
                f"The ceiling ${ceiling:.2f} is below the largest per call bound "
                f"${priced.largest_bound_usd:.4f}, so a real run would refuse to start."
            )
        _say("Dry run: no extraction call made.")
        return
    if ceiling < priced.largest_bound_usd:
        _fail(
            f"the ceiling ${ceiling:.2f} is below the largest per call bound "
            f"${priced.largest_bound_usd:.4f}, so no call is made."
        )
    if resume:
        try:
            resume_preflight(base, plans)
        except ArtifactCollisionError as exc:
            _fail(str(exc))

    outcome = run_metered(
        plans,
        calls_through(client, settings),
        settings,
        base,
        commit,
        now_utc(),
        ceiling,
        _say,
    )
    for line in summary_lines(outcome):
        _say(line)
    if outcome.stop is not None:
        _fail(outcome.stop)
