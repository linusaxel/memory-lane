"""Contrast scoring: rank by the gap between then and now, not by importance.

The brief calls this the difference between the product being interesting and
being wallpaper. A jazz club that is now a bank lobby beats a cathedral's
founding date, because the cathedral is still a cathedral.

Scored once at extraction and stored. Extraction is a one-time cost per place,
amortised across everyone who ever stands there, so nothing here recomputes.

Note what is NOT tested, because it is not built: there is no enrichment pass
comparing the memory against what OSM says is at those coordinates today. It
would describe the wrong place - 60% of placed places in the live corpus sit on
a city centroid rather than the venue. See TODO.md 1.5.
"""

import pytest
from sqlalchemy import text

from pipeline.extract import HISTORICAL_SYSTEM_PROMPT, _contrast_score, save_memories

HIGH_CONTRAST = {
    "venue": "Vega",
    "locality": "Copenhagen",
    "region": "Denmark",
    "lat": 55.6668,
    "lng": 12.5379,
    "summary": "A touring band played the upstairs room in June 1978 to about four hundred people.",
    "tags": ["music"],
    "confidence": "high",
    "location_precision": "street",
    "contrast_score": 0.95,
    "contrast_note": "a 400-capacity room above a bicycle shop; a bank branch since 1994",
    "timestamp_start": 0,
}


def test_the_prompt_ranks_by_change_not_by_fame():
    """The instruction that decides whether the product is interesting."""
    assert "Fame is not contrast" in HISTORICAL_SYSTEM_PROMPT
    assert "still a cathedral" in HISTORICAL_SYSTEM_PROMPT
    assert "bank" in HISTORICAL_SYSTEM_PROMPT


def test_the_prompt_forbids_guessing_what_is_there_now():
    """An invented 'now' is as bad as an invented 'then', and harder to spot."""
    assert "Do not guess what is there now" in HISTORICAL_SYSTEM_PROMPT


@pytest.mark.parametrize(
    "raw,expected",
    [
        (0.95, 0.95),
        ("0.5", 0.5),
        (0, 0.0),
        (7, 1.0),
        (-3, 0.0),
        (None, None),
        ("high", None),
        ("", None),
        (True, None),
    ],
)
def test_an_unusable_score_becomes_null_not_a_rank(raw, expected):
    """Ordering depends on this column. A stray 'high' or a 7 must not sort
    above a real 0.95, and True must not quietly become 1.0."""
    assert _contrast_score({"contrast_score": raw}) == expected


@pytest.mark.db
def test_the_score_and_the_note_are_stored(db_session):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.invalid/c', 'text', 'c', 'archive') RETURNING id"
        )
    ).scalar()
    save_memories(db_session, content_id, [HIGH_CONTRAST])

    row = db_session.execute(text("SELECT contrast_score, contrast_note FROM memories")).fetchone()
    assert row.contrast_score == pytest.approx(0.95)
    assert "bank branch" in row.contrast_note


@pytest.mark.db
def test_a_memory_with_no_score_still_saves(db_session):
    """Every video memory in the corpus predates contrast scoring."""
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=ccccccccccc', 'youtube', 'ccccccccccc') "
            "RETURNING id"
        )
    ).scalar()
    without = {k: v for k, v in HIGH_CONTRAST.items() if not k.startswith("contrast")}
    save_memories(db_session, content_id, [without])
    row = db_session.execute(text("SELECT contrast_score FROM memories")).fetchone()
    assert row.contrast_score is None


@pytest.mark.db
def test_unscored_memories_sort_last_not_first(db_session):
    """NULL sorts FIRST under DESC in Postgres, so the 224 unscored memories
    would outrank every scored one. The query must say NULLS LAST."""
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.invalid/d', 'text', 'd', 'archive') RETURNING id"
        )
    ).scalar()
    unscored = {
        **{k: v for k, v in HIGH_CONTRAST.items() if not k.startswith("contrast")},
        "venue": "Somewhere Else",
    }
    save_memories(db_session, content_id, [HIGH_CONTRAST, unscored])

    ordered = db_session.execute(
        text("SELECT contrast_score FROM memories ORDER BY contrast_score DESC NULLS LAST")
    ).fetchall()
    assert ordered[0][0] == pytest.approx(0.95)
    assert ordered[-1][0] is None
