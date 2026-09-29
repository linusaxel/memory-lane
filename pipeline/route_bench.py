"""How today's route behaves on a full map, from many starts and lengths.

    ROUTING_URL=http://localhost:5001 python -m pipeline.route_bench
    python -m pipeline.route_bench --runs 200 --seed 2
    ROUTING_URL=http://localhost:5001 python -m pipeline.route_bench --scenario all
    python -m pipeline.route_bench --solvers
    ROUTING_URL=http://localhost:5001 python -m pipeline.route_bench --end

Read, not gated, like perf.py and quality.py. Each run plans a walk through
api/route_solver.py's _plan_route for a fresh device, from a random start inside
seed_dev's dense map (300 memories, planted in the bench's own transaction), in its box, with everything the plan page lets a person set rolled
at random: slider length, loop or one way, and the app's own
`again`. Then once more with the next `again`: `fresh` is how often that is a
different walk, which is "Show me another" working. The bar is "no spur": a stop
off the loop is walked to and back the same way, and `retraced` is how many
metres of that there are (api/streets.py, retraced_meters). `spur` is any at
all, often a few metres from a mid-block start to its corner; `>50m` is one
you would notice. `cross` is any walk that passes a street corner twice
without retracing, a figure of eight (crossings). `gap` is the shortest leg over the mean leg, out and home
included: 1 is stops evenly spaced, near 0 is two of them bunched. `max` is the
longest leg over the mean: a long empty stretch, often the last leg to an end.

`--end` makes every run one way to an end at a random heading, 0.5-0.8 of the
slider away as the crow flies over walking's 1.3, as a tapped end would be.

`--scenario` plants seed_dev's route scenarios instead, one at a time, and starts round each one's start. The rollback at the
end puts back whatever the database held.

`--solvers` needs neither database nor streets: random crow-flies maps of
SOLVER_CANDIDATES stops, few enough to brute-force, scored for nearest-neighbour,
the solver, and the exact optimum. The optimum is the orienteering one - most
stops, then most prize - which the solver deliberately trades against turns
back and filling the slider, so its prize gap is an upper bound on what the
heuristic loses. The classic OP sets (Tsiligirides, Chao) are not here: they
end somewhere other than the start and cap nothing but length, and this walk
is five stops with a layer quota.
"""

import argparse
import datetime
import itertools
import math
import random
import statistics
import time
import uuid
from itertools import pairwise
from types import SimpleNamespace

from api.gate import meters_between
from api.models import Coordinates
from api.route_solver import (
    ROUTE_SIZE,
    _choose_stops,
    _path_meters,
    _plan_route,
    _route_size,
    _walking_order,
)
from api.streets import crossings, retraced_meters, walking_matrix
from pipeline.config import ROUTING_URL
from pipeline.db import get_session
from pipeline.seed_dev import LAT, LNG, ROUTE_SCENARIOS, dense, scenario, seed

BUDGETS = (1000, 2000, 3000, 4000, 6000, 8000, 10_000)
# Starts stay well inside the pool's box, so a walk is not short of stops
# only because it began at the edge of the map.
START_BOX = (0.004, 0.007)


def run(
    session, rng: random.Random, budget: int, around: tuple[float, float], to_end: bool = False
) -> dict:
    start = Coordinates(
        lat=around[0] + rng.uniform(-START_BOX[0], START_BOX[0]),
        lng=around[1] + rng.uniform(-START_BOX[1], START_BOX[1]),
    )
    device = str(uuid.UUID(int=rng.getrandbits(128)))
    loop = rng.random() < 0.5
    again = rng.randrange(1_000_000)
    end = None
    if to_end:
        heading, reach = rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 0.8) * budget / 1.3
        end = Coordinates(
            lat=start.lat + reach * math.cos(heading) / 111_320,
            lng=start.lng
            + reach * math.sin(heading) / (111_320 * math.cos(math.radians(start.lat))),
        )
    today = datetime.date.today()
    began = time.perf_counter()
    stops, legs, ends = _plan_route(session, device, start, budget, today, loop, again, end=end)
    ms = (time.perf_counter() - began) * 1000
    another, _, _ = _plan_route(session, device, start, budget, today, loop, again + 1, end=end)
    fresh = {r.id for r in another} != {r.id for r in stops}
    if legs is None:  # no stops at all, or the sidecar went away mid-run
        return {
            "budget": budget,
            "stops": len(stops),
            "walk": 0,
            "retraced": 0,
            "crossings": 0,
            "ms": ms,
            "fresh": fresh,
            "gap": 1,
            "max": 1,
        }
    path = [*ends["out"], *(p for leg in legs for p in leg), *(ends["home"] or [])]
    gaps = [
        sum(meters_between(a, b) for a, b in pairwise(leg))
        for leg in [ends["out"], *legs, *([ends["home"]] if ends["home"] else [])]
    ]
    return {
        "budget": budget,
        "stops": len(stops),
        "walk": sum(meters_between(a, b) for a, b in pairwise(path)),
        "retraced": retraced_meters(path, [Coordinates(lat=r.lat, lng=r.lng) for r in stops]),
        "crossings": crossings(path, [start, *(Coordinates(lat=r.lat, lng=r.lng) for r in stops)]),
        "ms": ms,
        "fresh": fresh,
        "gap": min(gaps) / (sum(gaps) / len(gaps)),
        "max": max(gaps) / (sum(gaps) / len(gaps)),
    }


# 12 candidates is 1,585 sets of up to five, each ordered exactly: well under a
# second of brute force per map.
SOLVER_CANDIDATES = 12


