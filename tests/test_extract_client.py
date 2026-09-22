from pathlib import Path

import pytest

from tracepath.config import DEFAULT_MODEL, RUNS_PER_UNIT, SettingsInvalid, load_anthropic_settings
from tracepath.extract.client import (
    MAX_TOKENS,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    user_prompt,
)
from tracepath.extract.units import split_units

SNAPSHOT = Path(__file__).resolve().parents[1] / "corpus" / "jobhunt" / "docs"


# A missing key fails at startup, not at the first call.


def test_a_missing_api_key_fails_with_a_message_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(SettingsInvalid) as caught:
        load_anthropic_settings()

    assert "ANTHROPIC_API_KEY" in str(caught.value)
    assert ".env.example" in str(caught.value)


def test_an_empty_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    with pytest.raises(SettingsInvalid):
        load_anthropic_settings()


def test_settings_carry_the_model_and_run_policy_the_spec_chose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

    settings = load_anthropic_settings()

    assert settings.model == DEFAULT_MODEL == "claude-sonnet-5"
    assert settings.runs_per_unit == RUNS_PER_UNIT == 3


def test_the_model_can_be_overridden_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("tracepath.config.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5")

    assert load_anthropic_settings().model == "claude-opus-5"


def test_the_example_env_file_names_the_key_so_a_fresh_clone_knows_to_set_it() -> None:
    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text()

    assert "ANTHROPIC_API_KEY" in example


# The prompt and the message are built from the unit, with no schema of their own.


def test_the_prompt_carries_the_unit_and_everything_a_citation_needs() -> None:
    path = SNAPSHOT / "specs" / "0012-model-client-router" / "index.md"
    unit = next(
        u
        for u in split_units("specs/0012-model-client-router/index.md", path.read_text())
        if u.section == "Requirements"
    )

    message = user_prompt(unit)

    assert "0012" in message
    assert "Requirements" in message
    assert unit.text in message


def test_the_prompt_tells_the_model_not_to_own_identity_or_the_markers() -> None:
    assert "Never invent an id" in SYSTEM_PROMPT
    assert "derived:N" in SYSTEM_PROMPT
    assert "read from the characters by code" in SYSTEM_PROMPT
    assert "unclassified" in SYSTEM_PROMPT


def test_the_prompt_version_is_recorded_so_a_prompt_change_is_visible() -> None:
    assert PROMPT_VERSION
    assert MAX_TOKENS >= 16000
