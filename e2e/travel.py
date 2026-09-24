"""Write walk-and-unlock.yml's legs and stop names for the walk from START.

    DATABASE_URL=... ROUTING_URL=... venv/bin/python e2e/travel.py LAT,LNG

e2e/run.sh runs this once per run, after `seed_dev --at LAT,LNG`. It plans the
walk the app will be offered, through api/read.py's own _plan_route on the same
database and streets, and writes:

  e2e/out/legs/N.yml   the street shape to stop N, a flow the journey runFlows
  e2e/out/legs/env     STOPn / WORDSn: each stop's name, and words from its summary

The seed's five stops are the only ones in reach, so every device and every
`again` gets the same five in the same order. Exits 3 when the walk from here
cannot carry the journey (fewer than five stops, or the stack first, whose
sheet pages through three), and run.sh picks another start.
"""

import datetime
import pathlib
import sys
import uuid

from api.models import Coordinates
from api.read import _plan_route
from pipeline.db import get_session

BUDGET_METERS = 4000  # WALK_KM.initial in mobile/src/Plan.tsx
OUT = pathlib.Path(__file__).with_name("out") / "legs"
# Words from each seeded summary, for "the sheet opened on this one".
WORDS = {
    "Where I was standing, dev seed": "filed this one myself",
    "The bench outside, dev seed": "pølsevogn",
    "Along the street, dev seed": "piano into the street",
    "Where the night went long, dev seed": "jukebox on shuffle",
    "The corner, dev seed": "taxi that reversed",
}


def main(start: Coordinates) -> None:
    with get_session() as session:
        stops, legs, ends = _plan_route(
            session, str(uuid.uuid4()), start, BUDGET_METERS, datetime.date.today()
        )
    if legs is None:
        sys.exit("no street shapes - is ROUTING_URL set and OSRM up?")
    names = [r.place_name for r in stops]
    if len(names) < 5 or names[0] == "The corner, dev seed":
        print(f"this start cannot carry the journey: {names}")
        sys.exit(3)

    OUT.mkdir(parents=True, exist_ok=True)
    env = []
    for n, (name, leg) in enumerate(zip(names, [ends["out"], *legs], strict=True), 1):
        points = [start, *leg] if n == 1 else leg
        (OUT / f"{n}.yml").write_text(
            "appId: ${APP_ID}\n---\n- travel:\n    points:\n"
            + "".join(f'      - "{p.lat:.6f},{p.lng:.6f}"\n' for p in points)
            + "    speed: 10\n"
        )
        env += [f"STOP{n}={name}", f"WORDS{n}={WORDS[name]}"]
    (OUT / "env").write_text("\n".join(env) + "\n")
    print(" -> ".join(names))


if __name__ == "__main__":
    lat, lng = (float(x) for x in sys.argv[1].split(","))
    main(Coordinates(lat=lat, lng=lng))
