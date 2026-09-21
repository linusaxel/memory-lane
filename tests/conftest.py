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
        # Discovered rather than listed. The list used to be hardcoded, and the
        # first table added after it was written (devices) leaked between tests:
        # unlocks was reached through a cascade from memories, devices was not,
        # and a test asserting "no devices yet" passed alone and failed in a
        # file. A list that has to be maintained is one somebody will not.
        #
        # spatial_ref_sys belongs to PostGIS and lives in public; truncating it
        # takes the coordinate systems with it.
        tables = conn.execute(
            text("""
                SELECT string_agg(quote_ident(tablename), ', ')
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename <> 'spatial_ref_sys'
            """)
        ).scalar()
        if tables:
            conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
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


@pytest.fixture
def api_client(db_session, monkeypatch, tmp_path):
    """A TestClient wired to the ephemeral database.

    The patching is **discovered, not listed**. Every module under `api/` that
    holds a `get_session` gets it replaced. A list would be one import away from
    wrong, and the failure is silent: `api.card` binds `get_session` at import,
    so patching `api.main` alone once left the card route on the live database -
    that looked like a passing gate test and was actually a 404. The same trap
    reopens every time a module is split out of `api.main`.

    `api.media.MEDIA_DIR` is redirected too, so uploads land in tmp_path and not
    in the repo. The session rolls back on an exception the way
    `pipeline.db.get_session` does; without that a refused write leaves its
    half-written rows behind in the test and nowhere else.
    """
    import importlib
    import pkgutil
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    import api
    import api.main
    import api.media

    @contextmanager
    def _session():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    patched = []
    for info in pkgutil.iter_modules(api.__path__):
        module = importlib.import_module(f"api.{info.name}")
        if hasattr(module, "get_session"):
            monkeypatch.setattr(module, "get_session", _session)
            patched.append(info.name)
    assert patched, "no api module exposes get_session - did the import path move?"

    monkeypatch.setattr(api.media, "MEDIA_DIR", tmp_path)

    # /v1/stats answers from a process-wide cache, and these tests share a
    # process - without this one test reads the corpus another one seeded.
    import api.read

    api.read.reset_stats_cache()

    return TestClient(api.main.app)
