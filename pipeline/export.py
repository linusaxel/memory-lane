"""Hand a customer the corpus without handing them the corpus.

Phase 2.5. The embed is the product for a tourism board that wants a map; this
is for the one that wants rows — an audio guide keying off coordinates, a city
archive cross-referencing its own holdings. The legal posture is the whole
design: short snippets, prominent attribution, deep links to the source at the
right second. Behave like a search engine. Never sell the raw corpus.

So three rules are enforced here and not left to the caller:

- **Snippets, not summaries.** SNIPPET_CHARS of the first sentence. A customer
  who wants the whole thing follows the link, which is the point of the link.
- **Historical only.** A memory somebody filed from their phone belongs to
  them, not to whoever bought a corpus, and there is no consent anywhere in the
  submit flow that says otherwise.
- **Every row carries its attribution and its link**, or it is not exported.
  A row that cannot say where it came from is the one that gets us sued.

    python -m pipeline.export --lat 55.6759 --lng 12.5655 --radius-km 2
    python -m pipeline.export --all --out corpus.json
"""

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime

from sqlalchemy import text

# api/card.py owns the deep link, including the rule that only YouTube honours
# a ?t= offset. Importing it rather than copying it: two implementations of the
# link is exactly the drift the attribution posture cannot afford. The usual
# direction is api -> pipeline; this is the one edge the other way, and it is
# safe because api.card imports nothing from here.
from api.card import source_href
from pipeline.db import get_session

# Enough to know whether to follow the link, not enough to replace it.
SNIPPET_CHARS = 180

# Where a card lives, so an exported row can be shown rather than only read.
# No default host: an export carrying links to localhost is worse than one
# carrying none, because it looks like it works.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

TERMS = (
    "Snippets and links only. Display the attribution with the snippet, link "
    "back to the source, and do not redistribute this file as a dataset."
)

EXPORT_QUERY = """
SELECT
    m.id,
    m.summary,
    m.tags,
    m.happened_at,
    m.timestamp_start,
    m.attribution,
    m.source_url,
    m.contrast_note,
    p.name AS place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) AS lat,
    ST_X(p.coordinates::geometry) AS lng,
    c.title AS content_title,
    c.url AS content_url,
    c.source_name
FROM memories m
JOIN places p ON m.place_id = p.id
LEFT JOIN content c ON m.content_id = c.id
WHERE NOT m.hidden
  AND m.layer = 'historical'
  AND m.user_id IS NULL
  AND p.coordinates IS NOT NULL
  -- The casts are what let one query serve both modes: an untyped NULL bind
  -- has no type for Postgres to plan against, the way LAYER_FILTER casts too.
  AND (CAST(:radius_meters AS float8) IS NULL OR ST_DWithin(
        p.coordinates,
        ST_MakePoint(CAST(:lng AS float8), CAST(:lat AS float8))::geography,
        CAST(:radius_meters AS float8)))
ORDER BY m.id
"""


def snippet(summary: str, limit: int = SNIPPET_CHARS) -> str:
    """The first sentence, or the first `limit` characters cut at a word.

    Cut at a word rather than mid-token so the snippet reads as a quotation and
    not as a truncated database field, and always mark the cut - a customer who
    cannot see that there is more will not go looking for it.
    """
    text_ = " ".join(summary.split())
    stop = text_.find(". ")
    if 0 < stop <= limit:
        return text_[: stop + 1]
    if len(text_) <= limit:
        return text_
    return text_[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def credit(row) -> str | None:
    """Who to name. Explicit attribution first, then the publisher, then the
    title. None means the row cannot say where it came from and is dropped."""
    return row.attribution or row.source_name or row.content_title or None


def record(row) -> dict:
    return {
        "id": row.id,
        "place": {
            "name": row.place_name,
            "lat": row.lat,
            "lng": row.lng,
            "precision_meters": row.precision_meters,
        },
        "snippet": snippet(row.summary),
        "happened_at": row.happened_at.isoformat() if row.happened_at else None,
        "tags": list(row.tags or []),
        "contrast_note": row.contrast_note,
        "attribution": credit(row),
        "source_url": source_href(row),
        "card_url": f"{PUBLIC_BASE_URL}/v1/memories/{row.id}/card" if PUBLIC_BASE_URL else None,
    }


def export(lat=None, lng=None, radius_km=None) -> dict:
    """Every exportable memory, optionally inside one radius.

    A row with nothing to credit and nowhere to link is skipped rather than
    exported bare: the two fields are the terms, so a row missing both is not
    ours to hand over.
    """
    params = {
        "lat": lat,
        "lng": lng,
        "radius_meters": radius_km * 1000 if radius_km is not None else None,
    }
    with get_session() as session:
        rows = session.execute(text(EXPORT_QUERY), params).fetchall()

    memories = [r for r in (record(row) for row in rows) if r["attribution"] and r["source_url"]]
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "terms": TERMS,
        "count": len(memories),
        "memories": memories,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lng", type=float)
    parser.add_argument("--radius-km", type=float)
    parser.add_argument("--all", action="store_true", help="the whole corpus, no radius")
    parser.add_argument("--out", help="write here instead of stdout")
    args = parser.parse_args(argv)

    located = args.lat is not None and args.lng is not None and args.radius_km is not None
    if not located and not args.all:
        parser.error("give --lat, --lng and --radius-km, or --all")

    payload = export(args.lat, args.lng, args.radius_km) if located else export()
    body = json.dumps(payload, indent=2, default=date.isoformat)

    if args.out:
        with open(args.out, "w") as handle:
            handle.write(body + "\n")
        print(f"{payload['count']} memories -> {args.out}", file=sys.stderr)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
