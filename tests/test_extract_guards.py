# ruff: noqa: F401, F811  (tests take the shared `fake_api` fixture, imported from the extract command tests)
"""Spec 0004's amendment of 2026-10-06: the per call bound, failures by kind, the dry
run over extracted units, and `extract --resume`. No paid call of any kind.

Three layers, each the cheapest that can show its claim:

* the metered run with a scripted call (`Script`, from the extract command tests);
* the real SDK over a mocked transport, for how `extract_once()` classifies a failure;
* the real command over real HTTP, against a fake local API behind a fault proxy
  (`tests/fake_api.py`), for the transport failure, resume and ceiling paths, the way
  `/check verify` drove them on 2026-10-06.
"""

import json
import math
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest
from typer.testing import CliRunner

from tests import fake_api as fake
from tests.test_extract_client import (
    FAILED_ATTEMPT,
    answering,
    dropping,
    first_events,
    recorded_stream,
    requirements_0021,
    settings_for,
)
from tests.test_extract_command import (
    BOUND,
    COUNTED,
    SETTINGS,
    SNAPSHOT,
    Script,
    failed,
    fake_api,
    first_call,
    flat,
    invoke,
    settled,
    targets,
)
from tracepath import cli, config
from tracepath.artifacts import (
    RUNS_DIR,
    artifact_payload,
    build_artifact,
    read_run,
    write_run,
)
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    Attempt,
    FailureKind,
    build_client,
)
from tracepath.extract.cost import attempt_cost, per_call_bound, recorded_cost
from tracepath.extract.metered import (
    Plan,
    ResumeRefused,
    RunOutcome,
    RunPlan,
    calls_through,
    fresh_runs,
    provenance_mismatch,
    resume_preflight,
    resume_runs,
    run_metered,
    summary_lines,
)
from tracepath.extract.units import Unit
from tracepath.rebuild import unit_passes

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()

TRANSPORT = FailureKind.TRANSPORT
MODEL = FailureKind.MODEL


def run(
    tmp_path: Path, script: Script, plans: list[Plan] | None = None, ceiling: float = 100.0
) -> RunOutcome:
    chosen = plans or [Plan(t, fresh_runs(3), BOUND) for t in targets("0002:Requirements")]
    return run_metered(
        chosen, script, SETTINGS, tmp_path, "2e40bcf", "2026-10-06T00:00:00+00:00", ceiling, print
    )


def dropped(number: int = 1) -> Attempt:
    """A call whose connection dropped before any usage arrived: a transport failure."""
    return failed(number, kind=TRANSPORT)


# AC-55: the per call bound.


def test_ac_55_the_bound_of_0010_context_is_max_tokens_output_its_input_and_one_write() -> None:
    """covers: AC-55. 57,559 counted: 65 uncached, 64,000 output, 57,494 written."""
    assert per_call_bound(57_559) == pytest.approx((65 * 2 + 64_000 * 10 + 57_494 * 4) / 1e6)


def test_ac_55_the_bound_of_0007_feature_design_is_0_8907() -> None:
    """covers: AC-55 (the figure the spec states for `0007 ## Feature design`)."""
    assert round(per_call_bound(67_865), 4) == 0.8907


# AC-10a: a failed attempt counts at its unit's bound.


def test_ac_10a_a_dropped_attempt_counts_at_the_bound_not_its_recorded_tokens() -> None:
    """covers: AC-10a."""
    assert attempt_cost(dropped(), 0.8701) == 0.8701


# AC-7b: the ceiling must be a finite number above 0.


@pytest.mark.parametrize("value", ["nan", "inf", "0", "-1"])
def test_ac_7b_a_ceiling_not_finite_and_above_0_exits_1_naming_the_flag(
    tmp_path: Path, fake_api: SimpleNamespace, value: str
) -> None:
    """covers: AC-7b."""
    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", value)

    assert code == 1
    assert "--ceiling" in stderr
    assert fake_api.built == 0, "before any call, count included"


