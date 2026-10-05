"""What extraction calls cost: the rates, the measured figures, and the estimate.

Pure. Every figure here is a measurement with a named source (spec 0004, Value
sourcing), never a round number: the reflex this exists for is an unflagged estimate
that turned out 10 to 15 times low.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from tracepath.extract.client import Attempt

#: USD per million tokens: standard interactive pricing, not Batch. The rates
#: experiment 0005 reproduced exactly against experiment 0004's bill.
INPUT_RATE = 2.00
OUTPUT_RATE = 10.00
CACHE_WRITE_RATE = 4.00
CACHE_READ_RATE = 0.20

#: The cached system prompt, as billed: experiment 0008's first call wrote 57,494
#: tokens and every later settled call read 57,494 (experiment 0008 README,
#: Configuration). The token count endpoint counts the whole request, so a unit's
#: uncached input is its count minus this.
CACHED_PREFIX_TOKENS = 57_494

#: Experiment 0006's calibration unit and its counted input. A count that differs
#: means the prompt or the counting changed under the figures above, and nothing is
#: priced on them (spec 0004, Value sourcing).
CALIBRATION_ADDRESS = "0014:Requirements"
CALIBRATION_TOKENS = 61_108

#: The central output per call, by section name, each the mean of a measured unit's
#: three runs under `0003.1` (experiment 0008 `data/run.json`, the unseen unit figures).
CENTRAL_OUTPUT: dict[str, tuple[int, str]] = {
    "Requirements": (27_384, "`0021 ## Requirements` (experiment 0008 data/run.json)"),
    "Feature design": (26_721, "`0006 ## Feature design` (experiment 0008 data/run.json)"),
}

#: The heaviest measured call's output, which the wider figure prices every call at
#: (experiment 0005, `0021` run 2).
HEAVIEST_OUTPUT = 39_234
HEAVIEST_SOURCE = "the heaviest measured call (experiment 0005, `0021` run 2)"

#: What a failed or dropped attempt adds to the running total, whatever it recorded:
#: one heaviest call reading the cache, 39,234 output, 5,276 uncached input and one
#: 57,494 token cache read (experiment 0008's script). A failed attempt's recorded
#: usage can undercount badly, so it is never used.
FLAT_FAILURE_USD = 0.4144


class EstimateUnavailable(Exception):
    """The measured figures cannot be trusted for this prompt, so nothing is priced."""


def tokens_cost(input_tokens: int, output_tokens: int, cache_write: int, cache_read: int) -> float:
    """USD for one call's tokens, each kind at its own rate."""
    return (
        input_tokens * INPUT_RATE
        + output_tokens * OUTPUT_RATE
        + cache_write * CACHE_WRITE_RATE
        + cache_read * CACHE_READ_RATE
    ) / 1e6


def attempt_cost(attempt: Attempt) -> float:
    """One attempt's figure in the running total (spec 0004 AC-10a, AC-10b).

    A settled attempt counts at its own recorded usage, cache write and read included.
    A failed or dropped one counts at `FLAT_FAILURE_USD`, never at its recorded tokens.
    """
    if attempt.output is None:
        return FLAT_FAILURE_USD
    return tokens_cost(
        attempt.input_tokens or 0,
        attempt.output_tokens or 0,
        attempt.cache_creation_input_tokens,
        attempt.cache_read_input_tokens,
    )


def check_calibration(counted: int) -> None:
    """Refuse to price when the calibration unit no longer counts as measured.

    Raises:
        EstimateUnavailable: the count differs from `CALIBRATION_TOKENS`.
    """
    if counted != CALIBRATION_TOKENS:
        raise EstimateUnavailable(
            f"the calibration unit {CALIBRATION_ADDRESS} counts {counted:,} input tokens, not "
            f"the {CALIBRATION_TOKENS:,} experiment 0006 measured, so the cached prefix of "
            f"{CACHED_PREFIX_TOKENS:,} no longer applies and nothing is priced"
        )


@dataclass(frozen=True)
class UnitCount:
    """One unit's input, as the token count endpoint counted it."""

    address: str
    section: str
    counted: int


@dataclass(frozen=True)
class UnitEstimate:
    """One unit's share of the estimate. `central_*` is `None` with no measured figure."""

    address: str
    counted: int
    uncached: int
    central_output: int | None
    central_source: str | None
    central_calls: int
    central_usd: float | None
    wider_calls: int
    wider_usd: float


