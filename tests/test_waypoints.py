"""Plain lockets are named OSM spots, thinned so none crowd another or sit on a
memory. No network: elements in the shape Overpass's `out center tags` gives."""

from pipeline.waypoints import CLEAR_M, SPACING_M, candidates, thin

NYHAVN = (55.6798, 12.5907)
# About a metre of latitude, in degrees.
M = 1 / 111_320


def _w(name, kind, lat, lng):
    return {"osm_id": name, "name": name, "kind": kind, "lat": lat, "lng": lng}


def test_only_named_spots_of_a_known_kind_are_candidates():
    elements = [
        {
            "type": "node",
            "id": 1,
            "lat": 55.1,
            "lon": 12.1,
            "tags": {"historic": "memorial", "name": "Anker"},
        },
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 55.2, "lon": 12.2},
            "tags": {"leisure": "park", "name": "Ørstedsparken"},
        },
        {"type": "node", "id": 3, "lat": 55.3, "lon": 12.3, "tags": {"historic": "memorial"}},
        {
            "type": "node",
            "id": 4,
            "lat": 55.4,
            "lon": 12.4,
            "tags": {"shop": "bakery", "name": "Bager"},
        },
    ]
    assert candidates(elements) == [
        {"osm_id": "node/1", "name": "Anker", "kind": "memorial", "lat": 55.1, "lng": 12.1},
        {"osm_id": "way/2", "name": "Ørstedsparken", "kind": "park", "lat": 55.2, "lng": 12.2},
    ]


def test_the_better_kind_stays_where_two_crowd():
    lat, lng = NYHAVN
    park = _w("park", "park", lat, lng)
    memorial = _w("memorial", "memorial", lat + 50 * M, lng)
    far = _w("far", "fountain", lat + (50 + SPACING_M + 20) * M, lng)
    assert [w["name"] for w in thin([park, memorial, far], [], [])] == ["memorial", "far"]


def test_a_rerun_keeps_room_for_what_is_already_there():
    lat, lng = NYHAVN
    assert thin([_w("new", "memorial", lat + 100 * M, lng)], [(lat, lng)], []) == []


def test_none_on_a_memorys_spot_but_one_nearby_is_fine():
    lat, lng = NYHAVN
    on = _w("on", "memorial", lat + (CLEAR_M - 10) * M, lng)
    near = _w("near", "fountain", lat - (CLEAR_M + 10) * M, lng)
    assert [w["name"] for w in thin([on, near], [], [(lat, lng)])] == ["near"]