def solvers(runs: int, seed: int) -> None:
    rng = random.Random(seed)
    rows = []
    for i in range(runs):
        at = Coordinates(lat=LAT, lng=LNG)
        picks = [
            SimpleNamespace(
                lat=LAT + rng.uniform(-0.01, 0.01),
                lng=LNG + rng.uniform(-0.01, 0.01),
                layer=rng.choice(["stranger", "historical"]),
                contrast_score=rng.choice([None, rng.random()]),
            )
            for _ in range(SOLVER_CANDIDATES)
        ]
        budget, loop = rng.choice(BUDGETS), rng.random() < 0.5
        d = walking_matrix([at] + [Coordinates(lat=p.lat, lng=p.lng) for p in picks])
        prize = {n: 1 + (p.contrast_score or 0) for n, p in enumerate(picks, 1)}
        nodes = range(1, len(picks) + 1)

        near: list[int] = []
        while len(near) < ROUTE_SIZE:
            c = min(
                (c for c in nodes if c not in near), key=lambda c: d[near[-1] if near else 0][c]
            )
            if _path_meters([*near, c], d, loop) > budget:
                break
            near.append(c)
        began = time.perf_counter()
        chosen = _choose_stops(picks, ROUTE_SIZE, d, str(i), budget, loop, at)
        ms = (time.perf_counter() - began) * 1000
        best = max(
            (
                s
                for k in range(ROUTE_SIZE + 1)
                for s in itertools.combinations(nodes, k)
                if _path_meters(_walking_order(list(s), d, loop), d, loop) <= budget
            ),
            key=lambda s: (len(s), sum(prize[n] for n in s)),
        )
        rows.append(
            {
                "nn": len(near),
                "solver": len(chosen),
                "exact": len(best),
                "prize": sum(prize[n] for n in chosen) / max(sum(prize[n] for n in best), 1),
                "ms": ms,
            }
        )
    print(
        f"{'runs':>5} {'nn<exact':>9} {'solver<exact':>13} {'prize p50/p5':>13} {'ms p50/p95':>11}"
    )
    same = [r["prize"] for r in rows if r["solver"] == r["exact"]]
    print(
        f"{runs:>5} {sum(r['nn'] < r['exact'] for r in rows) / runs:>9.0%} "
        f"{sum(r['solver'] < r['exact'] for r in rows) / runs:>13.0%} "
        f"{pct(same, 50):>6.0%}/{pct(same, 5):<6.0%} "
        f"{pct([r['ms'] for r in rows], 50):>5.0f}/{pct([r['ms'] for r in rows], 95):<5.0f}"
    )
    print("prize is the solver's share of the optimum's, over maps where both have as many stops")


def pct(values: list[float], q: int) -> float:
    return statistics.quantiles(values, n=100)[q - 1] if len(values) > 1 else values[0]


def report(results: list[dict]) -> None:
    print(
        f"{'budget':>7} {'runs':>5} {'full':>6} {'spur':>6} {'>50m':>6} {'cross':>6} {'retr p50/p95':>14} "
        f"{'walk/budget':>12} {'gap p50/p5':>11} {'max p50/p95':>12} {'fresh':>6} {'ms p50/p95':>12}"
    )
    for budget in (*BUDGETS, None):
        mine = [r for r in results if budget is None or r["budget"] == budget]
        if not mine:
            continue
        retraced = [r["retraced"] for r in mine]
        ms = [r["ms"] for r in mine]
        ratio = [r["walk"] / r["budget"] for r in mine]
        gap = [r["gap"] for r in mine]
        most = [r["max"] for r in mine]
        print(
            f"{budget or 'all':>7} {len(mine):>5} "
            f"{sum(r['stops'] == _route_size(r['budget']) for r in mine) / len(mine):>6.0%} "
            f"{sum(x >= 1 for x in retraced) / len(mine):>6.0%} "
            f"{sum(x > 50 for x in retraced) / len(mine):>6.0%} "
            f"{sum(r['crossings'] > 0 for r in mine) / len(mine):>6.0%} "
            f"{pct(retraced, 50):>6.0f}/{pct(retraced, 95):<6.0f}m "
            f"{statistics.median(ratio):>11.2f} "
            f"{pct(gap, 50):>5.2f}/{pct(gap, 5):<5.2f} "
            f"{pct(most, 50):>6.2f}/{pct(most, 95):<5.2f} "
            f"{sum(r['fresh'] for r in mine) / len(mine):>6.0%} "
            f"{pct(ms, 50):>5.0f}/{pct(ms, 95):<5.0f}"
        )
    # Worst-case 95% interval of a rate, at p = 0.5: 40 runs once moved spur 40% -> 45% on
    # the same code.
    print(f"a rate over {len(results)} runs is ±{1.96 * (0.25 / len(results)) ** 0.5:.0%} noise")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--scenario", choices=[*ROUTE_SCENARIOS, "all"], help="plant and bench seed_dev --routes"
    )
    parser.add_argument(
        "--solvers", action="store_true", help="nearest-neighbour, solver and exact, no streets"
    )
    parser.add_argument("--end", action="store_true", help="every run one way to an end")
    args = parser.parse_args()
    if args.solvers:
        return solvers(args.runs, args.seed)
    if not ROUTING_URL:
        raise SystemExit("ROUTING_URL is unset: without streets there are no spurs to measure")

    names = [*ROUTE_SCENARIOS] if args.scenario == "all" else [args.scenario]
    with get_session() as session:
        for name in names:
            around = (LAT, LNG)
            if name:
                around, planted = scenario(session, name, args.seed)
                print(f"\n{name}, {planted} places: {ROUTE_SCENARIOS[name]}")
            else:
                seed(session)
                dense(session, 300, args.seed)
            rng = random.Random(args.seed)
            report(
                [run(session, rng, rng.choice(BUDGETS), around, args.end) for _ in range(args.runs)]
            )
        session.rollback()


if __name__ == "__main__":
    main()
