"""The `extract` command and its metered run, with a fake client and no paid call.

Spec 0004 build plan steps 6 and 7. Every call here is scripted: the model call is
`client.extract_once` swapped for a script, and the token count endpoint is a fake that
answers from the unit it is asked about. Artifacts land under `tmp_path`.
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import anthropic
import httpx2
import pytest
from typer.testing import CliRunner

from tests.test_extract_client import recorded_stream, replaying_client
from tracepath import cli, config
from tracepath.artifacts import RUNS_DIR, read_run
from tracepath.config import AnthropicSettings
from tracepath.extract import client as client_module
from tracepath.extract.address import Target, UnitAddressError, resolve_address, resolve_addresses
from tracepath.extract.client import Attempt
from tracepath.extract.cost import (
    CACHED_PREFIX_TOKENS,
    FLAT_FAILURE_USD,
    UnitCount,
    attempt_cost,
    estimate,
)
from tracepath.extract.metered import (
    RunOutcome,
    calls_through,
    count_input,
    preflight,
    run_metered,
    summary_lines,
)
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
FIXTURES = Path(__file__).parent / "fixtures" / "runs"
QUESTION_3 = [
    "0002:Requirements",
    "0002:Feature design",
    "0007:Requirements",
    "0007:Feature design",
]
SETTINGS = AnthropicSettings(
    api_key="sk-ant-test", model="claude-sonnet-5", runs_per_unit=3, effort="medium"
)
COUNTED = 62_000

runner = CliRunner()


def flat(text: str) -> str:
    return " ".join(text.split())


def an_output() -> ExtractionOutput:
    return ExtractionOutput.model_validate(json.loads((FIXTURES / "run1.json").read_text()))


def settled(
    number: int = 1, cache_read: int = CACHED_PREFIX_TOKENS, cache_write: int = 0
) -> Attempt:
    return Attempt(
        number=number,
        input_tokens=4_000,
        output_tokens=27_000,
        run_id="r",
        output=an_output(),
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cache_read,
        stop_reason="end_turn",
    )


def failed(
    number: int = 1,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read: int = 0,
) -> Attempt:
    return Attempt(
        number=number,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        run_id="r",
        error="the connection dropped mid stream",
        cache_read_input_tokens=cache_read,
    )


def first_call() -> Attempt:
    return settled(cache_read=0, cache_write=CACHED_PREFIX_TOKENS)


class Script:
    """A scripted model call: hands back the next attempt, keeps every call it got."""

    def __init__(self, attempts: list[Attempt], before: Callable[[int], None] | None = None):
        self.attempts = attempts
        self.calls: list[tuple[str, int]] = []
        self.before = before

    def __call__(self, unit: Unit, number: int) -> Attempt:
        if self.before is not None:
            self.before(len(self.calls))
        self.calls.append((f"{unit.record_id}:{unit.section}", number))
        attempt = self.attempts[len(self.calls) - 1]
        return Attempt(**{**attempt.__dict__, "number": number})


def targets(*addresses: str) -> tuple[Target, ...]:
    return resolve_addresses(SNAPSHOT, list(addresses))


def run(
    tmp_path: Path, script: Script, *addresses: str, ceiling: float = 100.0
) -> tuple[RunOutcome, list[str]]:
    said: list[str] = []
    outcome = run_metered(
        targets(*addresses),
        script,
        SETTINGS,
        tmp_path,
        "2e40bcf",
        "2026-10-05T00:00:00+00:00",
        ceiling,
        said.append,
    )
    return outcome, said


# Unit addresses.


def test_an_address_names_one_unit_with_its_section_slug() -> None:
    target = resolve_address(SNAPSHOT, "0002:Feature design")

    assert (target.unit.record_id, target.unit.section, target.section_slug) == (
        "0002",
        "Feature design",
        "feature-design",
    )
    assert target.unit.start_line == 53


def test_a_section_two_units_share_is_refused_naming_both() -> None:
    with pytest.raises(UnitAddressError, match="ambiguous") as caught:
        resolve_address(SNAPSHOT, "0007:Build plan")

    assert "line 263" in str(caught.value) and "line 264" in str(caught.value)


@pytest.mark.parametrize("address", ["0002", "0002:", ":Requirements", "9999:Requirements"])
def test_a_malformed_or_unknown_address_is_refused(address: str) -> None:
    with pytest.raises(UnitAddressError):
        resolve_address(SNAPSHOT, address)


def test_a_unit_named_twice_is_refused() -> None:
    with pytest.raises(UnitAddressError, match="named twice"):
        targets("0002:Requirements", "0002:Requirements")


# AC-4: the whole command's collision preflight.


def test_preflight_stops_on_one_collision_in_any_run_of_any_unit(tmp_path: Path) -> None:
    taken = tmp_path / RUNS_DIR / "0002" / "feature-design" / "run-2.json"
    taken.parent.mkdir(parents=True)
    taken.write_text("{}")

    with pytest.raises(Exception, match="already exists") as caught:
        preflight(tmp_path, targets("0002:Requirements", "0002:Feature design"), runs=3)

    assert str(taken) in str(caught.value)


# AC-12a, AC-12b: each attempt is written as it settles, failed ones under their own name.


def test_each_attempt_is_written_before_the_next_call_starts(tmp_path: Path) -> None:
    unit_dir = tmp_path / RUNS_DIR / "0002" / "requirements"
    seen: list[list[str]] = []
    script = Script(
        [first_call(), failed(1), settled(2), settled()],
        before=lambda n: seen.append(sorted(p.name for p in unit_dir.glob("*.json"))),
    )

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    assert outcome.stop is None
    assert seen == [
        [],
        ["run-1.json"],
        ["failed-run-2-attempt-1.json", "run-1.json"],
        ["failed-run-2-attempt-1.json", "run-1.json", "run-2.json"],
    ]


def test_a_dropped_attempt_is_written_as_a_failed_run_with_null_usage(tmp_path: Path) -> None:
    script = Script([first_call(), failed(1), settled(2), settled()])

    run(tmp_path, script, "0002:Requirements")

    artifact = read_run(
        tmp_path / RUNS_DIR / "0002" / "requirements" / "failed-run-2-attempt-1.json"
    )
    assert artifact.output is None
    assert artifact.input_tokens is None and artifact.output_tokens is None
    assert artifact.error is not None


# AC-10a, AC-10b: what the running total counts.


def test_a_failed_attempt_counts_at_the_flat_figure_whatever_it_recorded() -> None:
    assert attempt_cost(failed(input_tokens=90_000, output_tokens=60_000)) == FLAT_FAILURE_USD
    assert attempt_cost(failed(input_tokens=10, output_tokens=2)) == FLAT_FAILURE_USD
    assert attempt_cost(failed()) == FLAT_FAILURE_USD == 0.4144


def test_a_settled_attempt_counts_at_its_recorded_usage_cache_included() -> None:
    attempt = settled(cache_read=57_494, cache_write=1_000)

    expected = (4_000 * 2.0 + 27_000 * 10.0 + 1_000 * 4.0 + 57_494 * 0.2) / 1e6

    assert attempt_cost(attempt) == pytest.approx(expected)


def test_the_running_total_sums_each_attempt_by_its_own_rule(tmp_path: Path) -> None:
    script = Script([first_call(), failed(1), settled(2), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    expected = attempt_cost(first_call()) + FLAT_FAILURE_USD + 2 * attempt_cost(settled())
    assert outcome.total_usd == pytest.approx(expected)


# AC-9: the check before every call.


def test_a_call_one_more_failure_could_carry_past_the_ceiling_is_not_made(tmp_path: Path) -> None:
    script = Script([first_call(), settled(), settled()])
    ceiling = attempt_cost(first_call()) + FLAT_FAILURE_USD - 0.0001

    outcome, _ = run(tmp_path, script, "0002:Requirements", ceiling=ceiling)

    assert len(script.calls) == 1
    assert outcome.stop == "stopping here before 0002:Requirements run 2 attempt 1: ceiling"


def test_a_call_exactly_at_the_ceiling_is_made(tmp_path: Path) -> None:
    script = Script([first_call(), settled(), settled()])
    ceiling = attempt_cost(first_call()) + FLAT_FAILURE_USD

    _, _ = run(tmp_path, script, "0002:Requirements", ceiling=ceiling)

    assert len(script.calls) == 2


# AC-11: after the first call, a call that read no cache stops the run.


def test_a_second_call_that_read_no_cache_stops_the_run(tmp_path: Path) -> None:
    script = Script([first_call(), settled(cache_read=0), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    assert outcome.stop == "stopping: call 2 read no cache"
    assert len(script.calls) == 2


def test_a_later_units_call_is_held_to_the_same_rule(tmp_path: Path) -> None:
    script = Script([first_call(), settled(), settled(), settled(cache_read=0)])

    outcome, _ = run(tmp_path, script, "0002:Requirements", "0007:Requirements")

    assert outcome.stop == "stopping: call 4 read no cache"
    assert script.calls[-1] == ("0007:Requirements", 1)


def test_the_first_call_of_the_command_may_read_no_cache(tmp_path: Path) -> None:
    script = Script([first_call(), settled(), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    assert outcome.stop is None


def test_a_call_refused_before_it_reported_any_usage_is_retried_not_stopped_on(
    tmp_path: Path,
) -> None:
    """A call that never reached the model reports zeros, which say nothing of the cache."""
    script = Script(
        [first_call(), failed(1, input_tokens=0, output_tokens=0), settled(), settled()]
    )

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    assert outcome.stop is None
    assert len(script.calls) == 4


# AC-5: before every retry, that attempt's paths are checked.


def test_a_retry_whose_artifact_already_exists_stops_before_it_is_paid_for(tmp_path: Path) -> None:
    taken = tmp_path / RUNS_DIR / "0002" / "requirements" / "failed-run-1-attempt-2.json"
    taken.parent.mkdir(parents=True)
    taken.write_text("{}")
    script = Script([failed(1, cache_read=0), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    assert len(script.calls) == 1
    assert outcome.stop is not None
    assert outcome.stop.startswith("stopping here before 0002:Requirements run 1 attempt 2:")
    assert str(taken) in outcome.stop


# AC-13: a run that fails after its retry stops the command and names the unit.


def test_a_unit_that_fails_after_its_retry_stops_before_the_next_call(tmp_path: Path) -> None:
    script = Script([first_call(), failed(1), failed(2), settled(), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements", "0007:Requirements")

    assert len(script.calls) == 3
    assert outcome.stop is not None
    assert "0002:Requirements run 2 failed after its retry" in outcome.stop
    assert "not run again" in outcome.stop


# AC-14: the summary names every attempt with null usage.


def test_the_summary_names_every_attempt_with_null_usage(tmp_path: Path) -> None:
    script = Script([first_call(), failed(1), settled(2), settled()])

    outcome, _ = run(tmp_path, script, "0002:Requirements")

    lines = summary_lines(outcome)
    assert "Attempts with null usage:" in lines
    assert "  0002:Requirements run 2 attempt 1: failed-run-2-attempt-1.json" in lines


def test_the_summary_says_none_when_every_attempt_reported_usage(tmp_path: Path) -> None:
    outcome, _ = run(tmp_path, Script([first_call(), settled(), settled()]), "0002:Requirements")

    assert "Attempts with null usage: none." in summary_lines(outcome)


# The estimate (AC-6c), checked against arithmetic written out here, not the module's.


def test_the_central_and_wider_figures_for_question_3s_four_units() -> None:
    counts = [UnitCount(a, a.split(":")[1], COUNTED) for a in QUESTION_3]

    result = estimate(counts, runs=3)

    uncached = COUNTED - 57_494
    write, read = 57_494 * 4.0, 57_494 * 0.2

    def calls(n: int, output: int, writes: bool) -> float:
        each = uncached * 2.0 + output * 10.0
        return (n * each + (write if writes else read) + (n - 1) * read) / 1e6

    central = (calls(3, 27_384, True) + calls(3, 26_721, False) + calls(3, 27_384, False)) + calls(
        3, 26_721, False
    )
    wider = calls(6, 39_234, True) + 3 * calls(6, 39_234, False)
    assert (result.central_calls, result.wider_calls) == (12, 24)
    assert result.central_usd == pytest.approx(central)
    assert result.wider_usd == pytest.approx(wider)


def test_a_section_with_no_measured_output_is_not_priced_centrally() -> None:
    result = estimate([UnitCount("0002:Consequences", "Consequences", COUNTED)], runs=3)

    assert result.central_usd is None
    assert result.wider_usd > 0


# The command, end to end through Typer, with a fake client.


class FakeMessages:
    def __init__(self, calibration: int) -> None:
        self.calibration = calibration
        self.counted: list[str] = []

    def count_tokens(self, **request: Any) -> SimpleNamespace:
        content = request["messages"][0]["content"]
        self.counted.append(content.split("\n", 1)[0])
        if content.startswith("Record: 0014\n") and "Section: Requirements\n" in content:
            return SimpleNamespace(input_tokens=self.calibration)
        return SimpleNamespace(input_tokens=COUNTED)


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A fake client and a scripted model call; no request leaves the process."""
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_EFFORT", raising=False)
    state = SimpleNamespace(
        messages=FakeMessages(61_108),
        built=0,
        script=Script([first_call(), *[settled() for _ in range(30)]]),
    )

    def build(_: object) -> object:
        state.built += 1
        return SimpleNamespace(messages=state.messages)

    def extract_once(client: object, settings: object, unit: Unit, number: int = 1) -> Attempt:
        return cast("Script", state.script)(unit, number)

    monkeypatch.setattr(cli, "build_client", build)
    monkeypatch.setattr(client_module, "extract_once", extract_once)
    yield state


