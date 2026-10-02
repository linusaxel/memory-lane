"""Write walk-and-unlock.yml's legs and stop names for the walk from START.

    DATABASE_URL=... ROUTING_URL=... venv/bin/python e2e/travel.py LAT,LNG

e2e/run.sh runs this once per run, after `seed_dev --at LAT,LNG`. It plans the
walk the app will be offered, through api/route_solver.py's _plan_route on the same
database and streets, and writes:

  e2e/out/legs/N.yml   the walk to stop N, a flow the journey runFlows: two
                       setLocations, halfway along the street shape and the
                       stop. Not `travel`, which spends 50 fixes (~6s) on
                       every segment however short
  e2e/out/legs/env     STOPn / WORDSn: each stop's name, and words from its summary;
                       BENCH_LAT / BENCH_LNG: the bench, stood on from the map
                       with no walk (subscribe-when-out-of-keys)

The 4 km default is four stops, and run.sh leaves the seed only four in reach,
so every device and every `again` gets the same four in the same order.
Exits 3 when the walk from here cannot carry the journey (fewer than four
stops, no bench, or the stack first, whose sheet pages through three), and
run.sh picks another start.
"""

import datetime
import pathlib
import sys
import uuid

from api.models import Coordinates
from api.route_solver import _plan_route
from pipeline.db import get_session

BUDGET_METERS = 4000  # WALK_KM.initial in mobile/src/Plan.tsx
OUT = pathlib.Path(__file__).with_name("out") / "legs"
# Words from each seeded summary, for "the sheet opened on this one".
WORDS = {
    "Where I was standing, dev seed": "filed this one myself",
    "Ringkaféen, dev seed": "Lygteå",
    "Nørrebrogade bridge, dev seed": "swam to the other side",
    "Where the night went long, dev seed": "jukebox on shuffle",
    "Woodstock, dev seed": "mortared it in",
}


def main(start: Coordinates) -> None:
    with get_session() as session:
        stops, legs, ends = _plan_route(
            session, str(uuid.uuid4()), start, BUDGET_METERS, datetime.date.today()
        )
    if legs is None:
        sys.exit("no street shapes - is ROUTING_URL set and OSRM up?")
    names = [r.place_name for r in stops]
    if len(names) < 4 or names[0] == "Woodstock, dev seed" or "Ringkaféen, dev seed" not in names:
        print(f"this start cannot carry the journey: {names}")
        sys.exit(3)

    OUT.mkdir(parents=True, exist_ok=True)
    env = []
    for n, (name, leg) in enumerate(zip(names, [ends["out"], *legs], strict=True), 1):
        # Two fixes a leg, halfway and the stop: every setLocation is a driver
        # round trip, and a walk turn by turn spent most of the journey on them.
        points = [leg[len(leg) // 2], leg[-1]]
        (OUT / f"{n}.yml").write_text(
            "appId: ${APP_ID}\n---\n"
            + "".join(
                f"- setLocation:\n    latitude: {p.lat:.6f}\n    longitude: {p.lng:.6f}\n"
                for p in points
            )
        )
        env += [f"STOP{n}={name}", f"WORDS{n}={WORDS[name]}"]
    [bench] = [r for r in stops if r.place_name == "Ringkaféen, dev seed"]
    env += [f"BENCH_LAT={bench.lat:.6f}", f"BENCH_LNG={bench.lng:.6f}"]
    (OUT / "env").write_text("\n".join(env) + "\n")
    print(" -> ".join(names))


if __name__ == "__main__":
    lat, lng = (float(x) for x in sys.argv[1].split(","))
    main(Coordinates(lat=lat, lng=lng))
