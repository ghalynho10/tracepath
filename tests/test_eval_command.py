"""`tracepath eval` on the real committed graph, against synthetic eval files (spec 0006).

The questions here are not eval questions: they cite spec 0012, which no eval chain
touches. The graph is the committed corpus, loaded through the `load` command from a
copy of its artifacts, by default or with `--with-held` as each test needs.
"""

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from neo4j import Driver
from typer.testing import CliRunner

from tracepath.artifacts import RUNS_DIR
from tracepath.cli import NO_HELD_ITEMS, app
from tracepath.config import Neo4jSettings
from tracepath.graph import connect
from tracepath.report import HELD_LABEL, HELD_MEANING, HELD_OUT_LABEL, UNCHECKED_LINE

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SPEC_0012 = "docs/specs/0012-model-client-router/index.md"
FILE_0012 = "specs/0012-model-client-router/index.md"
FILE_0001 = "specs/0001-stack-and-architecture/index.md"


def step(record: str, line: int, file: str = SPEC_0012) -> dict[str, Any]:
    return {"record": record, "file": file, "line": line}


PASSING = {
    "question": "Why does the router span open first?",
    "trace": [step("spec 0012 AC-7", 26), step("spec 0012 build step registering the span", 88)],
}
FAILING = {
    "question": "Why is the router charged per call?",
    "trace": [step("spec 0012 AC-7", 26), step("spec 0012 AC-3", 22)],
}
NO_START = {
    "question": "A question with nothing to start from",
    "checked": [{"where": f"{SPEC_0012} line 26", "found": "x"}],
}
LINE_START = {
    "question": "Why does a consequence start the walk?",
    "trace": [step("spec 0012 Consequences", 99), step("spec 0012 AC-2", 21)],
}
ABSENCE = {
    "question": "Is AC-7 tied to the follow up?",
    "checked": [{"where": f"{SPEC_0012} line 26 (AC-7)", "found": "x"}],
}
MISSING_FILE = {
    "question": "A question citing a file the snapshot lacks",
    "trace": [step("spec 9999 a paragraph", 5, "docs/specs/9999-missing/index.md")],
}
BEFORE_FIRST_UNIT = {
    "question": "A question citing line 0",
    "trace": [step("spec 0012 AC-7", 26), step("spec 0012 nothing", 0)],
}

QUESTIONS = {"entries": [PASSING, FAILING, NO_START, LINE_START, ABSENCE]}
SCORABLE = {"entries": [PASSING, FAILING]}
BROKEN = {"entries": [MISSING_FILE, BEFORE_FIRST_UNIT, PASSING]}
HELD_OUT = {"held_out": True, "entries": [PASSING, FAILING]}

ENTRY = {
    "examples_sha256": "not the digest",
    "questions": {
        "1": {"evidence": "none", "reason": "a synthetic question"},
        "5": {
            "evidence": "light",
            "reason": "a synthetic absence",
            "absence": [
                {"label": "spec 0012 AC-1", "file": FILE_0012, "line": 20},
                {"label": "spec 0012 follow up", "file": FILE_0012, "line": 113},
            ],
        },
    },
}
SIDECAR = {name: ENTRY for name in ("questions.json", "scorable.json")}

runner = CliRunner()


def write_root(root: Path) -> Path:
    shutil.copytree(ROOT / RUNS_DIR, root / RUNS_DIR)
    (root / "eval").mkdir()
    for name, payload in (
        ("questions.json", QUESTIONS),
        ("scorable.json", SCORABLE),
        ("broken.json", BROKEN),
        ("synthetic-held-out.json", HELD_OUT),
        ("runner.json", SIDECAR),
    ):
        (root / "eval" / name).write_text(json.dumps(payload))
    return root


@pytest.fixture(scope="module")
def corpus_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_root(tmp_path_factory.mktemp("corpus"))


def load(root: Path, *flags: str) -> None:
    result = runner.invoke(app, ["load", "--root", str(root), "--snapshot", str(SNAPSHOT), *flags])
    assert result.exit_code == 0, result.stderr


def _count(driver: Driver, database: str, query: str) -> int:
    found, _, _ = driver.execute_query(query, database_=database)
    return int(found[0]["n"])


