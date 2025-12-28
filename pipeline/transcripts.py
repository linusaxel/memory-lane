"""Fetch YouTube transcripts and store in database."""

import json
import logging

from sqlalchemy import text
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from pipeline.db import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_transcript(video_id: str) -> dict | None:
    """
    Fetch transcript for a YouTube video using the new API.

    Returns dict with segments, full_text, and language, or None on failure.
    """
    languages = ["en", "en-US", "en-GB", "en-AU"]

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        segments = fetched.to_raw_data()
        full_text = " ".join(seg["text"] for seg in segments)

        return {
            "segments": segments,
            "full_text": full_text,
            "language": "en",
        }

    except TranscriptsDisabled:
        logger.warning(f"Transcripts disabled for {video_id}")
        return None
    except VideoUnavailable:
        logger.warning(f"Video unavailable: {video_id}")
        return None
    except NoTranscriptFound:
        logger.warning(f"No transcript found for {video_id}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching transcript for {video_id}: {e}")
        return None


def fetch_pending_transcripts():
    """Fetch transcripts for all pending content."""
    fetched = 0
    failed = 0

    with get_session() as session:
        # Get pending content
        pending = session.execute(
            text("""
                SELECT id, platform_id, title
                FROM content
                WHERE transcript_fetched = FALSE
                  AND transcript_failed = FALSE
                  AND platform = 'youtube'
            """)
        ).fetchall()

        logger.info(f"Found {len(pending)} videos pending transcript fetch")

        for row in pending:
            content_id, video_id, title = row
            logger.info(f"Fetching transcript for: {title or video_id}")

            result = fetch_transcript(video_id)

            if result:
                # Insert transcript
                session.execute(
                    text("""
                        INSERT INTO transcripts (content_id, segments, full_text, language)
                        VALUES (:content_id, :segments, :full_text, :language)
                        ON CONFLICT (content_id) DO UPDATE SET
                            segments = EXCLUDED.segments,
                            full_text = EXCLUDED.full_text,
                            language = EXCLUDED.language,
                            fetched_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "content_id": content_id,
                        "segments": json.dumps(result["segments"]),
                        "full_text": result["full_text"],
                        "language": result["language"],
                    }
                )

                # Mark content as fetched
                session.execute(
                    text("UPDATE content SET transcript_fetched = TRUE WHERE id = :id"),
                    {"id": content_id}
                )

                logger.info(f"Stored transcript: {len(result['segments'])} segments")
                fetched += 1
            else:
                # Mark as failed
                session.execute(
                    text("UPDATE content SET transcript_failed = TRUE WHERE id = :id"),
                    {"id": content_id}
                )
                failed += 1

    logger.info(f"Transcript fetch complete: {fetched} fetched, {failed} failed")
    return {"fetched": fetched, "failed": failed}


if __name__ == "__main__":
    fetch_pending_transcripts()
