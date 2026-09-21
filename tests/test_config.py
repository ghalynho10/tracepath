import pytest

from tracepath import config
from tracepath.config import Neo4jSettings, load_neo4j_settings

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

    settings = load_neo4j_settings()

    assert (settings.uri, settings.username, settings.database) == (
        "bolt://localhost:7687",
        "neo4j",
        "neo4j",
    )


def test_settings_are_immutable() -> None:
    settings = Neo4jSettings(uri="bolt://x:1", username="u", password="p", database="d")

    with pytest.raises(AttributeError):
        settings.uri = "bolt://other:2"  # type: ignore[misc]
