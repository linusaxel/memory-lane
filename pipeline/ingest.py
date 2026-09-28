"""Content ingestion from the `sources` table into the database."""

import json
import logging
import re

import yaml
from sqlalchemy import text

from pipeline.db import get_session

logger = logging.getLogger(__name__)


def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def normalize_youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def load_config(statuses=("active",)) -> dict:
    """The YouTube channels in `sources` with one of `statuses`, shaped as the
    config dict ingest_content has always taken. Only `active` is polled: a
    trial is one video, added by hand with --video."""
    with get_session() as session:
        rows = session.execute(
            text("""
                SELECT id, name, locator, poll_limit FROM sources
                WHERE kind = 'youtube_channel' AND status = ANY(:statuses)
                ORDER BY id
            """),
            {"statuses": list(statuses)},
        ).fetchall()
    return {
        "sources": [
            {"id": r.id, "name": r.name, "channel": r.locator, "limit": r.poll_limit} for r in rows
        ]
    }


def ingest_content(config: dict | None = None):
    """Ingest content from config into database.

    `config` defaults to the active channels in `sources`; passing one in keeps
    the DB write path testable without a crawl.
    """
    if config is None:
        config = load_config()
    sources = config.get("sources", [])

    inserted = 0
    skipped = 0

    with get_session() as session:
        for source in sources:
            source_name = source.get("name", "Unknown")
            platform = source.get("platform", "youtube")
            videos = source.get("videos", [])

            # A `channel:` source discovers its videos instead of listing them,
            # and is also where the publisher's name, link and avatar come from.
            # Local import so yt_dlp stays off the path for yaml-only runs.
            channel = {}
            if source.get("channel"):
                from crawler.yt_crawler import channel_metadata, list_channel_videos

                videos = videos + list_channel_videos(source["channel"], limit=source.get("limit"))
                channel = channel_metadata(source["channel"])
                # The config's name wins: it is what a human chose to call this,
                # and YouTube's has an exclamation mark in it.
                source_name = source.get("name") or channel.get("name") or source_name

            for video in videos:
                url = video.get("url", "")
                title = video.get("title")

                if platform == "youtube":
                    video_id = extract_youtube_id(url)
                    if not video_id:
                        logger.warning(f"Could not extract video ID from: {url}")
                        continue
                    normalized_url = normalize_youtube_url(video_id)
                else:
                    logger.warning(f"Unsupported platform: {platform}")
                    continue

                existing = session.execute(
                    text("SELECT id FROM content WHERE url = :url"), {"url": normalized_url}
                ).fetchone()

                if existing:
                    logger.debug(f"Skipping existing: {normalized_url}")
                    skipped += 1
                    continue

                session.execute(
                    text("""
                        INSERT INTO content (
                            url, platform, platform_id, source_id, source_name, source_url,
                            source_icon_url, title, published_at, duration_seconds
                        )
                        VALUES (
                            :url, :platform, :platform_id, :source_id, :source_name, :source_url,
                            :source_icon_url, :title, :published_at, :duration_seconds
                        )
                    """),
                    {
                        "url": normalized_url,
                        "platform": platform,
                        "platform_id": video_id,
                        "source_id": source.get("id"),
                        "source_name": source_name,
                        "source_url": channel.get("url"),
                        "source_icon_url": channel.get("icon_url"),
                        "title": title,
                        "published_at": video.get("published_at"),
                        "duration_seconds": video.get("duration_seconds"),
                    },
                )
                logger.info(f"Inserted: {normalized_url}")
                inserted += 1

    logger.info(f"Ingestion complete: {inserted} inserted, {skipped} skipped")
    return {"inserted": inserted, "skipped": skipped}


def refresh_sources(config: dict | None = None):
    """Backfill source_url, source_icon_url, duration_seconds and a missing
    title on rows ingested without them.

    Separate from ingest_content because it is the only part that must touch the
    network for rows that are already present, and because re-running ingest
    would skip every one of them as existing.
    """
    from crawler.yt_crawler import channel_metadata, list_channel_videos

    if config is None:
        config = load_config(("trial", "active"))

    updated = 0
    with get_session() as session:
        for source in config.get("sources", []):
            if not source.get("channel"):
                continue
            channel = channel_metadata(source["channel"])
            if not channel.get("url"):
                logger.warning(f"No channel metadata for {source['channel']}")
                continue

            result = session.execute(
                text("""
                    UPDATE content
                    SET source_url = :url, source_icon_url = :icon
                    WHERE source_name = :name
                """),
                {
                    "url": channel["url"],
                    "icon": channel.get("icon_url"),
                    "name": source.get("name") or channel.get("name"),
                },
            )
            logger.info(f"{source.get('name')}: {result.rowcount} rows")
            updated += result.rowcount

            # The whole channel, not `limit`: rows ingested months ago have
            # long since dropped out of the newest N.
            for video in list_channel_videos(source["channel"]):
                session.execute(
                    text("""
                        UPDATE content
                        SET duration_seconds = COALESCE(duration_seconds, :d),
                            title = COALESCE(NULLIF(title, ''), :t)
                        WHERE platform_id = :id
                    """),
                    {
                        "d": video.get("duration_seconds"),
                        "t": video.get("title"),
                        "id": extract_youtube_id(video["url"]),
                    },
                )

    return {"updated": updated}


