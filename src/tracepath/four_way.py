"""The four way comparison of spec 0008 (AC-8 to AC-8f): step states, noise, and the checks.

Pure. One scored question under one configuration becomes one state per expected step,
read exactly as spec 0005 defines them: reached by the clean walk is reached as
accepted (AC-12), reached only by the held walk is reached only as held (AC-12b), else
not reached. `--code-pass` is off in every configuration, so only the two candidates
vary. The checks report facts from the table; nothing here flips a default.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from tracepath.report import Finding, Question, Report
from tracepath.traverse.graph_slice import NodeKind
from tracepath.traverse.walk import Chain, Step


class State(StrEnum):
    """One expected step's state under one configuration (AC-8c)."""

    ACCEPTED = "reached as accepted"
    HELD_ONLY = "reached only as held"
    NOT_REACHED = "not reached"


#: How close each state is to accepted, so "worse" can be compared (AC-8f).
RANK: Mapping[State, int] = {State.NOT_REACHED: 0, State.HELD_ONLY: 1, State.ACCEPTED: 2}


@dataclass(frozen=True)
class Config:
    """One of the four configurations: which of the two candidate flags is given."""

    name: str
    with_held: bool
    narrow_hold: bool

    @property
    def flags(self) -> tuple[str, ...]:
        """The flags `load` and `eval` both take for this configuration, each one stated.

        Both are given either way, so a configuration never rests on a project default.
        """
        return (
            "--with-held" if self.with_held else "--no-with-held",
            "--narrow-hold" if self.narrow_hold else "--no-narrow-hold",
        )


BASELINE = Config("baseline", with_held=False, narrow_hold=False)
WITH_HELD = Config("--with-held", with_held=True, narrow_hold=False)
NARROW_HOLD = Config("--narrow-hold", with_held=False, narrow_hold=True)
BOTH = Config("both", with_held=True, narrow_hold=True)

#: The four configurations, in the order the table prints them (AC-8).
CONFIGS = (BASELINE, WITH_HELD, NARROW_HOLD, BOTH)


@dataclass(frozen=True)
class Cell:
    """One step under one configuration: its state."""

    state: State


@dataclass(frozen=True)
class StepRow:
    """One expected step of one question, with its cell under each configuration."""

    question: int
    absence: bool
    label: str
    where: str
    cells: tuple[Cell, ...]

    def state(self, config: Config) -> State:
        """This step's state under `config`."""
        return self.cells[CONFIGS.index(config)].state


@dataclass(frozen=True)
class Noise:
    """Visited steps matching no expected item, split held and accepted when held items show."""

    total: int
    held: int | None = None
    accepted: int | None = None


def cell_of(finding: Finding) -> Cell:
    """A finding's state."""
    if finding.reached_by is not None:
        state = State.ACCEPTED
    elif finding.held_by is not None:
        state = State.HELD_ONLY
    else:
        state = State.NOT_REACHED
    return Cell(state)


def _matches(step: Step, question: Question) -> bool:
    """Whether a visited step is one of the question's items, the rule `score()` counts by."""
    return any(
        step.node.kind is NodeKind.ENTITY
        and step.node.file == item.file
        and step.node.file_line == item.line
        for item in question.items
    )


def _held_step(step: Step) -> bool:
    """A step the chain prints `HELD:` on: a held node, or reached by a held link."""
    return step.node.held or (step.via is not None and step.via.held)


def noise_of(report: Report, chain: Chain | None, *, with_held: bool) -> Noise:
    """AC-8d's count for one question, split by whether each step is held.

    `chain` is the chain `trace` prints: the held walk when held items show, else the
    clean walk, the same walk `score()` counts visited steps over.
    """
    if not with_held:
        return Noise(report.unmatched_steps)
    unmatched = [s for s in (chain.steps if chain else ()) if not _matches(s, report.question)]
    held = sum(1 for step in unmatched if _held_step(step))
    return Noise(report.unmatched_steps, held=held, accepted=len(unmatched) - held)


