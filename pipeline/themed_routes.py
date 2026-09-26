"""Which areas could carry themed walks: the check before the job.

    python -m pipeline.themed_routes

TODO.md § Routes plans an offline job that solves one walk per hotspot x tag
from the hotspot's centroid and files it as a draft to review. It is not worth
building until one area has MIN_TAGS tags with ROUTE_SIZE walkable stops each,
and this says whether one does.

A stop is a place, not a memory (`_one_per_place` in api/route_solver.py), and
walkable is what ROUTE_CANDIDATES_QUERY lets onto a walk, less the per-device
unlocks: the job plans for nobody in particular. The reach is the longest walk's,
half of ROUTE_BUDGET_MAX_METERS.

ponytail: no check that a stop is close enough to a street, which needs OSRM,
so a count can run high. The job's own planning drops those stops anyway.
"""

from sqlalchemy import text

from api.gate import today
from api.models import ROUTE_BUDGET_MAX_METERS
from api.queries import COORDINATE_IS_UNIQUE_EXPR, HOTSPOTS_QUERY, VISIBLE
from api.route_solver import ROUTE_SIZE
from pipeline.db import get_session
from pipeline.tags import TAGS

MIN_TAGS = 3

THEMES_QUERY = f"""
SELECT h.label, h.memories, t.tag, COUNT(DISTINCT p.id) AS stops
FROM ({HOTSPOTS_QUERY}) h
JOIN places p
    ON ST_DWithin(p.coordinates, ST_MakePoint(h.lng, h.lat)::geography, :radius_meters)
JOIN memories m ON m.place_id = p.id
CROSS JOIN LATERAL unnest(m.tags) AS t(tag)
WHERE {VISIBLE}
    AND (m.user_id IS NOT NULL OR {COORDINATE_IS_UNIQUE_EXPR})
    AND (m.opens_at IS NULL OR m.opens_at <= CAST(:today AS date))
    AND t.tag = ANY(CAST(:tags AS varchar[]))
GROUP BY h.lat, h.lng, h.label, h.memories, t.tag
HAVING COUNT(DISTINCT p.id) >= :min_stops
ORDER BY h.memories DESC, stops DESC
"""


def themes(session) -> list[tuple[str, int, dict[str, int]]]:
    """(label, memories, {tag: stops}) for each area with any tag of
    ROUTE_SIZE stops, busiest area first."""
    rows = session.execute(
        text(THEMES_QUERY),
        {
            "limit": 1000,
            "radius_meters": ROUTE_BUDGET_MAX_METERS / 2,
            "today": today(),
            "tags": list(TAGS),
            "min_stops": ROUTE_SIZE,
        },
    ).fetchall()
    areas: dict[tuple[str, int], dict[str, int]] = {}
    for r in rows:
        areas.setdefault((r.label, r.memories), {})[r.tag] = r.stops
    return [(label, memories, tags) for (label, memories), tags in areas.items()]


def main() -> None:
    with get_session() as session:
        found = themes(session)
    for label, memories, tags in found:
        mark = "ready" if len(tags) >= MIN_TAGS else "     "
        counts = ", ".join(f"{t} {n}" for t, n in tags.items())
        print(f"{mark} {label or '?':<24} {memories:>6} memories  {counts}")
    ready = sum(len(tags) >= MIN_TAGS for _, _, tags in found)
    print(f"ready: {ready} areas with {MIN_TAGS}+ tags of {ROUTE_SIZE}+ walkable stops")


if __name__ == "__main__":
    main()
