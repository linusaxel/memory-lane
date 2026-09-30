"""A summary's claims its chunk doesn't make are listed, never edited in."""

import json

import pytest
from sqlalchemy import text

from pipeline.extract import extract_chunk_stored, unsupported
from pipeline.review import check
from tests.fakes import FakeAnthropic

BOER = "Mr. Gig screened footage of the Boer War."
CLAIMS = {
    "checks": [
        {
            "index": 0,
            "claims": [
                {
                    "claim": "the Boer War",
                    "source_says": "Spanish-American",
                    "verdict": "contradicts",
                },
                {"claim": "Mr. Gig", "source_says": "Mr. Gig", "verdict": "supported"},
            ],
        }
    ]
}


def _content(db_session, source_type="archive") -> int:
    return db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.org/a', 'web', 'uuuuuuuuuuu', :t) RETURNING id"
        ),
        {"t": source_type},
    ).scalar()


@pytest.mark.db
def test_the_claims_are_listed_per_memory_and_the_summary_is_left(db_session):
    memories = [{"summary": BOER}, {"summary": "Mark argued about pastrami."}]
    claims = unsupported(
        db_session, FakeAnthropic(CLAIMS), _content(db_session), 0, "c", "", memories
    )
    assert claims == [["the Boer War (source: Spanish-American)"], []]


@pytest.mark.db
def test_a_failed_check_is_no_list_not_a_clean_one(db_session):
    """NULL is never checked; [] would read as checked and clean."""
    fake = FakeAnthropic({"memories": FakeAnthropic().messages._payload})
    [mem] = extract_chunk_stored(db_session, fake, _content(db_session), 0, "hello at Katz's")
    assert "unsupported" not in mem
    assert len(fake.messages.calls) == 2, "the extraction, then its check"


@pytest.mark.db
def test_check_lists_claims_for_a_memory_extracted_before_it(db_session):
    content_id = _content(db_session)
    db_session.execute(
        text(
            "INSERT INTO transcripts (content_id, segments, full_text) "
            "VALUES (:c, CAST(:s AS JSONB), 'x')"
        ),
        {"c": content_id, "s": json.dumps([{"start": 0, "text": "Wargraph, 1898, Cuba"}])},
    )
    db_session.execute(
        text(
            "INSERT INTO extraction_chunks (request_hash, content_id, chunk_index, prompt_hash, "
            "model, response) VALUES ('h', :c, 0, 'p', 'm', :r)"
        ),
        {"c": content_id, "r": json.dumps({"memories": [{"summary": BOER}]})},
    )
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Cirkusbygningen', 'Cirkusbygningen', ST_MakePoint(12.56, 55.67)::geography, 50) "
            "RETURNING id"
        )
    ).scalar()
    ids = [
        db_session.execute(
            text(
                "INSERT INTO memories (place_id, content_id, summary) "
                "VALUES (:p, :c, :s) RETURNING id"
            ),
            {"p": place, "c": content_id, "s": s},
        ).scalar()
        for s in (BOER, "Edited by hand since, so no reply wrote it.")
    ]

    assert check(db_session, FakeAnthropic(CLAIMS)) == 1
    found = dict(
        db_session.execute(
            text("SELECT id, unsupported FROM memories WHERE id = ANY(:i)"), {"i": ids}
        ).fetchall()
    )
    assert found == {ids[0]: ["the Boer War (source: Spanish-American)"], ids[1]: None}
