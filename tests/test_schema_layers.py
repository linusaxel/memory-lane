"""The three content layers, event dates, attribution and contrast scores.

The product is historical / friend / stranger content ranked by contrast rather
than distance. None of that had anywhere to live: memories could say where a
story sits in a video but not when the thing happened, carried no attribution of
its own, and had no score to order by.

Two things are worth asserting here and nothing else is. The CHECK on `layer` is
load-bearing - the layers must never render at equal weight, and a typo that
slips past the constraint silently hides content. And db/schema.sql must agree
with db/migrations/002_layers.sql, because fresh databases get the columns from
one and existing ones from the other; drift between them is invisible until a
deploy behaves differently from a laptop.
"""

import pathlib

import psycopg
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "db" / "migrations" / "002_layers.sql"


def _columns(session, table):
    rows = session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table},
    ).fetchall()
    return {r[0] for r in rows}


def _place_and_content(session):
    place_id = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates) "
            "VALUES ('Vega', 'Vega Copenhagen', ST_MakePoint(12.5379, 55.6668)::geography) "
            "RETURNING id"
        )
    ).scalar()
    content_id = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://example.org/a', 'archive', 'a') RETURNING id"
        )
    ).scalar()
    return place_id, content_id


def _insert_memory(session, **kw):
    place_id, content_id = _place_and_content(session)
    cols = {"place_id": place_id, "content_id": content_id, "timestamp_start": 0.0, "summary": "s"}
    cols.update(kw)
    names = ", ".join(cols)
    binds = ", ".join(f":{k}" for k in cols)
    return session.execute(
        text(f"INSERT INTO memories ({names}) VALUES ({binds}) RETURNING id"), cols
    ).scalar()


def test_a_memory_defaults_to_the_historical_layer(db_session):
    """Everything extracted before layers existed is public, permanent content."""
    memory_id = _insert_memory(db_session)
    layer = db_session.execute(
        text("SELECT layer FROM memories WHERE id = :i"), {"i": memory_id}
    ).scalar()
    assert layer == "historical"


@pytest.mark.parametrize("layer", ["historical", "friend", "stranger"])
def test_the_three_layers_are_accepted(db_session, layer):
    assert _insert_memory(db_session, layer=layer)


def test_a_layer_outside_the_three_is_rejected(db_session):
    """Not merely unused - an unknown layer would escape the rendering rules."""
    with pytest.raises(Exception, match="memories_layer_check"):
        _insert_memory(db_session, layer="public")


def test_a_nonsense_date_precision_is_rejected(db_session):
    with pytest.raises(Exception, match="memories_happened_precision_check"):
        _insert_memory(db_session, happened_at="1978-01-01", happened_precision="ish")


def test_when_it_happened_is_separate_from_where_it_sits_in_a_video(db_session):
    """A 1978 gig at timestamp 0 of a 2024 recording. Both facts must survive."""
    memory_id = _insert_memory(
        db_session, timestamp_start=0.0, happened_at="1978-06-17", happened_precision="day"
    )
    row = db_session.execute(
        text("SELECT timestamp_start, happened_at FROM memories WHERE id = :i"), {"i": memory_id}
    ).fetchone()
    assert row.timestamp_start == 0.0
    assert str(row.happened_at) == "1978-06-17"


def test_content_defaults_to_video(db_session):
    """Only video rows have a transcript; the flags stop meaning anything otherwise."""
    source_type = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://example.org/b', 'archive', 'b') RETURNING source_type"
        )
    ).scalar()
    assert source_type == "video"


def _replay(migration: pathlib.Path, db_url: str):
    """psycopg rather than `docker compose exec psql`: that was 0.3 s a migration."""
    with psycopg.connect(db_url.replace("+psycopg", ""), autocommit=True) as conn:
        conn.execute(migration.read_text())


def _shape(session):
    """Every table and column in the public schema."""
    rows = session.execute(
        text("""
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'public'
        """)
    ).fetchall()
    return {(r[0], r[1]) for r in rows}


# 001 is excluded: it is a one-time data merge whose `CREATE UNIQUE INDEX` is
# bare, so replaying it on a database that already has the index is an error
# rather than a no-op. Its schema half is asserted separately below.
REPLAYABLE = sorted(
    m for m in (ROOT / "db" / "migrations").glob("*.sql") if not m.name.startswith("001")
)


@pytest.mark.parametrize("migration", REPLAYABLE, ids=lambda m: m.stem)
def test_every_migration_agrees_with_the_schema(migration, db_session, db_url):
    """Fresh databases get their shape from schema.sql, existing ones from the
    migrations. If the two drift, a deploy differs from a laptop and nothing
    says so until something behaves differently in production.

    db_session built this database from schema.sql, so replaying any migration
    on top of it must change nothing. Parametrized rather than written once for
    002, because the argument applies to every migration and 003 through 007
    went unguarded - including the two that added six tables.
    """
    before = _shape(db_session)

    _replay(migration, db_url)

    db_session.commit()
    after = _shape(db_session)
    assert after == before, (
        f"{migration.name} changes a database built from schema.sql.\n"
        f"only in the migration: {sorted(after - before)}\n"
        f"only in schema.sql:    {sorted(before - after)}"
    )


def test_the_dev_database_has_every_migration(db_session, db_url):
    """Nothing records which migrations a database has. The dev DB once lacked
    010, so search 500'd locally while every test, built from schema.sql,
    passed. Comparing it to the schema is the check that would have said so."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    with Session(create_engine(db_url.rsplit("/", 1)[0] + "/memorylane")) as dev:
        dev_shape = _shape(dev)
    schema_shape = _shape(db_session)
    assert dev_shape == schema_shape, (
        "the dev database differs from db/schema.sql: run python -m pipeline.migrate.\n"
        f"missing from dev: {sorted(schema_shape - dev_shape)}\n"
        f"only in dev:      {sorted(dev_shape - schema_shape)}"
    )


def test_the_places_unique_index_is_in_the_schema_too(db_session):
    """001's half that is not replayable. Without this index the ON CONFLICT in
    save_memories is a silent no-op and every memory mints a duplicate place."""
    found = db_session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'places'")
    ).fetchall()
    assert "idx_places_place_query" in {r[0] for r in found}


def test_migrate_builds_an_empty_database_and_replays_an_existing_one(db_session, db_url):
    """The deploy path: Railway's database starts empty, a dev one predates
    schema_migrations. Both end in schema.sql's shape with every file recorded,
    and a second run applies nothing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from pipeline.migrate import MIGRATIONS, migrate

    every = {m.name for m in MIGRATIONS.glob("*.sql")}
    admin = db_url.rsplit("/", 1)[0].replace("+psycopg", "") + "/memorylane"
    fresh = db_url + "_fresh"
    name = fresh.rsplit("/", 1)[1]
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {name}")
    try:
        assert migrate(fresh) == ["schema.sql"]
        assert migrate(fresh) == []
        engine = create_engine(fresh)
        with Session(engine) as s:
            assert _shape(s) == _shape(db_session)
            recorded = {r[0] for r in s.execute(text("SELECT name FROM schema_migrations"))}
        engine.dispose()
        assert recorded == every
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")

    db_session.commit()
    assert "001_places_unique.sql" not in migrate(db_url)
    assert migrate(db_url) == []
