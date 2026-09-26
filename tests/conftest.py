"""Shared fixtures.

The database fixture builds a real ephemeral PostGIS database from db/schema.sql
rather than mocking it, because the queries under test are mostly PostGIS
(ST_DWithin, the GIST index) and a mock would prove nothing about them.

loop/verify.sh starts Docker and exits 2 before pytest runs if it cannot, so
these fixtures may assume the db container is up.
"""

import os
import pathlib
import random
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Offline and crow-flies, whatever a developer's .env says: load_dotenv never
# overrides a variable already set, and the solver tests assert crow-flies
# metres. A test that wants streets monkeypatches api.streets itself.
os.environ["ROUTING_URL"] = ""

# Per-process, because more than one pytest run can share this Postgres - two
# sessions working the same repo, or xdist workers. A fixed name means one run's
# session teardown DROPs the database another run is still using, and the second
# fails with "database memorylane_test does not exist" nowhere near the cause.
TEST_DB = f"memorylane_test_{os.getpid()}"

# The random route instances, new ones every run. A red run names the seed that
# replays it: ROUTE_SEED=<n>.
_seed = os.environ.get("ROUTE_SEED", "random")
ROUTE_SEED = random.randrange(2**32) if _seed == "random" else int(_seed)


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """Only `live` tests leave this machine. A fake that covered one crawler
    call but not its sibling had eight ingest tests asking YouTube about
    `@test`, a second each, passing either way."""
    if request.node.get_closest_marker("live"):
        return
    import socket

    connect = socket.socket.connect

    def _local_only(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in (
            "127.0.0.1",
            "::1",
            "localhost",
        ):
            raise RuntimeError(f"network in an unmarked test: {address}; mark it live or fake it")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", _local_only)


@pytest.fixture
def route_seed():
    return ROUTE_SEED


def pytest_terminal_summary(terminalreporter, exitstatus):
    if exitstatus:
        terminalreporter.write_line(f"ROUTE_SEED={ROUTE_SEED} replays the random route instances")


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

    # Negative tests break constraints on purpose and the teardown's FORCE kills
    # pooled backends; pytest reports what matters, and in the db log it read as
    # ~950 errors hiding the one real one.
    schema = f"ALTER DATABASE {TEST_DB} SET log_min_messages = panic;\n"
    schema += (ROOT / "db" / "schema.sql").read_text()
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


@pytest.fixture(scope="session")
def db_engine(db_url):
    """One pool for the run: a new connection is ~20 ms, and a per-test engine
    paid it on every db test. Disposed before db_url drops the database."""
    from sqlalchemy import create_engine

    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """A session against the test DB, emptied between tests."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    with db_engine.connect() as conn:
        # Discovered rather than listed. The list used to be hardcoded, and the
        # first table added after it was written (devices) leaked between tests:
        # unlocks was reached through a cascade from memories, devices was not,
        # and a test asserting "no devices yet" passed alone and failed in a
        # file. A list that has to be maintained is one somebody will not.
        #
        # spatial_ref_sys belongs to PostGIS and lives in public; emptying it
        # takes the coordinate systems with it.
        #
        # DELETE rather than TRUNCATE: TRUNCATE rewrites every table's files,
        # ~23 ms a test against ~3. The replica role skips the
        # foreign keys, so the order does not matter.
        conn.execute(
            text("""
                DO $$
                DECLARE r record;
                BEGIN
                    SET LOCAL session_replication_role = replica;
                    FOR r IN SELECT tablename FROM pg_tables
                             WHERE schemaname = 'public' AND tablename <> 'spatial_ref_sys' LOOP
                        EXECUTE format('DELETE FROM %I', r.tablename);
                    END LOOP;
                    FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' LOOP
                        EXECUTE format('ALTER SEQUENCE %I RESTART', r.sequencename);
                    END LOOP;
                END $$
            """)
        )
        conn.commit()

    session = sessionmaker(bind=db_engine)()
    try:
        yield session
        session.commit()
    finally:
        session.close()


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
    in the repo. The session commits on success and rolls back on an exception
    the way `pipeline.db.get_session` does; without the rollback a refused write
    leaves its half-written rows behind, and without the commit a 404 rolls back
    every earlier request's writes with it.
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
            db_session.commit()
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


def on_todays_route(session, device, *memory_ids):
    """Make these memories stops of `device`'s walk today. The unlock refuses
    anything else, so a test that unlocks outside a planned walk states it."""
    from sqlalchemy import text

    from api.gate import today

    session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT DO NOTHING"),
        {"d": device},
    )
    session.execute(
        text("""
            INSERT INTO daily_routes (device_id, route_date, memory_ids)
            VALUES (CAST(:d AS uuid), :day, :ids)
            ON CONFLICT (device_id, route_date) WHERE ended_at IS NULL
            DO UPDATE SET memory_ids = daily_routes.memory_ids || EXCLUDED.memory_ids
        """),
        {"d": device, "day": today(), "ids": list(memory_ids)},
    )
    session.commit()
