"""The walk rubric's sum is stored once per extracted memory, never on what a
person filed. FakeAnthropic answers; nothing bills."""

import pytest
from sqlalchemy import text

from pipeline import walk_score
from tests.fakes import FakeAnthropic

SCORES = {
    "site_lock": 2,
    "visible_trace": 2,
    "incident": 1,
    "surprise": 2,
    "feeling": 1,
    "relates": 2,
}


def test_the_score_is_the_sum():
    assert walk_score.walk_score(FakeAnthropic(SCORES), "a story") == 10


def test_an_unusable_answer_is_no_score():
    assert walk_score.walk_score(FakeAnthropic({"site_lock": 2}), "a story") is None


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