def invoke(tmp_path: Path, *args: str) -> tuple[int, str, str]:
    result = runner.invoke(
        cli.app, ["extract", *args, "--root", str(tmp_path), "--snapshot", str(SNAPSHOT)]
    )
    return result.exit_code, result.stdout, result.stderr


def test_extract_without_a_ceiling_names_the_flag_before_any_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    code, stdout, stderr = invoke(tmp_path, "0002:Requirements")

    assert code == 1
    assert "--ceiling" in stderr
    assert fake_api.built == 0
    assert fake_api.script.calls == []
    assert "Traceback" not in stdout + stderr


def test_a_failing_worked_example_stops_extract_with_no_api_call(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    client_module.system_prompt.cache_clear()
    monkeypatch.setattr(client_module, "EXAMPLES_DIR", tmp_path / "no-examples-here")
    try:
        code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")
    finally:
        client_module.system_prompt.cache_clear()

    assert code == 1
    assert f"no worked examples found in {tmp_path / 'no-examples-here'}" in flat(stderr)
    assert fake_api.built == 0, "no client, so no call of any kind, count included"
    assert fake_api.script.calls == []
    assert "Traceback" not in stdout + stderr


def test_a_collision_in_run_2_of_the_second_unit_stops_before_the_first_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    taken = tmp_path / RUNS_DIR / "0002" / "feature-design" / "run-2.json"
    taken.parent.mkdir(parents=True)
    taken.write_text("{}")

    code, _, stderr = invoke(tmp_path, *QUESTION_3, "--ceiling", "20")

    assert code == 1
    assert "already exists" in flat(stderr)
    assert fake_api.script.calls == []
    assert fake_api.messages.counted == [], "nothing is counted or paid after a collision"


def test_a_dry_run_counts_and_prices_but_makes_no_extraction_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    code, stdout, _ = invoke(tmp_path, *QUESTION_3, "--ceiling", "20", "--dry-run")

    out = flat(stdout)
    assert code == 0
    assert fake_api.script.calls == []
    assert not (tmp_path / RUNS_DIR).exists()
    assert "standard interactive pricing, not Batch" in out
    assert f"0002:Requirements: {COUNTED:,} input tokens counted, 57,494 cached prefix" in out
    assert "27,384 output per call, from `0021 ## Requirements`" in out
    assert "26,721 output per call, from `0006 ## Feature design`" in out
    assert "Central total: 12 calls" in out
    assert "Wider total: 24 calls" in out
    assert "Dry run: no extraction call made." in out


def test_a_calibration_count_that_moved_refuses_to_price(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    fake_api.messages.calibration = 61_000

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run")

    assert code == 1
    assert "nothing is priced" in flat(stderr)
    assert "Central total" not in stdout


def test_a_wider_estimate_above_the_ceiling_stops_before_any_paid_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    code, _, stderr = invoke(tmp_path, *QUESTION_3, "--ceiling", "5")

    assert code == 1
    assert "above the ceiling $5.00" in flat(stderr)
    assert fake_api.script.calls == []


def test_extract_runs_every_unit_three_times_and_writes_every_artifact(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    code, stdout, stderr = invoke(
        tmp_path, "0002:Requirements", "0007:Requirements", "--ceiling", "20"
    )

    assert code == 0, stderr
    assert len(fake_api.script.calls) == 6
    for record in ("0002", "0007"):
        names = sorted(p.name for p in (tmp_path / RUNS_DIR / record / "requirements").iterdir())
        assert names == ["run-1.json", "run-2.json", "run-3.json"]
    assert "Attempts with null usage: none." in stdout


def test_a_stop_partway_prints_the_summary_and_exits_1(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    fake_api.script = Script([first_call(), settled(cache_read=0)])

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "stopping: call 2 read no cache" in flat(stderr)
    assert "2 calls, 2 settled" in flat(stdout)
    assert "Traceback" not in stdout + stderr


def by_hand(*sections: str) -> tuple[float, float]:
    """Central and wider USD for units that each count `COUNTED`, written out from the
    spec's Value sourcing: the first call writes the 57,494 token prefix, every later
    call reads it; central is 3 calls at the section's measured output, wider is 6 at
    39,234."""
    uncached = COUNTED - 57_494
    measured = {"Requirements": 27_384, "Feature design": 26_721}

    def calls(n: int, output: int, first: bool) -> float:
        cache = 57_494 * 4.0 if first else 57_494 * 0.2
        return (n * (uncached * 2.0 + output * 10.0) + cache + (n - 1) * 57_494 * 0.2) / 1e6

    central = sum(calls(3, measured[s], i == 0) for i, s in enumerate(sections))
    wider = sum(calls(6, 39_234, i == 0) for i, _ in enumerate(sections))
    return central, wider


def test_ac_6b_the_dry_run_prints_a_counted_line_for_every_requested_unit(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6b (per unit, the counted input and the cached prefix)."""
    _, stdout, _ = invoke(tmp_path, *QUESTION_3, "--ceiling", "20", "--dry-run")

    out = flat(stdout)
    for address in QUESTION_3:
        assert f"{address}: {COUNTED:,} input tokens counted, 57,494 cached prefix" in out


def test_ac_6c_the_dry_run_states_the_standard_rates_it_assumed(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6c and AC-49 (standard interactive rates, not Batch)."""
    _, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run")

    assert (
        "Rates assumed, standard interactive pricing, not Batch: input $2.00, output $10.00, "
        "1 hour cache write $4.00, cache read $0.20, per million tokens."
    ) in flat(stdout)


def test_ac_6c_the_dry_run_prints_the_central_total_for_question_3(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6c (the central USD figure, 12 calls)."""
    central, _ = by_hand("Requirements", "Feature design", "Requirements", "Feature design")

    _, stdout, _ = invoke(tmp_path, *QUESTION_3, "--ceiling", "20", "--dry-run")

    assert f"Central total: 12 calls, ${central:.4f}." in flat(stdout)


def test_ac_6c_the_dry_run_prints_the_wider_total_for_question_3(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6c (the wider USD figure, 24 calls)."""
    _, wider = by_hand("Requirements", "Feature design", "Requirements", "Feature design")

    _, stdout, _ = invoke(tmp_path, *QUESTION_3, "--ceiling", "20", "--dry-run")

    assert f"Wider total: 24 calls, ${wider:.4f}" in flat(stdout)


def test_ac_6c_every_wider_line_names_the_heaviest_measured_output_and_its_source(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6c (the wider figure's output assumption and its named source)."""
    _, stdout, _ = invoke(tmp_path, *QUESTION_3, "--ceiling", "20", "--dry-run")

    wider_lines = [line for line in stdout.splitlines() if line.strip().startswith("wider:")]
    assert len(wider_lines) == len(QUESTION_3)
    assert all(
        "39,234 output per call, the heaviest measured call (experiment 0005" in line
        for line in wider_lines
    )


def ceiling_reached_after_two_calls(fake_api: SimpleNamespace) -> float:
    """A ceiling the wider estimate fits under, which a heavy second call uses up."""
    heavy = Attempt(**{**settled().__dict__, "output_tokens": 200_000})
    fake_api.script = Script([first_call(), heavy, settled()])
    _, wider = by_hand("Requirements")
    return wider + 0.01


def test_ac_9_a_ceiling_stop_partway_is_said_plainly_through_the_command(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-9 (the stop wording names the unit, run and attempt it stopped before)."""
    ceiling = ceiling_reached_after_two_calls(fake_api)

    _, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", f"{ceiling:.4f}")

    assert "stopping here before 0002:Requirements run 3 attempt 1: ceiling" in flat(stderr)


def test_ac_9_a_ceiling_stop_partway_exits_1(tmp_path: Path, fake_api: SimpleNamespace) -> None:
    """covers: AC-9 (exit 1)."""
    ceiling = ceiling_reached_after_two_calls(fake_api)

    code, _, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", f"{ceiling:.4f}")

    assert code == 1
    assert len(fake_api.script.calls) == 2


def test_ac_5_a_retry_collision_stops_the_command_with_exit_1(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-5 (exit 1, before the retry is paid for)."""
    taken = tmp_path / RUNS_DIR / "0002" / "requirements" / "failed-run-1-attempt-2.json"
    taken.parent.mkdir(parents=True)
    taken.write_text("{}")
    fake_api.script = Script([failed(1), settled()])

    code, _, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert len(fake_api.script.calls) == 1


def test_ac_13_both_attempts_of_a_run_that_failed_after_its_retry_are_recorded(
    tmp_path: Path,
) -> None:
    """covers: AC-13 (the failed unit is recorded as it stands)."""
    script = Script([first_call(), failed(1), failed(2), settled()])

    run(tmp_path, script, "0002:Requirements", "0007:Requirements")

    names = sorted(p.name for p in (tmp_path / RUNS_DIR / "0002" / "requirements").iterdir())
    assert names == ["failed-run-2-attempt-1.json", "failed-run-2-attempt-2.json", "run-1.json"]


def test_ac_44_a_unit_failing_after_its_retry_exits_1_with_no_traceback(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-44 (the `UnitFailed` case, AC-13's stop through the command)."""
    fake_api.script = Script([first_call(), failed(1), failed(2)])

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "failed after its retry" in flat(stderr)
    assert "Traceback" not in stdout + stderr


def test_ac_44_extract_with_no_api_key_exits_1_naming_it_before_any_call(
    tmp_path: Path, fake_api: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """covers: AC-44 (the `SettingsInvalid` case in `extract`)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    code, stdout, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "ANTHROPIC_API_KEY" in stderr
    assert fake_api.built == 0
    assert "Traceback" not in stdout + stderr


# AC-48: a unit cut short is never resumed; running it again stops at the preflight.


def test_running_a_partial_unit_again_stops_at_the_collision_check(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    fake_api.script = Script([first_call(), settled(cache_read=0)])
    invoke(tmp_path, "0002:Requirements", "--ceiling", "20")
    fake_api.script = Script([settled() for _ in range(3)])

    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20")

    assert code == 1
    assert "already exists" in flat(stderr)
    assert fake_api.script.calls == []


# AC-49: the real call goes to the interactive streaming messages endpoint, not Batch.


def test_the_real_call_streams_from_the_messages_endpoint_not_batch() -> None:
    requests: list[httpx2.Request] = []
    body = recorded_stream(json.dumps(an_output().model_dump(mode="json")), 27_000)
    unit = resolve_address(SNAPSHOT, "0002:Requirements").unit

    attempt = calls_through(replaying_client(body, requests), SETTINGS)(unit, 1)

    assert attempt.output is not None
    [request] = requests
    assert request.url.path == "/v1/messages"
    assert json.loads(request.content)["stream"] is True


def test_the_count_sends_the_same_system_message_and_schema_as_the_call() -> None:
    requests: list[httpx2.Request] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"input_tokens": 61_108})

    fake = anthropic.Anthropic(
        api_key="sk-ant-test",
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
        max_retries=0,
    )
    unit = resolve_address(SNAPSHOT, "0014:Requirements").unit

    assert count_input(fake, SETTINGS, unit) == 61_108
    [request] = requests
    sent = json.loads(request.content)
    assert request.url.path == "/v1/messages/count_tokens"
    assert sent["system"][0]["cache_control"]["type"] == "ephemeral"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["messages"][0]["content"].startswith("Record: 0014\n")
