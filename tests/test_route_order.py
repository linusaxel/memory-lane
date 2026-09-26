"""api/route_solver.py: which stops, and in what order."""

import itertools
import math
import random
from types import SimpleNamespace

from api.gate import meters_between
from api.models import Coordinates
from api.route_solver import ROUTE_FILL, _choose_stops, _choose_walks, _path_meters, _walking_order
from api.streets import ROUTE_CIRCUITY, walking_matrix

ANCHOR = Coordinates(lat=40.75, lng=-73.99)
# ~84m of longitude per 0.001 at this latitude.
STEP = 0.001


def stop(name, east, layer="historical", contrast=None):
    return SimpleNamespace(
        name=name,
        lat=ANCHOR.lat,
        lng=ANCHOR.lng + east * STEP,
        layer=layer,
        contrast_score=contrast,
    )


def crow(picks):
    """Walking metres with no sidecar, node 0 the anchor."""
    return walking_matrix([ANCHOR] + [Coordinates(lat=p.lat, lng=p.lng) for p in picks])


def order(picks, loop=False):
    return [picks[i - 1] for i in _walking_order(list(range(1, len(picks) + 1)), crow(picks), loop)]


def choose(picks, size, seed, budget, loop):
    return [
        picks[i - 1] for i in _choose_stops(picks, size, crow(picks), seed, budget, loop, ANCHOR)
    ]


def walked(picks, stops):
    nodes = [next(i for i, p in enumerate(picks, 1) if p is s) for s in stops]
    return _path_meters(nodes, crow(picks))


def test_the_nearest_stop_first_is_not_the_shortest_walk():
    # Nearest-neighbour goes east 1, back west 3, then east 6: 10 steps.
    # West 2 first, then straight east through the rest: 8.
    ordered = order([stop("a", 1), stop("b", -2), stop("c", 4)])
    assert [s.name for s in ordered] == ["b", "a", "c"]


def test_never_longer_than_any_other_ordering(route_seed):
    rng = random.Random(route_seed + 0)
    for _ in range(200):
        picks = [
            SimpleNamespace(
                lat=ANCHOR.lat + rng.uniform(-0.01, 0.01), lng=ANCHOR.lng + rng.uniform(-0.01, 0.01)
            )
            for _ in range(rng.randint(1, 6))
        ]
        best = walked(picks, order(picks))
        shuffled = rng.sample(picks, len(picks))
        assert best <= walked(picks, shuffled) + 1e-6
        assert sorted(map(id, order(picks))) == sorted(map(id, picks))


def names(stops):
    return sorted(s.name for s in stops)


def test_a_tight_cluster_ahead_beats_one_stop_behind():
    # The three nearest are behind(-4), a(6), b(7): 4 + 10 + 1 = 15 steps.
    # The cluster a, b, c is 6 + 1 + 1 = 8.
    picks = [stop("behind", -4), stop("a", 6), stop("b", 7), stop("c", 8)]
    assert names(choose(picks, 3, "seed", 4000, False)) == ["a", "b", "c"]


def test_a_striking_stop_further_out_beats_a_dull_one_nearby():
    # 1 step is 109m walked; 5 steps is 546m.
    picks = [stop("dull", 1), stop("striking", 5, contrast=0.9)]
    assert names(choose(picks, 1, "seed", 4000, False)) == ["striking"]
    assert names(choose(picks, 1, "seed", 400, False)) == ["dull"]


def test_each_layer_keeps_its_share_even_when_it_costs_metres():
    # The shortest four are all historical; two strangers far out still get in.
    picks = [stop(f"h{i}", i) for i in range(1, 5)]
    picks += [stop("s1", -20, "stranger"), stop("s2", 30, "stranger")]
    chosen = choose(picks, 4, "seed", 20_000, False)
    assert sum(s.layer == "stranger" for s in chosen) == 2


def test_the_budget_caps_the_walk_not_the_count():
    # 84m apart in a line: 3 stops is 252m x 1.3 = 328m, a fourth is 437m.
    picks = [stop(f"s{i}", i) for i in range(1, 11)]
    assert names(choose(picks, 5, "seed", 400, False)) == ["s1", "s2", "s3"]


