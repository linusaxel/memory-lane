"""The source funnel: find candidates, screen them cheaply, promote the good ones.

    python -m pipeline.sources list                  # every source and its yield
    python -m pipeline.sources discover              # YouTube search over Copenhagen
    python -m pipeline.sources screen 3              # Haiku only, about a cent
    python -m pipeline.sources set 3 trial --note "…"
    python -m pipeline.sources add youtube_channel https://www.youtube.com/@x "X"

A trial is one item extracted by hand: `pipeline.ingest --video <url> --to <id>`,
then `pipeline.enqueue --video <content id>`. See
docs/10-decisions.md#sources-are-rows-with-a-status.
"""

import argparse
import logging

import anthropic
from sqlalchemy import text

from pipeline.config import (
    ANTHROPIC_API_KEY,
    CHUNK_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    MIN_VIDEO_MINUTES,
)
from pipeline.db import get_session
from pipeline.extract import chunk_transcript

logger = logging.getLogger(__name__)

# ponytail: Copenhagen only, by decision (one neighbourhood before a second
# city). A `city` argument when there is a second one.
NEIGHBOURHOODS = (
    "Nørrebro",
    "Vesterbro",
    "Østerbro",
    "Christianshavn",
    "Indre By",
    "Frederiksberg",
    "Amager",
    "Valby",
    "Nordvest",
    "Sydhavnen",
    "Nyhavn",
    "Istedgade",
    "Blågårdsgade",
    "Kødbyen",
)
PHRASES = ("voksede op på {}", "{} minder", "historier fra {}", "growing up in {} Copenhagen")
QUERIES = tuple(p.format(n) for n in NEIGHBOURHOODS for p in PHRASES)
# A search returns tarot readings and accounting webinars for "Valby minder";
# the first run's keepers all named the place in the title.
PLACE_WORDS = tuple(w.casefold() for w in NEIGHBOURHOODS + ("København", "Copenhagen", "Kbh"))


def discover(session, queries=QUERIES, search=None, per_query: int = 20) -> list[dict]:
    """Each channel with a long video that names a Copenhagen place becomes a
    candidate. A channel already in `sources`, rejected ones included, is left
    alone."""
    if search is None:
        from crawler.yt_crawler import search_videos as search

    channels: dict[str, dict] = {}
    for query in queries:
        for video in search(query, per_query):
            # A clip is never extracted, so it says nothing about the channel.
            if (video.get("duration_seconds") or 0) < MIN_VIDEO_MINUTES * 60:
                continue
            if not any(w in (video.get("title") or "").casefold() for w in PLACE_WORDS):
                continue
            c = channels.setdefault(
                video["channel_url"], {"name": video["channel"], "query": query, "hits": []}
            )
            c["hits"].append(video["title"])

    new = []
    for url, c in channels.items():
        added = session.execute(
            text("""
                INSERT INTO sources (kind, locator, name, found_via, note)
                VALUES ('youtube_channel', :url, :name, :found_via, :note)
                ON CONFLICT (locator) DO NOTHING
                RETURNING id
            """),
            {
                "url": url,
                "name": c["name"] or url,
                "found_via": f"search:{c['query']}",
                "note": f"{len(c['hits'])} long hit(s), e.g. {c['hits'][0]!r}",
            },
        ).scalar()
        if added:
            new.append({"id": added, "name": c["name"], "hits": len(c["hits"])})
    return new


def _ingest_sample(row, sample: int):
    """Put `sample` items of the source in `content`, free: listing, captions
    and text fetches cost nothing."""
    from pipeline.ingest import ingest_content, ingest_records

    if row.kind == "youtube_channel":
        from crawler.yt_crawler import list_channel_videos
        from pipeline.transcripts import fetch_pending_transcripts

        videos = [
            v
            for v in list_channel_videos(row.locator, limit=sample * 3)
            if (v.get("duration_seconds") or 0) >= MIN_VIDEO_MINUTES * 60
        ][:sample]
        logger.info("%d long video(s) in the newest %d", len(videos), sample * 3)
        ingest_content({"sources": [{"id": row.id, "name": row.name, "videos": videos}]})
        with get_session() as session:
            ids = session.execute(
                text("SELECT id FROM content WHERE source_id = :id AND NOT transcript_fetched"),
                {"id": row.id},
            ).scalars()
            ids = list(ids)
        if ids:
            fetch_pending_transcripts(ids)
        with get_session() as session:
            failed = session.execute(
                text("SELECT count(*) FROM content WHERE source_id = :id AND transcript_failed"),
                {"id": row.id},
            ).scalar()
        logger.info("%d without captions", failed)
    elif row.kind in ("text", "book"):
        from crawler.sources import SOURCES

        key, _, query = row.locator.partition(":")
        if key not in SOURCES or not query:
            raise SystemExit(f"{row.locator!r}: screen needs '<crawler.sources key>:<query>'")
        src = SOURCES[key]
        ingest_records(src.fetch(query, sample), row.name, src.source_type, source_id=row.id)
    else:
        raise SystemExit(f"nothing fetches a {row.kind} yet")


