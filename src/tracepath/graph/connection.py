"""Access to the Neo4j graph store."""

import logging

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from tracepath.config import Neo4jSettings

log = logging.getLogger(__name__)


class GraphUnavailable(Exception):
    """Neo4j could not be reached or refused the credentials."""


def connect(settings: Neo4jSettings) -> Driver:
    """Open a driver and confirm the database answers, or raise GraphUnavailable."""
    log.debug("connecting to %s (database %s)", settings.uri, settings.database)
    driver = GraphDatabase.driver(settings.uri, auth=(settings.username, settings.password))
    try:
        driver.verify_connectivity()
    except ServiceUnavailable as exc:
        driver.close()
        log.debug("connection failed", exc_info=exc)
        raise GraphUnavailable(
            f"Neo4j is not reachable at {settings.uri}. Start it with `docker compose up -d`."
        ) from None
    except AuthError as exc:
        driver.close()
        log.debug("authentication failed", exc_info=exc)
        raise GraphUnavailable(
            "Neo4j rejected the credentials. Check NEO4J_USERNAME and NEO4J_PASSWORD in `.env`."
        ) from None
    return driver


def server_version(driver: Driver, database: str) -> str:
    """Return the Neo4j server version, e.g. `5.26.30`."""
    records, _, _ = driver.execute_query(
        "CALL dbms.components() YIELD versions RETURN versions[0] AS version",
        database_=database,
    )
    return str(records[0]["version"])
