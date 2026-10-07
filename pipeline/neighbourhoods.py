"""Neighbourhood outlines from OpenStreetMap, for "Where stories wait"
(docs/10-decisions.md#where-stories-wait). Free and any city: one Overpass
query for the administrative boundaries at one level inside an area.

    python -m pipeline.neighbourhoods --area "Københavns Kommune" --level 10
    python -m pipeline.neighbourhoods --area "Frederiksberg Kommune" --level 7

Copenhagen's bydele should be level 10; Frederiksberg has none, so it is
itself one. Unchecked against live Overpass: TODO.md, *Load the neighbourhoods*.
"""

import argparse
import urllib.parse

from sqlalchemy import text

from pipeline import geocode
from pipeline.config import OVERPASS_URL

QUERY = (
    '[out:json][timeout:120];area["name"="{area}"]["boundary"="administrative"]->.a;'
    'rel(area.a)["boundary"="administrative"]["admin_level"="{level}"];out geom;'
)

# The outer ways, polygonized: OSM draws a boundary as ways that meet end to
# end. ponytail: inner rings are left out, a hole in a neighbourhood counts as
# in it; add them as holes if a city has one that matters.
UPSERT = """
INSERT INTO neighbourhoods (id, name, outline)
SELECT :id, :name,
    ST_Multi(ST_CollectionExtract(ST_Polygonize(ST_GeomFromText(w, 4326)), 3))::geography
FROM unnest(CAST(:ways AS text[])) w
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, outline = EXCLUDED.outline
"""


def outlines(found: dict) -> list[dict]:
    """Each relation as {id, name, ways}, its outer ways as WKT linestrings."""
    rows = []
    for rel in found.get("elements", []):
        ways = [
            "LINESTRING(" + ", ".join(f"{pt['lon']} {pt['lat']}" for pt in m["geometry"]) + ")"
            for m in rel.get("members", [])
            if m.get("type") == "way" and m.get("role") == "outer" and m.get("geometry")
        ]
        name = rel.get("tags", {}).get("name")
        if name and ways:
            rows.append({"id": rel["id"], "name": name, "ways": ways})
    return rows


def fetch(session, area: str, level: int) -> int:
    """Upserts the area's neighbourhoods; how many. None from Overpass is 0."""
    query = QUERY.format(area=area, level=level)
    found = geocode._get_json(f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': query})}")
    rows = outlines(found or {})
    for row in rows:
        session.execute(text(UPSERT), row)
    return len(rows)


def main():
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--area", required=True, help='an OSM boundary name, "Københavns Kommune"')
    parser.add_argument("--level", type=int, default=10, help="the admin_level inside it")
    args = parser.parse_args()
    with get_session() as session:
        print(f"{fetch(session, args.area, args.level)} neighbourhoods in {args.area}")


if __name__ == "__main__":
    main()
