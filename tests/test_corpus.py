"""The eval set's expected chains cite records that exist in the pinned corpus snapshot."""

import json
import re
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / "corpus" / "jobhunt"
EVAL_FILE = REPO_ROOT / "eval" / "linked-records-research.json"


class Passage(TypedDict):
    line: int
    quote: str


class Link(TypedDict):
    record: str
    file: str
    line: int
    quote: str
    also: NotRequired[Passage]


class Checked(TypedDict):
    where: str
    found: str


class Entry(TypedDict):
    shape: str
    question: str
    trace: NotRequired[list[Link]]
    checked: NotRequired[list[Checked]]


class EvalSet(TypedDict):
    commit: str
    entries: list[Entry]


class Citation(TypedDict):
    record: str
    file: str
    line: int
    quote: str


def load_eval() -> EvalSet:
    return cast(EvalSet, json.loads(EVAL_FILE.read_text()))


def citations(eval_set: EvalSet) -> tuple[Citation, ...]:
    found: list[Citation] = []
    for entry in eval_set["entries"]:
        for link in entry.get("trace", []):
            found.append(
                Citation(
                    record=link["record"], file=link["file"], line=link["line"], quote=link["quote"]
                )
            )
            if "also" in link:
                found.append(
                    Citation(
                        record=link["record"],
                        file=link["file"],
                        line=link["also"]["line"],
                        quote=link["also"]["quote"],
                    )
                )
    return tuple(found)


def normalize(text: str) -> str:
    """The eval quotes shorten `[0014](../path)` links to `[0014]` and join wrapped lines."""
    return re.sub(r"\s+", " ", re.sub(r"\]\([^)]*\)", "]", text)).strip()


def test_eval_set_has_five_questions() -> None:
    assert len(load_eval()["entries"]) == 5


def test_snapshot_records_the_commit_the_eval_set_was_read_at() -> None:
    record = (SNAPSHOT_DIR / "SNAPSHOT.md").read_text()
    match = re.search(r"\*\*Commit\*\*: `([0-9a-f]{40})`", record)

    assert match is not None
    assert match.group(1).startswith(load_eval()["commit"])


@pytest.mark.parametrize("citation", citations(load_eval()), ids=lambda c: c["record"])
def test_cited_passage_exists_in_the_snapshot_at_its_line(citation: Citation) -> None:
    path = SNAPSHOT_DIR / citation["file"]
    assert path.is_file()

    lines = path.read_text().splitlines()
    whole = normalize("\n".join(lines))
    pieces = [normalize(p) for p in citation["quote"].split("[...]") if normalize(p)]
    for piece in pieces:
        assert piece in whole

    # The cited line may be the blank line just above a paragraph, so allow one line either side.
    near = normalize(" ".join(lines[citation["line"] - 2 : citation["line"] + 1]))
    assert pieces[0][:30] in near


def test_docs_checked_for_the_no_connection_question_exist_in_the_snapshot() -> None:
    checked = [c for e in load_eval()["entries"] for c in e.get("checked", [])]
    docs_paths = [m.group(1) for c in checked if (m := re.match(r"(docs/\S+)", c["where"]))]

    assert docs_paths
    for docs_path in docs_paths:
        assert (SNAPSHOT_DIR / docs_path).is_file(), docs_path
