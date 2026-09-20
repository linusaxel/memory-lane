"""YouTube channel discovery, via yt-dlp. Transcripts belong to
pipeline/transcripts.py.

Must not import `pipeline` - pipeline.ingest imports this. Why yt-dlp and not a
scrape: docs/10-decisions.md#channel-discovery-uses-yt-dlp-not-a-scrape.
"""

import argparse
import logging
from datetime import UTC, datetime

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


def channel_metadata(channel_url: str) -> dict:
    """Who published this. {"name", "url", "icon_url"} - any value may be None.

    A memory reads as an anonymous assertion without it: "somebody got lost in
    the medina" is a rumour, and "Tuesdays with Stories, 12:04" is a citation.
    The channel is also the only reliable answer to "who is the speaker?", since
    transcripts frequently never say.

    The avatar is picked by aspect ratio rather than by position. YouTube
    returns the banner and the avatar in one `thumbnails` list with no field
    saying which is which; the banner is ~6:1 and the avatar is square, so the
    square one is the avatar. Taking the largest, or the last, gets the banner.
    """
    if not channel_url.rstrip("/").endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"

    # One video is enough to resolve the channel, and asking for zero makes
    # yt-dlp walk the whole playlist.
    with YoutubeDL({**YDL_OPTS, "playlistend": 1}) as ydl:
        info = ydl.extract_info(channel_url, download=False) or {}

    square = [
        t
        for t in (info.get("thumbnails") or [])
        if t.get("width") and t.get("height") and t["width"] == t["height"]
    ]
    avatar = max(square, key=lambda t: t["width"]) if square else None

    return {
        "name": info.get("channel") or info.get("uploader"),
        "url": info.get("channel_url") or info.get("uploader_url"),
        "icon_url": avatar["url"] if avatar else None,
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
                "published_at": datetime.fromtimestamp(ts, UTC) if ts else None,
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
