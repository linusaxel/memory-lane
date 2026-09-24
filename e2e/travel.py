"""Print walk-and-unlock.yml's `travel` blocks from the walk the API plans now.

    ./e2e/run.sh --keep walk      # leaves the e2e API on :8090, seeded, with OSRM
    venv/bin/python e2e/travel.py [http://localhost:8090]

Paste each block over the matching one in .maestro/walk-and-unlock.yml. If the
stop order printed differs from the file's, the stop names in it change too.
"""

import json
import sys
import urllib.parse
import urllib.request
import uuid

START = (55.67886, 12.57586)  # the flow's setLocation: seed_dev.LAT, LNG
BUDGET_METERS = 4000  # WALK_KM.initial in mobile/src/Plan.tsx


def point(c):
    return f'      - "{c["lat"]:.6f},{c["lng"]:.6f}"'


def main(api):
    query = urllib.parse.urlencode(
        {
            "device": str(uuid.uuid4()),
            "lat": START[0],
            "lng": START[1],
            "budget_meters": BUDGET_METERS,
        }
    )
    with urllib.request.urlopen(f"{api}/v1/routes/preview?{query}") as reply:
        walk = json.load(reply)
    meta = walk["meta"]
    if not meta.get("legs") or not meta.get("out_leg"):
        sys.exit("no street shapes in the preview - is the API running with ROUTING_URL?")

    start = {"lat": START[0], "lng": START[1]}
    for n, (memory, leg) in enumerate(
        zip(walk["memories"], [meta["out_leg"], *meta["legs"]], strict=True), 1
    ):
        if n == 1 and leg[0] != start:
            leg = [start, *leg]
        print(f"# stop {n}: {memory['place']['name']}")
        print("- travel:\n    points:")
        print("\n".join(point(c) for c in leg))
        print("    speed: 10\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090")
