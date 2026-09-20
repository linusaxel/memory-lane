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

# Per-process, because more than one pytest run can share this Postgres - two
# sessions working the same repo, or xdist workers. A fixed name means one run's
# session teardown DROPs the database another run is still using, and the second
# fails with "database memorylane_test does not exist" nowhere near the cause.
TEST_DB = f"memorylane_test_{os.getpid()}"


def _psql(db, sql):
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "memorylane", "-d", db, "-c", sql],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _drop_test_db():
    """WITH (FORCE) terminates lingering backends, and the result is checked.

    Both halves matter. A plain DROP fails while any connection to the database
    is still open - which is exactly what happens when the gate runs twice in
    quick succession, because the previous run's pooled connections have not
    been reaped yet. The old code discarded the DROP's return code, so the
    failure was silent and surfaced as CREATE reporting "already exists",
    erroring every db-marked test. The gate was flaky, not the tests.
    """
    dropped = _psql("memorylane", f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    if dropped.returncode != 0:
        pytest.fail(f"could not drop {TEST_DB}: {dropped.stderr}")


@pytest.fixture(scope="session")
def db_url():
    """Create memorylane_test from db/schema.sql once per session."""
    _drop_test_db()
    created = _psql("memorylane", f"CREATE DATABASE {TEST_DB}")
    if created.returncode != 0:
        pytest.fail(f"could not create {TEST_DB}: {created.stderr}")

    schema = (ROOT / "db" / "schema.sql").read_text()
    loaded = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "memorylane", "-d", TEST_DB],
        cwd=ROOT,
        input=schema,
        capture_output=True,
        text=True,
    )
    if loaded.returncode != 0:
        pytest.fail(f"could not load schema: {loaded.stderr}")

    yield f"postgresql+psycopg://memorylane:memorylane@localhost:5432/{TEST_DB}"
    _drop_test_db()


@pytest.fixture
def db_session(db_url):
    """A session against the test DB, truncated between tests."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(
            text("TRUNCATE content, transcripts, places, memories RESTART IDENTITY CASCADE")
        )
        conn.commit()

    session = sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def ingest_into(db_session, monkeypatch):
    """Point pipeline.ingest at the ephemeral test database.

    Not optional. The ingest functions open their own session through
    pipeline.db, which reads DATABASE_URL and therefore points at the real
    database - a db-marked test that forgets this writes to production and
    passes while doing it. Shared from here so there is one copy to get right.
    """
    from contextlib import contextmanager

    from pipeline import ingest

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(ingest, "get_session", _session)
    return db_session


@pytest.fixture
def fake_anthropic():
    from tests.fakes import FakeAnthropic

    return FakeAnthropic()
