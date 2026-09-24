"""How today's route behaves on a full map, from many starts and lengths.

    python -m pipeline.seed_dev --dense 300 --seed 1
    ROUTING_URL=http://localhost:5001 python -m pipeline.route_bench
    python -m pipeline.route_bench --runs 200 --seed 2
    ROUTING_URL=http://localhost:5001 python -m pipeline.route_bench --scenario all

Read, not gated, like perf.py and quality.py. Each run plans a walk through
api/read.py's own _plan_route for a fresh device, from a random start inside
the dense seed's box, at a random slider length. The bar is "no spur": a stop
off the loop is walked to and back the same way, and `retraced` is how many
metres of that there are (api/streets.py, retraced_meters). `spur` is any at
all, often a few metres from a mid-block start to its corner; `>50m` is one
you would notice.

`--scenario` plants seed_dev's route scenarios in the bench's own transaction
instead, one at a time, and starts round each one's start. The rollback at the
end puts back whatever the database held.
"""

import argparse
import datetime
import random
import statistics
import time
import uuid
from itertools import pairwise

from api.gate import meters_between
from api.models import Coordinates
from api.read import ROUTE_SIZE, _plan_route
from api.streets import retraced_meters
from pipeline.config import ROUTING_URL
from pipeline.db import get_session
from pipeline.seed_dev import LAT, LNG, ROUTE_SCENARIOS, scenario

BUDGETS = (1000, 2000, 3000, 4000, 6000)
# Starts stay well inside the pool's box, so a walk is not short of stops
# only because it began at the edge of the map.
START_BOX = (0.004, 0.005)


def run(session, rng: random.Random, budget: int, around: tuple[float, float]) -> dict:
    start = Coordinates(
        lat=around[0] + rng.uniform(-START_BOX[0], START_BOX[0]),
        lng=around[1] + rng.uniform(-START_BOX[1], START_BOX[1]),
    )
    began = time.perf_counter()
    stops, legs, ends = _plan_route(
        session, str(uuid.UUID(int=rng.getrandbits(128))), start, budget, datetime.date.today()
    )
    ms = (time.perf_counter() - began) * 1000
    if legs is None:  # no stops at all, or the sidecar went away mid-run
        return {"budget": budget, "stops": len(stops), "walk": 0, "retraced": 0, "ms": ms}
    path = [*ends["out"], *(p for leg in legs for p in leg), *(ends["home"] or [])]
    return {
        "budget": budget,
        "stops": len(stops),
        "walk": sum(meters_between(a, b) for a, b in pairwise(path)),
        "retraced": retraced_meters(path, [Coordinates(lat=r.lat, lng=r.lng) for r in stops]),
        "ms": ms,
    }


def pct(values: list[float], q: int) -> float:
    return statistics.quantiles(values, n=100)[q - 1] if len(values) > 1 else values[0]


def report(results: list[dict]) -> None:
    print(
        f"{'budget':>7} {'runs':>5} {'full':>6} {'spur':>6} {'>50m':>6} {'retr p50/p95':>14} "
        f"{'walk/budget':>12} {'ms p50/p95':>12}"
    )
    for budget in (*BUDGETS, None):
        mine = [r for r in results if budget is None or r["budget"] == budget]
        if not mine:
            continue
        retraced = [r["retraced"] for r in mine]
        ms = [r["ms"] for r in mine]
        ratio = [r["walk"] / r["budget"] for r in mine]
        print(
            f"{budget or 'all':>7} {len(mine):>5} "
            f"{sum(r['stops'] == ROUTE_SIZE for r in mine) / len(mine):>6.0%} "
            f"{sum(x >= 1 for x in retraced) / len(mine):>6.0%} "
            f"{sum(x > 50 for x in retraced) / len(mine):>6.0%} "
            f"{pct(retraced, 50):>6.0f}/{pct(retraced, 95):<6.0f}m "
            f"{statistics.median(ratio):>11.2f} "
            f"{pct(ms, 50):>5.0f}/{pct(ms, 95):<5.0f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--scenario", choices=[*ROUTE_SCENARIOS, "all"], help="plant and bench seed_dev --routes"
    )
    args = parser.parse_args()
    if not ROUTING_URL:
        raise SystemExit("ROUTING_URL is unset: without streets there are no spurs to measure")

    names = [*ROUTE_SCENARIOS] if args.scenario == "all" else [args.scenario]
    with get_session() as session:
        for name in names:
            around = (LAT, LNG)
            if name:
                around, planted = scenario(session, name, args.seed)
                print(f"\n{name}, {planted} places: {ROUTE_SCENARIOS[name]}")
            rng = random.Random(args.seed)
            report([run(session, rng, rng.choice(BUDGETS), around) for _ in range(args.runs)])
        session.rollback()


if __name__ == "__main__":
    main()
