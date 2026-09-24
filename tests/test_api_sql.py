"""Every query constant in api.queries must be valid SQL against the real schema.

Nothing else in the suite executes these strings - the API tests use TestClient
without a database - so a typo in a query reaches production untouched. That
matters most right after the 14-column SELECT block stopped being copy-pasted
seven times and became a composed fragment.

EXPLAIN parses and plans the statement without returning rows, so this runs
against the empty ephemeral DB and stays fast.
"""

import pytest
from sqlalchemy import text

import api.queries as m

pytestmark = pytest.mark.db

PARAMS = {
    "lat": 40.7484,
    "lng": -73.9857,
    "radius_meters": 10000.0,
    "limit": 20,
    "offset": 0,
    "min_confidence": "medium",
    # None means "every layer", which is the unfiltered shape these assert on.
    "layer": None,
    "tags": ["food"],
    # None means "no theme", the route's unfiltered shape.
    "tag": None,
    "query": "coffee",
    "memory_id": 1,
    "place_id": 1,
    "content_id": 1,
    "route_id": 1,
    "note_id": 1,
    # Any valid UUID: EXPLAIN only needs the cast to parse.
    "device_id": "00000000-0000-0000-0000-000000000000",
    "device": "00000000-0000-0000-0000-000000000000",
    "ids": [1],
    "today": "2026-09-22",
}

QUERIES = sorted(
    name
    for name in dir(m)
    if name.endswith(("_QUERY", "_COUNT_QUERY")) and isinstance(getattr(m, name), str)
)


def test_every_query_constant_is_collected():
    """A rename that hides a query from this test would defeat the point."""
    assert len(QUERIES) >= 11, QUERIES


@pytest.mark.parametrize("name", QUERIES)
def test_query_is_valid_sql(db_session, name):
    sql = getattr(m, name)
    bound = {k: v for k, v in PARAMS.items() if f":{k}" in sql}
    db_session.execute(text(f"EXPLAIN {sql}"), bound)


def test_the_gates_uniqueness_question_can_use_an_index(db_session):
    """COORDINATE_IS_UNIQUE compares ST_SnapToGrid on both sides, so without a
    matching expression index Postgres scans every place - once per row
    returned. At 50k memories that was 305ms of a 338ms request; with the index
    the whole query is 14ms.

    The index has to match the query's expression exactly, argument form
    included, so this asserts the planner will actually reach for it rather
    than that the index exists.
    """
    from sqlalchemy import text

    db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Here', 'grid:here', ST_MakePoint(12.5, 55.6)::geography, 50)"
        )
    )
    db_session.execute(text("SET LOCAL enable_seqscan = off"))

    plan = "\n".join(
        row[0]
        for row in db_session.execute(
            text(
                "EXPLAIN SELECT COUNT(*) FROM places p2 "
                "WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001) "
                "= ST_SnapToGrid(ST_MakePoint(12.5, 55.6)::geography::geometry, 0.0001)"
            )
        )
    )

    assert "idx_places_grid" in plan, (
        "the gate's uniqueness check is not using its index, which makes every "
        f"nearby query scan the places table:\n{plan}"
    )
