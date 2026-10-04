"""Estimate the type coverage rerun's 24 calls, free, with the token counting endpoint.

Spec 0003, build plan step 30 (AC-18): the eight units' own runs cannot price a
`0003.1` call (six are `0002.2` and record no usage; `0008` is `0002.3` and `0021` is
`0003.0`), so each unit's output is read from measured `0003.x` runs of the same unit
kind, and each figure below names the runs it comes from. Input is counted here, free.
Nothing in this script spends API credit.

The output figures are copied as constants, not read from `artifacts/runs/`, because
the rerun this estimates moves `0021`'s runs to `artifacts/superseded/`. Every figure
was checked against its run artifact's `output_tokens` on 2026-10-04, at `dd08b35`.

Run from the repository root: uv run python <this file>
"""

import json
from pathlib import Path
from statistics import mean

import anthropic

from tracepath.config import load_anthropic_settings
from tracepath.extract.client import PROMPT_VERSION, system_blocks, user_prompt
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, UnitKind, split_units

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent

#: The `0003.1` cached prefix as the API billed it: experiment 0006's first after call
#: (`0014` run 1) wrote 57,494 cache tokens, and every later `0003.1` call read 57,494.
#: The counting endpoint's probe gave 54,279 for the system block alone; the billed
#: prefix also carries the output schema, so the billed figure is the one used.
CACHED_PREFIX = 57_494

#: A calibration unit: experiment 0006 counted `0014 ## Requirements` at 61,108 input
#: tokens under `0003.1` (`data/prefix-count.json`), and its real calls billed exactly
#: 3,614 uncached plus 57,494 cached. A recount here must match, or the prompt moved.
CALIBRATION = ("specs/0014-", "Requirements", 61_108)

#: Rates per token, Sonnet 5: input, output, 1 hour cache write, cache read. The same
#: rates experiment 0005's `run_units.py` uses, reproduced against experiment 0004's bill.
INPUT_RATE, OUTPUT_RATE, CACHE_WRITE_RATE, CACHE_READ_RATE = (
    rate / 1_000_000 for rate in (2.0, 10.0, 4.0, 0.2)
)

#: Measured `0003.x` output tokens per call, by unit kind (spec 0003, step 30).
MEASURED = {
    "requirements": {
        "primary": (
            "experiment 0006, 0014 ## Requirements afters, 0003.1",
            (18_483, 18_687, 21_020),
        ),
        "second": (
            "experiment 0005, 0021 ## Requirements afters, 0003.0",
            (29_284, 39_234, 28_652),
        ),
    },
    "feature design": {
        "primary": (
            "experiment 0006, 0015 ## Feature design afters, 0003.1",
            (25_937, 24_751, 25_391),
        ),
        "second": (
            "experiment 0005, 0013 ## Feature design afters, 0003.0",
            (18_752, 23_434, 18_735),
        ),
    },
    "scope row": {
        "primary": (
            "experiment 0006, feature-33 scope row afters, 0003.1",
            (10_669, 15_955, 9_484),
        ),
        "second": ("experiment 0005, feature-9 scope row afters, 0003.0", (20_654, 16_873, 16_285)),
    },
}

#: The heaviest measured `0003.x` call: experiment 0005's `0021` run 2.
HEAVIEST = ("experiment 0005, 0021 ## Requirements run 2, 0003.0", 39_234)

#: Central figure for a kind with no `0003.x` measurement: the mean of every `0003.1`
#: section call measured (experiment 0006's `0014` and `0015` afters, six calls). Step
#: 30 names only the wider bound for these kinds; this central figure is a stated choice.
UNMEASURED_CENTRAL = (
    "mean of experiment 0006's six 0003.1 section calls (0014 and 0015 afters)",
    round(mean(MEASURED["requirements"]["primary"][1] + MEASURED["feature design"]["primary"][1])),
)

#: The eight units (spec 0003, AC-18): file prefix, section, and the kind it is priced as.
UNITS = [
    ("specs/0012-", "Requirements", "requirements"),
    ("specs/0012-", "Consequences", None),
    ("specs/0012-", "Follow-up", None),
    ("specs/0012-", "Build plan", None),
    ("scope/scope.md", "21. Terms & privacy notices · done · Alpha", "scope row"),
    ("specs/0008-", "Preamble", None),
    ("specs/0021-", "Requirements", "requirements"),
    ("specs/0006-", "Feature design", "feature design"),
]

RUNS_PER_UNIT = 3
RETRIES_PER_UNIT = 1


