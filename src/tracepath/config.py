"""Settings loaded from the environment, with a local `.env` file read first."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class SettingsInvalid(Exception):
    """A required setting is missing or empty."""


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection settings for the Neo4j graph store."""

    uri: str
    username: str
    password: str
    database: str


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