def _state(settings: Neo4jSettings) -> tuple[bool, bool]:
    """Whether the graph holds the corpus, and whether it holds any held item."""
    with connect(settings) as driver:
        corpus = _count(
            driver,
            settings.database,
            "MATCH (e:Entity {canonical_id: '0012/AC-7'}) RETURN count(e) AS n",
        )
        held = _count(driver, settings.database, "MATCH (n {held: true}) RETURN count(n) AS n")
    return bool(corpus), bool(held)


@pytest.fixture
def default_graph(corpus_root: Path, neo4j_settings: Neo4jSettings) -> Iterator[Path]:
    """The committed corpus loaded by default: no held item in the graph."""
    if _state(neo4j_settings) != (True, False):
        load(corpus_root)
    yield corpus_root


@pytest.fixture
def held_graph(corpus_root: Path, neo4j_settings: Neo4jSettings) -> Iterator[Path]:
    """The committed corpus loaded with `--with-held`."""
    if _state(neo4j_settings) != (True, True):
        load(corpus_root, "--with-held")
    yield corpus_root


def run(root: Path, *args: str, eval_file: str = "eval/questions.json") -> tuple[int, str, str]:
    result = runner.invoke(
        app,
        [*args, "--eval-file", eval_file, "--root", str(root), "--snapshot", str(SNAPSHOT)],
    )
    return result.exit_code, result.stdout, result.stderr


def blocks(stdout: str) -> list[list[str]]:
    """The output cut at each `Question N: TEXT` line, with what came before it first."""
    found: list[list[str]] = [[]]
    for line in stdout.splitlines():
        if re.match(r"^Question \d+: ", line) and not re.match(
            r"^Question \d+: (PASS|FAIL|INCONCLUSIVE) ·", line
        ):
            found.append([])
        found[-1].append(line)
    return found


# AC-1, AC-2, AC-2b: one block per question, opening with the trace report.


def test_ac_1_one_block_per_question_in_the_files_order(default_graph: Path) -> None:
    """covers: AC-1, AC-8d (an UNUSABLE line stands in its question's place)."""
    _, stdout, _ = run(default_graph, "eval")

    heads = [line for line in stdout.splitlines() if re.match(r"^Question \d+: ", line)]
    numbers = [int(re.match(r"^Question (\d+)", h).group(1)) for h in heads]  # type: ignore[union-attr]
    assert sorted(set(numbers)) == [1, 2, 3, 4, 5]
    assert numbers == sorted(numbers)
    assert "Question 3: UNUSABLE, question 3 has no trace list" in stdout


def test_ac_2_a_block_opens_with_exactly_what_trace_eval_prints(default_graph: Path) -> None:
    """covers: AC-2 (from `Question N:` to the `Across records` line)."""
    _, stdout, _ = run(default_graph, "eval")
    code, traced, stderr = run(default_graph, "trace", "--eval", "1")

    assert code == 0, stderr
    first = traced.splitlines()
    report = first[first.index(f"Question 1: {PASSING['question']}") :]
    assert blocks(stdout)[1][: len(report)] == report
    assert report[-1].startswith("Across records:")


def test_ac_2b_a_block_ends_with_a_blank_line_its_result_and_its_evidence(
    default_graph: Path,
) -> None:
    """covers: AC-2b, AC-5, AC-6, AC-18."""
    _, stdout, _ = run(default_graph, "eval")
    first = blocks(stdout)[1]

    across = next(i for i, line in enumerate(first) if line.startswith("Across records:"))
    assert first[across + 1 :] == [
        "",
        "Question 1: PASS · 1 of 1 expected items reached besides the start.",
        "Evidence: no overlap with a worked example · a synthetic question",
        "",
    ]


def test_ac_6c_a_question_with_an_item_not_reached_fails(default_graph: Path) -> None:
    """covers: AC-6c, AC-5, AC-18 (not assessed)."""
    _, stdout, _ = run(default_graph, "eval")
    second = blocks(stdout)[2]

    assert f"  not reached  spec 0012 AC-3 · {FILE_0012}:22 · held_for_review" in second
    assert second[-3:] == [
        "Question 2: FAIL · 0 of 1 expected items reached besides the start.",
        "Evidence: not assessed",
        "",
    ]


