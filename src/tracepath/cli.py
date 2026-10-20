"""The `tracepath` terminal command."""

import logging
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn

import anthropic
import typer
from rich.console import Console

from tracepath import __version__
from tracepath.artifacts import (
    GRAPH_BUILD,
    REVIEW_LOG,
    ArtifactCollisionError,
    GraphBuildSummary,
    ManifestUnreadable,
    built_with_code_pass,
    built_with_held_view,
    built_with_narrow_hold,
    ensure_review_log,
    graph_build_summary,
    now_utc,
    review_log_entries,
    review_queue_file,
    write_graph_build,
    write_review_queue,
)
from tracepath.ask.answer import ASK_MAX_TOKENS, answer_lines
from tracepath.ask.answer import PROMPT_VERSION as ASK_PROMPT_VERSION
from tracepath.ask.record import (
    EvalSource,
    RecordUnreadable,
    eval_record_name,
    no_call_record,
    record_name,
    settled_eval_record,
    write_record,
)
from tracepath.ask.retrieve import Pack, build_pack, pack_lines
from tracepath.config import (
    DEFAULT_MODEL,
    AnthropicSettings,
    SettingsInvalid,
    load_anthropic_settings,
    load_neo4j_settings,
)
from tracepath.extract.address import UnitAddressError, resolve_address, resolve_addresses
from tracepath.extract.client import build_client, system_prompt
from tracepath.extract.cost import (
    CALIBRATION_ADDRESS,
    EstimateUnavailable,
    UnitCount,
    ask_bound,
    check_calibration,
    estimate,
    estimate_lines,
    rates_for,
)
from tracepath.extract.examples import ExampleError
from tracepath.extract.metered import (
    CountUnreadable,
    Plan,
    ResumeRefused,
    RunPlan,
    ask_calls_through,
    ask_cost_line,
    ask_metered,
    calls_through,
    count_ask_input,
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
    CodePassUnit,
    NarrowHoldTally,
    RebuildFailed,
    apply_code_pass,
    apply_narrow_hold,
    code_pass_report,
    committed_units,
    narrow_hold_tally,
    narrow_link_keys,
    partial_units,
    records_for_units,
    released_links,
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

#: The help of every `--code-pass` option (spec 0007 AC-7).
CODE_PASS_HELP = (
    "Route with the code pass of spec 0007: a parsed criterion whose three runs agree on "
    "its id and type is not held by a multi_condition_split flag alone. Off by default."
)

#: The help of every `--narrow-hold` option (spec 0008 AC-5b).
NARROW_HOLD_HELP = (
    "Route with the narrow hold rule of spec 0008: an item held only for known_trap_flag "
    "or endpoint_not_accepted, its runs agreeing, is released once every entity it waits "
    "on is accepted. On by default; --no-narrow-hold turns it off."
)

#: Whether the narrow hold rule applies to a command given neither `--narrow-hold` nor
#: `--no-narrow-hold` (spec 0008 AC-9b, spec 0002 AC-11 as amended 2026-10-18).
NARROW_HOLD_DEFAULT = True

#: Whether held items are written and shown when a command is given neither
#: `--with-held` nor `--no-with-held` (spec 0008 AC-11b, spec 0005 as amended 2026-10-18).
WITH_HELD_DEFAULT = True

#: Why `trace --with-held` refuses a graph a default load wrote (spec 0005 AC-26b).
NO_HELD_ITEMS = (
    "--with-held: the graph holds no held item, so there is nothing held to show. "
    "Run `tracepath load --with-held` first, then trace again."
)


#: Why `ask` refuses a graph loaded without held items (spec 0009 AC-5b).
ASK_NEEDS_HELD = (
    "ask reads held items too, but the graph holds no held item. Run `tracepath load` "
    "without --no-with-held first, then ask again."
)


def _setting(given: bool | None, default: bool) -> bool:
    """A two way flag's value: what the command was given, else the project default."""
    return default if given is None else given


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
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        help="The model a held link names when its unit has no run artifacts. "
        "Every other row names the model its unit's artifacts name.",
    ),
    code_pass: bool = typer.Option(False, "--code-pass", help=CODE_PASS_HELP),
    narrow_hold: bool | None = typer.Option(
        None, "--narrow-hold/--no-narrow-hold", help=NARROW_HOLD_HELP
    ),
) -> None:
    """Rebuild the review queue from the committed run artifacts. No API call, no graph.

    Every held item needs somewhere durable to live, or AC-11c's promise that a held
    link sits in a file tracked in git is not true. The artifacts are the source of
    truth (spec 0001), so the queue is derived from them and never hand maintained.
    With `--code-pass`, the queue goes to its own file and the default one is left
    alone (spec 0007 AC-8). `--narrow-hold` does the same with its own file (spec 0008
    AC-5e), and the two together write a third. The default routing always writes
    the default file; each departure from it is named in the file it writes.
    """
    base = Path(root)
    corpus_snapshot = base / snapshot
    narrow = _setting(narrow_hold, NARROW_HOLD_DEFAULT)
    try:
        results = committed_units(base, corpus_snapshot, code_pass=code_pass, narrow_hold=narrow)
    except RebuildFailed as exc:
        err_console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(code=1) from None

    records = records_for_units(results, corpus_snapshot, commit)
    corpus = resolve_accepted(results, records)
    queued_at = max(a.extracted_at for r in results for a in r.artifacts)
    try:
        rows = review_rows(results, corpus.held, model, queued_at)
    except ProvenanceMismatch as exc:
        _fail(str(exc))

    queue = review_queue_file(
        code_pass=code_pass, narrow_hold=narrow, narrow_default=NARROW_HOLD_DEFAULT
    )
    write_review_queue(base, list(rows), queue)
    ensure_review_log(base)
    console.print(
        f"[green]✓[/green] {len(rows)} held items from {len(results)} units "
        f"→ {queue}, log at {REVIEW_LOG}"
    )


