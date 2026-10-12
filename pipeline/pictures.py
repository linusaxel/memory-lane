"""Picture-first memories: a Commons picture of a moment, placed and told
(docs/10, *A picture can be the memory*).

    python -m pipeline.pictures --source <id>           # bills: looks, prints
    python -m pipeline.pictures --source <id> --save    # and saves

For each pending picture of a `commons` source: its licence is checked, the
model looks at the picture with its caption and says whether it shows a
moment worth standing at, where, when, and writes the few lines beside it.
Commons' own point wins over a geocoded venue. The picture is the memory's
first picture, so enrichment leaves it be. It is scored with the picture in
view before it is saved, and one under GOOD is never made.
"""

import argparse
import json
import re
import urllib.parse

import anthropic
from sqlalchemy import text

from crawler import commons
from pipeline import enrich, extract, geocode, tasks, walk_score
from pipeline.config import ANTHROPIC_API_KEY, LAUNCH_BBOX
from pipeline.db import get_session
from pipeline.tags import TAGS

LOOK_PROMPT = """You look at one picture of Copenhagen from Wikimedia Commons, with its
caption, date, categories and the point Commons gives it. A walker standing
on that spot will see the picture on their phone with a few lines beside it.

- moment: true if something is happening in it that a walker standing there
  today would be glad to see: people doing something, an event, a crowd, a
  famous person, the harbour frozen, a street as it was with life in it.
  False for a building with nothing going on, a portrait with no place, an
  object, a map, a document, a view anyone could take today.
- occasion: true if the caption, date or categories say what was going on -
  the event, the occasion, who is in it - and not only where it was taken.
- striking: 1-5, how much the picture holds the eye on a phone. 5 is a
  picture people would stop to look at; a pleasant tourist snapshot is 2.
- venue: where to stand, as today's map of Copenhagen names it, in Danish
  ("Kongens Nytorv", "Rådhuspladsen", "Nyhavn 17"). From the caption, the
  categories or what the picture plainly shows; null if none of them says.
- address: street and number if known, else null.
- happened_at: ISO date ("1972-04-23", "1972-04", "1972") and its precision,
  from the date or caption; nulls if neither says.
- summary: 30 to 80 words, past tense, English, beside the picture. The
  walker can see it: do not describe it. Tell what was going on - the
  occasion, who, when, what came of it - from the caption, the date and the
  categories, and anyone named, introduced. No name, fact, cause or feeling
  of your own: what came of it only if the caption says. Never "this photo
  shows" or "in this picture".
- tags: 1 to 3 from the list."""

LOOK_SCHEMA = {
    "type": "object",
    "properties": {
        "moment": {"type": "boolean"},
        "occasion": {"type": "boolean"},
        "striking": {"type": "integer"},
        "venue": extract._NULLABLE_STRING,
        "address": extract._NULLABLE_STRING,
        "happened_at": extract._NULLABLE_STRING,
        "happened_precision": {
            "anyOf": [
                {"type": "string", "enum": ["day", "month", "year", "decade"]},
                {"type": "null"},
            ]
        },
        "summary": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string", "enum": list(TAGS)}},
    },
    "required": [
        "moment",
        "occasion",
        "striking",
        "venue",
        "address",
        "happened_at",
        "happened_precision",
        "summary",
        "tags",
    ],
    "additionalProperties": False,
}

STRIKING = 4
GOOD = 6

PENDING = """SELECT c.id, c.url, c.title, t.full_text FROM content c
JOIN transcripts t ON t.content_id = c.id
WHERE c.source_id = :s AND NOT c.memories_extracted AND NOT c.extraction_failed ORDER BY c.id"""


def look(session, client, cid: int, f: dict, caption: str) -> dict | None:
    user = [
        extract.image_block(f["thumb"]),
        {"type": "text", "text": caption},
    ]
    raw = extract._stored_request(session, client, cid, 0, LOOK_PROMPT, user, LOOK_SCHEMA)
    return json.loads(raw) if raw else None


def spot(seen: dict, f: dict) -> tuple[float, float] | None:
    """Commons' point, or the venue on the map; None outside the launch area."""
    if f["lat"] is not None:
        at = (f["lat"], f["lng"])
    elif seen["venue"]:
        hit = geocode.place(seen["address"], seen["venue"], "Copenhagen", "DK", None, None)
        at = hit and hit[:2]
    else:
        at = None
    if at and LAUNCH_BBOX and not extract._in_box(*at, LAUNCH_BBOX):
        return None
    return at


