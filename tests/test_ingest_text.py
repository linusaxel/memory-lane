"""Ingesting text records - archive entries, clippings - not just video.

`ingest_content` only understands YouTube: anything else hits a `continue` and
is dropped with a warning. Archives, newspapers and registries need a way in
that does not pretend to be a video, and the extraction stage should not have to
learn about it.

These run against real PostGIS because the behaviour under test is mostly what
lands in the tables.
"""

import pathlib

import pytest
from sqlalchemy import text

from pipeline.extract import chunk_transcript
from pipeline.ingest import ingest_records, load_records

pytestmark = pytest.mark.db

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "copenhagen_synthetic.yaml"


def _records():
    return [
        {
            "source_url": "https://example.invalid/a",
            "title": "A room above a bicycle shop",
            "text": "A band played here in 1978. It is a bank now.",
        }
    ]


def test_a_text_record_becomes_content_and_a_transcript(ingest_into, db_session):
    result = ingest_records(_records(), source_name="Test Archive")
    assert result == {"inserted": 1, "skipped": 0}

    row = db_session.execute(
        text("""
            SELECT c.url, c.source_type, c.platform, c.transcript_fetched, t.full_text
            FROM content c JOIN transcripts t ON t.content_id = c.id
        """)
    ).fetchone()
    assert row.url == "https://example.invalid/a"
    assert row.source_type == "archive"
    assert row.transcript_fetched is True
    assert "1978" in row.full_text


def test_re_ingesting_the_same_record_changes_nothing(ingest_into, db_session):
    ingest_records(_records(), source_name="Test Archive")
    assert ingest_records(_records(), source_name="Test Archive") == {"inserted": 0, "skipped": 1}
    assert db_session.execute(text("SELECT count(*) FROM content")).scalar() == 1


def test_the_extraction_stage_needs_no_branch(ingest_into, db_session):
    """The point of storing the body as one segment at t=0: the existing chunker
    handles a source with no timings without knowing anything about it.
    """
    ingest_records(_records(), source_name="Test Archive")
    segments = db_session.execute(text("SELECT segments FROM transcripts")).scalar()
    chunks = chunk_transcript(segments)
    assert len(chunks) == 1
    assert "1978" in chunks[0]


def test_a_record_with_no_text_is_skipped_not_fatal(ingest_into, db_session):
    records = _records() + [{"source_url": "https://example.invalid/b", "text": "   "}]
    assert ingest_records(records, source_name="Test Archive")["inserted"] == 1


def test_a_video_row_is_untouched_by_the_text_path(ingest_into, db_session):
    """source_type defaults to 'video', so the YouTube path keeps its meaning."""
    db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=aaaaaaaaaaa', 'youtube', 'aaaaaaaaaaa')"
        )
    )
    db_session.commit()
    ingest_records(_records(), source_name="Test Archive")
    kinds = dict(
        db_session.execute(text("SELECT source_type, count(*) FROM content GROUP BY 1")).fetchall()
    )
    assert kinds == {"video": 1, "archive": 1}


def test_the_synthetic_fixture_loads_and_is_labelled(ingest_into, db_session):
    """The fixture must stay obviously fake: extracted memories carry no marker
    saying they were invented, and invented history is what this must not ship.
    """
    data = load_records(FIXTURE)
    assert "NOT REAL HISTORY" in data["source_name"]
    assert all(r["source_url"].endswith((".invalid", "1", "2", "3")) for r in data["records"])

    result = ingest_records(
        data["records"], source_name=data["source_name"], source_type=data["source_type"]
    )
    assert result["inserted"] == 3


def test_a_story_across_a_chunk_boundary_is_whole_in_one_chunk():
    """The overlap is repeated text: a line in the 30 s before a boundary
    opens the next chunk as well as closing this one."""
    segments = [{"start": t, "text": f"line {t}"} for t in range(0, 600, 10)]
    first, second, *_ = chunk_transcript(segments, chunk_minutes=4, overlap_seconds=30)
    assert "[230.0] line 230" in first and "[230.0] line 230" in second
    assert "[200.0] line 200" not in second