@app.command(name="load")
def load_graph(
    root: str = typer.Option(".", "--root", help="The repository root to read and write."),
    snapshot: str = typer.Option(
        "corpus/jobhunt/docs", "--snapshot", help="The pinned corpus snapshot."
    ),
    commit: str = typer.Option("2e40bcf", "--commit", help="The corpus commit the run pins."),
    with_held: bool | None = typer.Option(
        None,
        "--with-held/--no-with-held",
        help="Also write the items review holds back, each marked held (spec 0005). "
        "On by default; --no-with-held writes accepted items only.",
    ),
    code_pass: bool = typer.Option(False, "--code-pass", help=CODE_PASS_HELP),
    narrow_hold: bool | None = typer.Option(
        None, "--narrow-hold/--no-narrow-hold", help=NARROW_HOLD_HELP
    ),
) -> None:
    """Rebuild the graph from the committed run artifacts. No API call.

    Clears the graph, creates the constraints and loads every fully extracted unit,
    every write asserting its own row count, then writes `artifacts/graph-build.json`.
    With `--with-held`, held items are written too, marked held; nothing is accepted.
    With `--code-pass`, units are routed with the code pass, each entity it released
    stamped `accepted_by` `code_pass`, and a report per unit says what it changed.
    With `--narrow-hold`, the narrow hold rule of spec 0008 releases what it may, each
    released entity and link stamped `accepted_by` `narrow_hold`, and the load prints
    how many it released by reason and by flag.
    """
    base = Path(root)
    corpus_snapshot = base / snapshot
    held: HeldView | None = None
    report: tuple[CodePassUnit, ...] = ()
    tally: NarrowHoldTally | None = None
    narrow_links: frozenset[tuple[Any, str, str]] = frozenset()
    narrow = _setting(narrow_hold, NARROW_HOLD_DEFAULT)
    show_held = _setting(with_held, WITH_HELD_DEFAULT)
    try:
        settings = load_neo4j_settings()
        results = committed_units(base, corpus_snapshot)
        records = records_for_units(results, corpus_snapshot, commit)
        corpus = resolve_accepted(results, records)
        if code_pass:
            # The whole corpus resolved both ways, so a link released in another unit
            # is counted too (spec 0007 AC-17).
            plain = corpus
            results = apply_code_pass(results)
            corpus = resolve_accepted(results, records)
            report = code_pass_report(results, released_links(plain, corpus))
        if narrow:
            # Resolved both ways under the same code pass setting, so a link released
            # in another unit is counted and stamped too (spec 0008 AC-5).
            before = corpus
            results = apply_narrow_hold(results, code_pass=code_pass)
            corpus = resolve_accepted(results, records)
            tally = narrow_hold_tally(before, results, corpus)
            narrow_links = narrow_link_keys(before, corpus)
        if show_held:
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
            code_pass=code_pass,
            narrow_hold=tally.counts() if tally is not None else None,
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
                narrow_links=narrow_links,
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
    for line in _code_pass_lines(report):
        _say(line)
    if tally is not None:
        for line in _narrow_hold_lines(tally):
            _say(line)
    versions = ", ".join(f"{v}: {n}" for v, n in manifest["prompt_versions"].items())
    _say(f"Units per prompt version: {versions}.")
    # The graph mixes models until feature 9, so a load says which made what (spec 0007 AC-4).
    models = Counter(provenance.model for provenance in provenances)
    _say(f"Units per model: {', '.join(f'{m}: {n}' for m, n in sorted(models.items()))}.")
    for partial in partial_units(base):
        _say(
            f"Not loaded: {partial.record} {partial.section} has {partial.settled_runs} "
            "settled runs of 3, so it is not extracted."
        )
    _say(f"Build manifest: {path.relative_to(base).as_posix()}")