def test_within_budget_repeatable_and_full_as_the_budget_allows(route_seed):
    rng = random.Random(route_seed + 1)
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
        chosen = choose(picks, 5, str(i), 4000, False)
        walk = walked(picks, chosen)
        assert walk <= 4000
        assert len(set(map(id, chosen))) == len(chosen) <= 5
        assert chosen == choose(picks, 5, str(i), 4000, False)
        # Short of five means no leftover could even be tacked onto the end.
        if len(chosen) < 5:
            last = chosen[-1] if chosen else ANCHOR
            for c in picks:
                if all(c is not s for s in chosen):
                    extra = meters_between(Coordinates(lat=last.lat, lng=last.lng), c)
                    assert walk + extra * ROUTE_CIRCUITY > 4000


def test_a_loop_counts_the_walk_home():
    # In steps: straight out east (1, 2) is 2 one-way, but 4 home again. East 1
    # then north 1.1 is 1 + 1.5 = 2.5 one-way, and 3.6 as a loop. 250m one-way
    # (2.3 steps) fits only the straight pair.
    north = SimpleNamespace(
        name="n", lat=ANCHOR.lat + 1.1 * STEP * 84 / 111, lng=ANCHOR.lng, layer="historical"
    )
    picks = [stop("e1", 1), stop("e2", 2), north]
    assert names(choose(picks, 2, "seed", 250, False)) == ["e1", "e2"]
    # A loop never walks straight out and straight back; it turns north.
    assert "n" in names(choose(picks, 2, "seed", 4000, True))


def test_solver_invariants_over_random_instances(route_seed):
    """Loop and one-way, 200 seeded maps: within budget with the walk home
    counted, no stop twice, repeatable, never fewer stops than nearest-neighbour
    manages, and as many as brute force finds when n <= 7."""
    rng = random.Random(route_seed + 2)
    for i in range(200):
        picks = [
            SimpleNamespace(
                lat=ANCHOR.lat + rng.uniform(-0.01, 0.01),
                lng=ANCHOR.lng + rng.uniform(-0.01, 0.01),
                layer=rng.choice(["stranger", "historical"]),
                contrast_score=rng.choice([None, rng.random()]),
            )
            for _ in range(rng.randint(0, 12))
        ]
        budget, loop = rng.uniform(500, 6000), rng.random() < 0.5
        d = crow(picks)
        chosen = _choose_stops(picks, 5, d, str(i), budget, loop, ANCHOR)
        assert _path_meters(chosen, d, loop) <= budget
        assert len(set(chosen)) == len(chosen) <= 5
        assert chosen == _choose_stops(picks, 5, d, str(i), budget, loop, ANCHOR)

        here, nn = 0, []
        while True:
            left = [c for c in range(1, len(picks) + 1) if c not in nn]
            nxt = min(left, key=lambda c: d[here][c], default=None)
            if nxt is None or len(nn) == 5 or _path_meters([*nn, nxt], d, loop) > budget:
                break
            nn.append(nxt)
            here = nxt
        assert len(chosen) >= len(nn)

        if len(picks) <= 7:
            most = max(
                len(s)
                for k in range(min(5, len(picks)) + 1)
                for s in itertools.combinations(range(1, len(picks) + 1), k)
                if _path_meters(_walking_order(list(s), d, loop), d, loop) <= budget
            )
            assert len(chosen) == most


def test_a_ring_round_the_start_is_walked_round_not_along_one_side():
    """The lakes round a flat: ten stops ~1.3km out on every side. Every other
    one is 8.6km, five neighbours on one side 5.9km; a 10km ask is the first."""
    picks = [
        SimpleNamespace(
            name=k,
            lat=ANCHOR.lat + 0.012 * math.cos(2 * math.pi * k / 10),
            lng=ANCHOR.lng + 0.016 * math.sin(2 * math.pi * k / 10),
            layer="historical",
        )
        for k in range(10)
    ]
    d = [[meters_between(a, b) for b in [ANCHOR, *picks]] for a in [ANCHOR, *picks]]
    for seed in "abcdef":
        chosen = _choose_stops(picks, 5, d, seed, 10000, True, ANCHOR)
        assert _path_meters(chosen, d, True) >= ROUTE_FILL * 10000, seed


def test_an_included_stop_is_on_every_walk_returned(route_seed):
    rng = random.Random(route_seed + 7)
    for i in range(30):
        picks = [stop(str(n), rng.uniform(-20, 20)) for n in range(12)]
        for n, p in enumerate(picks):
            p.id = n
        pin = rng.randrange(len(picks))
        d = crow(picks)
        if _path_meters([pin + 1], d, True) > 4000:
            continue
        walks = _choose_walks(picks, 5, d, str(i), 4000, True, ANCHOR, pin)
        assert walks and all(pin + 1 in w for w in walks)
