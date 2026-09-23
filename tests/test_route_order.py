"""api/read.py's route solver: which stops, and in what order."""

import random
from types import SimpleNamespace

from api.models import Coordinates
from api.read import ROUTE_CIRCUITY, _choose_stops, _path_meters, _walking_order

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
    assert names(_choose_stops(picks, 3, ANCHOR, "seed", 4000)) == ["a", "b", "c"]


def test_each_layer_keeps_its_share_even_when_it_costs_metres():
    # The shortest four are all historical; two strangers far out still get in.
    picks = [stop(f"h{i}", i) for i in range(1, 5)]
    picks += [stop("s1", -20, "stranger"), stop("s2", 30, "stranger")]
    chosen = _choose_stops(picks, 4, ANCHOR, "seed", 20_000)
    assert sum(s.layer == "stranger" for s in chosen) == 2


def test_the_budget_caps_the_walk_not_the_count():
    # 84m apart in a line: 3 stops is 252m x 1.3 = 328m, a fourth is 437m.
    picks = [stop(f"s{i}", i) for i in range(1, 11)]
    assert names(_choose_stops(picks, 5, ANCHOR, "seed", 400)) == ["s1", "s2", "s3"]


def test_within_budget_repeatable_and_full_as_the_budget_allows():
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
        chosen = _choose_stops(picks, 5, ANCHOR, str(i), 4000)
        walked = _path_meters(ANCHOR, chosen)
        assert walked * ROUTE_CIRCUITY <= 4000
        assert len(set(map(id, chosen))) == len(chosen) <= 5
        assert chosen == _choose_stops(picks, 5, ANCHOR, str(i), 4000)
        # Short of five means no leftover could even be tacked onto the end.
        if len(chosen) < 5:
            last = chosen[-1] if chosen else ANCHOR
            for c in picks:
                if all(c is not s for s in chosen):
                    extra = _path_meters(Coordinates(lat=last.lat, lng=last.lng), [c])
                    assert (walked + extra) * ROUTE_CIRCUITY > 4000
