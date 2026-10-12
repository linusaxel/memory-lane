"""The walk score is stored once per extracted memory, never on what a
person filed. FakeAnthropic answers; nothing bills."""

import pytest
from sqlalchemy import text

from pipeline import walk_score
from tests.fakes import FakeAnthropic

SCORES = {"score": 10}


def test_the_score_is_the_answer_kept_in_range():
    assert walk_score.walk_score(FakeAnthropic(SCORES), "a story") == 10
    assert walk_score.walk_score(FakeAnthropic({"score": 40}), "a story") == 12


def test_an_unusable_answer_is_no_score():
    assert walk_score.walk_score(FakeAnthropic({"site_lock": 2}), "a story") is None


def test_auc_is_the_chance_a_walk_beats_a_skip():
    assert walk_score.auc([9, 8], [3, 4]) == 1.0
    assert walk_score.auc([5], [5]) == 0.5
    assert walk_score.auc([2], [7, 1]) == 0.5


@pytest.mark.db
def test_scored_once_and_only_extracted(db_session):
    place = db_session.execute(
        text("INSERT INTO places (name, place_query) VALUES ('p', 'p') RETURNING id")
    ).scalar()
    extracted = db_session.execute(
        text("INSERT INTO memories (place_id, summary) VALUES (:p, 's') RETURNING id"),
        {"p": place},
    ).scalar()
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    db_session.execute(
        text("INSERT INTO memories (place_id, summary, user_id) VALUES (:p, 'mine', :u)"),
        {"p": place, "u": user},
    )
    fake = FakeAnthropic(SCORES)
    assert walk_score.score_memories(db_session, fake) == {extracted: 10}
    assert walk_score.score_memories(db_session, fake) == {}
    assert len(fake.messages.calls) == 1
    # A changed prompt makes the old score stale, and it is scored again.
    db_session.execute(text("UPDATE memories SET walk_score_prompt = 'older'"))
    assert walk_score.score_memories(db_session, fake) == {extracted: 10}


def test_graded_by_the_grader_whatever_extracts():
    """2026-10-04: a bake-off under EXTRACTION_MODEL=Opus scored Opus with Opus."""
    fake = FakeAnthropic(SCORES)
    walk_score.walk_score(fake, "a story")
    assert fake.messages.calls[0]["model"] == walk_score.GRADER_MODEL
