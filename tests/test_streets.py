"""api/streets.py: OSRM when it answers, crow-flies when it does not."""

import io
import json

import pytest

from api import streets
from api.models import Coordinates

A, B, C = (Coordinates(lat=40.75, lng=-73.99 + i * 0.001) for i in range(3))


@pytest.fixture
def osrm(monkeypatch):
    """Point streets at a fake sidecar that answers with `reply[0]`."""
    reply, asked = [None], []
    monkeypatch.setattr(streets, "ROUTING_URL", "http://osrm")

    def urlopen(url, timeout):
        asked.append(url)
        if isinstance(reply[0], Exception):
            raise reply[0]
        return io.BytesIO(json.dumps(reply[0]).encode())

    monkeypatch.setattr(streets, "urlopen", urlopen)
    return reply, asked


def crow():
    return [[streets.meters_between(a, b) * streets.ROUTE_CIRCUITY for b in (A, B)] for a in (A, B)]


def test_no_sidecar_is_crow_flies_and_no_shapes(monkeypatch):
    monkeypatch.setattr(streets, "ROUTING_URL", None)
    assert streets.walking_matrix([A, B]) == crow()
    assert streets.street_legs([A, B]) is None


def test_the_sidecar_distances_are_used(osrm):
    reply, asked = osrm
    reply[0] = {"code": "Ok", "distances": [[0, 120], [130, 0]]}
    assert streets.walking_matrix([A, B]) == [[0, 120], [130, 0]]
    assert asked == [
        f"http://osrm/table/v1/foot/{A.lng},{A.lat};{B.lng},{B.lat}?annotations=distance"
    ]


@pytest.mark.parametrize(
    "answer",
    [OSError("down"), {"code": "NoTable"}, {"code": "Ok", "distances": [[0, None], [1, 0]]}],
)
def test_a_sidecar_that_fails_is_crow_flies(osrm, answer):
    osrm[0][0] = answer
    assert streets.walking_matrix([A, B]) == crow()
    assert streets.street_legs([A, B]) is None


def step(*points):
    return {"geometry": {"coordinates": [[p.lng, p.lat] for p in points]}}


def test_one_shape_per_leg_joined_across_steps(osrm):
    mid = Coordinates(lat=40.751, lng=-73.9895)
    osrm[0][0] = {
        "code": "Ok",
        "routes": [{"legs": [{"steps": [step(A, mid), step(mid, B)]}, {"steps": [step(B, C)]}]}],
    }
    assert streets.street_legs([A, B, C]) == [[A, mid, B], [B, C]]


def test_one_stop_has_no_legs(osrm):
    assert streets.street_legs([A]) is None
    assert osrm[1] == []
