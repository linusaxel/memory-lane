"""Enqueueing a content twice must not extract it twice: aggregation only
inserts, so a second pass duplicates every memory it made."""

from contextlib import contextmanager

import pytest
from sqlalchemy import text

from pipeline import tasks

pytestmark = pytest.mark.db


def test_an_extracted_content_is_not_chunked_again(db_session, monkeypatch):
    content_id = db_session.execute(
        text("""
            INSERT INTO content (url, platform, memories_extracted, transcript_fetched)
            VALUES ('https://example.com/done', 'text', TRUE, TRUE) RETURNING id
        """)
    ).scalar()
    db_session.execute(
        text("INSERT INTO transcripts (content_id, segments) VALUES (:id, '[]')"),
        {"id": content_id},
    )

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(tasks, "get_session", _session)
    monkeypatch.setattr(tasks, "get_queue", lambda name: pytest.fail("enqueued a chunk"))
    monkeypatch.setattr(tasks, "get_redis", lambda: pytest.fail("wrote extraction state"))

    assert tasks.task_enqueue_chunks(content_id) == {"skipped": "already_extracted"}