def _code_pass_lines(report: Sequence[CodePassUnit]) -> tuple[str, ...]:
    """The code pass report `load --code-pass` prints, one line per unit (spec 0007 AC-17)."""
    if not report:
        return ()
    lines = ["Code pass (spec 0007), per unit:"]
    for row in report:
        decided = ", ".join(row.decided) if row.decided else "none"
        repeated = f" (ids on two bullets: {', '.join(row.repeated)})" if row.repeated else ""
        lines.append(
            f"  {row.record} {row.section}: code decided {len(row.decided)} ({decided}); "
            f"{row.released_entities} entities released, {row.released_links} links "
            f"released; {row.not_decided} parsed bullets not code decided{repeated}; "
            f"{row.struck} bullets opening with ~~ after the colon left to the model; "
            f"{row.unparsed} other AC bullets failed the parse."
        )
    lines.append(
        f"Code pass total: {sum(r.released_entities for r in report)} entities and "
        f"{sum(r.released_links for r in report)} links released, each entity stamped "
        "accepted_by code_pass."
    )
    return tuple(lines)


def _narrow_hold_lines(tally: NarrowHoldTally) -> tuple[str, ...]:
    """What `load --narrow-hold` prints about its releases (spec 0008 AC-5)."""
    reasons = ", ".join(f"{name} {n}" for name, n in tally.by_reason)
    flags = ", ".join(f"{flag} {n}" for flag, n in tally.by_flag) or "none"
    return (
        f"Narrow hold (spec 0008): {tally.entities} entities and {tally.links} links "
        "released, each stamped accepted_by narrow_hold.",
        f"  By hold reason, an item counted under each reason that held it: {reasons} "
        f"({tally.held_for_both} held for both).",
        "  known_trap_flag releases by flag, an item counted under each flag any of its runs "
        f"raised: {flags}.",
    )


