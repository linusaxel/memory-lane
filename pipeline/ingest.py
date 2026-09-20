"""Content ingestion from config/content.yaml into the database."""

import logging
import re
from pathlib import Path

import yaml
from sqlalchemy import text

from pipeline.db import get_session

logging.basicConfig(level=logging.INFO)
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
    """Return canonical YouTube URL format."""
    return f"https://www.youtube.com/watch?v={video_id}"


def load_config() -> dict:
    """Load content configuration from YAML file."""
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
                videos = videos + list_channel_videos(
                    source["channel"], limit=source.get("limit")
                )

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

                # Check if already exists (idempotent)
                existing = session.execute(
                    text("SELECT id FROM content WHERE url = :url"),
                    {"url": normalized_url}
                ).fetchone()

                if existing:
                    logger.debug(f"Skipping existing: {normalized_url}")
                    skipped += 1
                    continue

                # Insert new content
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
                    }
                )
                logger.info(f"Inserted: {normalized_url}")
                inserted += 1

    logger.info(f"Ingestion complete: {inserted} inserted, {skipped} skipped")
    return {"inserted": inserted, "skipped": skipped}


if __name__ == "__main__":
    ingest_content()
