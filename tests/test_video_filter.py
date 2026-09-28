"""Clips cut from full episodes are skipped before their transcript is fetched.

On the channel this was calibrated against, every clip is under 17 minutes and
every episode over 60; a clip re-tells a story its episode already holds.
"""

import pytest
from sqlalchemy import text

from pipeline import ingest
from pipeline.extract import PENDING_EXTRACTION
from pipeline.transcripts import LONG_ENOUGH

pytestmark = pytest.mark.db


def _video(session, vid, duration, transcript=False):
    content_id = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, duration_seconds, transcript_fetched)"
            " VALUES (:url, 'youtube', :vid, :d, :t) RETURNING id"
        ),
        {
            "url": f"https://www.youtube.com/watch?v={vid}",
            "vid": vid,
            "d": duration,
            "t": transcript,
        },
    ).scalar()
    if transcript:
        session.execute(
            text("INSERT INTO transcripts (content_id, segments) VALUES (:id, '[]')"),
            {"id": content_id},
        )


def _ids(session, sql):
    return sorted(r[0] for r in session.execute(text(sql)))


def test_a_clip_is_never_fetched_but_an_episode_or_an_unknown_is(db_session):
    _video(db_session, "clip0000000", 990)
    _video(db_session, "episode0000", 4452)
    _video(db_session, "handlisted0", None)
    got = _ids(db_session, f"SELECT platform_id FROM content c WHERE {LONG_ENOUGH}")
    assert got == ["episode0000", "handlisted0"]


def test_a_clip_whose_transcript_predates_the_filter_is_not_extracted(db_session):
    _video(db_session, "clip0000000", 990, transcript=True)
    _video(db_session, "episode0000", 4452, transcript=True)
    got = _ids(db_session, f"SELECT c.platform_id {PENDING_EXTRACTION}")
    assert got == ["episode0000"]


def test_refresh_backfills_duration_and_title_without_overwriting(db_session, monkeypatch):
    from contextlib import contextmanager

    import crawler.yt_crawler as yt

    _video(db_session, "aaaaaaaaaaa", None)
    _video(db_session, "bbbbbbbbbbb", 3000)
    db_session.execute(text("UPDATE content SET source_name = 'Test Channel'"))
    db_session.execute(text("UPDATE content SET title = 'Kept' WHERE platform_id = 'bbbbbbbbbbb'"))

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(ingest, "get_session", _session)
    monkeypatch.setattr(yt, "channel_metadata", lambda url: {"url": "https://yt/c", "name": "T"})
    monkeypatch.setattr(
        yt,
        "list_channel_videos",
        lambda url, limit=None: [
            {"url": f"https://www.youtube.com/watch?v={v}", "duration_seconds": 600, "title": v}
            for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")
        ],
    )
    ingest.refresh_sources(
        {"sources": [{"name": "Test Channel", "channel": "https://www.youtube.com/@t"}]}
    )
    got = db_session.execute(
        text("SELECT platform_id, duration_seconds, title FROM content ORDER BY platform_id")
    ).fetchall()
    assert got == [("aaaaaaaaaaa", 600, "aaaaaaaaaaa"), ("bbbbbbbbbbb", 3000, "Kept")]