def summed(noises: Sequence[Noise]) -> Noise:
    """Several questions' noise counted together."""
    total = sum(n.total for n in noises)
    if any(n.held is None for n in noises):
        return Noise(total)
    return Noise(
        total,
        held=sum(n.held or 0 for n in noises),
        accepted=sum(n.accepted or 0 for n in noises),
    )


def worse_under_both(rows: Sequence[StepRow]) -> tuple[StepRow, ...]:
    """Every step whose state with both flags is worse than its better single flag (AC-8f)."""
    return tuple(
        row
        for row in rows
        if RANK[row.state(BOTH)] < max(RANK[row.state(WITH_HELD)], RANK[row.state(NARROW_HOLD)])
    )


def newly_accepted(rows: Sequence[StepRow]) -> tuple[StepRow, ...]:
    """AC-9(a): steps `--narrow-hold` reaches as accepted that baseline did not."""
    return tuple(
        r
        for r in rows
        if r.state(BASELINE) is not State.ACCEPTED and r.state(NARROW_HOLD) is State.ACCEPTED
    )


def regressed(rows: Sequence[StepRow]) -> tuple[StepRow, ...]:
    """AC-9(b) fails on these: accepted at baseline, not reached or held only under the rule."""
    return tuple(
        r
        for r in rows
        if r.state(BASELINE) is State.ACCEPTED and r.state(NARROW_HOLD) is not State.ACCEPTED
    )


def newly_held_only(rows: Sequence[StepRow]) -> tuple[StepRow, ...]:
    """AC-11: steps not reached at baseline that `--with-held` reaches only as held."""
    return tuple(
        r
        for r in rows
        if r.state(BASELINE) is State.NOT_REACHED and r.state(WITH_HELD) is State.HELD_ONLY
    )


def _cell(cell: Cell) -> str:
    return str(cell.state)


def _named(rows: Sequence[StepRow]) -> str:
    if not rows:
        return "none"
    return "; ".join(
        f"Q{r.question}{' (absence item)' if r.absence else ''} {r.label} · {r.where}" for r in rows
    )


def table_lines(
    rows: Sequence[StepRow], noise: Mapping[str, Noise], runs_commit: str, eval_file: str
) -> tuple[str, ...]:
    """The per step table, the noise table, then the facts AC-8f, AC-9 and AC-11 read."""
    lines = [
        f"Run against `artifacts/runs/` at {runs_commit}; `--code-pass` off in every "
        f"configuration; eval file `{eval_file}`.",
        "",
        "| Q | expected step | " + " | ".join(c.name for c in CONFIGS) + " |",
        "|---|---|" + "---|" * len(CONFIGS),
    ]
    for row in rows:
        absence = " (absence item)" if row.absence else ""
        lines.append(
            f"| {row.question} | {row.label}{absence} · {row.where} | "
            + " | ".join(_cell(c) for c in row.cells)
            + " |"
        )
    lines += [
        "",
        "Visited steps matching no expected item, all five questions summed (AC-8d):",
        "",
        "| configuration | total | among held steps | among accepted steps |",
        "|---|---|---|---|",
    ]
    for config in CONFIGS:
        n = noise[config.name]
        held = "n/a" if n.held is None else str(n.held)
        accepted = "n/a" if n.accepted is None else str(n.accepted)
        lines.append(f"| {config.name} | {n.total} | {held} | {accepted} |")
    broken = worse_under_both(rows)
    lines += [
        "",
        f"AC-8f, steps worse with both flags than the better single flag: {_named(broken)}.",
    ]
    if broken:
        lines.append("STOPPED: the both flags check failed, so no AC-9 or AC-11 fact is read.")
        return tuple(lines)
    lines += [
        "AC-9(a), steps newly reached as accepted under --narrow-hold: "
        f"{_named(newly_accepted(rows))}.",
        "AC-9(b), steps accepted at baseline and not under --narrow-hold: "
        f"{_named(regressed(rows))}.",
        f"AC-11, steps moving from not reached to reached only as held under --with-held: "
        f"{_named(newly_held_only(rows))}.",
    ]
    return tuple(lines)
