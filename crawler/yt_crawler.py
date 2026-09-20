"""YouTube channel discovery.

Discovery only. Transcripts belong to pipeline/transcripts.py and the database;
this module used to duplicate them into transcripts/*.txt that nothing read,
which is what made it dead weight.

Why yt-dlp instead of scraping the channel page: as of 2026-09-20 the old
regex over `"videoId":"..."` in the channel HTML returns **zero** videos for
every channel tested - YouTube no longer serves that markup to a plain client.
Rebuilding it on the internal youtubei/v1/browse endpoint means a lot of
undocumented JSON walking that fails silently by returning a short list.
yt-dlp is that parser, maintained weekly, with no hard dependencies.

This module must not import `pipeline` - pipeline.ingest imports it.
"""

import argparse
import logging
from datetime import datetime, timezone

from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YDL_OPTS = {
    # Metadata only: one request for the channel, not one per video.
    "extract_flat": "in_playlist",
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 20,
    "retries": 3,
}


def list_channel_videos(channel_url: str, limit: int | None = None) -> list[dict]:
    """List a channel's videos, newest first.

    Returns [{"url", "title", "published_at"}, ...] shaped for the `videos:`
    entries that pipeline.ingest already knows how to insert.
    """
    if not channel_url.rstrip("/").endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"

    opts = dict(YDL_OPTS)
    if limit:
        opts["playlistend"] = limit

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    videos = []
    for entry in info.get("entries") or []:
        if not entry:
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        # Build the canonical URL from the id: the flat `url` field is not always
        # a watch URL, and pipeline.ingest dedups on the exact normalized string.
        # ponytail: flat extraction often omits the timestamp. Exact dates for
        # every video would need a per-video fetch (slow) or the channel RSS
        # feed (newest 15 only). published_at is nullable - revisit if dates
        # become load-bearing.
        ts = entry.get("timestamp") or entry.get("release_timestamp")
        videos.append(
            {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": entry.get("title"),
                "published_at": datetime.fromtimestamp(ts, timezone.utc) if ts else None,
            }
        )

    logger.info(f"Found {len(videos)} videos on {channel_url}")
    return videos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List a YouTube channel's videos.")
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel URL or @handle page, e.g. https://www.youtube.com/@someone",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Stop after N videos (newest first)"
    )
    args = parser.parse_args()

    for video in list_channel_videos(args.channel, limit=args.limit):
        print(f"{video['url']}\t{video['title']}")