def _refuse_narrow_hold_mismatch(base: Path, narrow_hold: bool) -> None:
    """Exit 1 unless the graph was loaded with the narrow hold setting given (spec 0008 AC-5d).

    Read from `artifacts/graph-build.json` before any connection; a missing
    `narrow_hold` key means the graph was loaded without the rule.
    """
    try:
        built = built_with_narrow_hold(base)
    except ManifestUnreadable as exc:
        _fail(str(exc))
    if built == narrow_hold:
        return
    if narrow_hold:
        _fail(
            f"the narrow hold rule is on for this command, but {GRAPH_BUILD.as_posix()} says "
            "the graph was loaded without it. Run `tracepath load` first, or add "
            "--no-narrow-hold."
        )
    _fail(
        f"{GRAPH_BUILD.as_posix()} says the graph was loaded with the narrow hold rule, but "
        "it is off for this command. Run `tracepath load --no-narrow-hold` first, or drop "
        "--no-narrow-hold."
    )


def _refuse_code_pass_mismatch(base: Path, code_pass: bool) -> None:
    """Exit 1 unless the graph was loaded with the routing this command will score.

    Read from `artifacts/graph-build.json` before any connection (spec 0007 AC-7c); a
    missing `code_pass` key means the graph was loaded without the pass.
    """
    try:
        built = built_with_code_pass(base)
    except ManifestUnreadable as exc:
        _fail(str(exc))
    if built == code_pass:
        return
    if code_pass:
        _fail(
            f"--code-pass scores the code pass routing, but {GRAPH_BUILD.as_posix()} says the "
            "graph was loaded without it. Run `tracepath load --code-pass` first, or drop "
            "--code-pass."
        )
    _fail(
        f"{GRAPH_BUILD.as_posix()} says the graph was loaded with --code-pass, but this "
        "command scores the default routing. Add --code-pass, or run `tracepath load` first."
    )


def _scored_held_view(base: Path, given: bool | None) -> bool:
    """The held view a score uses: the flag given, else how the graph was loaded.

    With neither `--with-held` nor `--no-with-held`, `eval` and `trace --eval` follow
    `artifacts/graph-build.json` (its `held_view` key), so a graph loaded with
    `--no-with-held` is never scored under the held view's label.
    """
    if given is not None:
        return given
    try:
        return built_with_held_view(base)
    except ManifestUnreadable as exc:
        _fail(str(exc))


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


