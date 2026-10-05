"""Build the re check's blind self agreement pair, no API call (spec 0003, AC-30).

10 items drawn at random, seed recorded, from the engineer's own already ruled marks
in experiment 0005's `ruling-sheet.md` (42 ruled items across groups A, B and C).
Writes two files: `blind-reread.md` carries each item's own text only, no mark, no
reason, ready to re-rule cold; `blind-reread-answers.md` carries the same 10 items'
original mark and reason, meant to be opened only after the blind re-ruling is done,
so the answer can't leak into it. Neither file states pass or fail; AC-30 reports the
agreement, it does not gate on it.

Run from the repository root: uv run python <this file>
"""

import random
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "0005-held-out-prompt-examples"
    / "data"
    / "ruling-sheet.md"
)
HERE = Path(__file__).resolve().parent
BLIND = HERE / "data" / "blind-reread.md"
ANSWERS = HERE / "data" / "blind-reread-answers.md"

SAMPLE = 10
SEED = 20260928002

#: Ruled items only; the placeholder text an unruled line still carries.
UNRULED_MARKS = {"agree / disagree", "real link lost / rightly dropped"}

#: Vocabulary an item's mark belongs to, so a blank checkbox offers the right words.
LOST_LINK_MARKS = {"real link lost", "rightly dropped"}
ENTITY_LINK_MARKS = {"agree", "disagree", "unsure"}

ITEM_HEAD = re.compile(r"^- \[([ x])\] (.+)$")


@dataclass(frozen=True)
class RuledItem:
    """One already ruled line from experiment 0005's ruling sheet, with its block."""

    group_heading: str
    section_heading: str
    mark: str
    head_rest: str
    sub_lines: tuple[str, ...]


def parse(text: str) -> list[RuledItem]:
    """Every ruled item block: its own `- [x] mark · ...` line and its sub-lines."""
    lines = text.splitlines()
    group = section = ""
    items: list[RuledItem] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## Group"):
            group = line.removeprefix("## ").strip()
        elif line.startswith("### "):
            section = line.removeprefix("### ").strip()
        match = ITEM_HEAD.match(line)
        if match and match.group(1) == "x":
            rest = match.group(2)
            mark, _, remainder = rest.partition(" · ")
            if mark not in UNRULED_MARKS:
                # A block runs to the next top level item or heading, blank lines
                # included: `report.py`'s own link blocks carry one between the
                # `reason:` line and `source:`, which a `.startswith("  ")` check
                # alone would stop at, silently dropping source, target and phrase.
                sub_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith(("- [", "#")):
                    sub_lines.append(lines[j])
                    j += 1
                while sub_lines and sub_lines[-1].strip() == "":
                    sub_lines.pop()
                items.append(RuledItem(group, section, mark, remainder, tuple(sub_lines)))
                i = j
                continue
        i += 1
    return items


def blank_mark(mark: str) -> str:
    """The unruled placeholder an item's own mark vocabulary uses."""
    return "real link lost / rightly dropped" if mark in LOST_LINK_MARKS else "agree / disagree"


def blind_lines(item: RuledItem) -> list[str]:
    """The item's own descriptive text, no mark, no `reason:` line."""
    lines = [f"- [ ] {blank_mark(item.mark)} · {item.head_rest}"]
    for sub in item.sub_lines:
        if sub.strip().startswith("- reason:"):
            continue
        lines.append(sub)
    return lines


def answer_lines(item: RuledItem) -> list[str]:
    """The item's original mark and reason, nothing else (the answer alone)."""
    lines = [f"- [x] {item.mark}"]
    for sub in item.sub_lines:
        if sub.strip().startswith("- reason:"):
            lines.append(sub)
    return lines


def build() -> None:
    """Draw 10 ruled items at random and write the blind sheet and its answer key."""
    # The same guard report.py and prepare_ruling.py carry (added 2026-10-04, after
    # the branch review): a blind sheet the engineer has re-marked is evidence, and a
    # rerun must never write over it.
    if BLIND.exists() and any(
        line.startswith("- [") and not any(mark in line for mark in UNRULED_MARKS)
        for line in BLIND.read_text().splitlines()
    ):
        raise SystemExit(f"{BLIND.name} already carries a ruling; not overwriting it")
    if not SOURCE.exists():
        raise SystemExit(f"no {SOURCE}: run experiment 0005's report.py ruling first")
    items = parse(SOURCE.read_text())
    if len(items) < SAMPLE:
        raise SystemExit(f"only {len(items)} ruled items in {SOURCE.name}, need {SAMPLE}")

    rng = random.Random(SEED)
    chosen = rng.sample(items, SAMPLE)

    blind = [
        "# Blind self agreement, experiment 0006 (spec 0003, AC-30)",
        "",
        f"{SAMPLE} items drawn at random from experiment 0005's already ruled "
        f"`ruling-sheet.md` (42 ruled items across groups A, B, C), seed `{SEED}`. Rule "
        "each cold, as if seeing it for the first time; only once every item here is "
        "re-marked, open `blind-reread-answers.md` in this same directory and compare.",
        "",
    ]
    answers = [
        "# Blind self agreement: answers, experiment 0006 (spec 0003, AC-30)",
        "",
        "The same 10 items, in the same order, with the original mark and reason "
        f"from experiment 0005's `ruling-sheet.md`. Seed `{SEED}`. Open only after "
        "`blind-reread.md` is fully re-marked.",
        "",
    ]
    for n, item in enumerate(chosen, start=1):
        blind += [f"## Item {n}", f"_{item.group_heading} · {item.section_heading}_", ""]
        blind += blind_lines(item)
        blind.append("")
        answers += [f"## Item {n}", ""]
        answers += answer_lines(item)
        answers.append("")

    (HERE / "data").mkdir(exist_ok=True)
    BLIND.write_text("\n".join(blind) + "\n")
    ANSWERS.write_text("\n".join(answers) + "\n")
    print(f"wrote {BLIND.name} and {ANSWERS.name}")


if __name__ == "__main__":
    build()
