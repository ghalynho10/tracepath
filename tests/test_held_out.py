"""The held out questions and their guard (spec 0006 AC-24 to AC-28b).

The three file checks run on synthetic held out files, one that keeps every rule and
one that breaks each, so each check is shown to catch what it guards. They also run on
`eval/held-out.json` once build step 10 has written it; until then those tests skip.
The refusals stop before any graph is read, so no Neo4j is needed: the graph address
here is one nothing listens on, and a read would fail with a different message.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.conftest import UNREACHABLE_URI
from tracepath.cli import app

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "corpus" / "jobhunt"
EXAMPLES = ROOT / "examples"
HELD_OUT = ROOT / "eval" / "held-out.json"

#: The brief's exclusion list (spec 0006, The held out brief).
EXCLUDED = frozenset(
    {
        "0001",
        "0002",
        "0003",
        "0006",
        "0007",
        "0008",
        "0009",
        "0011",
        "0012",
        "0013",
        "0014",
        "0015",
        "0019",
        "0021",
        "scope",
    }
)

#: The record an example draws from, read from its first heading (AC-25).
EXAMPLE_HEADING = re.compile(r"^# Worked example: (?:`?(feature-\d+|\d{4}))")

runner = CliRunner()

Citation = tuple[str, int, str]


def flat(text: str) -> str:
    return " ".join(text.split())


def citations(held_out: dict[str, Any]) -> list[Citation]:
    """Every `(file, line, quote)` the entries cite, `also` passages included."""
    found: list[Citation] = []
    for entry in held_out["entries"]:
        for step in entry.get("trace", []):
            found.append((step["file"], step["line"], step["quote"]))
            also = step.get("also")
            for extra in [also] if isinstance(also, dict) else also or []:
                found.append((step["file"], extra["line"], extra["quote"]))
    return found


def record_of(file: str) -> str:
    """The record a cited file belongs to: a spec's number, or `scope`."""
    match = re.match(r"docs/specs/(\d{4})-", file)
    if match is not None:
        return match.group(1)
    return "scope" if file == "docs/scope/scope.md" else file


def excluded_citations(held_out: dict[str, Any]) -> list[Citation]:
    """AC-24: citations of a record on the brief's exclusion list."""
    return [c for c in citations(held_out) if record_of(c[0]) in EXCLUDED]


def example_records(examples: Path = EXAMPLES) -> frozenset[str]:
    """The records `examples/` draws from; a heading that does not match fails (AC-25)."""
    records: set[str] = set()
    for path in sorted(examples.glob("*.md")):
        first = path.read_text().splitlines()[0]
        match = EXAMPLE_HEADING.match(first)
        assert match is not None, f"{path.name}: its first heading names no record: {first!r}"
        records.add("scope" if match.group(1).startswith("feature-") else match.group(1))
    return frozenset(records)


def example_citations(held_out: dict[str, Any]) -> list[Citation]:
    """AC-25: citations of a record a worked example draws from."""
    drawn = example_records()
    return [c for c in citations(held_out) if record_of(c[0]) in drawn]


def normalize(text: str) -> str:
    """As `tests/test_corpus.py`: links shortened to `[0014]`, whitespace joined."""
    return re.sub(r"\s+", " ", re.sub(r"\]\([^)]*\)", "]", text)).strip()


def misplaced_quotes(held_out: dict[str, Any]) -> list[Citation]:
    """AC-26: a quote not at its cited file and line exactly, or a file not allowed."""
    wrong: list[Citation] = []
    for file, line, quote in citations(held_out):
        path = SNAPSHOT_DIR / file
        allowed = file.endswith("/index.md") or file == "docs/scope/scope.md"
        if not allowed or not path.is_file():
            wrong.append((file, line, quote))
            continue
        lines = path.read_text().splitlines()
        pieces = [normalize(p) for p in quote.split("[...]") if normalize(p)]
        whole = normalize("\n".join(lines))
        head = normalize(lines[line - 1]) if 1 <= line <= len(lines) else ""
        rest = normalize(" ".join(lines[line - 1 :])) if head else ""
        at = rest.find(pieces[0]) if pieces else -1
        if not (pieces and head and 0 <= at < len(head) and all(p in whole for p in pieces)):
            wrong.append((file, line, quote))
    return wrong


def cite(file: str, line: int) -> dict[str, Any]:
    """A trace step quoting the corpus line as it stands, list marker dropped."""
    text = (SNAPSHOT_DIR / file).read_text().splitlines()[line - 1]
    return {"record": record_of(file), "file": file, "line": line, "quote": text.lstrip("- ")}


SPEC_0004 = "docs/specs/0004-test-foundation/index.md"
SPEC_0010 = "docs/specs/0010-profile-entry/index.md"
SPEC_0007 = "docs/specs/0007-auth-and-per-user-isolation/index.md"
SPEC_0012 = "docs/specs/0012-model-client-router/index.md"


def held_out_file(*traces: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "held_out": True,
        "entries": [
            {"shape": "synthetic", "question": f"Why {n}?", "trace": trace, "answer": "x"}
            for n, trace in enumerate(traces, 1)
        ],
    }


GOOD = held_out_file([cite(SPEC_0004, 19), cite(SPEC_0010, 27)], [cite(SPEC_0010, 28)])


def real_held_out() -> dict[str, Any]:
    if not HELD_OUT.is_file():
        pytest.skip("eval/held-out.json is written at spec 0006 build step 10")
    payload: dict[str, Any] = json.loads(HELD_OUT.read_text())
    return payload


# AC-24: no record on the exclusion list.


