"""Settings loaded from the environment, with a local `.env` file read first."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection settings for the Neo4j graph store."""

    uri: str
    username: str
    password: str
    database: str


def load_neo4j_settings() -> Neo4jSettings:
    """Read the Neo4j settings from the environment, after loading `.env`."""
    load_dotenv()
    return Neo4jSettings(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", ""),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
