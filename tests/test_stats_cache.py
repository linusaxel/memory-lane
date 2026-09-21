"""/v1/stats is the most expensive endpoint and the one strangers call most.

Four unbounded counts and ST_ClusterDBSCAN over every placed memory, with
OVER () for a partition - so no index helps and no filter shrinks it. It is
also what the app asks for when the map comes back empty, which is the normal
experience anywhere the corpus does not reach. The cost grows with the corpus
while the answer only changes when the pipeline runs.
"""

import pytest
from sqlalchemy import text

import api.read

pytestmark = pytest.mark.db


@pytest.fixture
def client(api_client):
    return api_client


def _a_memory(session):
    place_id = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Vega, Copenhagen', :q, ST_MakePoint(12.5, 55.6)::geography, 50) "
            "RETURNING id"
        ),
        {"q": f"cache:{session.execute(text('SELECT gen_random_uuid()')).scalar()}"},
    ).scalar()
    session.execute(
        text("INSERT INTO memories (place_id, summary) VALUES (:p, 'the amp died')"),
        {"p": place_id},
    )
    session.commit()


def test_the_answer_is_reused_within_the_window(client, db_session):
    _a_memory(db_session)
    first = client.get("/v1/stats").json()["memories"]

    _a_memory(db_session)
    assert client.get("/v1/stats").json()["memories"] == first, (
        "the corpus was counted again inside the cache window"
    )


def test_the_answer_is_recomputed_once_the_window_passes(client, db_session, monkeypatch):
    _a_memory(db_session)
    first = client.get("/v1/stats").json()["memories"]

    _a_memory(db_session)
    monkeypatch.setattr(api.read, "STATS_TTL_SECONDS", 0)
    assert client.get("/v1/stats").json()["memories"] == first + 1


def test_each_hotspot_count_is_its_own_answer(client, db_session):
    """It is a query parameter, so one cache entry would serve the wrong shape
    of answer to whoever asked second."""
    _a_memory(db_session)

    assert client.get("/v1/stats?hotspots=0").json()["hotspots"] == []
    named = client.get("/v1/stats?hotspots=5").json()["hotspots"]
    assert named, "a corpus with a place in it should name at least one hotspot"
    # And back again, from the other cache entry rather than the one just set.
    assert client.get("/v1/stats?hotspots=0").json()["hotspots"] == []