def test_ac_24_a_file_citing_only_records_left_to_the_brief_passes() -> None:
    """covers: AC-24 (the check passes a good file)."""
    assert excluded_citations(GOOD) == []


def test_ac_24_a_citation_of_an_excluded_record_is_caught() -> None:
    """covers: AC-24 (the check fails a bad file)."""
    bad = held_out_file([cite(SPEC_0004, 19), cite(SPEC_0007, 25)])

    assert [c[0] for c in excluded_citations(bad)] == [SPEC_0007]


def test_ac_24_the_held_out_file_cites_no_excluded_record() -> None:
    """covers: AC-24."""
    assert excluded_citations(real_held_out()) == []


# AC-25: no record a worked example draws from.


def test_ac_25_the_examples_draw_from_the_records_their_headings_name() -> None:
    """covers: AC-25 (`feature-N` stands for the scope document)."""
    assert example_records() == {"0006", "0008", "0012", "0019", "scope"}


def test_ac_25_an_example_heading_that_names_no_record_fails(tmp_path: Path) -> None:
    """covers: AC-25 (a heading that does not match fails the test)."""
    (tmp_path / "odd.md").write_text("# Worked example: a section of something\n")

    with pytest.raises(AssertionError, match="names no record"):
        example_records(tmp_path)


def test_ac_25_a_citation_of_a_record_an_example_draws_from_is_caught() -> None:
    """covers: AC-25 (the check fails a bad file, passes a good one)."""
    bad = held_out_file([cite(SPEC_0004, 19), cite(SPEC_0012, 20)])

    assert example_citations(GOOD) == []
    assert [c[0] for c in example_citations(bad)] == [SPEC_0012]


def test_ac_25_the_held_out_file_cites_no_record_an_example_draws_from() -> None:
    """covers: AC-25."""
    assert example_citations(real_held_out()) == []


# AC-26: every quote at exactly its cited line, in an index.md or scope.md.


def test_ac_26_quotes_at_their_exact_lines_pass() -> None:
    """covers: AC-26 (the check passes a good file)."""
    assert misplaced_quotes(GOOD) == []


def test_ac_26_a_quote_one_line_off_is_caught() -> None:
    """covers: AC-26 (exactly that line, not within one line of it)."""
    off = cite(SPEC_0004, 19) | {"line": 20}

    assert misplaced_quotes(held_out_file([off])) == [(SPEC_0004, 20, off["quote"])]


def test_ac_26_a_quote_in_a_file_other_than_index_or_scope_is_caught() -> None:
    """covers: AC-26 (citations point at index.md and scope.md only)."""
    rationale = cite(SPEC_0004, 19) | {"file": "docs/specs/0004-test-foundation/rationale.md"}

    assert len(misplaced_quotes(held_out_file([rationale]))) == 1


def test_ac_26_every_quote_of_the_held_out_file_is_at_its_exact_line() -> None:
    """covers: AC-26."""
    assert misplaced_quotes(real_held_out()) == []


# AC-27, AC-28, AC-28b: the guard.


def test_ac_27_no_source_file_names_the_held_out_file() -> None:
    """covers: AC-27 (the flag `--release-held-out` itself is allowed)."""
    sources = sorted((ROOT / "src").rglob("*"))

    naming = [p for p in sources if p.is_file() and b"held-out.json" in p.read_bytes()]

    assert naming == []


def test_ac_28b_the_held_out_file_marks_itself_held_out() -> None:
    """covers: AC-28b."""
    assert real_held_out().get("held_out") is True


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / "synthetic-held-out.json").write_text(json.dumps(GOOD))
    plain = {k: v for k, v in GOOD.items() if k != "held_out"}
    (tmp_path / "eval" / "plain.json").write_text(json.dumps(plain))
    return tmp_path


def invoke(root: Path, *args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, [*args, "--root", str(root)], env={"NEO4J_URI": UNREACHABLE_URI})
    return result.exit_code, result.stdout, result.stderr


@pytest.mark.parametrize(
    "command", [["eval"], ["trace", "--eval", "1"]], ids=["eval", "trace --eval"]
)
def test_ac_28_a_held_out_file_without_the_flag_is_refused_naming_it(
    root: Path, command: list[str]
) -> None:
    """covers: AC-28 (exit 1, names the flag, reads no graph, prints no question)."""
    code, stdout, stderr = invoke(root, *command, "--eval-file", "eval/synthetic-held-out.json")

    assert code == 1
    assert "--release-held-out" in flat(stderr)
    assert "held out" in flat(stderr)
    assert "Neo4j" not in stderr
    assert stdout == ""


@pytest.mark.parametrize(
    "command", [["eval"], ["trace", "--eval", "1"]], ids=["eval", "trace --eval"]
)
def test_ac_28_the_flag_on_a_file_that_is_not_held_out_is_refused(
    root: Path, command: list[str]
) -> None:
    """covers: AC-28 (`--release-held-out` on a file that is not held out exits 1)."""
    code, stdout, stderr = invoke(
        root, *command, "--eval-file", "eval/plain.json", "--release-held-out"
    )

    assert code == 1
    assert "is not a held out file" in flat(stderr)
    assert stdout == ""


def test_ac_28_the_flag_lets_the_held_out_file_through_to_the_graph(root: Path) -> None:
    """covers: AC-28 (released, the run goes on, here to the unreachable graph)."""
    code, _, stderr = invoke(
        root, "eval", "--eval-file", "eval/synthetic-held-out.json", "--release-held-out"
    )

    assert code == 1
    assert "held out" not in flat(stderr)
    assert "--release-held-out" not in flat(stderr)