def within(records, bbox):
    """Drop a record whose own point lies outside bbox (south, west, north, east).
    A record with no point passes: nothing says where it is yet."""
    south, west, north, east = bbox
    for record in records:
        lat, lng = record.get("lat"), record.get("lng")
        if lat is None or lng is None or (south <= lat <= north and west <= lng <= east):
            yield record


def ingest_records(records, source_name, source_type="archive", platform="text", source_id=None):
    """Ingest already-fetched text records - archive entries, newspaper clippings.

    A second entry point rather than a wider `ingest_content`, so the YouTube
    path keeps its behaviour and its tests. Callers fetch; this only writes.

    Each record is {source_url, text, title?, happened_at?}. `source_url` becomes
    `content.url`, so the UNIQUE constraint there makes re-ingesting a no-op
    exactly as it does for videos.

    The text is stored as a single transcript segment at t=0 rather than in a new
    column. It reads oddly for a newspaper clipping, but it means the extraction
    stage needs no branch: chunk_transcript, extract and save_memories all work
    unchanged on a source that simply has no timings.

    ponytail: `transcripts` is really "source text, timings optional". Rename it
    if a source ever arrives that this genuinely cannot hold.
    """
    inserted = 0
    skipped = 0

    with get_session() as session:
        for record in records:
            url = (record.get("source_url") or "").strip()
            body = (record.get("text") or "").strip()
            if not url or not body:
                logger.warning("Skipping record with no source_url or no text: %r", record)
                continue

            existing = session.execute(
                text("SELECT id FROM content WHERE url = :url"), {"url": url}
            ).fetchone()
            if existing:
                logger.debug("Skipping existing: %s", url)
                skipped += 1
                continue

            content_id = session.execute(
                text("""
                    INSERT INTO content
                        (url, platform, source_id, source_name, title, source_type,
                         transcript_fetched)
                    VALUES (:url, :platform, :source_id, :source_name, :title, :source_type,
                            TRUE)
                    RETURNING id
                """),
                {
                    "url": url,
                    "platform": platform,
                    "source_id": source_id,
                    "source_name": source_name,
                    "title": record.get("title"),
                    "source_type": source_type,
                },
            ).scalar()

            session.execute(
                text("""
                    INSERT INTO transcripts (content_id, segments, full_text, language)
                    VALUES (:content_id, CAST(:segments AS jsonb), :full_text, :language)
                """),
                {
                    "content_id": content_id,
                    "segments": json.dumps([{"start": 0.0, "text": body}]),
                    "full_text": body,
                    "language": record.get("language", "en"),
                },
            )
            logger.info("Inserted: %s", url)
            inserted += 1

    logger.info("Record ingestion complete: %d inserted, %d skipped", inserted, skipped)
    return {"inserted": inserted, "skipped": skipped}


def text_source_row(key: str, query: str):
    """The `sources` row a text-source run belongs to: the exact
    `<key>:<query>` (one book), else the bare `<key>:` (a searchable archive)."""
    with get_session() as session:
        return session.execute(
            text("""
                SELECT id, name FROM sources
                WHERE locator IN (:exact, :bare)
                ORDER BY locator = :exact DESC LIMIT 1
            """),
            {"exact": f"{key}:{query}", "bare": f"{key}:"},
        ).fetchone()


def load_records(path):
    """Read a YAML file of {source_name, source_type, records:[...]} for ingest_records."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Load content from the active sources, one video, or a text source."
    )
    parser.add_argument("--video", help="one YouTube URL, e.g. a source's trial episode")
    parser.add_argument("--to", type=int, metavar="SOURCE_ID", help="the source --video belongs to")
    parser.add_argument(
        "--refresh-sources",
        action="store_true",
        help="only backfill publisher, duration and title on rows already ingested",
    )
    parser.add_argument("--source", help="a text source from crawler.sources, e.g. kb-aviser")
    parser.add_argument("--query", help="what to ask the source for, e.g. a street name")
    parser.add_argument("--limit", type=int, default=20, help="most records to fetch")
    parser.add_argument(
        "--bbox",
        type=lambda v: tuple(float(x) for x in v.split(",")),
        help="south,west,north,east: drop records whose own point is outside, "
        "e.g. 55.60,12.45,55.74,12.66 for Copenhagen",
    )
    args = parser.parse_args()

    if args.source:
        from crawler.sources import SOURCES

        if args.source not in SOURCES:
            parser.error(f"--source must be one of {', '.join(SOURCES)}")
        if not args.query:
            parser.error("--source needs --query")
        src = SOURCES[args.source]
        row = text_source_row(args.source, args.query)
        records = src.fetch(args.query, args.limit)
        ingest_records(
            within(records, args.bbox) if args.bbox else records,
            source_name=row.name if row else src.source_name,
            source_type=src.source_type,
            source_id=row.id if row else None,
        )
    elif args.video:
        if not args.to:
            parser.error("--video needs --to <source id>: python -m pipeline.sources list")
        with get_session() as session:
            name = session.execute(
                text("SELECT name FROM sources WHERE id = :id"), {"id": args.to}
            ).scalar()
        if not name:
            parser.error(f"no source {args.to}")
        from crawler.yt_crawler import video_metadata

        ingest_content(
            {"sources": [{"id": args.to, "name": name, "videos": [video_metadata(args.video)]}]}
        )
    elif args.refresh_sources:
        refresh_sources()
    else:
        ingest_content()
