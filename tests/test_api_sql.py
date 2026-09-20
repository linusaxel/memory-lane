"""Every query constant in api.main must be valid SQL against the real schema.

Nothing else in the suite executes these strings - the API tests use TestClient
without a database - so a typo in a query reaches production untouched. That
matters most right after the 14-column SELECT block stopped being copy-pasted
seven times and became a composed fragment.

EXPLAIN parses and plans the statement without returning rows, so this runs
against the empty ephemeral DB and stays fast.
"""

import pytest
from sqlalchemy import text

import api.main as m

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
    "query": "coffee",
    "memory_id": 1,
    "place_id": 1,
    "content_id": 1,
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