def _committed(
    base: Path, corpus_snapshot: Path, commit: str, code_pass: bool, narrow_hold: bool = False
) -> _Committed:
    """Rebuild every fully extracted unit from the run files, for scoring.

    With `code_pass`, routed with the pass, so the scoring explains the routing the
    graph holds (spec 0007 AC-7d); with `narrow_hold`, the same for the narrow hold
    rule (spec 0008).
    """
    results = committed_units(base, corpus_snapshot, code_pass=code_pass, narrow_hold=narrow_hold)
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
    with_held: bool | None = typer.Option(
        None,
        "--with-held/--no-with-held",
        help="Walk through held items too, each printed as held (spec 0005). On by default; "
        "with --eval N and neither flag, follows how the graph was loaded. --no-with-held "
        "walks accepted items only. Given by name, needs a graph holding held items.",
    ),
    release_held_out: bool = typer.Option(
        False,
        "--release-held-out",
        help="Run a held out eval file (spec 0006). Only once features 13 and 11 committed.",
    ),
    code_pass: bool = typer.Option(
        False, "--code-pass", help=CODE_PASS_HELP + " Needs --eval N and a graph from it."
    ),
    narrow_hold: bool | None = typer.Option(
        None,
        "--narrow-hold/--no-narrow-hold",
        help=NARROW_HOLD_HELP + " Needs --eval N and a graph from it.",
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
    if code_pass and eval_question is None:
        _fail("--code-pass changes the routing scored, so it needs --eval N.")
    if narrow_hold is True and eval_question is None:
        _fail("--narrow-hold changes the routing scored, so it needs --eval N.")
    narrow = _setting(narrow_hold, NARROW_HOLD_DEFAULT)
    show_held = _setting(with_held, WITH_HELD_DEFAULT)
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
            _refuse_code_pass_mismatch(base, code_pass)
            _refuse_narrow_hold_mismatch(base, narrow)
            show_held = _scored_held_view(base, with_held)
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database, with_held=show_held)
    except (
        EvalEntryUnusable,
        HeldOutRefused,
        SidecarInvalid,
        SettingsInvalid,
        GraphUnavailable,
        SliceError,
    ) as exc:
        _fail(str(exc))
    if with_held is True and not _holds_held(graph):
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
            _committed(base, corpus_snapshot, commit, code_pass, narrow),
            corpus_snapshot,
            with_held=show_held,
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
    with_held: bool | None = typer.Option(
        None,
        "--with-held/--no-with-held",
        help="Score under the held item view too (spec 0005). With neither flag, follows how "
        "the graph was loaded; --no-with-held scores accepted items only. Given by name, "
        "needs a graph holding held items.",
    ),
    release_held_out: bool = typer.Option(
        False,
        "--release-held-out",
        help="Run a held out eval file (spec 0006). Only once features 13 and 11 committed.",
    ),
    code_pass: bool = typer.Option(
        False, "--code-pass", help=CODE_PASS_HELP + " Needs a graph from `load --code-pass`."
    ),
    narrow_hold: bool | None = typer.Option(
        None,
        "--narrow-hold/--no-narrow-hold",
        help=NARROW_HOLD_HELP + " Needs a graph loaded with the same setting.",
    ),
) -> None:
    """Score every question of an eval file: pass, fail or inconclusive, difference shown.

    No API call. Prints each question's report block, then its result and its evidence,
    and never a total or a rate. Exits 0 when every question reached a result, and 1
    when one could not be scored or the run itself failed.
    """
    base = Path(root)
    path = base / eval_file
    narrow = _setting(narrow_hold, NARROW_HOLD_DEFAULT)
    show_held = _scored_held_view(base, with_held)
    try:
        eval_set = read_eval_set(path, release_held_out=release_held_out)
        sidecar = read_sidecar(base, path)
        _refuse_code_pass_mismatch(base, code_pass)
        _refuse_narrow_hold_mismatch(base, narrow)
        settings = load_neo4j_settings()
        with connect(settings) as driver:
            graph = read_graph(driver, settings.database, with_held=show_held)
    except (
        EvalEntryUnusable,
        HeldOutRefused,
        SidecarInvalid,
        SettingsInvalid,
        GraphUnavailable,
        SliceError,
    ) as exc:
        _fail(str(exc))
    if with_held is True and not _holds_held(graph):
        _fail(NO_HELD_ITEMS)
    corpus_snapshot = base / snapshot
    try:
        committed = _committed(base, corpus_snapshot, commit, code_pass, narrow)
    except (RebuildFailed, RecordError, OSError, UnicodeDecodeError) as exc:
        _fail(str(exc))

    # Above the first block, in this order (AC-9c): held out, unchecked, held view.
    header: list[str] = []
    if eval_set.held_out:
        header.append(HELD_OUT_LABEL)
    if sidecar is not None:
        try:
            digest = examples_digest(base)
        except OSError as exc:
            _fail(f"cannot read a tracked example: {exc}")
        if digest is not None and digest != sidecar.examples_sha256:
            header.append(UNCHECKED_LINE)
    if show_held:
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
                question, graph, committed, corpus_snapshot, with_held=show_held
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
    expect_model: str | None = typer.Option(
        None,
        "--expect-model",
        help="Refuse before any call unless the settings name this model (spec 0007 AC-29).",
    ),
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
    # An old `ANTHROPIC_MODEL` in `.env` overrides the default silently (spec 0007 AC-29).
    if expect_model is not None and settings.model != expect_model:
        _fail(
            f"--expect-model {expect_model}, but the settings name {settings.model} "
            "(check ANTHROPIC_MODEL in `.env`), so no call is made."
        )

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
            ],
            settings.model,
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


def _ask_graph() -> GraphSlice:
    """The graph `ask` reads: every item, held ones included (spec 0009 AC-5).

    Raises:
        SettingsInvalid: a Neo4j setting is missing.
        GraphUnavailable: Neo4j cannot be reached.
        SliceError: a node read back has no canonical id or no known label.
    """
    settings = load_neo4j_settings()
    with connect(settings) as driver:
        return read_graph(driver, settings.database, with_held=True)


