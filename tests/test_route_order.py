"""api/read.py's route solver: which stops, and in what order."""

import random
from types import SimpleNamespace

from api.models import Coordinates
from api.read import _choose_stops, _path_meters, _walking_order

ANCHOR = Coordinates(lat=40.75, lng=-73.99)
# ~84m of longitude per 0.001 at this latitude.
STEP = 0.001


def stop(name, east, layer="historical"):
    return SimpleNamespace(name=name, lat=ANCHOR.lat, lng=ANCHOR.lng + east * STEP, layer=layer)


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


def names(stops):
    return sorted(s.name for s in stops)


def test_a_tight_cluster_ahead_beats_one_stop_behind():
    # The three nearest are behind(-4), a(6), b(7): 4 + 10 + 1 = 15 steps.
    # The cluster a, b, c is 6 + 1 + 1 = 8.
    picks = [stop("behind", -4), stop("a", 6), stop("b", 7), stop("c", 8)]
    assert names(_choose_stops(picks, 3, ANCHOR, "seed")) == ["a", "b", "c"]


def test_each_layer_keeps_its_share_even_when_it_costs_metres():
    # The shortest four are all historical; two strangers far out still get in.
    picks = [stop(f"h{i}", i) for i in range(1, 5)]
    picks += [stop("s1", -20, "stranger"), stop("s2", 30, "stranger")]
    chosen = _choose_stops(picks, 4, ANCHOR, "seed")
    assert sum(s.layer == "stranger" for s in chosen) == 2


def test_same_seed_same_stops_and_never_short_or_repeated():
    rng = random.Random(1)
    for i in range(100):
        picks = [
            SimpleNamespace(
                name=n,
                lat=ANCHOR.lat + rng.uniform(-0.02, 0.02),
                lng=ANCHOR.lng + rng.uniform(-0.02, 0.02),
                layer=rng.choice(["stranger", "historical"]),
            )
            for n in range(rng.randint(0, 20))
        ]
        chosen = _choose_stops(picks, 5, ANCHOR, str(i))
        assert len(chosen) == min(5, len(picks))
        assert len(set(map(id, chosen))) == len(chosen)
        assert chosen == _choose_stops(picks, 5, ANCHOR, str(i))
