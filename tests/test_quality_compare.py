"""Two prompts, one sample, scored side by side - and paid for once."""

import json

import pytest
from sqlalchemy import text

from pipeline.quality import compare, report, sample_chunks
from tests.fakes import FakeAnthropic

BASE = FakeAnthropic().messages._payload[0]


class _ByPrompt:
    """Answers with a different summary depending on which system prompt asked."""

    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        system = kwargs["system"][0]["text"]
        summary = (
            "The speaker describes a sandwich."
            if system == "OLD"
            else "Mark argued about pastrami at Katz's."
        )
        reply = json.dumps({"memories": [dict(BASE, summary=summary)]})
        return type("R", (), {"content": [type("C", (), {"text": reply})()]})()


def _video_with_chunks(db_session, n):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=fffffffffff', 'youtube', 'fffffffffff') "
            "RETURNING id"
        )
    ).scalar()
    segments = [{"start": k * 300, "text": f"part {k} at Katz's"} for k in range(n)]
    db_session.execute(
        text(
            "INSERT INTO transcripts (content_id, segments, full_text) "
            "VALUES (:id, CAST(:s AS JSONB), 'x')"
        ),
        {"id": content_id, "s": json.dumps(segments)},
    )
    db_session.commit()
    return content_id


@pytest.mark.db
def test_both_prompts_see_the_same_stable_sample(db_session):
    _video_with_chunks(db_session, 4)
    first = sample_chunks(db_session, 3)
    assert len(first) == 3
    assert first == sample_chunks(db_session, 3)
    assert sample_chunks(db_session, 3, source_type="archive") == []


@pytest.mark.db
def test_the_comparison_scores_each_side_and_reruns_free(db_session):
    _video_with_chunks(db_session, 2)
    chunks = sample_chunks(db_session, 10)
    client = _ByPrompt()

    results = compare(db_session, client, {"baseline": "OLD", "candidate": "NEW"}, chunks)
    assert len(client.calls) == 2 * len(chunks)

    def flagged(name):
        summaries = [m["summary"] for kept in results[name] for m in kept]
        return {check: n for check, n, _ in report(summaries)}

    assert flagged("baseline")["anonymous subject"] == len(chunks)
    assert flagged("candidate")["anonymous subject"] == 0

    compare(db_session, client, {"baseline": "OLD", "candidate": "NEW"}, chunks)
    assert len(client.calls) == 2 * len(chunks), "a rerun must read extraction_chunks back"


@pytest.mark.db
def test_the_brief_is_paid_for_once_per_video(db_session):
    from pipeline.extract import video_brief

    content_id = _video_with_chunks(db_session, 2)
    fake = FakeAnthropic({"brief": "Trip Nørrebro: a yearly crawl."})
    segments = [{"start": 0, "text": "Trip Nørbrong 30 års jubilæum"}]
    for _ in range(2):
        brief = video_brief(db_session, fake, content_id, segments, "Københavnerliv", None)
    assert brief == "Trip Nørrebro: a yearly crawl."
    assert len(fake.messages.calls) == 1
