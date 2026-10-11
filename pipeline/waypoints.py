"""Plain lockets: the named spots a walk collects between its memories.

    python -m pipeline.waypoints                 # the launch area
    python -m pipeline.waypoints --box s,w,n,e   # another one

A waypoint is a place, not a story, so it needs no gate and no model: OSM's
monuments, memorials, landmark buildings, churches, artworks, fountains,
viewpoints, squares and parks, with a name. Thinned so no two stand within `SPACING_M`, and none on a memory's spot.
A rerun only adds: a waypoint a walk names keeps its id.
See docs/10-decisions.md#the-locket-keeper-most-stops-are-plain-lockets.
OSM is ODbL: credit "© OpenStreetMap contributors".
"""

import argparse
import json
import math
import urllib.parse

from sqlalchemy import text

from crawler.gutenberg import download
from pipeline.config import LAUNCH_BBOX, OVERPASS_URL

USER_AGENT = "memory-lane/1.0 (+https://github.com/linusaxel/memory-lane)"
SPACING_M = 100
CLEAR_M = 40
# Most telling first: where two crowd, the earlier kind stays.
KINDS = (
    "memorial",
    "monument",
    "historic",
    "landmark",
    "church",
    "artwork",
    "fountain",
    "viewpoint",
    "attraction",
    "square",
    "park",
)


def query_for(box: tuple[float, float, float, float]) -> str:
    b = "({},{},{},{})".format(*box)
    return (
        "[out:json][timeout:180];("
        f'nwr["historic"]["name"]{b};'
        f'nwr["tourism"~"^(artwork|viewpoint|attraction)$"]["name"]{b};'
        f'nwr["amenity"="place_of_worship"]["name"]{b};'
        f'nwr["building"]["wikidata"]["name"]{b};'
        f'nwr["amenity"="fountain"]["name"]{b};'
        f'nwr["place"="square"]["name"]{b};'
        f'nwr["leisure"="park"]["name"]{b};'
        ");out center tags;"
    )


def kind(tags: dict) -> str | None:
    historic = tags.get("historic")
    if historic in ("memorial", "monument"):
        return historic
    if historic:
        return "historic"
    if tags.get("building") and tags.get("wikidata"):
        return "landmark"
    if tags.get("amenity") == "place_of_worship":
        return "church"
    if tags.get("tourism") in ("artwork", "viewpoint", "attraction"):
        return tags["tourism"]
    if tags.get("amenity") == "fountain":
        return "fountain"
    if tags.get("place") == "square":
        return "square"
    if tags.get("leisure") == "park":
        return "park"
    return None


def candidates(elements: list[dict]) -> list[dict]:
    """{osm_id, name, kind, lat, lng} for each named element of a known kind."""
    out = []
    for e in elements:
        tags = e.get("tags", {})
        k = kind(tags)
        at = e.get("center") or e
        if k and tags.get("name") and "lat" in at:
            out.append(
                {
                    "osm_id": f"{e['type']}/{e['id']}",
                    "name": tags["name"],
                    "kind": k,
                    "lat": at["lat"],
                    "lng": at["lon"],
                }
            )
    return out


class _Grid:
    """Points bucketed by a cell `size_m` wide, so `near` looks at nine cells."""

    def __init__(self, size_m: float):
        self.size = size_m / 111_320
        self.cells: dict[tuple[int, int], list[tuple[float, float]]] = {}

    def _cell(self, lat, lng):
        return int(lat // self.size), int(lng * math.cos(math.radians(lat)) // self.size)

    def add(self, lat, lng):
        self.cells.setdefault(self._cell(lat, lng), []).append((lat, lng))

    def near(self, lat, lng, metres) -> bool:
        i, j = self._cell(lat, lng)
        return any(
            _metres(lat, lng, a, b) < metres
            for di in (-1, 0, 1)
            for dj in (-1, 0, 1)
            for a, b in self.cells.get((i + di, j + dj), ())
        )


def _metres(lat1, lng1, lat2, lng2) -> float:
    x = math.radians(lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(x, math.radians(lat2 - lat1)) * 6_371_000


def thin(found: list[dict], kept: list[tuple], memories: list[tuple]) -> list[dict]:
    """The found waypoints to add: none within SPACING_M of another or of one
    already `kept`, none within CLEAR_M of a memory. Greedy, best kind first."""
    spaced, spots = _Grid(SPACING_M), _Grid(CLEAR_M)
    for lat, lng in kept:
        spaced.add(lat, lng)
    for lat, lng in memories:
        spots.add(lat, lng)
    added = []
    for w in sorted(found, key=lambda w: KINDS.index(w["kind"])):
        if spaced.near(w["lat"], w["lng"], SPACING_M) or spots.near(w["lat"], w["lng"], CLEAR_M):
            continue
        spaced.add(w["lat"], w["lng"])
        added.append(w)
    return added


def load(session, box=LAUNCH_BBOX) -> int:
    """Add the waypoints in `box` that thinning keeps; return how many."""
    found = json.loads(
        download(f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': query_for(box)})}", USER_AGENT)
    )
    known = {r[0] for r in session.execute(text("SELECT osm_id FROM waypoints"))}
    point = "ST_Y(coordinates::geometry), ST_X(coordinates::geometry)"
    kept = session.execute(text(f"SELECT {point} FROM waypoints")).fetchall()
    memories = session.execute(
        text(f"""
            SELECT {point} FROM places p
            WHERE coordinates IS NOT NULL
              AND EXISTS (SELECT 1 FROM memories m WHERE m.place_id = p.id)
        """)
    ).fetchall()
    fresh = [w for w in candidates(found.get("elements", [])) if w["osm_id"] not in known]
    added = thin(fresh, kept, memories)
    for w in added:
        session.execute(
            text("""
                INSERT INTO waypoints (osm_id, name, kind, coordinates)
                VALUES (:osm_id, :name, :kind, ST_MakePoint(:lng, :lat)::geography)
            """),
            w,
        )
    return len(added)


def main():
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--box", help="south,west,north,east (default: LAUNCH_BBOX)")
    args = parser.parse_args()
    box = tuple(float(x) for x in args.box.split(",")) if args.box else LAUNCH_BBOX
    with get_session() as session:
        print(f"{load(session, box)} waypoints added")


if __name__ == "__main__":
    main()
