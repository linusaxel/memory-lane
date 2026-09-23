"""The review loop's verdicts, and the before/after pairs it keeps."""

import pytest
from sqlalchemy import text

from pipeline.extract import save_memories
from pipeline.review import review, stats, unreviewed
from tests.fakes import FakeAnthropic


def _three_memories(db_session):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=eeeeeeeeeee', 'youtube', 'eeeeeeeeeee') "
            "RETURNING id"
        )
    ).scalar()
    base = FakeAnthropic().messages._payload[0]
    save_memories(
        db_session,
        content_id,
        [dict(base, summary=f"Summary {n}.", timestamp_start=n) for n in (1, 2, 3)],
    )
    return [r[0] for r in db_session.execute(text("SELECT id FROM memories ORDER BY id"))]


@pytest.mark.db
def test_each_verdict_is_recorded_and_applied(db_session):
    ok, bad, fix = _three_memories(db_session)

    review(db_session, ok, "accept")
    review(db_session, bad, "reject")
    review(db_session, fix, "edit", "Mark and Joe got thrown out.")

    summary, hidden = db_session.execute(
        text("SELECT summary, hidden FROM memories WHERE id = :id"), {"id": fix}
    ).fetchone()
    assert summary == "Mark and Joe got thrown out."
    assert not hidden
    assert db_session.execute(
        text("SELECT hidden FROM memories WHERE id = :id"), {"id": bad}
    ).scalar()

    assert unreviewed(db_session, 10) == []
    [month] = stats(db_session)
    assert (month.reviewed, month.accepted, month.edited, month.rejected) == (3, 1, 1, 1)


@pytest.mark.db
def test_a_second_review_keeps_the_models_original_text(db_session):
    """The pair is model text -> human text; re-editing must not overwrite the model's side."""
    _, _, fix = _three_memories(db_session)
    review(db_session, fix, "edit", "First pass.")
    review(db_session, fix, "edit", "Second pass.")

    before, after = db_session.execute(
        text("SELECT before, after FROM memory_reviews WHERE memory_id = :id"), {"id": fix}
    ).fetchone()
    assert (before, after) == ("Summary 3.", "Second pass.")


@pytest.mark.db
def test_reviews_outlive_a_reprocessed_video(db_session):
    ok, _, _ = _three_memories(db_session)
    review(db_session, ok, "accept")
    db_session.execute(text("DELETE FROM memories"))

    row = db_session.execute(text("SELECT memory_id, before FROM memory_reviews")).fetchone()
    assert row == (None, "Summary 1.")


@pytest.mark.db
def test_only_extracted_memories_can_be_reviewed(db_session):
    with pytest.raises(SystemExit):
        review(db_session, 999, "accept")
