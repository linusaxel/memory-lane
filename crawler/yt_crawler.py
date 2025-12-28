import os
import time
import re
import requests
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def extract_video_id(video_url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    Handles URLs like:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
    """
    parsed = urlparse(video_url)

    # Short youtu.be links
    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")

    # Standard YouTube watch URLs
    if parsed.path == "/watch":
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]

    # Fallback: last path segment (not perfect, but works for many cases)
    return parsed.path.split("/")[-1]


def get_channel_video_urls(channel_url: str):
    """
    Scrape the channel /videos page for video IDs.
    This avoids pytube and works with @handle URLs.
    """
    # Normalize to the /videos tab
    if "/videos" not in channel_url:
        channel_url = channel_url.rstrip("/") + "/videos"

    print(f"Fetching video list from: {channel_url}")
    resp = requests.get(channel_url)
    resp.raise_for_status()
    html = resp.text

    # Find all occurrences of "videoId":"XXXXXXXXXXX"
    video_ids = set(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html))
    video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]

    print(f"Found {len(video_urls)} unique video IDs")
    return video_urls


def fetch_transcript(video_id: str, languages=None):
    """
    Fetch transcript for a given video ID using the *new* youtube-transcript-api API.

    Returns:
        list[dict] with keys 'text', 'start', 'duration'
        or None if no transcript available.
    """
    languages = languages or ["en", "en-US", "en-GB"]

    try:
        api = YouTubeTranscriptApi()
        # New API: fetch() instead of get_transcript()
        fetched = api.fetch(video_id, languages=languages)
        # Convert to the old-style raw data (list of dicts)
        return fetched.to_raw_data()

    except TranscriptsDisabled:
        print(f"  ❌ Transcripts disabled for {video_id}")
    except NoTranscriptFound:
        print(f"  ❌ No transcript found for {video_id}")
    except VideoUnavailable:
        print(f"  ❌ Video unavailable: {video_id}")
    except Exception as e:
        print(f"  ⚠️ Unexpected error fetching transcript for {video_id}: {e}")

    return None


def save_transcript_txt(video_id: str, transcript, output_dir="transcripts"):
    """
    Save transcript to a text file with simple formatting.
    Expects transcript to be a list of dicts with 'text', 'start', 'duration'.
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{video_id}.txt")

    with open(filepath, "w", encoding="utf-8") as f:
        for entry in transcript:
            start = entry["start"]
            text = entry["text"]
            # Format: [start] text
            line = f"[{start:.2f}] {text}\n"
            f.write(line)

    print(f"  ✅ Saved transcript to {filepath}")


def crawl_channel_transcripts(
    channel_url: str,
    output_dir: str = "transcripts",
    sleep_seconds: float = 0.5,
):
    """
    Main function:
    - Lists all videos in the channel (via HTML scraping)
    - Fetches transcripts where available
    - Saves them as text files
    """
    print(f"Loading videos from channel: {channel_url}")
    video_urls = get_channel_video_urls(channel_url)

    print("\nStarting transcript crawl...\n")
    for idx, video_url in enumerate(video_urls, start=1):
        video_id = extract_video_id(video_url)
        print(f"[{idx}/{len(video_urls)}] Processing video: {video_id} ({video_url})")

        transcript = fetch_transcript(video_id)
        if transcript:
            save_transcript_txt(video_id, transcript, output_dir=output_dir)

        # Be polite & avoid hammering servers:
        time.sleep(sleep_seconds)

    print("\nDone! 🎉")


if __name__ == "__main__":
    CHANNEL_URL = "https://www.youtube.com/@TheMountainDispatch"
    crawl_channel_transcripts(CHANNEL_URL)