def test_ac_12b_a_first_entry_not_in_ac_form_starts_at_the_lowest_id_on_its_line(
    default_graph: Path,
) -> None:
    """covers: AC-12, AC-12b, AC-10, AC-10c."""
    _, stdout, _ = run(default_graph, "eval")
    fourth = blocks(stdout)[4]

    assert fourth[1] == (
        'Start item: 0012#consequences:3, from the first trace entry "spec 0012 Consequences", '
        f"the entity at {FILE_0012}:99, the lowest id of the 2 entities on that line."
    )
    assert (
        f"  reached      spec 0012 Consequences · {FILE_0012}:99 · hop 0 · the start · "
        "0012#consequences:3"
    ) in fourth


def test_ac_17b_an_absence_item_the_walk_reaches_fails_naming_its_hop(
    default_graph: Path,
) -> None:
    """covers: AC-16, AC-17b, AC-14 on the real graph."""
    _, stdout, _ = run(default_graph, "eval")
    fifth = blocks(stdout)[5]

    assert fifth[1] == (
        f'Start item: 0012/AC-7, from the first checked entry "{SPEC_0012} line 26 (AC-7)".'
    )
    assert "Items that should not be reached:" in fifth
    assert fifth[-2:] == [
        "Question 5: FAIL · spec 0012 AC-1 was reached at hop 2, "
        "a connection the record does not document.",
        "Evidence: light · a synthetic absence",
    ]


def test_ac_7_no_line_counts_questions_or_gives_a_rate(default_graph: Path) -> None:
    """covers: AC-7, AC-9c (no chain)."""
    _, stdout, _ = run(default_graph, "eval")

    assert "%" not in stdout
    assert not re.search(r"\b(total|rate|passed)\b", stdout, re.IGNORECASE)
    assert not re.search(r"\d+ of \d+ questions", stdout)
    assert "Chain from" not in stdout


# AC-8 to AC-8d: exit codes.


def test_ac_8_every_question_reaching_a_result_exits_0_fail_included(default_graph: Path) -> None:
    """covers: AC-8."""
    code, stdout, stderr = run(default_graph, "eval", eval_file="eval/scorable.json")

    assert code == 0, stderr
    assert "Question 2: FAIL" in stdout


def test_ac_8b_an_unusable_question_lets_the_rest_run_then_exits_1(default_graph: Path) -> None:
    """covers: AC-8b, AC-8d (on stdout)."""
    code, stdout, stderr = run(default_graph, "eval")

    assert code == 1
    assert stdout.index("Question 3: UNUSABLE, ") < stdout.index("Question 5: FAIL")
    assert "Question 3: UNUSABLE" not in stderr
    assert "Traceback" not in stdout + stderr


def test_ac_8d_an_unreadable_file_and_a_line_before_the_first_unit_are_unusable(
    default_graph: Path,
) -> None:
    """covers: AC-8d (each makes only its own question unusable)."""
    code, stdout, _ = run(default_graph, "eval", eval_file="eval/broken.json")

    assert code == 1
    assert "Question 1: UNUSABLE, a cited file cannot be read" in stdout
    assert "Question 2: UNUSABLE, spec 0012 nothing cites " in stdout
    assert "before the first unit of its file" in stdout
    assert "Question 3: PASS" in stdout


@pytest.fixture
def undecodable(default_graph: Path, tmp_path: Path) -> Path:
    """A snapshot copy holding one cited file that is not UTF-8, and a question citing it."""
    snapshot = tmp_path / "docs"
    shutil.copytree(SNAPSHOT, snapshot)
    (snapshot / "specs" / "9998-undecodable").mkdir()
    (snapshot / "specs" / "9998-undecodable" / "index.md").write_bytes(b"# 9998. \xff\xfe\n")
    question = {
        "question": "A question citing a file that is not UTF-8",
        "trace": [step("spec 9998 a paragraph", 1, "docs/specs/9998-undecodable/index.md")],
    }
    (default_graph / "eval" / "undecodable.json").write_text(
        json.dumps({"entries": [question, PASSING]})
    )
    return snapshot


def run_undecodable(root: Path, snapshot: Path, *args: str) -> tuple[int, str, str]:
    result = runner.invoke(
        app,
        [
            *args,
            *("--eval-file", "eval/undecodable.json"),
            *("--root", str(root), "--snapshot", str(snapshot)),
        ],
    )
    return result.exit_code, result.stdout, result.stderr


