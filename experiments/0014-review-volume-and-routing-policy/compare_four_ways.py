"""Run the eval four ways and tabulate each step's state (spec 0008 AC-8), no API call.

The four configurations are baseline, `--with-held` alone, `--narrow-hold` alone, and
both, `--code-pass` off throughout. For each one the script runs `tracepath load` and
`tracepath eval` with the same flags, keeping their printed output under
`data/four-way/`, then scores the five questions of `eval/linked-records-research.json`
in process from the very graph that load wrote, through the same `_score_question()`
`eval` uses, to read each expected step's state and the visited steps matching no
expected item. It never opens the held out file.

After the four runs, whatever happened, it runs a plain `tracepath load`, so the graph
and `artifacts/graph-build.json` are left as a default load leaves them (AC-8e). If any
step is worse with both flags than with the better single flag, it says so and reads no
AC-9 or AC-11 fact (AC-8f), and exits 1.

Refuses to run when `artifacts/runs/` has uncommitted changes, since the table names
the commit it ran against (AC-8b).

Run from the repository root: uv run python <this file>
"""

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from tracepath.artifacts import GRAPH_BUILD
from tracepath.cli import _committed, _question, _score_question
from tracepath.config import load_neo4j_settings
from tracepath.four_way import (
    CONFIGS,
    Config,
    Noise,
    StepRow,
    cell_of,
    noise_of,
    summed,
    table_lines,
    worse_under_both,
)
from tracepath.graph import connect
from tracepath.graph.read import read_graph
from tracepath.report import EVAL_FILE, Finding, read_eval_set, read_sidecar

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"
OUT = Path(__file__).resolve().parent / "data"


class ComparisonRefused(Exception):
    """The comparison cannot run, or a load did not leave the state it was asked for."""


def runs_commit(root: Path) -> str:
    """The last commit that touched `artifacts/runs/`, refusing uncommitted changes there."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()

    if git("status", "--porcelain", "--", "artifacts/runs"):
        raise ComparisonRefused("artifacts/runs/ has uncommitted changes")
    return git("log", "-1", "--format=%H", "--", "artifacts/runs")


def tracepath(root: Path, snapshot: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one `tracepath` command over `root`, as a person would type it."""
    return subprocess.run(
        ["tracepath", *args, "--root", str(root), "--snapshot", str(snapshot)],
        capture_output=True,
        text=True,
        check=False,
    )


def check_manifest(root: Path, config: Config) -> None:
    """The load wrote what `config` asked for, and never the code pass (AC-8)."""
    manifest = json.loads((root / GRAPH_BUILD).read_text())
    if "code_pass" in manifest:
        raise ComparisonRefused(f"{config.name}: the graph was loaded with the code pass")
    if (manifest.get("narrow_hold") is True) != config.narrow_hold:
        raise ComparisonRefused(f"{config.name}: the manifest's narrow_hold key does not match")
    if ("held_view" in manifest) != config.with_held:
        raise ComparisonRefused(f"{config.name}: the manifest's held_view key does not match")


Scored = list[tuple[int, bool, Finding]]


def score_config(root: Path, snapshot: Path, config: Config) -> tuple[list[Scored], Noise]:
    """Every question's findings under the graph now loaded, and their summed noise."""
    path = root / EVAL_FILE
    eval_set = read_eval_set(path)
    sidecar = read_sidecar(root, path)
    settings = load_neo4j_settings()
    with connect(settings) as driver:
        graph = read_graph(driver, settings.database, with_held=config.with_held)
    committed = _committed(root, snapshot, COMMIT, False, config.narrow_hold)
    per_question: list[Scored] = []
    noises: list[Noise] = []
    for number in range(1, len(eval_set.entries) + 1):
        question = _question(eval_set.entries, sidecar, number, held_out=False)
        scored = _score_question(question, graph, committed, snapshot, with_held=config.with_held)
        per_question.append([(number, question.absence, f) for f in scored.report.findings])
        noises.append(noise_of(scored.report, scored.chain, with_held=config.with_held))
    return per_question, summed(noises)


def compare(
    root: Path, snapshot: Path, commit: str, out: Path, say: Callable[[str], None] = print
) -> int:
    """Run the four configurations, restore a plain load, write the table; 1 if AC-8f stops it."""
    raw = out / "four-way"
    raw.mkdir(parents=True, exist_ok=True)
    found: dict[str, list[Scored]] = {}
    noise: dict[str, Noise] = {}
    try:
        for config in CONFIGS:
            say(f"{config.name}: load {' '.join(config.flags)}")
            loaded = tracepath(root, snapshot, "load", *config.flags)
            slug = config.name.lstrip("-")
            (raw / f"{slug}-load.txt").write_text(loaded.stdout + loaded.stderr)
            if loaded.returncode != 0:
                raise ComparisonRefused(f"{config.name}: load failed: {loaded.stderr.strip()}")
            check_manifest(root, config)
            scored = tracepath(root, snapshot, "eval", *config.flags)
            (raw / f"{slug}-eval.txt").write_text(scored.stdout + scored.stderr)
            found[config.name], noise[config.name] = score_config(root, snapshot, config)
    finally:
        say("restoring a plain load")
        restored = tracepath(root, snapshot, "load")
        (raw / "restore-load.txt").write_text(restored.stdout + restored.stderr)
        if restored.returncode != 0:
            raise ComparisonRefused(f"the plain load after failed: {restored.stderr.strip()}")
        check_manifest(root, CONFIGS[0])

    rows: list[StepRow] = []
    baseline = found[CONFIGS[0].name]
    for q, items in enumerate(baseline):
        for i, (number, absence, finding) in enumerate(items):
            cells = tuple(cell_of(found[c.name][q][i][2]) for c in CONFIGS)
            where = f"{finding.item.file}:{finding.item.line}"
            rows.append(StepRow(number, absence, finding.item.label, where, cells))
    lines = (
        "# Four way comparison (spec 0008 AC-8 to AC-8f)",
        "",
        *table_lines(rows, noise, commit, EVAL_FILE.as_posix()),
    )
    text = "\n".join(lines) + "\n"
    (out / "four-way.md").write_text(text)
    say(text)
    return 1 if worse_under_both(rows) else 0


def main() -> int:
    """Compare over this repository's committed runs."""
    return compare(ROOT, SNAPSHOT, runs_commit(ROOT), OUT)


if __name__ == "__main__":
    sys.exit(main())
