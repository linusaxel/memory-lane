"""Channel discovery feeding the existing ingest stage.

These run against a REAL PostGIS database (marked `db`), not a mock, because
what is worth proving here is the dedup and the INSERT - and a mocked session
would prove neither. loop/verify.sh starts the db service when it sees these.

No network: list_channel_videos is faked. No Anthropic: ingest never calls it.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from pipeline import ingest

pytestmark = pytest.mark.db


@pytest.fixture
def fake_channel(monkeypatch):
    """Fake the crawler. ingest imports it locally, so patch it at the source."""
    calls = []

    def _list(channel_url, limit=None):
        calls.append((channel_url, limit))
        return [
            {
                "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
                "title": "First crawled video",
                "published_at": datetime(2026, 1, 2, tzinfo=UTC),
            },
            {
                "url": "https://www.youtube.com/watch?v=bbbbbbbbbbb",
                "title": "Second crawled video",
                "published_at": None,
            },
        ]

    import crawler.yt_crawler as yt

    monkeypatch.setattr(yt, "list_channel_videos", _list)
    return calls


CHANNEL_SOURCE = {
    "sources": [
        {
            "name": "Test Channel",
            "platform": "youtube",
            "channel": "https://www.youtube.com/@test",
            "limit": 2,
        }
    ]
}


def _rows(session):
    return session.execute(
        text("SELECT url, title, published_at, source_name, platform_id FROM content ORDER BY url")
    ).fetchall()


# -- the new behaviour -------------------------------------------------------


def test_channel_source_discovers_and_inserts(ingest_into, fake_channel):
    result = ingest.ingest_content(CHANNEL_SOURCE)

    assert result["inserted"] == 2
    rows = _rows(ingest_into)
    assert [r.url for r in rows] == [
        "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        "https://www.youtube.com/watch?v=bbbbbbbbbbb",
    ]


def test_limit_is_passed_through_to_the_crawler(ingest_into, fake_channel):
    ingest.ingest_content(CHANNEL_SOURCE)
    assert fake_channel == [("https://www.youtube.com/@test", 2)]


def test_title_is_captured(ingest_into, fake_channel):
    """content.title was always NULL for crawled videos before this."""
    ingest.ingest_content(CHANNEL_SOURCE)
    titles = [r.title for r in _rows(ingest_into)]
    assert titles == ["First crawled video", "Second crawled video"]


def test_published_at_is_populated(ingest_into, fake_channel):
    """The column already existed in db/schema.sql and was never written to."""
    ingest.ingest_content(CHANNEL_SOURCE)
    rows = _rows(ingest_into)
    assert rows[0].published_at == datetime(2026, 1, 2)
    assert rows[1].published_at is None, "a missing date must not become 'now'"


def test_platform_id_is_the_validated_video_id(ingest_into, fake_channel):
    ingest.ingest_content(CHANNEL_SOURCE)
    assert [r.platform_id for r in _rows(ingest_into)] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]


# -- reusing what already worked ---------------------------------------------


def test_re_ingesting_is_idempotent(ingest_into, fake_channel):
    """The existing dedup SELECT does this for free - no new dedup logic."""
    first = ingest.ingest_content(CHANNEL_SOURCE)
    second = ingest.ingest_content(CHANNEL_SOURCE)

    assert first["inserted"] == 2
    assert second == {"inserted": 0, "skipped": 2}
    assert len(_rows(ingest_into)) == 2


def test_a_video_listed_both_ways_is_inserted_once(ingest_into, fake_channel):
    """Same video in `videos:` and discovered on the channel. The dedup SELECT
    sees uncommitted inserts in the same transaction, so this is already safe."""
    config = {
        "sources": [
            {
                "name": "Test Channel",
                "platform": "youtube",
                "channel": "https://www.youtube.com/@test",
                "videos": [{"url": "https://youtu.be/aaaaaaaaaaa", "title": "Hand-added"}],
            }
        ]
    }

    result = ingest.ingest_content(config)

    assert len(_rows(ingest_into)) == 2
    assert result["inserted"] == 2 and result["skipped"] == 1


def test_yaml_only_sources_still_work_unchanged(ingest_into):
    """No channel key, no crawler import, published_at stays NULL."""
    config = {
        "sources": [
            {
                "name": "Hand-maintained",
                "platform": "youtube",
                "videos": [{"url": "https://www.youtube.com/watch?v=ccccccccccc", "title": "T"}],
            }
        ]
    }

    assert ingest.ingest_content(config)["inserted"] == 1
    row = _rows(ingest_into)[0]
    assert row.published_at is None and row.title == "T"


def test_unparseable_url_is_skipped_not_fatal(ingest_into):
    config = {
        "sources": [
            {
                "name": "Junk",
                "platform": "youtube",
                "videos": [{"url": "https://example.com/not-a-video"}],
            }
        ]
    }

    assert ingest.ingest_content(config)["inserted"] == 0
    assert _rows(ingest_into) == []


def test_default_config_still_reads_the_yaml_file(ingest_into, monkeypatch):
    """ingest_content() with no argument must behave exactly as before -
    pipeline/run_all.py calls it that way."""
    called = []

    def _load():
        called.append(True)
        return {"sources": []}

    monkeypatch.setattr(ingest, "load_config", _load)
    assert ingest.ingest_content() == {"inserted": 0, "skipped": 0}
    assert called, "ingest_content() must fall back to load_config()"
