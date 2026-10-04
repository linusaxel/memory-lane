"""Two prompts, one sample, scored side by side - and paid for once."""

import json

import pytest
from sqlalchemy import text

from pipeline import quality
from pipeline.quality import compare, places, report, sample_chunks
from tests.fakes import FakeAnthropic, _Response

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
        return _Response(reply)


def _extractions(client):
    """The extractor's calls, not the check each kept memory gets (extract.checked)."""
    return [c for c in client.calls if c["system"][0]["text"] in ("OLD", "NEW")]


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
    assert len(_extractions(client)) == 2 * len(chunks)
    paid = len(client.calls)

    def flagged(name):
        summaries = [m["summary"] for runs in results[name] for m in runs[0]]
        return {check: n for check, n, _ in report(summaries)}

    assert flagged("baseline")["anonymous subject"] == len(chunks)
    assert flagged("candidate")["anonymous subject"] == 0

    compare(db_session, client, {"baseline": "OLD", "candidate": "NEW"}, chunks)
    assert len(client.calls) == paid, "a rerun must read extraction_chunks back"


@pytest.mark.db
def test_runs_are_fresh_draws_and_each_is_stored(db_session):
    _video_with_chunks(db_session, 2)
    chunks = sample_chunks(db_session, 10)
    client = _ByPrompt()

    results = compare(db_session, client, {"baseline": "OLD"}, chunks, runs=3)
    assert len(_extractions(client)) == 3 * len(chunks)
    assert all(len(runs) == 3 for runs in results["baseline"])
    paid = len(client.calls)

    compare(db_session, client, {"baseline": "OLD"}, chunks, runs=3)
    assert len(client.calls) == paid


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


def test_a_brief_ending_in_a_curly_quote_is_cut_there():
    """Both shapes stored on 2026-09-28: 535 rambled past its ”, and 583 repeated
    } until max_tokens, which does not parse at all."""
    from pipeline.extract import brief_from

    rambled = '{"brief":"Leth\'s portrait films.”}} 434 words? no.  Let\'s not worry."}'
    spiral = '{"brief":"25 of 220 pubs have closed.”}]' + "}" * 50
    assert brief_from(rambled) == "Leth's portrait films."
    assert brief_from(spiral) == "25 of 220 pubs have closed."
    assert (
        brief_from('{"brief":"Trip Nørrebro: a yearly crawl."}') == "Trip Nørrebro: a yearly crawl."
    )


class _Venues:
    """OLD names a venue no geocoder finds, NEW the one it does."""

    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        venue = "Nowhere Bar" if kwargs["system"][0]["text"] == "OLD" else "Katz's Delicatessen"
        return _Response(json.dumps({"memories": [dict(BASE, venue=venue)]}))


@pytest.mark.db
def test_places_counts_what_each_prompt_gets_placed(db_session, monkeypatch):
    content_id = _video_with_chunks(db_session, 2)
    every_chunk = sample_chunks(db_session, None)
    place_id = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, geocode_status) VALUES ('n', 'n', 'llm') RETURNING id"
        )
    ).scalar()
    db_session.execute(
        text("INSERT INTO memories (place_id, content_id, summary) VALUES (:p, :c, 's')"),
        {"p": place_id, "c": content_id},
    )
    db_session.commit()
    monkeypatch.setattr(
        quality,
        "place_of",
        lambda m: (40.7, -73.9, 30, "fake") if m["venue"] == "Katz's Delicatessen" else None,
    )
    client = _Venues()

    n, counts = places(db_session, client, {"baseline": "OLD", "candidate": "NEW"})
    assert n == len(every_chunk)
    assert counts == {"baseline": (n, 0), "candidate": (n, n)}

    billed = len(client.calls)
    places(db_session, client, {"baseline": "OLD", "candidate": "NEW"})
    assert len(client.calls) == billed, "a rerun reads extraction_chunks back"
