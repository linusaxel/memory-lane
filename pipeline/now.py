"""What stands on a memory's spot today, from OpenStreetMap.

    python -m pipeline.now               # every building-level place not yet looked at
    python -m pipeline.now --place 42    # one, printed
    python -m pipeline.now --again       # the confirmed ones too, for a new field

A contrast the model writes is a guess about the present ("current use
unknown"). This asks OSM which named building or amenity the pin stands
inside, and only then writes the "now" side: "Still Rigshospitalet, a
hospital." or "Now Designmuseum Danmark, a museum." The model's score gives
way to the name match: the same place scores low, a different one high.
When the OSM area carries a `wikidata` tag, the item's inception (P571) adds
the year: "Still Børsen, a stock exchange, since 1619."

Free, no key. Only pins a geocoder put on a building: a model's guess or a
street's middle stands inside whatever happens to be there.
"""

import argparse
import json
import logging
import re
import time
import urllib.parse

from sqlalchemy import text

from pipeline import geocode
from pipeline.config import OVERPASS_URL

logger = logging.getLogger(__name__)

# The tags that say what a place is, most telling first. Landuse is left out:
# "Hellebæksgade Stefansgade (residential)" is a neighbourhood, not a place.
KINDS = ("amenity", "tourism", "shop", "leisure", "office", "craft", "building", "historic")
# ponytail: a flat score from a name match. A cinema renamed ("Palads Teatret",
# now "Palads Biograferne") reads as changed; compare kinds if that misleads.
STILL, CHANGED = 0.2, 0.9
# ponytail: areas only. A bar is usually an OSM point, which needs an `around`
# query the public server times out on; a self-hosted Overpass can ask it.


class LookupFailed(Exception):
    """Overpass did not answer. The place is looked at again next run."""


def _names(tags: dict) -> list[str]:
    """Every name it goes by today. `old_name` is not one: a pin inside what was
    Frederiks Hospital and is now Designmuseum Danmark has changed."""
    return [
        v
        for k, v in tags.items()
        if k in ("name", "alt_name", "official_name", "short_name") or k.startswith("name:")
    ]


def _kind(tags: dict) -> str | None:
    """ "museum" from tourism=museum; None for building=yes, which says nothing."""
    for k in KINDS:
        if tags.get(k) and tags[k] != "yes":
            return tags[k].replace("_", " ")
    return None


def since(qid: str | None) -> int | None:
    """The earliest year Wikidata says it began (P571), or None. A building's
    year or an institution's founding: "since" is true of both. A date known
    only to the decade or century is no year."""
    if not qid or not re.fullmatch(r"Q\d+", qid):
        return None
    params = {"action": "wbgetentities", "ids": qid, "props": "claims", "format": "json"}
    found = geocode._get_json(f"{geocode.Wikidata.API}?{urllib.parse.urlencode(params)}")
    if found is None:
        raise LookupFailed(qid)
    claims = found.get("entities", {}).get(qid, {}).get("claims", {}).get("P571", [])
    values = [c["mainsnak"].get("datavalue", {}).get("value", {}) for c in claims]
    years = [
        int(v["time"][1:].split("-")[0])
        for v in values
        if v.get("time", "").startswith("+") and v.get("precision", 0) >= 9
    ]
    return min(years, default=None)


def now_at(lat: float, lng: float, venue: str | None) -> dict:
    """{"name", "kind", "same"} for what the pin stands inside, or {} when OSM
    names nothing there. A different name counts only with a kind: a bare
    "building=yes" around a hot-dog stand is not what stands there now."""
    query = (
        f"[out:json][timeout:10];is_in({lat},{lng})->.a;area.a[name][!boundary][!place];out tags;"
    )
    found = geocode._get_json(f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': query})}")
    if found is None:
        raise LookupFailed((lat, lng))
    areas = [e["tags"] for e in found.get("elements", []) if any(k in e["tags"] for k in KINDS)]
    for tags in areas:
        hits = (geocode.Hit(lat, lng, n, None, None, "poi", "osm") for n in _names(tags))
        if any(geocode._same_venue(venue, h) for h in hits):
            return _found(tags, True)
    for tags in areas:
        if _kind(tags):
            return _found(tags, False)
    return {}


def _found(tags: dict, same: bool) -> dict:
    found = {"name": tags["name"], "kind": _kind(tags), "same": same}
    year = since(tags.get("wikidata"))
    return found | {"since": year} if year else found


def clause(now: dict) -> str:
    kind = f", {'an' if now['kind'][0] in 'aeiou' else 'a'} {now['kind']}" if now["kind"] else ""
    year = f", since {now['since']}" if now.get("since") else ""
    return f"{'Still' if now['same'] else 'Now'} {now['name']}{kind}{year}."


def look_up(
    session, place_id: int | None = None, content_id: int | None = None, again: bool = False
) -> dict:
    """Store what OSM says on each building-level place not yet looked at, then
    write the clause onto the extracted memories there. {place_id: now}.
    content_id keeps it to that content's places: the backlog is `main`'s job.
    again looks at the confirmed places once more."""
    rows = session.execute(
        text("""
            SELECT id, venue, name,
                   ST_Y(coordinates::geometry) AS lat, ST_X(coordinates::geometry) AS lng
            FROM places
            WHERE (now IS NULL OR (:again AND now->>'name' IS NOT NULL)) AND coordinates IS NOT NULL AND precision_meters <= 50
              AND geocode_status IN ('dawa', 'photon', 'wikidata', 'chosen')
              AND (CAST(:place_id AS INTEGER) IS NULL OR id = :place_id)
              AND (CAST(:content_id AS INTEGER) IS NULL
                   OR id IN (SELECT place_id FROM memories WHERE content_id = :content_id))
            ORDER BY id
        """),
        {"place_id": place_id, "content_id": content_id, "again": again},
    ).fetchall()
    done = {}
    for n, r in enumerate(rows):
        if n:
            time.sleep(1)  # the public server's fair use
        try:
            now = now_at(r.lat, r.lng, r.venue or r.name.split(",")[0])
        except LookupFailed:
            logger.warning("Overpass did not answer for place %s; it stays unlooked", r.id)
            time.sleep(10)  # a refusal is usually a rate limit, and the next one would be too
            continue
        session.execute(
            text("UPDATE places SET now = CAST(:now AS JSONB) WHERE id = :id"),
            {"now": json.dumps(now), "id": r.id},
        )
        done[r.id] = now
    # Every confirmed place, not only this run's: a memory saved later onto a
    # place already looked at gets its clause too.
    for pid, now in session.execute(
        text("SELECT id, now FROM places WHERE now->>'name' IS NOT NULL")
    ).fetchall():
        session.execute(
            text("""
                UPDATE memories SET contrast_note = :note, contrast_score = :score
                WHERE place_id = :id AND user_id IS NULL
                  AND contrast_note IS DISTINCT FROM :note
            """),
            {"note": clause(now), "score": STILL if now["same"] else CHANGED, "id": pid},
        )
    return done


def main():
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--place", type=int, help="one place, by id")
    parser.add_argument("--again", action="store_true", help="the confirmed places too")
    args = parser.parse_args()
    with get_session() as session:
        done = look_up(session, place_id=args.place, again=args.again)
    for place_id, now in done.items():
        print(f"{place_id}\t{clause(now) if now else '-'}")
    print(f"{len(done)} looked at, {sum(1 for now in done.values() if now)} confirmed")


if __name__ == "__main__":
    main()
