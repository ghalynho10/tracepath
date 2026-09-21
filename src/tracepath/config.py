"""Settings loaded from the environment, with a local `.env` file read first."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    username: str
    password: str
    database: str


def load_neo4j_settings() -> Neo4jSettings:
    load_dotenv()
    return Neo4jSettings(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", ""),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