# AC-8, AC-8b, AC-8c: the ceiling against one call's bound.


def test_ac_8_a_ceiling_below_the_bound_exits_1_before_any_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-8."""
    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "0.5")

    assert code == 1
    assert "below the largest per call bound" in flat(stderr)
    assert fake_api.script.calls == []


class CountsBySection:
    """A fake count endpoint that counts `0007 ## Feature design` higher than the rest."""

    def __init__(self) -> None:
        self.counted: list[str] = []

    def count_tokens(self, **request: Any) -> SimpleNamespace:
        content = request["messages"][0]["content"]
        if content.startswith("Record: 0014\n") and "Section: Requirements\n" in content:
            return SimpleNamespace(input_tokens=61_108)
        if content.startswith("Record: 0007\n") and "Section: Feature design\n" in content:
            return SimpleNamespace(input_tokens=70_000)
        return SimpleNamespace(input_tokens=COUNTED)


def test_ac_8_the_largest_bound_among_the_units_is_the_one_checked(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-8 (a ceiling the first unit's bound fits, the second's does not)."""
    fake_api.messages = CountsBySection()
    between = (per_call_bound(COUNTED) + per_call_bound(70_000)) / 2

    code, _, _ = invoke(
        tmp_path, "0002:Requirements", "0007:Feature design", "--ceiling", f"{between:.6f}"
    )

    assert code == 1
    assert fake_api.script.calls == []


