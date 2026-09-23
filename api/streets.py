"""Walking metres and street shapes for today's route, from an OSRM `foot`
sidecar (osrm/build.sh). With ROUTING_URL unset, or the sidecar down, every
answer falls back to crow-flies x ROUTE_CIRCUITY and no shapes - the route
still works, it just draws through buildings.

ponytail: no (place_id, place_id) cache; one local /table is milliseconds.
Add one when the sidecar is remote or billed.
"""

import json
from itertools import pairwise
from urllib.request import urlopen

from api.gate import meters_between
from api.models import Coordinates
from pipeline.config import ROUTING_URL

# A street walk is ~1.2-1.3x the straight line (Boeing 2019,
# https://arxiv.org/abs/1708.00836). Only used when nothing routes on streets.
ROUTE_CIRCUITY = 1.3
TIMEOUT_SECONDS = 2


def _osrm(service: str, points: list[Coordinates], query: str):
    coords = ";".join(f"{p.lng},{p.lat}" for p in points)
    with urlopen(f"{ROUTING_URL}/{service}/v1/foot/{coords}?{query}", timeout=TIMEOUT_SECONDS) as r:
        body = json.load(r)
    if body.get("code") != "Ok":
        raise ValueError(body.get("code"))
    return body


def street_table(points: list[Coordinates]) -> tuple[list[list[float]], list[float] | None]:
    """(d, snaps): d[i][j] is metres on foot from points[i] to points[j], not
    symmetric when streets come back from OSRM; snaps[i] is how far points[i]
    is from the nearest walkable way, or None without streets."""
    if ROUTING_URL and len(points) > 1:
        try:
            body = _osrm("table", points, "annotations=distance")
            d = body["distances"]
            if all(cell is not None for row in d for cell in row):
                return d, [source["distance"] for source in body["sources"]]
        except Exception:
            pass
    return [[meters_between(a, b) * ROUTE_CIRCUITY for b in points] for a in points], None


def walking_matrix(points: list[Coordinates]) -> list[list[float]]:
    """street_table's distances alone."""
    return street_table(points)[0]


def retraced_meters(path: list[Coordinates]) -> float:
    """Metres of `path` that walk a stretch of street already walked, either
    way: the out-and-back to a stop that sits off the loop. Street routes
    reuse the same map nodes, so a retraced segment has the same two ends."""
    seen: set = set()
    total = 0.0
    for a, b in pairwise(path):
        ka, kb = (round(a.lat, 5), round(a.lng, 5)), (round(b.lat, 5), round(b.lng, 5))
        if ka == kb:
            continue
        key = (ka, kb) if ka < kb else (kb, ka)
        if key in seen:
            total += meters_between(a, b)
        else:
            seen.add(key)
    return total


def street_legs(stops: list[Coordinates]) -> list[list[Coordinates]] | None:
    """legs[i] is the street shape from stops[i] to stops[i + 1]. A leg that
    touches where the walk started is that start, so only the preview gets
    those, and nothing stores them (docs/10-decisions.md § Routes)."""
    if not ROUTING_URL or len(stops) < 2:
        return None
    try:
        route = _osrm("route", stops, "overview=false&steps=true&geometries=geojson")
        legs = []
        for leg in route["routes"][0]["legs"]:
            shape: list[Coordinates] = []
            for step in leg["steps"]:
                for lng, lat in step["geometry"]["coordinates"]:
                    at = Coordinates(lat=lat, lng=lng)
                    if not shape or shape[-1] != at:
                        shape.append(at)
            legs.append(shape)
        return legs
    except Exception:
        return None
