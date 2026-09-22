"""Settings loaded from the environment, with a local `.env` file read first."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

#: The model spec 0001 chose for extraction. Its judgement heavy calls are what the
#: known trap flags exist to catch, so a smaller model is not a drop in swap.
DEFAULT_MODEL = "claude-sonnet-5"

#: Runs per unit, from spec 0001's run policy. The run comparator's whole signal is
#: the variation between these, so there is no point running fewer.
RUNS_PER_UNIT = 3


class SettingsInvalid(Exception):
    """A required setting is missing or empty."""


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection settings for the Neo4j graph store."""

    uri: str
    username: str
    password: str
    database: str


@dataclass(frozen=True)
class AnthropicSettings:
    """Settings for the model calls extraction makes."""

    api_key: str
    model: str
    runs_per_unit: int


def load_anthropic_settings() -> AnthropicSettings:
    """Read the Anthropic settings from the environment, after loading `.env`.

    Checked at startup rather than at the first call, so a missing key fails before
    any work starts instead of part way through a run.

    Raises:
        SettingsInvalid: ANTHROPIC_API_KEY is unset or empty.
    """
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SettingsInvalid(
            "ANTHROPIC_API_KEY is not set. Add it to `.env` (see `.env.example`)."
        )
    return AnthropicSettings(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
        runs_per_unit=RUNS_PER_UNIT,
    )


def load_neo4j_settings() -> Neo4jSettings:
    """Read the Neo4j settings from the environment, after loading `.env`.

    Raises:
        SettingsInvalid: NEO4J_PASSWORD is unset or empty.
    """
    load_dotenv()
    password = os.getenv("NEO4J_PASSWORD", "")
    if not password:
        raise SettingsInvalid("NEO4J_PASSWORD is not set. Add it to `.env` (see `.env.example`).")
    return Neo4jSettings(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=password,
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