@dataclass(frozen=True)
class Estimate:
    """The central and wider figures for a whole command, unit by unit."""

    units: tuple[UnitEstimate, ...]
    central_calls: int
    central_usd: float | None
    wider_calls: int
    wider_usd: float


def _calls_cost(calls: int, uncached: int, output: int, writes_cache: bool) -> float:
    """`calls` calls of one unit, the first writing the cache when `writes_cache`."""
    if calls == 0:
        return 0.0
    first = tokens_cost(
        uncached,
        output,
        CACHED_PREFIX_TOKENS if writes_cache else 0,
        0 if writes_cache else CACHED_PREFIX_TOKENS,
    )
    rest = tokens_cost(uncached, output, 0, CACHED_PREFIX_TOKENS)
    return first + (calls - 1) * rest


def estimate(counts: Sequence[UnitCount], runs: int) -> Estimate:
    """The central and wider cost of extracting every unit, in the order given.

    Central: `runs` calls per unit, each at its section's measured output. Wider: a
    retry on every run, so twice the calls, each at the heaviest measured output. In
    both, the command's first call writes the cache and every later call reads it.

    Raises:
        EstimateUnavailable: a unit counts fewer tokens than the cached prefix alone.
    """
    units: list[UnitEstimate] = []
    for position, count in enumerate(counts):
        uncached = count.counted - CACHED_PREFIX_TOKENS
        if uncached < 0:
            raise EstimateUnavailable(
                f"{count.address} counts {count.counted:,} tokens, fewer than the cached "
                f"prefix of {CACHED_PREFIX_TOKENS:,} alone"
            )
        first = position == 0
        central = CENTRAL_OUTPUT.get(count.section)
        units.append(
            UnitEstimate(
                address=count.address,
                counted=count.counted,
                uncached=uncached,
                central_output=central[0] if central else None,
                central_source=central[1] if central else None,
                central_calls=runs,
                central_usd=_calls_cost(runs, uncached, central[0], first) if central else None,
                wider_calls=2 * runs,
                wider_usd=_calls_cost(2 * runs, uncached, HEAVIEST_OUTPUT, first),
            )
        )
    centrals = [unit.central_usd for unit in units]
    return Estimate(
        units=tuple(units),
        central_calls=sum(unit.central_calls for unit in units),
        central_usd=None if None in centrals else sum(c for c in centrals if c is not None),
        wider_calls=sum(unit.wider_calls for unit in units),
        wider_usd=sum(unit.wider_usd for unit in units),
    )


def estimate_lines(result: Estimate, ceiling: float) -> tuple[str, ...]:
    """The estimate as `extract` prints it (spec 0004 AC-6b, AC-6c)."""
    lines = [
        f"Rates assumed, standard interactive pricing, not Batch: input ${INPUT_RATE:.2f}, "
        f"output ${OUTPUT_RATE:.2f}, 1 hour cache write ${CACHE_WRITE_RATE:.2f}, "
        f"cache read ${CACHE_READ_RATE:.2f}, per million tokens.",
        f"Cached prefix: {CACHED_PREFIX_TOKENS:,} tokens, as billed (experiment 0008); "
        f"calibration {CALIBRATION_ADDRESS} counted {CALIBRATION_TOKENS:,}, as measured.",
    ]
    for unit in result.units:
        lines.append(
            f"  {unit.address}: {unit.counted:,} input tokens counted, "
            f"{CACHED_PREFIX_TOKENS:,} cached prefix, {unit.uncached:,} uncached per call."
        )
        if unit.central_output is None or unit.central_usd is None:
            lines.append("    central: no measured output figure for this section, not priced")
        else:
            lines.append(
                f"    central: {unit.central_output:,} output per call, from "
                f"{unit.central_source}; {unit.central_calls} calls, ${unit.central_usd:.4f}"
            )
        lines.append(
            f"    wider: {HEAVIEST_OUTPUT:,} output per call, {HEAVIEST_SOURCE}, a retry on "
            f"every run; {unit.wider_calls} calls, ${unit.wider_usd:.4f}"
        )
    central = "not priced" if result.central_usd is None else f"${result.central_usd:.4f}"
    within = "within" if result.wider_usd <= ceiling else "above"
    lines += [
        f"Central total: {result.central_calls} calls, {central}.",
        f"Wider total: {result.wider_calls} calls, ${result.wider_usd:.4f}, {within} the "
        f"ceiling of ${ceiling:.2f}.",
        f"A failed or dropped attempt counts ${FLAT_FAILURE_USD:.4f} in the running total.",
    ]
    return tuple(lines)
