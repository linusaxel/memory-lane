"""How the read path behaves on a corpus bigger than the one we have.

    python -m pipeline.perf              # 50k memories, 20k places
    python -m pipeline.perf --rows 200000

In `pipeline/` because that is where this project keeps the tools you run by
hand and read the output of - `quality.py` scores summaries, `dedup.py`
proposes merges, this one times queries. None of them belong in the gate: they
take minutes and their output is a judgement, not a pass or a fail.

It builds a throwaway database, fills it with plausibly-shaped noise - a few
clusters rather than a uniform scatter, because a GIST index on evenly spread
points is not the index this app has - times each query the API actually
issues, and drops it again.

It is worth running before and after anything that touches api/queries.py. Two
of the worst problems in this codebase were invisible at 224 memories and
obvious at 50,000:

  * COORDINATE_IS_UNIQUE scanned every place, once per row returned, which was
    305ms of a 338ms /v1/memories/nearby. An expression index took the whole
    query to 14ms.
  * ST_ClusterDBSCAN was fed one point per memory rather than per place, and
    took eleven seconds.

Neither was a guess. Both came out of EXPLAIN (ANALYZE) on this data.

Where it stands at 50,000 memories across 20,000 places, after both:

    nearby, 10km                 10.7 ms
    nearby count                  5.4 ms
    places nearby                 8.2 ms
    single memory (unlock)        1.2 ms
    search, common word          60.5 ms
    search, rare word             4.3 ms
    hotspots (DBSCAN)          1286.3 ms   (cached; see STATS_TTL_SECONDS)

A common word matching every row is search's worst case and is what 60ms buys.
Hotspots is the only one still measured in seconds, which is why /v1/stats
does not recompute it per request.
"""

import argparse
import subprocess
import time

from sqlalchemy import create_engine, text

from api.queries import (
    COUNT_QUERY,
    HOTSPOTS_QUERY,
    NEARBY_MEMORIES_QUERY,
    NEARBY_PLACES_QUERY,
    SEARCH_MEMORIES_QUERY,
    SINGLE_MEMORY_QUERY,
)

DB = "memorylane_perf"
URL = f"postgresql+psycopg://memorylane:memorylane@localhost:5432/{DB}"

# mod() rather than %, which psycopg reads as the start of a parameter.
# Four cities, because the corpus is a touring history and not a uniform
# scatter - a GIST index over evenly spread points answers a question this app
# never asks.
CITIES = "(ARRAY[-73.98, 12.56, -0.12, 13.40])", "(ARRAY[40.75, 55.67, 51.50, 52.52])"

FILL_PLACES = f"""
INSERT INTO places (name, place_query, coordinates, precision_meters)
SELECT
  'Place ' || g || ', ' || (ARRAY['New York','Copenhagen','London','Berlin'])[1 + mod(g, 4)],
  'perf:' || g,
  ST_MakePoint(
    {CITIES[0]}[1 + mod(g, 4)] + (random() - 0.5) * 0.4,
    {CITIES[1]}[1 + mod(g, 4)] + (random() - 0.5) * 0.4
  )::geography,
  50
FROM generate_series(1, :places) g
"""

FILL_MEMORIES = """
INSERT INTO memories (place_id, summary, extraction_confidence, layer, contrast_score, tags)
SELECT
  p.id,
  'A thing that happened here, number ' || g || ', with some words to search.',
  (ARRAY['low','medium','high'])[1 + mod(g, 3)],
  'historical',
  random(),
  ARRAY['food','music']::varchar[]
FROM generate_series(1, :rows) g
JOIN places p ON p.id = 1 + mod(g, :places)
"""


def psql(database, *args):
    return subprocess.run(
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
            database,
            *args,
        ],
        capture_output=True,
        text=True,
    )


def build(rows: int, places: int) -> None:
    psql("memorylane", "-c", f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
    created = psql("memorylane", "-c", f"CREATE DATABASE {DB}")
    if created.returncode != 0:
        raise SystemExit(f"could not create {DB}: {created.stderr}")

    with open("db/schema.sql") as schema:
        subprocess.run(
            ["docker", "compose", "exec", "-T", "db", "psql", "-q", "-U", "memorylane", "-d", DB],
            stdin=schema,
            capture_output=True,
            text=True,
        )

    engine = create_engine(URL)
    with engine.begin() as conn:
        # Separately: psycopg will not prepare two commands at once.
        conn.execute(text(FILL_PLACES), {"places": places})
        conn.execute(text(FILL_MEMORIES), {"rows": rows, "places": places})
        conn.execute(text("ANALYZE places"))
        conn.execute(text("ANALYZE memories"))
    engine.dispose()


def best_of(conn, sql, params, runs):
    conn.execute(text(sql), params).fetchall()  # warm the cache
    best = float("inf")
    for _ in range(runs):
        started = time.perf_counter()
        conn.execute(text(sql), params).fetchall()
        best = min(best, time.perf_counter() - started)
    return best * 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=50_000, help="memories")
    parser.add_argument("--places", type=int, default=20_000)
    parser.add_argument("--keep", action="store_true", help="leave the database behind")
    args = parser.parse_args()

    print(f"building {args.rows:,} memories across {args.places:,} places…")
    build(args.rows, args.places)

    near = {
        "lat": 40.75,
        "lng": -73.98,
        "radius_meters": 10_000,
        "limit": 20,
        "offset": 0,
        "layer": None,
        "min_confidence": "medium",
    }
    work = [
        ("nearby, 10km", NEARBY_MEMORIES_QUERY, near, 5),
        ("nearby count", COUNT_QUERY, near, 5),
        (
            "places nearby",
            NEARBY_PLACES_QUERY,
            {k: near[k] for k in ("lat", "lng", "radius_meters", "limit", "offset")},
            5,
        ),
        ("single memory (unlock)", SINGLE_MEMORY_QUERY, {"memory_id": 1}, 5),
        (
            "search, common word",
            SEARCH_MEMORIES_QUERY,
            {"query": "words", "limit": 20, "offset": 0},
            5,
        ),
        (
            "search, rare word",
            SEARCH_MEMORIES_QUERY,
            {"query": "number 4211", "limit": 20, "offset": 0},
            5,
        ),
        ("hotspots (DBSCAN)", HOTSPOTS_QUERY, {"limit": 5}, 2),
    ]

    engine = create_engine(URL)
    print()
    with engine.connect() as conn:
        for name, sql, params, runs in work:
            print(f"  {name:24} {best_of(conn, sql, params, runs):8.1f} ms")
    engine.dispose()

    print(
        "\nEXPLAIN anything surprising before changing it:\n"
        f"  docker compose exec db psql -U memorylane -d {DB}"
    )
    if not args.keep:
        psql("memorylane", "-c", f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
    else:
        print(f"  ({DB} left behind; --keep)")


if __name__ == "__main__":
    main()
