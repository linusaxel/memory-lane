"""Bring a database up to db/schema.sql, and record what it applied.

    python -m pipeline.migrate

An empty database gets schema.sql and every migration recorded as applied. An
existing one gets each migration not yet in `schema_migrations`, in order.
Every migration but 001 replays as a no-op on a database that already has it
(tests/test_schema_layers.py), so a database that predates the table is simply
replayed. The Dockerfile runs this before the API starts.
"""

import pathlib

import psycopg

from pipeline.db import DATABASE_URL

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"

# Deploys can overlap; only one runs migrations at a time.
LOCK = 20260929


def migrate(url: str = DATABASE_URL) -> list[str]:
    """Apply what is missing; return the names applied."""
    names = sorted(m.name for m in MIGRATIONS.glob("*.sql"))
    with psycopg.connect(url.replace("+psycopg", ""), autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK,))
        if conn.execute("SELECT to_regclass('public.places')").fetchone()[0] is None:
            conn.execute((ROOT / "db" / "schema.sql").read_text())
            _record(conn, names)
            return ["schema.sql"]
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
        # 001 is a one-time merge ending in a bare CREATE UNIQUE INDEX; its index
        # says it ran, and schema.sql has it too.
        if conn.execute("SELECT to_regclass('public.idx_places_place_query')").fetchone()[0]:
            done |= {n for n in names if n.startswith("001")}
        applied = [n for n in names if n not in done]
        for name in applied:
            # Autocommit, so a migration's own BEGIN/COMMIT (001, 002) holds.
            # A crash before its row is written re-runs it, which is a no-op.
            conn.execute((MIGRATIONS / name).read_text())
            print(f"applied {name}")
        _record(conn, names)
        return applied


def _record(conn, names):
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO schema_migrations (name) VALUES (%s) ON CONFLICT DO NOTHING",
            [(n,) for n in names],
        )


if __name__ == "__main__":
    print(f"{len(migrate())} applied")
