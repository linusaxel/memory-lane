"""Where stories wait: neighbourhood outlines from OSM, and each one's opened
out of total (docs/10-decisions.md#where-stories-wait). Overpass is faked in
the shape `out geom` returns: a relation's ways, each with its points."""

import pytest
from sqlalchemy import text

from pipeline import geocode, neighbourhoods
from tests.test_api_routes import DEVICE, LNG, _offset

pytestmark = pytest.mark.db

WEST, EAST = LNG - 0.001, LNG + 0.001


def _way(*points, role="outer"):
    return {"type": "way", "role": role, "geometry": [{"lat": a, "lon": b} for a, b in points]}


def _square(osm_id, name, south, north):
    """A box drawn as two ways that meet end to end, as OSM draws a boundary."""
    return {
        "type": "relation",
        "id": osm_id,
        "tags": {"name": name, "admin_level": "10"},
        "members": [
            _way((south, WEST), (south, EAST), (north, EAST)),
            _way((north, EAST), (north, WEST), (south, WEST)),
            _way((south, WEST), (north, EAST), role="inner"),
        ],
    }


def _overpass(monkeypatch):
    found = {
        "elements": [
            _square(1, "Near", 55.6755, 55.6784),
            _square(2, "Far", 55.6784, 55.6810),
            {"type": "relation", "id": 3, "tags": {}, "members": []},
        ]
    }
    monkeypatch.setattr(geocode, "_get_json", lambda url: found)


def test_outlines_upsert_from_osm_and_count_opened_out_of_total(
    api_client, db_session, monkeypatch
):
    _overpass(monkeypatch)
    assert neighbourhoods.fetch(db_session, "Testby", 10) == 2, "a relation with no name is skipped"
    assert neighbourhoods.fetch(db_session, "Testby", 10) == 2, "and again, in place"
    assert db_session.execute(text("SELECT COUNT(*) FROM neighbourhoods")).scalar() == 2

    near = [_offset(db_session, n) for n in (1, 2)]
    for n in (3, 4, 5):
        _offset(db_session, n)
    db_session.execute(text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid))"), {"d": DEVICE})
    db_session.execute(
        text("INSERT INTO unlocks (device_id, memory_id) VALUES (CAST(:d AS uuid), :m)"),
        {"d": DEVICE, "m": near[0]},
    )
    db_session.commit()

    body = api_client.get(f"/v1/me/neighbourhoods?device={DEVICE}&lat=55.6760&lng={LNG}").json()[
        "neighbourhoods"
    ]
    assert [(n["name"], n["opened"], n["total"]) for n in body] == [("Near", 1, 2), ("Far", 0, 3)]
    assert 55.6755 < body[0]["end"]["lat"] < 55.6784, "the walk ends inside it"
