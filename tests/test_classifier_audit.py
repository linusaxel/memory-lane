"""The pre-filter's rejections are recorded, and the audit can count its misses.

Offline: FakeAnthropic stands in for the extractor.
"""

import pytest
from sqlalchemy import text

from pipeline.classifier_audit import audit
from pipeline.tasks import FAIL_OPEN, classify_chunk, record_verdict
from tests.fakes import FakeAnthropic


def test_a_fail_open_verdict_says_so():
    """A cut-off reply is not the model saying yes; the audit must not read it as one."""

    class _Messages:
        def create(self, **kwargs):
            return type("R", (), {"content": [type("C", (), {"text": '{"has_mem'})()]})()

    class _Client:
        messages = _Messages()

    has_memories, reason = classify_chunk(_Client(), "a chunk")
    assert has_memories is True
    assert reason.startswith(FAIL_OPEN)


@pytest.mark.db
def test_the_audit_finds_a_memory_the_classifier_rejected(db_session):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=ddddddddddd', 'youtube', 'ddddddddddd') "
            "RETURNING id"
        )
    ).scalar()
    record_verdict(db_session, content_id, 0, False, "just banter", "[0:00] we went to Katz's")
    record_verdict(db_session, content_id, 1, True, "a venue", "[4:00] something else")
    # Re-classifying the same chunk replaces its verdict rather than adding one.
    record_verdict(db_session, content_id, 0, False, "still banter", "[0:00] we went to Katz's")
    db_session.commit()

    fake = FakeAnthropic({"memories": FakeAnthropic().messages._payload})
    total, missed = audit(db_session, fake, sample=10)

    assert total == 1, "only rejections are sampled"
    assert len(missed) == 1
    row, kept = missed[0]
    assert row.reason == "still banter"
    assert kept[0]["venue"] == "Katz's Delicatessen"
    assert "Katz's" in fake.messages.calls[0]["messages"][0]["content"]