def test_ac_8d_a_cited_file_that_is_not_utf_8_makes_only_its_question_unusable(
    default_graph: Path, undecodable: Path
) -> None:
    """covers: AC-8d (a file that cannot be decoded cannot be read either)."""
    code, stdout, stderr = run_undecodable(default_graph, undecodable, "eval")

    assert code == 1
    assert "Question 1: UNUSABLE, a cited file cannot be read" in stdout
    assert "Question 2: PASS" in stdout
    assert "Traceback" not in stdout + stderr


def test_trace_eval_on_a_cited_file_that_is_not_utf_8_exits_1_with_no_traceback(
    default_graph: Path, undecodable: Path
) -> None:
    """covers: AC-8c (`trace --eval` turns the same failure into a message)."""
    code, stdout, stderr = run_undecodable(default_graph, undecodable, "trace", "--eval", "1")

    assert code == 1
    assert stderr.strip()
    assert stdout == ""
    assert "Traceback" not in stdout + stderr


@pytest.mark.parametrize(
    "command", [["eval"], ["trace", "--eval", "1"]], ids=["eval", "trace --eval"]
)
def test_ac_8c_a_root_with_no_run_files_exits_1_before_any_question(
    default_graph: Path, tmp_path: Path, command: list[str]
) -> None:
    """covers: AC-8c (`RebuildFailed`, raised after the graph is read)."""
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / "questions.json").write_text(json.dumps(SCORABLE))

    code, stdout, stderr = run(tmp_path, *command)

    assert code == 1
    assert "no run artifacts found" in " ".join(stderr.split())
    assert stdout == ""
    assert "Traceback" not in stdout + stderr


# AC-4, AC-14, AC-16: `trace --eval` takes the same start rules and absence items.


def test_ac_4_trace_eval_scores_an_absence_question_from_the_sidecar(default_graph: Path) -> None:
    """covers: AC-4, AC-14, AC-16 (the sidecar's absence items reach `trace --eval` too)."""
    code, stdout, stderr = run(default_graph, "trace", "--eval", "5")
    lines = stdout.splitlines()

    assert code == 0, stderr
    where = f"{SPEC_0012} line 26 (AC-7)"
    assert f'Start item: 0012/AC-7, from the first checked entry "{where}".' in lines
    assert "Items that should not be reached:" in lines
    assert f"  reached      spec 0012 AC-1 · {FILE_0012}:20 · hop 2 · 0012/AC-1" in lines


# AC-9 to AC-9c: the held item view.


def test_ac_9_with_held_on_a_graph_with_no_held_item_exits_1_before_any_question(
    default_graph: Path,
) -> None:
    """covers: AC-9 (the message `trace --with-held` gives)."""
    code, stdout, stderr = run(default_graph, "eval", "--with-held")

    assert code == 1
    assert " ".join(NO_HELD_ITEMS.split()) in " ".join(stderr.split())
    assert stdout == ""


def test_ac_9b_the_held_label_prints_once_above_the_first_block(held_graph: Path) -> None:
    """covers: AC-9b, AC-9c."""
    code, stdout, stderr = run(held_graph, "eval", "--with-held", eval_file="eval/scorable.json")

    assert code == 0, stderr
    lines = stdout.splitlines()
    assert lines[:2] == [HELD_LABEL, ""]
    assert lines.count(HELD_LABEL) == 1
    assert lines.count(HELD_MEANING) == 2
    assert "Chain from" not in stdout


def test_ac_9b_a_held_block_is_the_held_trace_report_without_its_label(held_graph: Path) -> None:
    """covers: AC-9b (spec 0005's report lines unchanged but for the label)."""
    _, stdout, _ = run(held_graph, "eval", "--with-held", eval_file="eval/scorable.json")
    _, traced, _ = run(
        held_graph, "trace", "--eval", "1", "--with-held", eval_file="eval/scorable.json"
    )

    report = traced.splitlines()
    report = report[report.index(HELD_LABEL) + 1 :]
    lines = stdout.splitlines()
    assert lines[2 : 2 + len(report)] == report


# AC-29 and AC-9c: the held out label, and the order above the first block.


def test_ac_29_a_released_held_out_file_opens_with_its_label(default_graph: Path) -> None:
    """covers: AC-29 (each question on its own, no total)."""
    code, stdout, stderr = run(
        default_graph,
        "eval",
        "--release-held-out",
        eval_file="eval/synthetic-held-out.json",
    )

    assert code == 0, stderr
    assert stdout.splitlines()[:2] == [HELD_OUT_LABEL, ""]
    assert "Question 1: PASS" in stdout and "Question 2: FAIL" in stdout