def _graph_line(built: GraphBuildSummary) -> str:
    """How the graph was loaded, read from `artifacts/graph-build.json` (AC-5c and its note)."""
    held = "yes" if built.held_view else "no"
    narrow = "yes" if built.narrow_hold else "no"
    code = "yes" if built.code_pass else "no"
    return (
        f"Graph: held view {held}, narrow hold {narrow}, code pass {code}, "
        f"corpus {built.corpus_commit}."
    )


@app.command()
def ask(
    question: str | None = typer.Argument(
        None, help='A why question in plain English, e.g. "Why does the landing rule hold?"'
    ),
    eval_question: int | None = typer.Option(
        None, "--eval", help="Ask the question of eval entry N instead of a typed one."
    ),
    ceiling: float | None = typer.Option(
        None,
        "--ceiling",
        help="The most this command may spend, in USD. Required, except with --dry-run.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Find the items and price the call only: no call, no record."
    ),
    eval_file: str = typer.Option(
        str(EVAL_FILE), "--eval-file", help="The eval set --eval reads, relative to --root."
    ),
    release_held_out: bool = typer.Option(
        False,
        "--release-held-out",
        help="Ask a question of a held out eval file. A question already answered once by a "
        "settled call is refused.",
    ),
    root: str = typer.Option(".", "--root", help="The repository root to read and write."),
) -> None:
    """Answer a why question from the graph, every claim citing the item it rests on.

    Code finds the items, one model call reads them, and code checks every citation.
    Prints the items first, then the answer, then what the call cost. Spends API credit
    unless `--dry-run`, which makes no paid call and so needs no `--ceiling`.
    """
    if (question is None) == (eval_question is None):
        _fail("give one QUESTION or --eval N, not both and not neither.")
    if release_held_out and eval_question is None:
        _fail("--release-held-out reads an eval file, so it needs --eval N.")
    if ceiling is None and not dry_run:
        _fail("--ceiling USD is required: the most this command may spend.")
    if ceiling is not None and not (math.isfinite(ceiling) and ceiling > 0):
        _fail(f"--ceiling USD must be a finite number above 0, not {ceiling}.")
    base = Path(root)
    source: EvalSource | None = None
    asked = str(question)
    if eval_question is not None:
        source = EvalSource(eval_file, eval_question)
        try:
            eval_set = read_eval_set(base / eval_file, release_held_out=release_held_out)
            asked = _eval_question_text(eval_set.entries, eval_question, eval_file)
            answered = settled_eval_record(base, source) if eval_set.held_out else None
        except (EvalEntryUnusable, HeldOutRefused, RecordUnreadable) as exc:
            _fail(str(exc))
        if answered is not None:
            _fail(
                f"{eval_file} question {eval_question} is held out and was already answered "
                f"by a settled call ({_shown_path(answered, base)}), so it is not asked again."
            )
    try:
        settings = load_anthropic_settings()
        built = graph_build_summary(base)
        graph = _ask_graph()
    except (ManifestUnreadable, SettingsInvalid, GraphUnavailable, SliceError) as exc:
        _fail(str(exc))
    if not _holds_held(graph):
        _fail(ASK_NEEDS_HELD)

    pack = build_pack(graph, asked)
    asked_at = datetime.now(UTC)
    _say(f"Question: {asked}")
    if source is not None:
        _say(f"Eval: {source.file} question {source.number}.")
    _say(_graph_line(built))
    for line in pack_lines(pack):
        _say(line)
    if not pack.items:
        if source is not None and ceiling is not None and not dry_run:
            _write_no_call_record(base, asked_at, pack, ceiling, settings, built, source)
        return

    # AC-23: an unpriced model stops before the count, and the count is the free endpoint.
    try:
        rates = rates_for(settings.model)
    except EstimateUnavailable as exc:
        _fail(str(exc))
    client = build_client(settings)
    try:
        counted = count_ask_input(client, settings, pack)
    except (anthropic.APIError, CountUnreadable) as exc:
        _fail(f"the token count endpoint failed, so nothing is priced ({exc})")
    bound = ask_bound(counted, settings.model)
    limit = "no ceiling given" if ceiling is None else f"ceiling ${ceiling:.2f}"
    _say(
        f"Input: {counted:,} tokens counted. Bound: ${bound:.4f} ({counted:,} in at "
        f"${rates.input:.2f}, {ASK_MAX_TOKENS:,} out at ${rates.output:.2f}, per million "
        f"tokens, model {settings.model}); {limit}."
    )
    if dry_run or ceiling is None:  # no ceiling got this far only as a dry run
        if ceiling is not None and bound > ceiling:
            _say("The bound is above the ceiling, so a real run would stop before the call.")
        _say("Dry run: no call made, no record written.")
        return

    name = eval_record_name(asked_at, source) if source else record_name(asked_at, asked)
    try:
        outcome = ask_metered(
            pack,
            ask_calls_through(client, settings),
            settings,
            root=base,
            name=name,
            asked_at=asked_at,
            commit=built.corpus_commit,
            counted=counted,
            bound=bound,
            ceiling=ceiling,
            source=source,
        )
    except ArtifactCollisionError as exc:
        _fail(str(exc))
    except KeyboardInterrupt as exc:
        # Click turns the interrupt into a bare "Aborted!", so the note ask_metered()
        # added (saved as failed, or lost) is printed here before it propagates.
        for note in getattr(exc, "__notes__", ()):
            err_console.print(note, markup=False, highlight=False, soft_wrap=True)
        raise
    if outcome.stop is not None:
        _fail(outcome.stop)
    attempt = outcome.attempt
    if attempt is not None and attempt.answer is not None:
        for line in answer_lines(attempt.answer, outcome.checked):
            _say(line)
    elif attempt is not None:
        _say(f"Answer: none, {attempt.error}. The call counts at its bound.")
    _say(ask_cost_line(outcome, ceiling))
    if outcome.lost is not None:
        _say("Record: lost.")
        _fail(f"the call was paid for, but its record could not be written ({outcome.lost}).")
    if outcome.path is not None:
        _say(f"Record: {_shown_path(outcome.path, base)}")
    if not outcome.settled:
        _fail("the call failed and is saved; it is not retried. Run the question again by hand.")


