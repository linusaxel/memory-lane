"""api/read.py's _walking_order: the shortest walk, not the greedy one."""

import random
from types import SimpleNamespace

from api.models import Coordinates
from api.read import _path_meters, _walking_order

ANCHOR = Coordinates(lat=40.75, lng=-73.99)
# ~84m of longitude per 0.001 at this latitude.
STEP = 0.001


def stop(name, east):
    return SimpleNamespace(name=name, lat=ANCHOR.lat, lng=ANCHOR.lng + east * STEP)


def test_the_nearest_stop_first_is_not_the_shortest_walk():
    # Nearest-neighbour goes east 1, back west 3, then east 6: 10 steps.
    # West 2 first, then straight east through the rest: 8.
    order = _walking_order([stop("a", 1), stop("b", -2), stop("c", 4)], ANCHOR)
    assert [s.name for s in order] == ["b", "a", "c"]


def test_never_longer_than_any_other_ordering():
    rng = random.Random(0)
    for _ in range(200):
        picks = [
            SimpleNamespace(
                lat=ANCHOR.lat + rng.uniform(-0.01, 0.01), lng=ANCHOR.lng + rng.uniform(-0.01, 0.01)
            )
            for _ in range(rng.randint(1, 6))
        ]
        best = _path_meters(ANCHOR, _walking_order(picks, ANCHOR))
        shuffled = rng.sample(picks, len(picks))
        assert best <= _path_meters(ANCHOR, shuffled) + 1e-6
        assert sorted(map(id, _walking_order(picks, ANCHOR))) == sorted(map(id, picks))