def test_ac_8c_a_dry_run_below_the_bound_warns_and_exits_0(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-8c."""
    code, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "0.5", "--dry-run")

    assert code == 0
    assert "a real run would refuse to start" in flat(stdout)


# AC-6d, AC-6e: the dry run over a unit already extracted.


def extracted(tmp_path: Path, address: str = "0002:Requirements") -> None:
    """A unit with all three runs settled, written as a real run writes them."""
    [target] = targets(address)
    for n in (1, 2, 3):
        write(tmp_path, target.unit, target.section_slug, n, 1, settled())


def test_ac_6d_a_dry_run_over_an_extracted_unit_prints_the_estimate_and_exits_0(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6d."""
    extracted(tmp_path)

    code, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run")

    assert code == 0
    assert "Central total: 3 calls" in flat(stdout)


def test_ac_6e_a_dry_run_names_the_unit_a_real_run_would_refuse(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-6e."""
    extracted(tmp_path)

    _, stdout, _ = invoke(
        tmp_path, "0002:Requirements", "0007:Requirements", "--ceiling", "20", "--dry-run"
    )

    out = flat(stdout)
    assert "0002:Requirements: a real run would refuse it at the collision check" in out
    assert "0007:Requirements: a real run would refuse" not in out


# AC-11: the no cache stop's exception.


def test_ac_11_a_retry_writing_the_cache_after_a_call_that_reported_nothing_continues(
    tmp_path: Path,
) -> None:
    """covers: AC-11 (finding 1: a first call dropped on a cold cache)."""
    script = Script([dropped(1), first_call(), settled(), settled()])

    outcome = run(tmp_path, script)

    assert outcome.stop is None
    assert len(script.calls) == 4


# AC-67, AC-68, AC-69, AC-13: the run policy by failure kind.


def test_ac_68_a_run_whose_failures_are_all_transport_stays_owed(tmp_path: Path) -> None:
    """covers: AC-68."""
    outcome = run(tmp_path, Script([dropped(1), dropped(2)]))

    assert outcome.stop is not None
    assert "The run is owed" in outcome.stop


def test_ac_68_a_transport_failure_does_not_use_up_the_retry(tmp_path: Path) -> None:
    """covers: AC-68 (one model failure and one transport failure leave the run owed)."""
    outcome = run(tmp_path, Script([failed(1, kind=MODEL), dropped(2)]))

    assert outcome.stop is not None
    assert "with 1 model failures. The run is owed" in outcome.stop


def test_ac_69_one_command_makes_at_most_two_attempts_per_run(tmp_path: Path) -> None:
    """covers: AC-69."""
    script = Script([dropped(1), dropped(2), settled(), settled(), settled()])

    run(tmp_path, script)

    assert script.calls == [("0002:Requirements", 1), ("0002:Requirements", 2)]


def test_ac_13_two_model_failures_block_the_run_and_stop_the_command(tmp_path: Path) -> None:
    """covers: AC-13 (amended: two model failures)."""
    script = Script([failed(1, kind=MODEL), failed(2, kind=MODEL), settled()])

    outcome = run(tmp_path, script)

    assert outcome.stop is not None
    assert "failed after its retry (2 model failures)" in outcome.stop
    assert len(script.calls) == 2


def test_ac_70_the_built_client_has_the_sdks_retries_off() -> None:
    """covers: AC-70."""
    assert build_client(SETTINGS).max_retries == 0


def test_ac_67_an_http_error_status_is_a_transport_failure() -> None:
    """covers: AC-67 (an HTTP error status: the response never completed)."""
    overloaded = {"type": "error", "error": {"type": "overloaded_error", "message": "x"}}
    client = answering(lambda: httpx2.Response(529, json=overloaded))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert attempt.failure_kind is TRANSPORT


def test_ac_67_a_stream_ended_before_message_stop_is_a_transport_failure() -> None:
    """covers: AC-67 (the output arrived, the final usage and `message_stop` did not)."""
    body = recorded_stream('{"entities":[],"relationships":[]}', 80)
    client = answering(lambda: dropping(first_events(body, 4)))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert attempt.failure_kind is TRANSPORT


def test_ac_67_a_complete_response_failing_validation_is_a_model_failure() -> None:
    """covers: AC-67 (malformed or failing validation)."""
    raw = json.loads(FAILED_ATTEMPT.read_text())["raw_response"]
    client = answering(lambda: httpx2.Response(200, content=recorded_stream(raw, 8123)))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert attempt.failure_kind is MODEL


def test_ac_67_a_complete_response_stopped_at_max_tokens_is_a_model_failure() -> None:
    """covers: AC-67 (stopped at `max_tokens`, the output cut short)."""
    body = recorded_stream('{"entities": [', 64_000).replace(b'"end_turn"', b'"max_tokens"')
    client = answering(lambda: httpx2.Response(200, content=body))

    attempt = calls_through(client, settings_for())(requirements_0021(), 1)

    assert attempt.stop_reason == "max_tokens"
    assert attempt.failure_kind is MODEL


# AC-67b: the kind is recorded, and the four artifacts written before it read as model.


def test_ac_67b_a_failed_attempt_records_its_kind_in_its_artifact(tmp_path: Path) -> None:
    """covers: AC-67b."""
    [target] = targets("0002:Requirements")

    path = write(tmp_path, target.unit, target.section_slug, 1, 1, dropped())

    assert json.loads(path.read_text())["failure_kind"] == "transport"


COMMITTED_FAILED_ATTEMPTS = (
    "artifacts/runs/0021/requirements/failed-run-2-attempt-1.json",
    "artifacts/runs/0021/requirements/failed-run-2-attempt-2.json",
    "artifacts/superseded/2026-09-24-prompt-0002.3/0021/requirements/failed-run-1-attempt-1.json",
    "artifacts/superseded/2026-09-28-prompt-0002.3/0014/requirements/failed-run-1-attempt-1.json",
)


@pytest.mark.parametrize("relative", COMMITTED_FAILED_ATTEMPTS)
def test_ac_67b_each_committed_failed_attempt_without_a_kind_reads_as_model(
    relative: str,
) -> None:
    """covers: AC-67b (the closed set of four schema failures written before the field)."""
    path = ROOT / relative
    assert "failure_kind" not in json.loads(path.read_text())

    assert read_run(path).failure_kind is MODEL


def test_ac_67b_the_four_are_every_failed_attempt_without_a_kind_in_the_repo() -> None:
    """covers: AC-67b (the set is closed: no other committed failed attempt lacks a kind)."""
    found = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "artifacts").rglob("failed-*.json")
        if "failure_kind" not in json.loads(path.read_text())
    )

    assert found == sorted(COMMITTED_FAILED_ATTEMPTS)


# AC-14b: both totals.


def test_ac_14b_the_summary_prints_the_guards_total_and_the_recorded_total(
    tmp_path: Path,
) -> None:
    """covers: AC-14b."""
    outcome = run(tmp_path, Script([first_call(), dropped(1), settled(), settled()]))

    guard = attempt_cost(first_call(), BOUND) + BOUND + 2 * attempt_cost(settled(), BOUND)
    recorded = recorded_cost(first_call()) + 2 * recorded_cost(settled())
    assert (
        f"Spent ${guard:.4f} by the running total's rule (a failed attempt at its per call "
        f"bound), ${recorded:.4f} by the usage the artifacts recorded."
    ) in summary_lines(outcome)[0]


# --resume: the plan read from a unit's artifacts (AC-56 to AC-61).


def write(
    root: Path, unit: Unit, slug: str, run_number: int, number: int, attempt: Attempt
) -> Path:
    """Write one attempt the way the metered run writes it."""
    return write_run(
        root,
        build_artifact(
            unit=unit,
            section_slug=slug,
            run=run_number,
            attempt=number,
            output=attempt.output,
            model=SETTINGS.model,
            prompt_version=PROMPT_VERSION,
            commit="2e40bcf",
            extracted_at="2026-10-06T00:00:00+00:00",
            max_output_tokens=MAX_TOKENS,
            effort="medium",
            input_tokens=attempt.input_tokens,
            output_tokens=attempt.output_tokens,
            error=attempt.error,
            failure_kind=attempt.failure_kind,
        ),
    )


@pytest.fixture
def unit_dir(tmp_path: Path) -> Iterator[tuple[Path, Any]]:
    [target] = targets("0002:Requirements")
    yield tmp_path, target


def test_ac_57_a_run_with_no_artifact_is_owed_from_attempt_1(unit_dir: Any) -> None:
    """covers: AC-57."""
    root, target = unit_dir
    write(root, target.unit, target.section_slug, 1, 1, settled())

    assert resume_runs(root, target, 3) == (RunPlan(2, 1, 0), RunPlan(3, 1, 0))


def test_ac_56_an_owed_run_is_numbered_on_from_its_highest_attempt(unit_dir: Any) -> None:
    """covers: AC-56 (two transport failures, so attempt 3 is next)."""
    root, target = unit_dir
    for n in (1, 3):
        write(root, target.unit, target.section_slug, n, 1, settled())
    write(root, target.unit, target.section_slug, 2, 1, dropped(1))
    write(root, target.unit, target.section_slug, 2, 2, dropped(2))

    assert resume_runs(root, target, 3) == (RunPlan(2, 3, 0),)


def test_ac_58_a_settled_run_gets_no_attempt_whatever_failed_files_sit_beside_it(
    unit_dir: Any,
) -> None:
    """covers: AC-58 (settled)."""
    root, target = unit_dir
    write(root, target.unit, target.section_slug, 1, 1, failed(1, kind=MODEL))
    write(root, target.unit, target.section_slug, 1, 2, settled())

    assert [r.run for r in resume_runs(root, target, 3)] == [2, 3]


def test_ac_58_a_run_with_two_model_failures_blocks_the_unit(unit_dir: Any) -> None:
    """covers: AC-58 (blocked), with AC-59's refusal."""
    root, target = unit_dir
    write(root, target.unit, target.section_slug, 1, 1, failed(1, kind=MODEL))
    write(root, target.unit, target.section_slug, 1, 2, failed(2, kind=MODEL))

    with pytest.raises(ResumeRefused, match="is blocked: run 1 holds 2 model failures"):
        resume_runs(root, target, 3)


def test_ac_58b_a_missing_attempt_below_a_higher_one_is_unplannable(unit_dir: Any) -> None:
    """covers: AC-58b (a gap in the attempt numbers)."""
    root, target = unit_dir
    path = write(root, target.unit, target.section_slug, 2, 2, dropped(2))

    with pytest.raises(ResumeRefused, match="cannot be planned") as caught:
        resume_runs(root, target, 3)

    assert str(path) in str(caught.value)


def test_ac_58b_a_run_beyond_the_policys_three_is_unplannable(unit_dir: Any) -> None:
    """covers: AC-58b (a run number outside the run policy)."""
    root, target = unit_dir
    write(root, target.unit, target.section_slug, 4, 1, settled())

    with pytest.raises(ResumeRefused, match="outside 3 runs"):
        resume_runs(root, target, 3)


def test_ac_59_a_unit_with_every_run_settled_owes_nothing(unit_dir: Any) -> None:
    """covers: AC-59 (nothing owed)."""
    root, target = unit_dir
    extracted(root)

    with pytest.raises(ResumeRefused, match="owes nothing"):
        resume_runs(root, target, 3)


def test_ac_60_a_unit_with_no_artifact_is_refused_pointing_at_a_plain_extract(
    unit_dir: Any,
) -> None:
    """covers: AC-60."""
    root, target = unit_dir

    with pytest.raises(ResumeRefused, match="a plain `extract` starts it"):
        resume_runs(root, target, 3)


def test_ac_60b_settled_runs_at_another_prompt_version_are_named(unit_dir: Any) -> None:
    """covers: AC-60b."""
    root, target = unit_dir
    path = write(root, target.unit, target.section_slug, 1, 1, settled())
    payload = json.loads(path.read_text())
    payload["prompt_version"] = "0003.0"
    path.write_text(json.dumps(payload))

    found = provenance_mismatch(root, target, SETTINGS, "2e40bcf")

    assert found is not None
    assert f"prompt_version 0003.0 (now {PROMPT_VERSION})" in found


def test_ac_61_the_resume_preflight_stops_on_a_taken_next_attempt(unit_dir: Any) -> None:
    """covers: AC-61."""
    root, target = unit_dir
    taken = write(root, target.unit, target.section_slug, 2, 1, dropped(1))

    with pytest.raises(Exception, match="already exists") as caught:
        resume_preflight(root, [Plan(target, (RunPlan(2, 1, 0),), BOUND)])

    assert str(taken) in str(caught.value)


def test_ac_61b_a_resume_checks_each_attempt_before_it_is_paid_for(unit_dir: Any) -> None:
    """covers: AC-61b (attempt 4 of run 2 is taken, so it is never made)."""
    root, target = unit_dir
    write(root, target.unit, target.section_slug, 2, 4, dropped(4))
    script = Script([dropped(3), settled()])

    outcome = run(root, script, [Plan(target, (RunPlan(2, 3, 0),), BOUND)])

    assert len(script.calls) == 1
    assert outcome.stop is not None
    assert outcome.stop.startswith("stopping here before 0002:Requirements run 2 attempt 4:")


def test_ac_62_a_resume_checks_each_attempt_against_the_ceiling(unit_dir: Any) -> None:
    """covers: AC-62."""
    root, target = unit_dir
    script = Script([first_call(), settled()])
    ceiling = attempt_cost(first_call(), BOUND) + BOUND - 0.0001

    outcome = run(
        root, script, [Plan(target, (RunPlan(2, 1, 0), RunPlan(3, 1, 0)), BOUND)], ceiling
    )

    assert outcome.stop == "stopping here before 0002:Requirements run 3 attempt 1: ceiling"


# --resume through the command, with the scripted call (AC-59, AC-60, AC-63, AC-64).


def test_ac_59_the_command_refuses_a_resume_naming_every_unit_that_owes_nothing(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-59 (every such unit named, before any call)."""
    extracted(tmp_path, "0002:Requirements")
    extracted(tmp_path, "0007:Requirements")

    code, _, stderr = invoke(
        tmp_path, "0002:Requirements", "0007:Requirements", "--ceiling", "20", "--resume"
    )

    assert code == 1
    assert "0002:Requirements owes nothing" in flat(stderr)
    assert "0007:Requirements owes nothing" in flat(stderr)
    assert fake_api.script.calls == []


def test_ac_63_a_resume_prices_only_its_owed_runs(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-63 (two owed runs: 2 calls central, 4 wider)."""
    [target] = targets("0002:Requirements")
    write(tmp_path, target.unit, target.section_slug, 1, 1, settled())

    _, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run", "--resume")

    assert "Central total: 2 calls" in flat(stdout)
    assert "Wider total: 4 calls" in flat(stdout)


def test_ac_64_a_dry_resume_prints_its_plan_and_makes_no_extraction_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-64."""
    [target] = targets("0002:Requirements")
    write(tmp_path, target.unit, target.section_slug, 1, 1, settled())

    code, stdout, _ = invoke(
        tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run", "--resume"
    )

    assert code == 0
    assert "0002:Requirements resume: run 2 from attempt 1, run 3 from attempt 1." in flat(stdout)
    assert fake_api.script.calls == []


def test_ac_64b_a_dry_resume_exits_1_for_a_unit_a_real_resume_refuses(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-64b."""
    code, _, stderr = invoke(
        tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run", "--resume"
    )

    assert code == 1
    assert "has no artifact" in flat(stderr)


def test_ac_56_the_command_resumes_only_the_owed_runs_and_keeps_the_settled_one(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-56 through the command, with AC-61b (run 1's file is untouched)."""
    [target] = targets("0002:Requirements")
    kept = write(tmp_path, target.unit, target.section_slug, 1, 1, settled())
    before = kept.read_bytes()
    fake_api.script = Script([first_call(), settled()])

    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--resume")

    assert code == 0, stderr
    assert fake_api.script.calls == [("0002:Requirements", 1), ("0002:Requirements", 1)]
    assert kept.read_bytes() == before


# AC-65: each unit's extracted_at values.


def test_ac_65_a_resumed_unit_lists_both_passes_failed_files_included(tmp_path: Path) -> None:
    """covers: AC-65 (the first pass left only a failed file)."""
    [target] = targets("0002:Requirements")
    first = write(tmp_path, target.unit, target.section_slug, 1, 1, dropped(1))
    payload = json.loads(first.read_text())
    payload["extracted_at"] = "2026-10-05T10:00:00+00:00"
    first.write_text(json.dumps(payload))
    for n in (1, 2, 3):
        write(tmp_path, target.unit, target.section_slug, n, 2 if n == 1 else 1, settled())

    passes = unit_passes(tmp_path)

    assert passes[("0002", "requirements")] == (
        "2026-10-05T10:00:00+00:00",
        "2026-10-06T00:00:00+00:00",
    )


def test_ac_65_the_manifest_carries_each_units_passes() -> None:
    """covers: AC-65 (in `graph-build.json`, read from the committed artifacts)."""
    from tests.test_load_provenance import manifest_for

    units = manifest_for(ROOT)["units"]

    assert isinstance(units, list)
    by_unit = {(u["record"], u["section"]): u["extracted_at"] for u in units}
    assert by_unit[("0002", "Requirements")] == ["2026-10-05T21:38:39+00:00"]


# The transport failure, resume and ceiling paths over real HTTP: the real command and
# SDK against the fake API, with the fault proxy injecting the fault.


@pytest.fixture
def over_http(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_EFFORT", raising=False)
    yield


def extract_over_http(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    base_url: str,
    *args: str,
    at: str = "2026-10-06T00:00:00+00:00",
) -> tuple[int, str, str]:
    """Run `extract 0010:Context` through the proxy, every pass stamped `at`."""
    monkeypatch.setattr("tracepath.cli.now_utc", lambda: at)
    result = runner.invoke(
        cli.app,
        ["extract", "0010:Context", "--root", str(root), "--snapshot", str(SNAPSHOT), *args],
        env={"ANTHROPIC_BASE_URL": base_url},
    )
    return result.exit_code, result.stdout, result.stderr


def context_files(root: Path) -> list[str]:
    return sorted(p.name for p in (root / RUNS_DIR / "0010" / "context").glob("*.json"))


@pytest.mark.usefixtures("over_http")
def test_ac_11_over_http_a_first_call_dropped_before_usage_does_not_stop_the_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """covers: AC-11 (finding 1, replayed over HTTP: the retry writes the cache)."""
    with fake.fake_api_behind_proxy({1: fake.DROP_BEFORE_USAGE}) as (url, _, _):
        code, _, stderr = extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "3")

    assert code == 0, stderr
    assert context_files(tmp_path) == [
        "failed-run-1-attempt-1.json",
        "run-1.json",
        "run-2.json",
        "run-3.json",
    ]


@pytest.mark.usefixtures("over_http")
@pytest.mark.parametrize("fault", [fake.DROP_BEFORE_USAGE, fake.CUT_AFTER_OUTPUT, fake.OVERLOADED])
def test_ac_67_over_http_each_injected_fault_is_recorded_as_transport(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    """covers: AC-67 with AC-67b (dropped before usage, cut after output, a 529)."""
    with fake.fake_api_behind_proxy({1: fault}) as (url, _, _):
        extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "3")

    artifact = tmp_path / RUNS_DIR / "0010" / "context" / "failed-run-1-attempt-1.json"
    assert json.loads(artifact.read_text())["failure_kind"] == "transport"


@pytest.mark.usefixtures("over_http")
def test_ac_70_over_http_a_529_reaches_the_api_once_per_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """covers: AC-70 (no silent SDK retry: four attempts, four requests)."""
    with fake.fake_api_behind_proxy({1: fake.OVERLOADED}) as (url, api, proxy):
        extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "3")

    assert proxy.messages_calls == len(context_files(tmp_path)) == 4
    assert api.messages_calls == 3, "the 529 was the proxy's, never relayed"


@pytest.mark.usefixtures("over_http")
def test_ac_69_over_http_two_transport_failures_stop_the_command_with_the_run_owed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """covers: AC-69."""
    faults = {1: fake.DROP_BEFORE_USAGE, 2: fake.OVERLOADED}
    with fake.fake_api_behind_proxy(faults) as (url, _, _):
        code, _, stderr = extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "3")

    assert code == 1
    assert "run 1 is not settled after 2 attempts" in flat(stderr)
    assert "resume the unit with `extract --resume`" in flat(stderr)


@pytest.mark.usefixtures("over_http")
def test_ac_56_over_http_a_resume_completes_the_owed_run_from_attempt_3(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """covers: AC-56 (transport failures leave run 1 owed; the resume makes attempt 3)."""
    faults = {1: fake.DROP_BEFORE_USAGE, 2: fake.OVERLOADED}
    with fake.fake_api_behind_proxy(faults) as (url, _, _):
        extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "3")
    with fake.fake_api_behind_proxy({}) as (url, _, _):
        code, _, stderr = extract_over_http(
            monkeypatch, tmp_path, url, "--ceiling", "3", "--resume", at="2026-10-06T01:00:00+00:00"
        )

    assert code == 0, stderr
    settled_run = json.loads((tmp_path / RUNS_DIR / "0010" / "context" / "run-1.json").read_text())
    assert settled_run["attempt"] == 3
    assert unit_passes(tmp_path)[("0010", "context")] == (
        "2026-10-06T00:00:00+00:00",
        "2026-10-06T01:00:00+00:00",
    )


@pytest.mark.usefixtures("over_http")
def test_ac_9_over_http_the_ceiling_stops_the_command_before_a_call_its_bound_could_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """covers: AC-9 (bound $0.8701: after the first call writes the cache, about $0.23,
    a second call could pass a $1.00 ceiling, so it is not made)."""
    with fake.fake_api_behind_proxy({}) as (url, api, _):
        code, _, stderr = extract_over_http(monkeypatch, tmp_path, url, "--ceiling", "1")

    assert code == 1
    assert "stopping here before 0010:Context run 2 attempt 1: ceiling" in flat(stderr)
    assert api.messages_calls == 1


def test_the_fake_api_bound_is_the_bound_of_0010_context() -> None:
    """The fake counts `0010 Context` as the real endpoint did, so its bound is AC-55's."""
    assert math.isclose(per_call_bound(fake.COUNTED), 0.870106)


def test_a_failed_attempt_payload_writes_its_kind_as_a_string() -> None:
    """covers: AC-67b (the JSON shape)."""
    [target] = targets("0002:Requirements")
    artifact = build_artifact(
        unit=target.unit,
        section_slug=target.section_slug,
        run=1,
        attempt=1,
        output=None,
        model="claude-sonnet-5",
        prompt_version=PROMPT_VERSION,
        commit="2e40bcf",
        extracted_at="2026-10-06T00:00:00+00:00",
        max_output_tokens=MAX_TOKENS,
        effort="medium",
        input_tokens=None,
        output_tokens=None,
        failure_kind=MODEL,
    )

    assert artifact_payload(artifact)["failure_kind"] == "model"


# Claims the first pass left untested (`/test`, 2026-10-07).


def test_ac_60b_the_command_refuses_a_resume_at_another_prompt_before_any_call(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-60b (through the command: exit 1, no extraction call)."""
    [target] = targets("0002:Requirements")
    path = write(tmp_path, target.unit, target.section_slug, 1, 1, settled())
    payload = json.loads(path.read_text())
    payload["model"] = "claude-older-model"
    path.write_text(json.dumps(payload))

    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--resume")

    assert code == 1
    assert "model claude-older-model (now claude-sonnet-5)" in flat(stderr)
    assert fake_api.script.calls == []


def test_ac_59_the_command_names_a_blocked_unit_as_blocked(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-59 ("which it is": blocked, not owing nothing)."""
    [target] = targets("0002:Requirements")
    write(tmp_path, target.unit, target.section_slug, 1, 1, failed(1, kind=MODEL))
    write(tmp_path, target.unit, target.section_slug, 1, 2, failed(2, kind=MODEL))

    code, _, stderr = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--resume")

    assert code == 1
    assert "0002:Requirements is blocked: run 1 holds 2 model failures" in flat(stderr)


def test_ac_64_a_dry_resume_prints_each_units_counted_input(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-64 (with the AC-6b counts)."""
    [target] = targets("0002:Requirements")
    write(tmp_path, target.unit, target.section_slug, 1, 1, settled())

    _, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "20", "--dry-run", "--resume")

    assert f"0002:Requirements: {COUNTED:,} input tokens counted, 57,494 cached prefix" in flat(
        stdout
    )


def test_ac_64_a_dry_resume_prints_the_may_stop_partway_warning(
    tmp_path: Path, fake_api: SimpleNamespace
) -> None:
    """covers: AC-64 (with the AC-8b warning, the wider total above a $1 ceiling)."""
    [target] = targets("0002:Requirements")
    write(tmp_path, target.unit, target.section_slug, 1, 1, settled())

    _, stdout, _ = invoke(tmp_path, "0002:Requirements", "--ceiling", "1", "--dry-run", "--resume")

    assert "may stop partway at the ceiling" in flat(stdout)


def test_ac_56_a_resume_makes_at_most_two_attempts_per_owed_run(unit_dir: Any) -> None:
    """covers: AC-56 (the AC-69 limit holds on a resume: attempts 3 and 4, then a stop)."""
    root, target = unit_dir
    script = Script([dropped(3), dropped(4), settled()])

    outcome = run(root, script, [Plan(target, (RunPlan(2, 3, 0),), BOUND)])

    assert script.calls == [("0002:Requirements", 3), ("0002:Requirements", 4)]
    assert outcome.stop is not None and "The run is owed" in outcome.stop
