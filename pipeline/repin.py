"""Place the places still on the model's own guess (`geocode_status='llm'`).

    python -m pipeline.repin                    # free: the geocoder chain again, printed
    python -m pipeline.repin --choose           # bills: the model picks from the map's candidates
    python -m pipeline.repin [--choose] --apply # write them

Most were extracted before the chain existed (docs/10-decisions.md
#the-llm-names-the-place-free-geocoders-place-it), so the free pass comes
first. What it can't place, --choose shows the model the stories told there
and the map's candidates (Photon, Wikidata by label, and Wikidata's full-text
search near its guess, which finds "Frederiksberg Gardens" where the label
search wants "Frederiksberg Garden"), one small
call a place. It may pick one or none, never a coordinate of its own: a pick
is stored as `geocode_status='chosen'` at the candidate's own point.
"""

import argparse
import json
import logging
import urllib.parse

from sqlalchemy import text

from pipeline.extract import _request
from pipeline.geocode import (
    MAX_KM_FROM_GUESS,
    PRECISION_M,
    Hit,
    Photon,
    Wikidata,
    _get_json,
    _km,
    place,
    unbracket,
)

logger = logging.getLogger(__name__)

LLM_PLACES = """
    SELECT p.id, p.name, p.venue, p.locality,
           ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng,
           MIN(EXTRACT(YEAR FROM m.happened_at))::int AS year,
           array_agg(m.summary ORDER BY m.id) AS stories
    FROM places p JOIN memories m ON m.place_id = p.id AND NOT m.hidden
    WHERE p.geocode_status = 'llm' AND p.coordinates IS NOT NULL
    GROUP BY p.id
    ORDER BY p.id
"""

CHOOSE_PROMPT = """A story is pinned to a place the map did not find by name. You get the
stories told there and numbered entries from the map. Pick the entry that is
the same place the stories happened at, or -1 if none is. A street is a right
answer only when the story happened along that street. Never pick an entry
only because it is near or similarly named: a wrong pin sends a walker to the
wrong door, and no pin is better."""

CHOOSE_SCHEMA = {
    "type": "object",
    "properties": {"reason": {"type": "string"}, "choice": {"type": "integer"}},
    "required": ["reason", "choice"],
    "additionalProperties": False,
}


# Full-text matches kept, nearest the guess first by Wikidata's own ranking.
NEAR_KM = 3


def wikidata_near(name: str, near: tuple) -> list[Hit]:
    """Items whose text matches the name within NEAR_KM of the guess: a
    story's English name is rarely an item's label prefix."""
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": f"{name} nearcoord:{NEAR_KM}km,{near[0]},{near[1]}",
            "srlimit": 5,
            "format": "json",
        }
    )
    ids = [
        r["title"]
        for r in ((_get_json(f"{Wikidata.API}?{q}") or {}).get("query") or {}).get("search", [])
    ]
    if not ids:
        return []
    q = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "claims|labels",
            "languages": "en|da",
            "format": "json",
        }
    )
    entities = (_get_json(f"{Wikidata.API}?{q}") or {}).get("entities", {})
    hits = []
    for i in ids:
        e = entities.get(i, {})
        coord = e.get("claims", {}).get("P625")
        if not coord or "datavalue" not in coord[0]["mainsnak"]:
            continue
        v = coord[0]["mainsnak"]["datavalue"]["value"]
        labels = e.get("labels", {})
        label = (labels.get("en") or labels.get("da") or {}).get("value")
        hits.append(Hit(v["latitude"], v["longitude"], label, None, None, "poi", "wikidata"))
    return hits


def candidates(name: str, locality: str | None, near: tuple) -> list:
    """Photon's and Wikidata's points for the name, near the guess, one each. Points
    only: a street's point is anywhere along it, and Gammel Toldbod picked as
    Toldbodgade landed 600 m from the door."""
    seen, out = set(), []
    name = unbracket(name)
    found = [*Photon().search(name, locality, near), *Wikidata().search(name, locality, near)]
    for hit in [*found, *wikidata_near(name, near)]:
        key = (round(hit.lat, 4), round(hit.lng, 4))
        if (
            hit.kind not in ("poi", "house")
            or key in seen
            or _km(near, (hit.lat, hit.lng)) > MAX_KM_FROM_GUESS
        ):
            continue
        seen.add(key)
        out.append(hit)
    return out


def choose(client, name: str, stories: list[str], hits: list):
    """The hit the model picked, or None. Only ever one of `hits`."""
    lines = "\n".join(
        f"[{i}] {h.name or ''} {h.street or ''} {h.housenumber or ''} ({h.kind}, {h.source})".strip()
        for i, h in enumerate(hits)
    )
    told = "\n".join(f"- {s}" for s in stories)
    raw = _request(
        client,
        CHOOSE_PROMPT,
        f"Pinned as: {name}\n\nStories:\n{told}\n\nMap:\n{lines}",
        CHOOSE_SCHEMA,
        max_tokens=300,
    )
    try:
        i = json.loads(raw)["choice"]
    except (
        TypeError,
        ValueError,
        KeyError,
    ):
        # Kept exploded with a trailing comma on purpose.
        # See docs/10-decisions.md#except-a-b-stays-exploded
        return None
    return hits[i] if isinstance(i, int) and 0 <= i < len(hits) else None


def repin(session, client=None) -> list[tuple]:
    """(place_id, name, lat, lng, precision, status) for each llm place newly
    placed: by the chain, else (with a client) by the model's pick."""
    found = []
    for r in session.execute(text(LLM_PLACES)).fetchall():
        venue = r.venue or r.name.split(",")[0]
        near = (r.lat, r.lng)
        hit = place(venue, venue, r.locality, "DK", near, r.year)
        if hit:
            found.append((r.id, r.name, *hit))
            continue
        if client is None:
            continue
        hits = candidates(venue, r.locality, near)
        picked = hits and choose(client, r.name, r.stories, hits)
        if picked:
            found.append((r.id, r.name, picked.lat, picked.lng, PRECISION_M[picked.kind], "chosen"))
    return found


def apply(session, found: list[tuple]):
    for place_id, _, lat, lng, precision, status in found:
        session.execute(
            text("""
                UPDATE places SET
                    coordinates = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    precision_meters = :precision, geocode_status = :status,
                    geocoded_at = CURRENT_TIMESTAMP
                WHERE id = :id AND geocode_status = 'llm'
            """),
            {"id": place_id, "lat": lat, "lng": lng, "precision": precision, "status": status},
        )
    session.commit()


def main():
    import anthropic

    from pipeline.config import ANTHROPIC_API_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--choose", action="store_true", help="the model picks; bills")
    parser.add_argument("--apply", action="store_true", help="write them")
    args = parser.parse_args()
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if args.choose else None
    with get_session() as session:
        left = len(session.execute(text(LLM_PLACES)).all())
        found = repin(session, client)
        for place_id, name, lat, lng, precision, status in found:
            print(f"[{place_id}] {name} -> {lat:.5f},{lng:.5f} ±{precision}m ({status})")
            print(f"    https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=18/{lat}/{lng}")
        print(f"{len(found)} of {left} llm places placed")
        if args.apply and found:
            apply(session, found)
            print("written")
        elif not args.apply:
            print("nothing changed - pass --apply to write them")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
