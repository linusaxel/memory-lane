"""Fetch YouTube transcripts and store in database."""

import json
import logging
import random
import time

from sqlalchemy import text
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import GenericProxyConfig

from pipeline.config import MIN_VIDEO_MINUTES, TRANSCRIPT_DELAY_SECONDS, TRANSCRIPT_PROXY
from pipeline.db import get_session

logger = logging.getLogger(__name__)


def fetch_transcript(video_id: str) -> dict | None:
    """
    Fetch transcript for a YouTube video using the new API.

    Returns dict with segments, full_text, and language.

    Returns None only for PERMANENT failures (captions disabled, video gone,
    no matching language). Transient errors propagate so the caller can retry.
    """
    languages = ["en", "en-US", "en-GB", "en-AU", "da"]

    try:
        proxy = TRANSCRIPT_PROXY and GenericProxyConfig(TRANSCRIPT_PROXY, TRANSCRIPT_PROXY)
        api = YouTubeTranscriptApi(proxy_config=proxy)
        # A person's captions before the machine's, in any of the languages:
        # English auto-captions heard "Nørrebro" as "naropa". The library's own
        # fetch() tries each language's two tracks before the next language.
        tracks = api.list(video_id)
        try:
            track = tracks.find_manually_created_transcript(languages)
        except NoTranscriptFound:
            track = tracks.find_generated_transcript(languages)
        fetched = track.fetch()
        segments = fetched.to_raw_data()
        full_text = " ".join(seg["text"] for seg in segments)

        return {
            "segments": segments,
            "full_text": full_text,
            "language": fetched.language_code,
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
    # Anything else - network blip, IP block, consent/age gate - is TRANSIENT and
    # deliberately propagates. Returning None here would be indistinguishable from
    # "no captions exist" and the caller would set transcript_failed permanently.


# Needs `content` aliased as c. See MIN_VIDEO_MINUTES.
LONG_ENOUGH = f"(c.duration_seconds IS NULL OR c.duration_seconds >= {MIN_VIDEO_MINUTES * 60})"


def fetch_pending_transcripts(content_ids: list[int] | None = None):
    fetched = 0
    failed = 0

    with get_session() as session:
        pending = session.execute(
            text(f"""
                SELECT id, platform_id, title
                FROM content c
                WHERE transcript_fetched = FALSE
                  AND transcript_failed = FALSE
                  AND platform = 'youtube'
                  AND {LONG_ENOUGH}
                  AND (CAST(:ids AS integer[]) IS NULL OR id = ANY(CAST(:ids AS integer[])))
            """),
            {"ids": content_ids},
        ).fetchall()

        logger.info(f"Found {len(pending)} videos pending transcript fetch")

        for n, row in enumerate(pending):
            content_id, video_id, title = row
            if n:
                time.sleep(random.uniform(0, 2 * TRANSCRIPT_DELAY_SECONDS))
            logger.info(f"Fetching transcript for: {title or video_id}")

            try:
                result = fetch_transcript(video_id)
            except RequestBlocked as e:
                # The IP, not the video: every row after this would fail the
                # same way and dig the block deeper. Stop; all stay pending.
                logger.error(f"YouTube is blocking this IP, stopping (set TRANSCRIPT_PROXY): {e}")
                return {"fetched": fetched, "failed": failed, "error": "blocked"}
            except Exception as e:
                # Leave transcript_failed FALSE so the next run retries this row.
                # The retry mechanism is the existing pending-rows query - no
                # counter column and no backoff scheduler needed.
                logger.warning(f"Transient error for {video_id}, will retry: {e}")
                failed += 1
                continue

            if result:
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
                    },
                )

                session.execute(
                    text("UPDATE content SET transcript_fetched = TRUE WHERE id = :id"),
                    {"id": content_id},
                )

                session.commit()
                logger.info(f"Stored transcript: {len(result['segments'])} segments")
                fetched += 1
            else:
                session.execute(
                    text("UPDATE content SET transcript_failed = TRUE WHERE id = :id"),
                    {"id": content_id},
                )
                session.commit()
                failed += 1

    logger.info(f"Transcript fetch complete: {fetched} fetched, {failed} failed")
    return {"fetched": fetched, "failed": failed}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_pending_transcripts()