def _eval_question_text(entries: Sequence[Mapping[str, Any]], number: int, eval_file: str) -> str:
    """The `question` text of eval entry `number`, counting from 1, and nothing else (AC-30).

    Raises:
        EvalEntryUnusable: `number` is out of range, or the entry has no question text.
    """
    if not 1 <= number <= len(entries):
        raise EvalEntryUnusable(
            f"--eval {number}: {eval_file} has {len(entries)} entries, numbered from 1."
        )
    entry = entries[number - 1]
    text = entry.get("question") if isinstance(entry, Mapping) else None
    if not isinstance(text, str) or not text.strip():
        raise EvalEntryUnusable(f"--eval {number}: entry {number} of {eval_file} has no question.")
    return text


def _write_no_call_record(
    base: Path,
    asked_at: datetime,
    pack: Pack,
    ceiling: float,
    settings: AnthropicSettings,
    built: GraphBuildSummary,
    source: EvalSource,
) -> None:
    """Write the record of an `--eval` ask that matched no item (AC-29)."""
    record = no_call_record(
        asked_at=asked_at,
        pack=pack,
        ceiling=ceiling,
        model=settings.model,
        effort=settings.effort or "default",
        prompt_version=ASK_PROMPT_VERSION,
        commit=built.corpus_commit,
        source=source,
    )
    try:
        path = write_record(base, eval_record_name(asked_at, source), record)
    except (OSError, ArtifactCollisionError) as exc:
        _fail(f"the record of this no call ask could not be written ({exc}).")
    _say(f"Record: {_shown_path(path, base)}")


def _shown_path(path: Path, base: Path) -> str:
    """A path relative to the root it was written under, when it is under it."""
    return path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path)
