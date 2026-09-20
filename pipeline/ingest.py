"""Content ingestion from config/content.yaml into the database."""

import json
import logging
import re
from pathlib import Path

import yaml
from sqlalchemy import text

from pipeline.db import get_session

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "content.yaml"


def extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
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


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def ingest_content(config: dict | None = None):
    """Ingest content from config into database.

    `config` defaults to config/content.yaml; passing one in keeps the DB write
    path testable without touching the file.
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

            # A `channel:` source discovers its videos instead of listing them.
            # Local import so yt_dlp stays off the path for yaml-only runs.
            if source.get("channel"):
                from crawler.yt_crawler import list_channel_videos

                videos = videos + list_channel_videos(source["channel"], limit=source.get("limit"))

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
                        INSERT INTO content (url, platform, platform_id, source_name, title, published_at)
                        VALUES (:url, :platform, :platform_id, :source_name, :title, :published_at)
                    """),
                    {
                        "url": normalized_url,
                        "platform": platform,
                        "platform_id": video_id,
                        "source_name": source_name,
                        "title": title,
                        "published_at": video.get("published_at"),
                    },
                )
                logger.info(f"Inserted: {normalized_url}")
                inserted += 1

    logger.info(f"Ingestion complete: {inserted} inserted, {skipped} skipped")
    return {"inserted": inserted, "skipped": skipped}


def ingest_records(records, source_name, source_type="archive", platform="text"):
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
                        (url, platform, source_name, title, source_type, transcript_fetched)
                    VALUES (:url, :platform, :source_name, :title, :source_type, TRUE)
                    RETURNING id
                """),
                {
                    "url": url,
                    "platform": platform,
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


def load_records(path):
    """Read a YAML file of {source_name, source_type, records:[...]} for ingest_records."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_content()