def screen(source_id: int, sample: int = 3, client=None) -> float | None:
    """Classify every chunk of up to `sample` unscreened items with Haiku. No
    Sonnet, no brief: this is the number that decides whether to spend those.
    Returns the source's pass rate from `source_yield`."""
    from pipeline.tasks import classify_chunk, record_verdict

    with get_session() as session:
        row = session.execute(
            text("SELECT id, kind, locator, name FROM sources WHERE id = :id"), {"id": source_id}
        ).fetchone()
    if not row:
        raise SystemExit(f"no source {source_id}")

    _ingest_sample(row, sample)
    client = client or anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    with get_session() as session:
        items = session.execute(
            text("""
                SELECT c.id, t.segments FROM content c
                JOIN transcripts t ON t.content_id = c.id
                WHERE c.source_id = :id
                  AND NOT EXISTS (SELECT 1 FROM classifier_verdicts v WHERE v.content_id = c.id)
                ORDER BY c.id DESC
                LIMIT :n
            """),
            {"id": source_id, "n": sample},
        ).fetchall()
        for content_id, segments in items:
            chunks = chunk_transcript(segments, CHUNK_MINUTES, CHUNK_OVERLAP_SECONDS)
            for i, chunk in enumerate(chunks):
                has, reason = classify_chunk(client, chunk)
                record_verdict(session, content_id, i, has, reason, chunk)
            logger.info("content %s: %d chunks screened", content_id, len(chunks))
        return session.execute(
            text("SELECT screened FROM source_yield WHERE id = :id"), {"id": source_id}
        ).scalar()


STATUS_ORDER = "array_position(ARRAY['active','trial','candidate','paused','rejected'], status)"


def _blank(v):
    return "" if v is None else v


def _list(session):
    rows = session.execute(
        text(f"""
            SELECT * FROM source_yield
            ORDER BY {STATUS_ORDER}, memories_per_hour DESC NULLS LAST,
                     screened DESC NULLS LAST, id
        """)
    ).fetchall()
    print(
        f"{'id':>3}  {'status':9}  {'kind':15}  {'items':>5}  {'mem':>4}  {'mem/h':>5}  "
        f"{'pass':>4}  name"
    )
    for r in rows:
        print(
            f"{r.id or '':>3}  {r.status:9}  {r.kind:15}  {r.items or 0:>5}  {r.memories or 0:>4}  "
            f"{_blank(r.memories_per_hour):>5}  {_blank(r.screened):>4}  {r.name}"
        )


def main():
    logging.basicConfig(force=True, level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="every source, best first")
    d = sub.add_parser("discover", help="YouTube search over Copenhagen neighbourhoods")
    d.add_argument("--query", action="append", help="instead of the built-in queries")
    d.add_argument("--per-query", type=int, default=20)
    s = sub.add_parser("screen", help="Haiku-classify a few items; no Sonnet")
    s.add_argument("id", type=int)
    s.add_argument("--sample", type=int, default=3)
    st = sub.add_parser("set", help="change a source's status")
    st.add_argument("id", type=int)
    st.add_argument("status", choices=["candidate", "trial", "active", "paused", "rejected"])
    st.add_argument("--note")
    a = sub.add_parser("add", help="a source found by hand")
    a.add_argument(
        "kind", choices=["youtube_channel", "text", "book", "podcast_feed", "institution"]
    )
    a.add_argument("locator", help="channel URL or @handle page, '<key>:<query>', or a URL")
    a.add_argument("name")
    a.add_argument("--language")
    a.add_argument("--status", default="candidate")
    a.add_argument("--licence")
    a.add_argument("--note")
    args = parser.parse_args()

    if args.cmd == "screen":
        rate = screen(args.id, args.sample)
        print("nothing screened" if rate is None else f"pass rate: {rate}")
        return

    with get_session() as session:
        if args.cmd == "list":
            _list(session)
        elif args.cmd == "discover":
            new = discover(session, args.query or QUERIES, per_query=args.per_query)
            for n in new:
                print(f"{n['id']:>4}  {n['hits']} hit(s)  {n['name']}")
            print(f"{len(new)} new candidates")
        elif args.cmd == "set":
            session.execute(
                text("UPDATE sources SET status = :s, note = coalesce(:n, note) WHERE id = :id"),
                {"s": args.status, "n": args.note, "id": args.id},
            )
        elif args.cmd == "add":
            locator = args.locator
            if args.kind == "youtube_channel" and "/channel/" not in locator:
                from crawler.yt_crawler import channel_metadata

                # An @handle and the /channel/<id> a search returns must dedup.
                locator = channel_metadata(locator)["url"] or locator
            added = session.execute(
                text("""
                    INSERT INTO sources (kind, locator, name, language, status, licence, note)
                    VALUES (:kind, :locator, :name, :language, :status, :licence, :note)
                    ON CONFLICT (locator) DO NOTHING RETURNING id
                """),
                {
                    "kind": args.kind,
                    "locator": locator,
                    "name": args.name,
                    "language": args.language,
                    "status": args.status,
                    "licence": args.licence,
                    "note": args.note,
                },
            ).scalar()
            print(f"added {added}" if added else f"already there: {locator}")


if __name__ == "__main__":
    main()
