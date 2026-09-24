import pytest

from tracepath import config
from tracepath.config import (
    Neo4jSettings,
    SettingsInvalid,
    load_anthropic_settings,
    load_neo4j_settings,
)

NEO4J_VARS = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")


def test_reads_every_setting_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://graph.example:7777")
    monkeypatch.setenv("NEO4J_USERNAME", "reader")
    monkeypatch.setenv("NEO4J_PASSWORD", "s3cret-pass")
    monkeypatch.setenv("NEO4J_DATABASE", "corpus")

    settings = load_neo4j_settings()

    assert settings == Neo4jSettings(
        uri="bolt://graph.example:7777",
        username="reader",
        password="s3cret-pass",
        database="corpus",
    )


def test_uses_local_defaults_for_uri_username_and_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep the developer's real .env out of this test (filesystem boundary).
    monkeypatch.setattr(config, "load_dotenv", lambda: False)
    for name in NEO4J_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NEO4J_PASSWORD", "s3cret-pass")

    settings = load_neo4j_settings()

    assert (settings.uri, settings.username, settings.database) == (
        "bolt://localhost:7687",
        "neo4j",
        "neo4j",
    )


def test_missing_password_raises_settings_invalid_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    with pytest.raises(SettingsInvalid, match="NEO4J_PASSWORD") as caught:
        load_neo4j_settings()

    assert ".env" in str(caught.value)


def test_empty_password_raises_settings_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: False)
    monkeypatch.setenv("NEO4J_PASSWORD", "")

    with pytest.raises(SettingsInvalid, match="NEO4J_PASSWORD"):
        load_neo4j_settings()


def test_settings_are_immutable() -> None:
    settings = Neo4jSettings(uri="bolt://x:1", username="u", password="p", database="d")

    with pytest.raises(AttributeError):
        settings.uri = "bolt://other:2"  # type: ignore[misc]


def test_effort_defaults_to_the_decided_medium(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec 0001's run policy decides `medium`; unset must not mean the model default.

    Unset used to fall through to the model's own default, `high`, which is exactly
    how the first runs came to use `high` by accident rather than by choice.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_EFFORT", raising=False)

    assert load_anthropic_settings().effort == "medium"


def test_an_explicit_effort_still_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "low")

    assert load_anthropic_settings().effort == "low"
