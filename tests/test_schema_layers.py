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
import subprocess

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


def test_the_migration_agrees_with_the_schema(db_session, db_url):
    """Fresh databases get these columns from schema.sql, existing ones from the
    migration. If the two drift, a deploy differs from a laptop and nothing says so.

    db_session built this database from schema.sql, so replaying the migration on
    top must be a no-op.
    """
    before = _columns(db_session, "memories") | _columns(db_session, "content")

    replay = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "memorylane",
            "-d",
            db_url.rsplit("/", 1)[-1],
            "-v",
            "ON_ERROR_STOP=1",
        ],
        cwd=ROOT,
        input=MIGRATION.read_text(),
        capture_output=True,
        text=True,
    )
    assert replay.returncode == 0, replay.stderr

    db_session.commit()
    after = _columns(db_session, "memories") | _columns(db_session, "content")
    assert after == before, f"migration added columns schema.sql lacks: {after - before}"
