"""Shared fixtures.

The database fixture builds a real ephemeral PostGIS database from db/schema.sql
rather than mocking it, because the queries under test are mostly PostGIS
(ST_DWithin, the GIST index) and a mock would prove nothing about them.

loop/verify.sh starts Docker and exits 2 before pytest runs if it cannot, so
these fixtures may assume the db container is up.
"""

import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEST_DB = "memorylane_test"


def _psql(db, sql):
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "memorylane", "-d", db, "-c", sql],
        cwd=ROOT, capture_output=True, text=True,
    )


@pytest.fixture(scope="session")
def db_url():
    """Create memorylane_test from db/schema.sql once per session."""
    _psql("memorylane", f"DROP DATABASE IF EXISTS {TEST_DB}")
    created = _psql("memorylane", f"CREATE DATABASE {TEST_DB}")
    if created.returncode != 0:
        pytest.fail(f"could not create {TEST_DB}: {created.stderr}")

    schema = (ROOT / "db" / "schema.sql").read_text()
    loaded = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "memorylane", "-d", TEST_DB],
        cwd=ROOT, input=schema, capture_output=True, text=True,
    )
    if loaded.returncode != 0:
        pytest.fail(f"could not load schema: {loaded.stderr}")

    yield f"postgresql+psycopg://memorylane:memorylane@localhost:5432/{TEST_DB}"
    _psql("memorylane", f"DROP DATABASE IF EXISTS {TEST_DB}")


@pytest.fixture
def db_session(db_url):
    """A session against the test DB, truncated between tests."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE content, transcripts, places, memories RESTART IDENTITY CASCADE"))
        conn.commit()

    session = sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def fake_anthropic():
    from tests.fakes import FakeAnthropic
    return FakeAnthropic()
