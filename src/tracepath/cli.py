"""The `tracepath` terminal command."""

import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, NoReturn

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
    CountUnreadable,
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
    CorpusResolution,
    HeldView,
    HeldViewIncomplete,
    ProvenanceMismatch,
    UnitResult,
    build_held_view,
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
    HELD_LABEL,
    HELD_OUT_LABEL,
    UNCHECKED_LINE,
    EvalEntryUnusable,
    HeldOutRefused,
    Question,
    Report,
    Sidecar,
    SidecarInvalid,
    examples_digest,
    holding_units,
    question_from,
    read_eval_set,
    read_sidecar,
    report_lines,
    resolve_start,
    result_lines,
    score,
    verdict,
)
from tracepath.traverse.graph_slice import GraphSlice, NodeKind, SliceError, drop_held
from tracepath.traverse.render import render_chain
from tracepath.traverse.walk import Chain, StartNotInGraph, walk

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)

#: Who accepted what a load writes. Nothing is reviewed by hand yet (spec 0002), so
#: every accepted item was accepted by the three run agreement rule.
ACCEPTED_BY = "auto"

#: Why `trace --with-held` refuses a graph a default load wrote (spec 0005 AC-26b).
NO_HELD_ITEMS = (
    "--with-held: the graph holds no held item, so there is nothing held to show. "
    "Run `tracepath load --with-held` first, then trace again."
)


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
    with_held: bool = typer.Option(
        False,
        "--with-held",
        help="Also write the items review holds back, each marked held (spec 0005).",
    ),
) -> None:
    """Rebuild the graph from the committed run artifacts. No API call.

    Clears the graph, creates the constraints and loads every fully extracted unit,
    every write asserting its own row count, then writes `artifacts/graph-build.json`.
    With `--with-held`, held items are written too, marked held; nothing is accepted.
    """
    base = Path(root)
    corpus_snapshot = base / snapshot
    held: HeldView | None = None
    try:
        settings = load_neo4j_settings()
        results = committed_units(base, corpus_snapshot)
        records = records_for_units(results, corpus_snapshot, commit)
        corpus = resolve_accepted(results, records)
        if with_held:
            held = build_held_view(results, corpus, records)
        provenances = [unit_provenance(result, ACCEPTED_BY) for result in results]
        manifest = graph_build(
            results,
            corpus,
            provenances,
            commit,
            review_log_entries(base),
            unit_passes(base),
            held,
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
                held=held,
            )
    except (
        SettingsInvalid,
        RebuildFailed,
        RecordError,
        ProvenanceMismatch,
        HeldViewIncomplete,
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
    if held is not None:
        _say(
            f"Held item view (spec 0005), nothing accepted: {written['held_entities']} held "
            f"entities, {written['held_links']} held links and {written['held_unresolved']} "
            "held unresolved written, each marked held. Skipped as already written: "
            f"{held.skipped_entities} held entities, {held.skipped_links} held links. "
            f"Not written, no first run item behind them: "
            f"{held.not_written_entities + held.not_written_links} queue rows."
        )
    versions = ", ".join(f"{v}: {n}" for v, n in manifest["prompt_versions"].items())
    _say(f"Units per prompt version: {versions}.")
    for partial in partial_units(base):
        _say(
            f"Not loaded: {partial.record} {partial.section} has {partial.settled_runs} "
            "settled runs of 3, so it is not extracted."
        )
    _say(f"Build manifest: {path.relative_to(base).as_posix()}")


def _holds_held(graph: GraphSlice) -> bool:
    """Whether a load wrote held items: any held entity or `:Unresolved` node (AC-26)."""
    return any(
        node.held and node.kind in (NodeKind.ENTITY, NodeKind.UNRESOLVED) for node in graph.nodes
    )


@dataclass(frozen=True)
class _Committed:
    """What the committed run files hold, read once: no API call, no graph."""

    results: tuple[UnitResult, ...]
    corpus: CorpusResolution
    settled: dict[tuple[str, str], int]


def _committed(base: Path, corpus_snapshot: Path, commit: str) -> _Committed:
    """Rebuild every fully extracted unit from the run files, for scoring."""
    results = committed_units(base, corpus_snapshot)
    corpus = resolve_accepted(results, records_for_units(results, corpus_snapshot, commit))
    return _Committed(results, corpus, settled_run_counts(base))


@dataclass(frozen=True)
class _Scored:
    """One scored question, the chain `trace` prints, and why there is none."""

    report: Report
    chain: Chain | None
    missing: str | None


def _score_question(
    question: Question,
    graph: GraphSlice,
    committed: _Committed,
    corpus_snapshot: Path,
    *,
    with_held: bool,
) -> _Scored:
    """The body `trace --eval` and `eval` share: resolve the start, walk, score.

    The start is resolved once, and the clean walk starts at that same id (spec 0006
    AC-13). Under the held view the printed chain is the held walk; the clean walk,
    over the same read with held items dropped, decides `reached` (spec 0005 AC-12).

    Raises:
        EvalEntryUnusable: a cited line sits before the first unit of its file.
        OSError: a cited file cannot be read.
    """
    start = resolve_start(question, graph)
    chain: Chain | None = None
    missing: str | None = None
    if start.id is None and question.start_at is not None:
        file, line = question.start_at
        missing = f"no entity at {file}:{line}, so the walk has no start."
    elif start.id is not None:
        try:
            chain = walk(graph, start.id)
        except StartNotInGraph as exc:
            missing = str(exc)
    clean: Chain | None = chain
    if with_held and start.id is not None:
        try:
            clean = walk(drop_held(graph), start.id)
        except StartNotInGraph:
            clean = None
    split = holding_units(corpus_snapshot, (item.file for item in question.items))
    report = score(
        question,
        clean,
        committed.results,
        committed.corpus,
        committed.settled,
        split,
        with_held=with_held,
        held=chain if with_held else None,
        start=start,
    )
    return _Scored(report, chain, missing)


def _question(
    entries: Sequence[Mapping[str, Any]],
    sidecar: Sidecar | None,
    number: int,
    *,
    held_out: bool,
) -> Question:
    """Question N with its sidecar absence items, if the sidecar lists any."""
    notes = sidecar.questions.get(number) if sidecar is not None else None
    return question_from(
        entries,
        number,
        absence=notes.absence if notes is not None else None,
        held_out=held_out,
    )


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
    with_held: bool = typer.Option(
        False,
        "--with-held",
        help="Walk through held items too, each printed as held (spec 0005). "
        "Needs a graph from `load --with-held`.",
    ),
    release_held_out: bool = typer.Option(
        False,
        "--release-held-out",
        help="Run a held out eval file (spec 0006). Only once features 13 and 11 committed.",
    ),
) -> None:
    """Walk the chain from one item and print every step, each citing its record.

    Breadth first along the seven typed links, both ways, at most three hops. A Record
    or Unresolved node is printed and not expanded. With `--eval N`, the start comes
    from question N, and the chain is then scored against its expected items. The walk
    never reads the eval set; only the scoring after it does. With `--with-held`, the
    chain runs through held items, each marked held, and the scoring walks twice:
    without held items and with them.
    """
    if (start is None) == (eval_question is None):
        _fail("give one START id or --eval N, not both and not neither.")
    if release_held_out and eval_question is None:
        _fail("--release-held-out reads an eval file, so it needs --eval N.")
    base = Path(root)
    question: Question | None = None
    held_out = False
    try:
        if eval_question is not None:
            eval_set = read_eval_set(base / eval_file, release_held_out=release_held_out)
            held_out = eval_set.held_out
            question = _question(
                eval_set.entries,
                read_sidecar(base, base / eval_file),
                eval_question,
                held_out=held_out,
            )
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database, with_held=with_held)
    except (
        EvalEntryUnusable,
        HeldOutRefused,
        SidecarInvalid,
        SettingsInvalid,
        GraphUnavailable,
        SliceError,
    ) as exc:
        _fail(str(exc))
    if with_held and not _holds_held(graph):
        _fail(NO_HELD_ITEMS)

    if question is None:
        try:
            chain = walk(graph, str(start))
        except StartNotInGraph as exc:
            _fail(str(exc))
        for line in render_chain(chain):
            _say(line)
        return

    corpus_snapshot = base / snapshot
    try:
        scored = _score_question(
            question,
            graph,
            _committed(base, corpus_snapshot, commit),
            corpus_snapshot,
            with_held=with_held,
        )
    except (RebuildFailed, RecordError, EvalEntryUnusable, OSError, UnicodeDecodeError) as exc:
        _fail(str(exc))
    if held_out:
        _say(HELD_OUT_LABEL)
    if scored.chain is not None:
        for line in render_chain(scored.chain):
            _say(line)
        _say("")
    for line in report_lines(scored.report):
        _say(line)
    if scored.chain is None:
        _fail(scored.missing or "the walk has no start.")