def test_ac_29_trace_eval_on_a_released_held_out_file_opens_with_its_label(
    default_graph: Path,
) -> None:
    """covers: AC-29 (`trace --eval` prints the label above its chain)."""
    code, stdout, stderr = run(
        default_graph,
        "trace",
        "--eval",
        "1",
        "--release-held-out",
        eval_file="eval/synthetic-held-out.json",
    )
    lines = stdout.splitlines()

    assert code == 0, stderr
    assert lines[0] == HELD_OUT_LABEL
    assert lines[1].startswith("Chain from 0012/AC-7:")


@pytest.fixture(scope="module")
def git_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A root that is a git work tree holding a copy of `examples/`."""
    root = write_root(tmp_path_factory.mktemp("git"))
    shutil.copytree(ROOT / "examples", root / "examples")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "examples"], check=True)
    return root


def test_ac_21_a_changed_examples_digest_prints_the_unchecked_line_once(
    git_root: Path, default_graph: Path
) -> None:
    """covers: AC-21 (the levels still print)."""
    code, stdout, _ = run(git_root, "eval", eval_file="eval/scorable.json")

    assert code == 0
    assert stdout.splitlines()[:2] == [UNCHECKED_LINE, ""]
    assert stdout.count(UNCHECKED_LINE) == 1
    assert "Evidence: no overlap with a worked example · a synthetic question" in stdout


def test_ac_21_a_matching_digest_prints_no_unchecked_line(
    git_root: Path, default_graph: Path
) -> None:
    """covers: AC-21 (only when the digests differ)."""
    sidecar = json.loads((git_root / "eval" / "runner.json").read_text())
    sidecar["scorable.json"]["examples_sha256"] = json.loads(
        (ROOT / "eval" / "runner.json").read_text()
    )["linked-records-research.json"]["examples_sha256"]
    (git_root / "eval" / "runner.json").write_text(json.dumps(sidecar))
    try:
        _, stdout, _ = run(git_root, "eval", eval_file="eval/scorable.json")
    finally:
        (git_root / "eval" / "runner.json").write_text(json.dumps(SIDECAR))

    assert UNCHECKED_LINE not in stdout


def test_ac_9c_lines_above_the_first_block_come_in_order(git_root: Path, held_graph: Path) -> None:
    """covers: AC-9c (held out label, unchecked line, held view label)."""
    sidecar = {"synthetic-held-out.json": ENTRY}
    (git_root / "eval" / "runner.json").write_text(json.dumps(sidecar))
    try:
        code, stdout, stderr = run(
            git_root,
            "eval",
            "--with-held",
            "--release-held-out",
            eval_file="eval/synthetic-held-out.json",
        )
    finally:
        (git_root / "eval" / "runner.json").write_text(json.dumps(SIDECAR))

    assert code == 0, stderr
    assert stdout.splitlines()[:4] == [HELD_OUT_LABEL, UNCHECKED_LINE, HELD_LABEL, ""]


def test_a_snapshot_document_that_cannot_be_decoded_gives_a_message_and_exit_1(
    tmp_path: Path, default_graph: Path
) -> None:
    """covers: the same failure message `trace --eval` gives (no traceback)."""
    snapshot = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, snapshot)
    (snapshot / FILE_0001).write_bytes(b"\xff\xfe not utf 8")

    result = runner.invoke(
        app,
        [
            "eval",
            "--eval-file",
            "eval/scorable.json",
            "--root",
            str(default_graph),
            "--snapshot",
            str(snapshot),
        ],
    )

    assert result.exit_code == 1
    assert result.stderr.strip()
    assert not isinstance(result.exception, UnicodeDecodeError)


def test_a_tracked_example_missing_from_the_work_tree_gives_a_message_and_exit_1(
    tmp_path: Path, default_graph: Path
) -> None:
    """covers: AC-20 (a tracked example that cannot be read stops the run cleanly)."""
    root = write_root(tmp_path)
    (root / "examples").mkdir()
    (root / "examples" / "gone.md").write_text("x")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "examples"], check=True)
    (root / "examples" / "gone.md").unlink()

    code, _, stderr = run(root, "eval", eval_file="eval/scorable.json")

    assert code == 1
    assert "cannot read a tracked example" in stderr
    assert "Traceback" not in stderr
