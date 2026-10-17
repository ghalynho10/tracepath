"""Join experiment 0013's rulings to its arm file and write the result, no API call.

Reads the committed `data/held-packet.md` and `data/held-arms.json` and refuses, with a
message naming what is wrong, unless:

- the committed arm file hashes to the value committed in `data/held-arms.sha256`;
- the commit adding the arm file comes after the last commit touching the packet, so
  the rulings were in before any group was known;
- every packet item carries exactly one readable mark: `agree`, `disagree` or `unsure`.

Each item's mark, note and "should have been" are read from the packet and joined to
the arm file's group, per run counts, wording run and model. Writes
`data/held-result.json` and prints the README's result tables. Counts marks per group
and nothing more: there is no pass or fail, and the notes are not sorted here.

Run from the repository root: uv run python <this file>
"""

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = HERE / "data" / "held-packet.md"
ARMS = HERE / "data" / "held-arms.json"
HASH = HERE / "data" / "held-arms.sha256"
RESULT = HERE / "data" / "held-result.json"

GROUPS = ("a", "b", "c", "d", "e")
MARKS = ("agree", "disagree", "unsure")

_HEAD = re.compile(
    r"^- \[(?P<box>.)\] (?P<mark>.*?) · `(?P<id>H\d+)` · (?P<kind>\w+) · (?P<type>\S+)$"
)
_NOTE = "  - note:"
_SHOULD = "  - should have been:"


class Refused(SystemExit):
    """The rulings cannot be scored as they stand; the message says why."""


@dataclass(frozen=True)
class Ruling:
    """One ruled item as the packet holds it."""

    opaque_id: str
    kind: str
    type: str
    mark: str
    note: str
    should_have_been: str


def parse_rulings(text: str) -> dict[str, Ruling]:
    """Every item of a ruled packet, keyed by opaque id.

    Raises:
        Refused: an item is unticked, carries no one readable mark, or appears twice.
    """
    found: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        head = _HEAD.match(line)
        if head is not None:
            opaque_id = head["id"]
            if head["box"] != "x":
                raise Refused(f"{opaque_id} is not ticked")
            if head["mark"] not in MARKS:
                raise Refused(f"{opaque_id} carries no one readable mark: {head['mark']!r}")
            if opaque_id in found:
                raise Refused(f"{opaque_id} appears twice")
            current = {
                "opaque_id": opaque_id,
                "kind": head["kind"],
                "type": head["type"],
                "mark": head["mark"],
                "note": "",
                "should_have_been": "",
            }
            found[opaque_id] = current
        elif line.startswith("- [") and "`H" in line:
            raise Refused(f"cannot read the item line {line!r}")
        elif current is not None and line.startswith(_NOTE):
            current["note"] = line.removeprefix(_NOTE).strip()
        elif current is not None and line.startswith(_SHOULD):
            current["should_have_been"] = line.removeprefix(_SHOULD).strip()
    return {i: Ruling(**fields) for i, fields in found.items()}


def check_hash(arms: bytes, hash_line: str) -> None:
    """Refuse an arm file whose hash differs from the one committed before the rulings."""
    if hashlib.sha256(arms).hexdigest() != hash_line.split()[0]:
        raise Refused(f"{ARMS.name} does not match the hash committed before the rulings")


def check_order(ruled: str, added: str, is_ancestor: bool) -> None:
    """Refuse unless the arm file was added in a commit after the packet's last change."""
    if not added:
        raise Refused(f"{ARMS.name} is not committed")
    if ruled == added or not is_ancestor:
        raise Refused(
            f"{ARMS.name} was committed in {added[:7]}, not after the ruled packet's {ruled[:7]}"
        )


def score(rulings: Mapping[str, Ruling], key: Mapping[str, Any]) -> dict[str, Any]:
    """Each item's ruling joined to its arm file entry, and the marks counted per group.

    Raises:
        Refused: the packet and the arm file do not name the same items.
    """
    arms = {i["opaque_id"]: i for i in key["items"]}
    if set(arms) != set(rulings):
        raise Refused(
            f"the packet and {ARMS.name} name different items: {sorted(set(arms) ^ set(rulings))}"
        )
    items = [
        {
            "opaque_id": i,
            "group": arms[i]["group"],
            "kind": rulings[i].kind,
            "type": rulings[i].type,
            "model": arms[i]["model"],
            "mark": rulings[i].mark,
            "note": rulings[i].note,
            "should_have_been": rulings[i].should_have_been,
            "counts": arms[i]["counts"],
            "wording_run": arms[i]["wording_run"],
            "record": arms[i]["record"],
            "section": arms[i]["section"],
            "signature": arms[i]["signature"],
        }
        for i in sorted(rulings)
    ]
    groups = {
        g: {
            "drawn": sum(1 for i in items if i["group"] == g),
            **{m: sum(1 for i in items if i["group"] == g and i["mark"] == m) for m in MARKS},
        }
        for g in GROUPS
    }
    return {"groups": groups, "items": items}


def _blank(text: str) -> str:
    return text if text else "_(blank)_"


def result_markdown(result: Mapping[str, Any]) -> str:
    """The README's result: marks per group, then every item's ruling as written."""
    lines = ["| Group | Drawn | Agree | Disagree | Unsure |", "|---|---|---|---|---|"]
    for g in GROUPS:
        n = result["groups"][g]
        lines.append(f"| {g} | {n['drawn']} | {n['agree']} | {n['disagree']} | {n['unsure']} |")
    for g in GROUPS:
        lines += ["", f"#### Group {g}", ""]
        for i in (i for i in result["items"] if i["group"] == g):
            lines += [
                f"- `{i['opaque_id']}` · {i['kind']} · {i['type']} · `{i['model']}` · {i['mark']}",
                f"  - note: {_blank(i['note'])}",
                f"  - should have been: {_blank(i['should_have_been'])}",
            ]
    return "\n".join(lines)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def _committed(path: Path) -> bytes:
    """A file as HEAD holds it, not as the working tree does."""
    return subprocess.run(
        ["git", "show", f"HEAD:{path.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _order() -> tuple[str, str, bool]:
    """The packet's last commit, the commit adding the arm file, and whether one precedes."""
    ruled = _git("log", "-1", "--format=%H", "--", str(PACKET.relative_to(ROOT))).strip()
    adds = _git("log", "--diff-filter=A", "--format=%H", "--", str(ARMS.relative_to(ROOT)))
    added = adds.split()[-1] if adds.split() else ""
    if not added:
        return ruled, added, False
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ruled, added], cwd=ROOT, check=False
    )
    return ruled, added, ancestor.returncode == 0


def run() -> None:
    """Check the arm file and the commit order, score the rulings and write the result."""
    try:
        arms = _committed(ARMS)
        hash_line = _committed(HASH).decode()
        packet = _committed(PACKET).decode()
    except subprocess.CalledProcessError as exc:
        raise Refused(f"a file is not committed: {exc.stderr.decode().strip()}") from None
    check_hash(arms, hash_line)
    check_order(*_order())
    result = score(parse_rulings(packet), json.loads(arms))
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(result_markdown(result))


if __name__ == "__main__":
    run()