def find(prefix: str, section: str) -> Unit:
    """The one unit a manifest key names."""
    if prefix.endswith(".md"):
        path = SNAPSHOT / prefix
    else:
        path = next(SNAPSHOT.glob(f"{prefix}*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    return next(u for u in units if u.section == section and u.kind is not UnitKind.INTRO)


def count(client: anthropic.Anthropic, model: str, unit: Unit) -> int:
    """Input tokens for one extraction call, schema included, as `extract_once` sends it."""
    return client.messages.count_tokens(
        model=model,
        system=system_blocks(),
        messages=[{"role": "user", "content": user_prompt(unit)}],
        output_format=ExtractionOutput,
    ).input_tokens


def output_figures(kind: str | None) -> dict[str, object]:
    """Central and wider output tokens per call for one unit kind, with their sources."""
    if kind is None:
        return {
            "central": UNMEASURED_CENTRAL[1],
            "central_source": UNMEASURED_CENTRAL[0],
            "wider": HEAVIEST[1],
            "wider_source": f"heaviest measured 0003.x call: {HEAVIEST[0]}",
        }
    primary_source, primary = MEASURED[kind]["primary"]
    second_source, second = MEASURED[kind]["second"]
    return {
        "central": round(mean(primary)),
        "central_source": f"mean of {primary_source}",
        "wider": max(primary + second),
        "wider_source": f"highest single call across {primary_source} and {second_source}",
    }


def call_cost(uncached: int, output: int, *, writes_cache: bool) -> float:
    """Dollars for one call: its uncached input, its output, and the prefix written or read."""
    prefix_rate = CACHE_WRITE_RATE if writes_cache else CACHE_READ_RATE
    return uncached * INPUT_RATE + output * OUTPUT_RATE + CACHED_PREFIX * prefix_rate


def main() -> None:
    """Count every unit's input, price the manifest twice, and write the estimate."""
    settings = load_anthropic_settings()
    client = anthropic.Anthropic(api_key=settings.api_key)

    prefix, section, expected = CALIBRATION
    recount = count(client, settings.model, find(prefix, section))
    if recount != expected:
        raise SystemExit(f"calibration: 0014 counted {recount}, expected {expected}")

    rows: list[dict[str, object]] = []
    totals = {"central": 0.0, "wider": 0.0}
    first = True
    for prefix, section, kind in UNITS:
        unit = find(prefix, section)
        total_input = count(client, settings.model, unit)
        uncached = total_input - CACHED_PREFIX
        figures = output_figures(kind)
        calls = RUNS_PER_UNIT + RETRIES_PER_UNIT
        row: dict[str, object] = {
            "unit": f"{unit.record_id} {unit.section}",
            "unit_kind": str(unit.kind),
            "priced_as": kind or "no 0003.x measurement",
            "chars": len(unit.text),
            "input_tokens_per_call": total_input,
            "uncached_input_tokens_per_call": uncached,
            "calls_priced": calls,
            **figures,
        }
        for band in ("central", "wider"):
            output = int(str(figures[band]))
            cost = sum(
                call_cost(uncached, output, writes_cache=first and n == 0) for n in range(calls)
            )
            row[f"{band}_usd"] = round(cost, 4)
            totals[band] += cost
        first = False
        rows.append(row)

    report = {
        "purpose": (
            "Go ahead figure for experiment 0008, the type coverage rerun (spec 0003, "
            "AC-18, build plan step 30): 8 units, 3 calls each, under 0003.1. A planning "
            "computation only; no paid call has run."
        ),
        "method": (
            "Input per call counted with the free token counting endpoint; uncached input "
            "is that count less the billed 57,494 token cached prefix. Output per call from "
            "measured 0003.x runs of the same unit kind, named per unit. Central: the mean "
            "of the kind's 0003.1 runs; wider: the highest single call across both measured "
            "points of the kind. Kinds with no 0003.x measurement: central is the mean of "
            "the six 0003.1 section calls, wider is the heaviest measured 0003.x call. Each "
            "unit is priced at 3 runs plus 1 retry, each retry a full call at the same "
            "figure. One 1 hour cache write (the first call); every other call reads it."
        ),
        "prompt_version": PROMPT_VERSION,
        "cached_prefix_tokens": CACHED_PREFIX,
        "calibration_recount_0014": recount,
        "rates_usd_per_million": {
            "input": 2.0,
            "output": 10.0,
            "cache_write_1h": 4.0,
            "cache_read": 0.2,
        },
        "calls_priced": len(UNITS) * (RUNS_PER_UNIT + RETRIES_PER_UNIT),
        "units": rows,
        "total_usd": {band: round(value, 4) for band, value in totals.items()},
    }
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "cost-estimate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
