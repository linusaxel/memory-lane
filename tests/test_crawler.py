"""Channel discovery.

Offline by design: YoutubeDL is faked, so these run in the gate every tick with
no network and no cost. The one test that really hits YouTube is marked `live`
and is deselected by the gate (it belongs to W1-03).
"""

import re
from datetime import datetime, timezone

import pytest

from crawler import yt_crawler


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL. Records the opts it was constructed with."""

    captured_opts = None
    captured_url = None
    info = {"entries": []}

    def __init__(self, opts):
        type(self).captured_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        type(self).captured_url = url
        return self.info


@pytest.fixture
def fake_ydl(monkeypatch):
    FakeYoutubeDL.captured_opts = None
    FakeYoutubeDL.captured_url = None
    FakeYoutubeDL.info = {"entries": []}
    monkeypatch.setattr(yt_crawler, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL


# -- the entry -> dict mapping ----------------------------------------------

def test_url_is_built_from_the_id_not_the_entry_url(fake_ydl):
    """yt-dlp's flat `url` field is not always a canonical watch URL, and
    pipeline.ingest dedups on the exact normalized URL."""
    fake_ydl.info = {"entries": [
        {"id": "dQw4w9WgXcQ", "title": "T", "url": "https://youtu.be/SOMETHING_ELSE"},
    ]}
    got = yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert got[0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_timestamp_becomes_an_aware_datetime(fake_ydl):
    fake_ydl.info = {"entries": [{"id": "a" * 11, "title": "T", "timestamp": 1700000000}]}
    published = yt_crawler.list_channel_videos("https://www.youtube.com/@x")[0]["published_at"]
    assert published == datetime.fromtimestamp(1700000000, timezone.utc)
    assert published.tzinfo is not None, "naive datetimes corrupt a TIMESTAMP column"


def test_release_timestamp_is_used_as_a_fallback(fake_ydl):
    fake_ydl.info = {"entries": [{"id": "b" * 11, "release_timestamp": 1700000000}]}
    got = yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert got[0]["published_at"] == datetime.fromtimestamp(1700000000, timezone.utc)


def test_missing_timestamp_is_none_not_an_error(fake_ydl):
    """Flat extraction often omits the timestamp. published_at is nullable."""
    fake_ydl.info = {"entries": [{"id": "c" * 11, "title": "T"}]}
    got = yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert got[0]["published_at"] is None
    assert got[0]["title"] == "T"


def test_entry_without_an_id_is_dropped(fake_ydl):
    fake_ydl.info = {"entries": [
        {"id": "d" * 11, "title": "keep"},
        {"title": "no id - drop me"},
        None,
    ]}
    got = yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert [v["title"] for v in got] == ["keep"]


def test_no_entries_key_is_not_a_crash(fake_ydl):
    fake_ydl.info = {}
    assert yt_crawler.list_channel_videos("https://www.youtube.com/@x") == []


# -- how we call yt-dlp ------------------------------------------------------

def test_videos_tab_is_appended_exactly_once(fake_ydl):
    yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert fake_ydl.captured_url == "https://www.youtube.com/@x/videos"

    yt_crawler.list_channel_videos("https://www.youtube.com/@x/videos")
    assert fake_ydl.captured_url == "https://www.youtube.com/@x/videos"

    yt_crawler.list_channel_videos("https://www.youtube.com/@x/")
    assert fake_ydl.captured_url == "https://www.youtube.com/@x/videos"


def test_limit_is_forwarded_as_playlistend(fake_ydl):
    yt_crawler.list_channel_videos("https://www.youtube.com/@x", limit=25)
    assert fake_ydl.captured_opts["playlistend"] == 25


def test_no_limit_means_no_playlistend(fake_ydl):
    yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    assert "playlistend" not in fake_ydl.captured_opts


def test_extraction_stays_flat_and_bounded(fake_ydl):
    """extract_flat keeps this metadata-only (one request, not one per video),
    and a socket timeout stops the old hang-forever behaviour."""
    yt_crawler.list_channel_videos("https://www.youtube.com/@x")
    opts = fake_ydl.captured_opts
    assert opts["extract_flat"] == "in_playlist"
    assert opts["socket_timeout"] > 0
    assert opts["retries"] >= 1


# -- what must NOT come back --------------------------------------------------

def test_transcript_handling_is_gone():
    """Transcripts are pipeline/transcripts.py's job. Duplicating them here is
    what made this module dead weight, and the .txt files it wrote were read by
    nothing. If any of these reappear, the module is drifting back."""
    for gone in ("fetch_transcript", "save_transcript_txt",
                 "crawl_channel_transcripts", "extract_video_id"):
        assert not hasattr(yt_crawler, gone), f"{gone} should have been deleted"


def test_crawler_does_not_import_pipeline():
    """pipeline.ingest imports crawler (W1-04). The reverse would be a cycle."""
    source = (yt_crawler.__file__)
    with open(source) as f:
        text = f.read()
    assert "import pipeline" not in text and "from pipeline" not in text


# -- the live proof (W1-03) --------------------------------------------------
# Marked `live`: needs network, costs nothing, and is DESELECTED by the gate so
# ticks stay deterministic and offline. Run it deliberately:
#   venv/bin/python -m pytest -q -m live tests/test_crawler.py
# Do NOT remove the marker, and do NOT put a network call in an unmarked test.

LIVE_CHANNEL = "https://www.youtube.com/@veritasium"


@pytest.mark.live
def test_real_channel_paginates_past_the_first_page():
    """The number that matters.

    The scraper this replaced returned ZERO videos for every channel tested on
    2026-09-20, and even when it worked it only ever saw the first HTML payload
    (~30 videos). Asserting >30 proves both the outage and the truncation are
    gone. Measured at the time of writing: 150 requested, 150 returned.
    """
    videos = yt_crawler.list_channel_videos(LIVE_CHANNEL, limit=60)

    assert len(videos) > 30, (
        f"only {len(videos)} videos - either discovery regressed to a single "
        f"page, or {LIVE_CHANNEL} no longer resolves (the previous hardcoded "
        f"channel, @TheMountainDispatch, 404s). Check the handle before "
        f"assuming the code broke."
    )


@pytest.mark.live
def test_real_channel_returns_usable_metadata():
    videos = yt_crawler.list_channel_videos(LIVE_CHANNEL, limit=10)
    assert videos, "no videos returned"

    for v in videos:
        video_id = v["url"].removeprefix("https://www.youtube.com/watch?v=")
        assert re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id), f"bad video id: {v['url']}"

    # Titles are the visible proof metadata capture works: before this rewrite
    # content.title was always NULL for crawled videos.
    assert all(v["title"] for v in videos), "some videos came back with no title"