def series(caption: str) -> str:
    """A caption without its numbers: a photographer uploads one show as
    "... 01", "... 02", and each was looked at and saved (13 of one Kings of
    Convenience matinee at Vega). The retelling check misses them: each is
    hidden under GOOD before the next is saved, and it only sees visible ones."""
    return re.sub(r"[\W\d_]+", " ", caption.lower()).strip()[:120]


def card(
    session, client, cid: int, page: str, caption: str, looked: set
) -> tuple[dict, dict] | None:
    name = urllib.parse.unquote(page.rsplit("File:", 1)[-1]).replace("_", " ")
    found = commons.files(["File:" + name])
    if not found or not enrich.free(found[0]["license"]):
        print(f"  drop, not free: {found and found[0]['license']}")
        return None
    f = found[0]
    if series(f["caption"]) in looked:
        print("  drop, one of a series already looked at")
        return None
    looked.add(series(f["caption"]))
    seen = look(session, client, cid, f, caption)
    if not seen or not (seen["moment"] and seen["occasion"]) or seen["striking"] < STRIKING:
        print(f"  drop, no moment: {seen and (seen['striking'], seen['summary'][:80])}")
        return None
    at = spot(seen, f)
    if not at:
        print(f"  drop, not placed in the launch area: {seen['venue']}")
        return None
    venue = seen["venue"] or f["title"][5:].rsplit(".", 1)[0]
    mem = {
        "place": venue,
        "summary": seen["summary"],
        "venue": venue,
        "address": seen["address"],
        "locality": "Copenhagen",
        "region": "Capital Region of Denmark",
        "country": "DK",
        "lat": at[0],
        "lng": at[1],
        "location_precision": "exact" if f["lat"] is not None else "street",
        "confidence": "high" if f["lat"] is not None else "medium",
        "happened_at": seen["happened_at"],
        "happened_precision": seen["happened_precision"],
        "tags": seen["tags"],
        "attribution": f"{f['author']}, Wikimedia Commons ({f['license']})",
        "source_url": f["page"],
    }
    picture = {
        "url": f["url"],
        "thumb": f["thumb"],
        "page": f["page"],
        "caption": f["caption"][:300],
        "year": (seen["happened_at"] or "")[:4] or None,
        "author": f["author"],
        "license": f["license"],
    }
    # Scored as the walker meets it, picture and words, before anything is
    # saved: a picture under GOOD is not amazing, and is never made.
    score = walk_score.walk_score(client, f"{venue}: {seen['summary']}", f["thumb"])
    if score is None or score < GOOD:
        print(f"  drop, walk score {score}: {seen['summary'][:80]}")
        return None
    return mem | {"walk_score": score}, picture


def save(session, client, cid: int, mem: dict, picture: dict):
    """The memory, with its picture as the enrichment's first: enrichment only
    fills a memory that has none."""
    extract.save_memories(session, cid, [mem], extract.layer_for("picture"), client)
    session.execute(
        text("""UPDATE memories SET enrichment = CAST(:e AS JSONB), walk_score = :w,
                       walk_score_prompt = :h
                WHERE content_id = :c AND enrichment IS NULL"""),
        {
            "e": json.dumps({"pictures": [picture]}, ensure_ascii=False),
            "w": mem["walk_score"],
            "h": walk_score.PROMPT_HASH,
            "c": cid,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--source", type=int, required=True)
    parser.add_argument("--save", action="store_true", help="save the memories")
    args = parser.parse_args()
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    with get_session() as s:
        looked: set = set()
        for r in s.execute(text(PENDING), {"s": args.source}).fetchall():
            print(f"######## {r.id} {r.title}", flush=True)
            made = card(s, client, r.id, r.url, r.full_text, looked)
            if made:
                print(f"--- {made[0]['venue']}\n{made[0]['summary']}\n{made[1]['url']}\n")
            if args.save:
                if made:
                    save(s, client, r.id, *made)
                s.execute(
                    text("UPDATE content SET memories_extracted = TRUE WHERE id = :id"),
                    {"id": r.id},
                )
                s.commit()
                if made:
                    tasks.after_save(client, r.id)


if __name__ == "__main__":
    main()
