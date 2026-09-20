"""A second extraction prompt for archival text, and honest precision.

Two separate problems.

The personal prompt asks the model for WHO, WHAT HAPPENED and THE VIBE, and
tells it to write like it is telling a friend. Pointed at a newspaper clipping
that is an invitation to invent - names, emotions, atmosphere that no source
supports. Third-party material needs its own instructions.

Separately, the model claims `location_precision: exact` for coordinates it
guessed. 111 of 186 placed places in the live corpus sit on 34 city-centroid
points and 35 of them claim 50m accuracy, so nothing can filter or rank on
precision. Both prompts now have to say what they do not know.

No credits are spent here: FakeAnthropic records the request that would have
been sent, which is what these assert against.
"""

import pytest
from sqlalchemy import text

from pipeline.extract import (
    HISTORICAL_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    _happened_at,
    extract_memories_from_chunk,
    layer_for,
    prompt_for,
    save_memories,
)
from tests.fakes import FakeAnthropic

ARCHIVE_MEMORY = {
    "place_name": "Vega, Vesterbro",
    "place_query": "Vega Enghavevej Vesterbro Copenhagen Denmark",
    "lat": 55.6668,
    "lng": 12.5379,
    "summary": "A touring band played the upstairs room in June 1978 to about four hundred people.",
    "tags": ["music", "history"],
    "confidence": "high",
    "location_precision": "street",
    "happened_at": "1978-06-17",
    "happened_precision": "day",
    "attribution": "SYNTHETIC FIXTURE",
    "source_url": "https://example.invalid/synthetic/1",
    "timestamp_start": 0,
}


def test_archival_text_gets_the_archival_prompt():
    assert prompt_for("archive") is HISTORICAL_SYSTEM_PROMPT
    assert prompt_for("newspaper") is HISTORICAL_SYSTEM_PROMPT
    assert prompt_for("video") is SYSTEM_PROMPT
    assert prompt_for(None) is SYSTEM_PROMPT, "unknown source must not get archival rules"


def test_the_archival_prompt_refuses_a_building_merely_existing():
    """'Constructed in 1902' is the failure mode for archive text, the way
    'I want to visit someday' is for a transcript."""
    assert "constructed in 1902" in HISTORICAL_SYSTEM_PROMPT
    assert "A building EXISTING is not something that HAPPENED" in HISTORICAL_SYSTEM_PROMPT


def test_the_archival_prompt_forbids_filling_gaps():
    """The one failure that would poison the corpus: plausible invented history
    is indistinguishable from the real thing once it is a row."""
    assert "Do not fill gaps with plausible history" in HISTORICAL_SYSTEM_PROMPT
    assert "An empty list" in HISTORICAL_SYSTEM_PROMPT


def test_the_archival_prompt_does_not_ask_for_a_vibe():
    """The personal register invites invention when pointed at a source document."""
    assert "THE VIBE" in SYSTEM_PROMPT
    assert "THE VIBE" not in HISTORICAL_SYSTEM_PROMPT
    assert "no invented emotions" in HISTORICAL_SYSTEM_PROMPT


def test_the_archival_prompt_asks_when_it_happened():
    assert "happened_at" in HISTORICAL_SYSTEM_PROMPT
    assert "happened_precision" in HISTORICAL_SYSTEM_PROMPT


@pytest.mark.parametrize("prompt", [SYSTEM_PROMPT, HISTORICAL_SYSTEM_PROMPT])
def test_both_prompts_forbid_claiming_accuracy_they_do_not_have(prompt):
    """35 stacked places claim precision_meters=50 today. 'Exact' and 'I guessed
    the city' cannot keep meaning the same thing."""
    assert 'say "city"' in prompt
    assert 'Only say "exact"' in prompt or 'Only "exact"' in prompt
    assert "claims 50m accuracy" in prompt


def _system_text(fake):
    """The system prompt is sent as one cacheable block, not a bare string.

    Identity, not equality: these tests exist to prove the *chosen* prompt is
    the one that travels, and two prompts that happen to match would pass an
    equality check while the wrong object was being sent.
    """
    system = fake.messages.calls[0]["system"]
    assert isinstance(system, list) and len(system) == 1, "one cached block"
    assert system[0]["cache_control"] == {"type": "ephemeral"}, "still cached"
    return system[0]["text"]


def test_the_chosen_prompt_is_the_one_actually_sent():
    """Selecting a prompt is worthless if the call ignores it."""
    fake = FakeAnthropic([ARCHIVE_MEMORY])
    extract_memories_from_chunk(fake, "some archive text", HISTORICAL_SYSTEM_PROMPT)
    assert _system_text(fake) is HISTORICAL_SYSTEM_PROMPT


def test_the_default_prompt_is_still_the_personal_one():
    fake = FakeAnthropic()
    extract_memories_from_chunk(fake, "some transcript")
    assert _system_text(fake) is SYSTEM_PROMPT


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1978-06-17", "1978-06-17"),
        ("1978-06", "1978-06-01"),
        ("1978", "1978-01-01"),
        ("", None),
        (None, None),
        ("sometime in the seventies", None),
    ],
)
def test_a_partial_date_widens_to_the_start_of_its_period(raw, expected):
    """A clipping that gives only a year is answering honestly; the precision
    field carries how much of the date to trust."""
    assert _happened_at({"happened_at": raw}) == expected


def test_everything_ingested_so_far_is_the_historical_layer():
    """Friend and stranger memories arrive through a write path that does not exist."""
    assert layer_for("archive") == "historical"
    assert layer_for("video") == "historical"


@pytest.mark.db
def test_an_archival_memory_keeps_its_date_and_credit(db_session):
    """The prompt asking for happened_at is pointless if the column stays null."""
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.invalid/x', 'text', 'x', 'archive') RETURNING id"
        )
    ).scalar()

    save_memories(db_session, content_id, [ARCHIVE_MEMORY], layer="historical")

    row = db_session.execute(
        text("""
            SELECT layer, happened_at, happened_precision, attribution, source_url
            FROM memories
        """)
    ).fetchone()
    assert row.layer == "historical"
    assert str(row.happened_at) == "1978-06-17"
    assert row.happened_precision == "day"
    assert row.attribution == "SYNTHETIC FIXTURE"
    assert row.source_url == "https://example.invalid/synthetic/1"


@pytest.mark.db
def test_a_transcript_memory_without_a_date_still_saves(db_session):
    """Most video memories will never have happened_at. Null, not an error."""
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=bbbbbbbbbbb', 'youtube', 'bbbbbbbbbbb') "
            "RETURNING id"
        )
    ).scalar()
    save_memories(db_session, content_id, [FakeAnthropic().messages._payload[0]])
    row = db_session.execute(text("SELECT layer, happened_at FROM memories")).fetchone()
    assert row.layer == "historical"
    assert row.happened_at is None