@app.command(name="eval")
def eval_set_command(
    eval_file: str = typer.Option(
        str(EVAL_FILE), "--eval-file", help="The eval set, relative to --root."
    ),
    root: str = typer.Option(".", "--root", help="The repository root to read."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
    with_held: bool = typer.Option(
        False,
        "--with-held",
        help="Score under the held item view too (spec 0005). "
        "Needs a graph from `load --with-held`.",
    ),
    release_held_out: bool = typer.Option(
        False,
        "--release-held-out",
        help="Run a held out eval file (spec 0006). Only once features 13 and 11 committed.",
    ),
) -> None:
    """Score every question of an eval file: pass, fail or inconclusive, difference shown.

    No API call. Prints each question's report block, then its result and its evidence,
    and never a total or a rate. Exits 0 when every question reached a result, and 1
    when one could not be scored or the run itself failed.
    """
    base = Path(root)
    path = base / eval_file
    try:
        eval_set = read_eval_set(path, release_held_out=release_held_out)
        sidecar = read_sidecar(base, path)
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database, with_held=with_held)
    except (
        EvalEntryUnusable,
        HeldOutRefused,
        SidecarInvalid,
        SettingsInvalid,
        GraphUnavailable,
        SliceError,
    ) as exc:
        _fail(str(exc))
    if with_held and not _holds_held(graph):
        _fail(NO_HELD_ITEMS)
    corpus_snapshot = base / snapshot
    try:
        committed = _committed(base, corpus_snapshot, commit)
    except (RebuildFailed, RecordError) as exc:
        _fail(str(exc))

    # Above the first block, in this order (AC-9c): held out, unchecked, held view.
    header: list[str] = []
    if eval_set.held_out:
        header.append(HELD_OUT_LABEL)
    if sidecar is not None:
        digest = examples_digest(base)
        if digest is not None and digest != sidecar.examples_sha256:
            header.append(UNCHECKED_LINE)
    if with_held:
        header.append(HELD_LABEL)
    for line in header:
        _say(line)

    unusable = False
    for number in range(1, len(eval_set.entries) + 1):
        if header or number > 1:
            _say("")
        notes = sidecar.questions.get(number) if sidecar is not None else None
        try:
            question = _question(eval_set.entries, sidecar, number, held_out=eval_set.held_out)
            report = _score_question(
                question, graph, committed, corpus_snapshot, with_held=with_held
            ).report
        except EvalEntryUnusable as exc:
            _say(f"Question {number}: UNUSABLE, {exc}")
            unusable = True
            continue
        except (OSError, UnicodeDecodeError) as exc:
            _say(f"Question {number}: UNUSABLE, a cited file cannot be read ({exc})")
            unusable = True
            continue
        lines = report_lines(report)
        # The held view's label prints once, above the first block (AC-9b).
        for line in lines[1:] if lines[:1] == (HELD_LABEL,) else lines:
            _say(line)
        _say("")
        for line in result_lines(report, verdict(report), notes.evidence if notes else None):
            _say(line)
    if unusable:
        _fail("a question could not be scored; its UNUSABLE line says why.")


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
    except (anthropic.APIError, CountUnreadable) as exc:
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
