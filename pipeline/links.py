"""Link the names in a summary to Wikipedia.

    python -m pipeline.links               # every extracted memory not yet looked at
    python -m pipeline.links --memory 42   # one, printed

The model names who and what in the summary an encyclopedia would know about,
as written and by its full name ("Christiansborg" is "Christiansborg
Palace"). Wikidata, not the model, says which article that is, and a name is
linked only when exactly one entity answers to it, with an article or without:
a wrong Stauning is worse than no link. Found live 2026-09-30: five entities
are called exactly "Christiansborg", and the one with an English article was a
slave ship. The
links sit beside the story and never replace it, so the rule against
Wikipedia-grade facts as content (docs/10-decisions.md) still holds.

Bills a little (one short model call per memory). Aggregation runs it on each
new video's memories; this command is the backfill.
"""

import argparse
import json
import logging
import urllib.parse

from sqlalchemy import text

from pipeline import geocode
from pipeline.extract import _request

logger = logging.getLogger(__name__)

# ponytail: English first, since the summaries are English, then the one city's
# language. Take the place's country's wiki when a second country lands.
WIKIS = ("enwiki", "dawiki")

# Entities that share a name with the subject and are never it: "Stauning" is
# also a family name, a village and a disambiguation page.
NOT_A_SUBJECT = frozenset(
    {
        "Q4167410",  # disambiguation page
        "Q101352",  # family name
        "Q202444",  # given name
        "Q4167836",  # category
        "Q13406463",  # list
    }
)

PROMPT = """The text is a short story told at a place. List the proper names in it
that an encyclopedia has an article about: well-known people, buildings,
institutions, organisations, events and works.

For each, `text` is the name exactly as the text writes it, and `name` is its
full, usual English name as an encyclopedia titles it ("Tivoli" is "Tivoli
Gardens"; often the two are the same). Leave out private people and anyone
known only from this story, streets, districts, cities and countries, and generic
words ("the bar", "the harbour"). An empty list is a fine answer."""

SCHEMA = {
    "type": "object",
    "properties": {
        "names": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "name": {"type": "string"}},
                "required": ["text", "name"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["names"],
    "additionalProperties": False,
}


class LookupFailed(Exception):
    """Wikidata did not answer. The memory is looked at again next run rather
    than stored with no links."""


def _wikidata(params: dict):
    found = geocode._get_json(
        f"{geocode.Wikidata.API}?" + urllib.parse.urlencode(params | {"format": "json"})
    )
    if found is None:
        raise LookupFailed(params)
    return found


def wikipedia_url(name: str, near: tuple | None) -> str | None:
    """The article of the one entity called exactly `name`, or None: two
    answers are no answer even when only one has an article. A place
    far from the pin is somewhere else with the same name (Christiansborg is
    also a castle in Ghana), the way geocode.place judges a hit."""
    found = _wikidata({"action": "wbsearchentities", "search": name, "language": "en", "limit": 7})
    ids = [
        s["id"]
        for s in found.get("search", [])
        if s.get("match", {}).get("text", "").casefold() == name.casefold()
    ]
    if not ids:
        return None
    entities = _wikidata(
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "claims|sitelinks/urls",
            "sitefilter": "|".join(WIKIS),
        }
    ).get("entities", {})

    candidates = []
    for i in ids:
        e = entities.get(i, {})
        claims = e.get("claims", {})
        kinds = {
            c["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
            for c in claims.get("P31", [])
        }
        if kinds & NOT_A_SUBJECT:
            continue
        coord = claims.get("P625")
        if near and coord and "datavalue" in coord[0]["mainsnak"]:
            v = coord[0]["mainsnak"]["datavalue"]["value"]
            if geocode._km(near, (v["latitude"], v["longitude"])) > geocode.MAX_KM_FROM_GUESS:
                continue
        sitelinks = e.get("sitelinks", {})
        candidates.append(next((sitelinks[w]["url"] for w in WIKIS if w in sitelinks), None))
    return candidates[0] if len(candidates) == 1 else None


def links_for(client, summary: str, near: tuple | None) -> list[dict] | None:
    """[{"text", "url"}] for the names that resolved, or None when the model
    did not answer. A name the summary does not contain is the model's, not the
    story's, and is dropped."""
    raw = _request(client, PROMPT, summary, SCHEMA)
    if raw is None:
        return None
    try:
        names = json.loads(raw)["names"]
    except (
        ValueError,
        KeyError,
    ):
        # Kept exploded with a trailing comma on purpose.
        # See docs/10-decisions.md#except-a-b-stays-exploded
        logger.warning("Unparseable names: %s", raw[:200])
        return None
    links, seen = [], set()
    for n in names:
        written, name = n["text"].strip(), n["name"].strip() or n["text"].strip()
        if not written or written in seen or written not in summary:
            continue
        seen.add(written)
        url = wikipedia_url(name, near)
        if url:
            links.append({"text": written, "url": url})
    return links


def link_memories(session, client, content_id: int | None = None, memory_id: int | None = None):
    """Look up every extracted memory whose links are still null; return
    {memory_id: links}. Only extracted ones: what a person filed is theirs."""
    rows = session.execute(
        text("""
            SELECT m.id, m.summary,
                   ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng
            FROM memories m JOIN places p ON p.id = m.place_id
            WHERE m.links IS NULL AND m.user_id IS NULL
              AND (CAST(:content_id AS INTEGER) IS NULL OR m.content_id = :content_id)
              AND (CAST(:memory_id AS INTEGER) IS NULL OR m.id = :memory_id)
            ORDER BY m.id
        """),
        {"content_id": content_id, "memory_id": memory_id},
    ).fetchall()
    done = {}
    for r in rows:
        near = (r.lat, r.lng) if r.lat is not None else None
        try:
            links = links_for(client, r.summary, near)
        except LookupFailed:
            logger.warning("Wikidata did not answer for memory %s; it stays unlinked", r.id)
            continue
        if links is None:
            continue
        session.execute(
            text("UPDATE memories SET links = CAST(:links AS JSONB) WHERE id = :id"),
            {"links": json.dumps(links), "id": r.id},
        )
        done[r.id] = links
    return done


def main():
    import anthropic

    from pipeline.config import ANTHROPIC_API_KEY
    from pipeline.db import get_session

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--memory", type=int, help="one memory, by id")
    args = parser.parse_args()
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    with get_session() as session:
        done = link_memories(session, client, memory_id=args.memory)
    linked = sum(1 for links in done.values() if links)
    for memory_id, links in done.items():
        for link in links:
            print(f"{memory_id}\t{link['text']}\t{link['url']}")
    print(f"{len(done)} looked at, {linked} with a link")


if __name__ == "__main__":
    main()
