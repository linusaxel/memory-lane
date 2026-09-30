"""The label replay: the pipeline's judge over labelled memories, paid for once."""

import pytest
from sqlalchemy import text

from pipeline.quality import replay_labels, score_labels
from tests.fakes import FakeAnthropic

QUESTIONS = ("only_here", "breach", "consequence", "visible_now", "so_what", "stands_alone")


def _memory(db_session, content_id, name, summary):
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :n, ST_MakePoint(12.57, 55.68)::geography, 50) RETURNING id"
        ),
        {"n": name},
    ).scalar()
    return db_session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence) VALUES (:p, :c, 0, :s, 'high') RETURNING id"
        ),
        {"p": place, "c": content_id, "s": summary},
    ).scalar()


@pytest.mark.db
def test_the_replay_scores_the_judge_against_the_labels_and_reruns_free(db_session):
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=lllllllllll', 'youtube', 'lllllllllll') "
            "RETURNING id"
        )
    ).scalar()
    sank = _memory(db_session, content, "Ringkaféen, Copenhagen", "It sank into a stream.")
    start = _memory(db_session, content, "Maskot, Copenhagen", "The crawl starts here.")
    db_session.commit()

    fake = FakeAnthropic(
        {
            "verdicts": [
                {"index": 0, "note": "sank", **dict.fromkeys(QUESTIONS, True)},
                {"index": 1, "note": "routine", **dict.fromkeys(QUESTIONS, False)},
            ]
        }
    )
    labels = [
        {"id": sank, "verdict": "walk", "flags": []},
        {"id": start, "verdict": "skip", "flags": ["desc"]},
        {"id": -1, "verdict": "walk", "flags": []},
    ]

    kept, failed = replay_labels(db_session, fake, [m["id"] for m in labels])
    assert (kept, failed) == ({sank: True, start: False}, [])
    calls = len(fake.messages.calls)

    score = score_labels(kept, labels)
    assert score["verdicts"] == {"walk": [0, 1], "maybe": [0, 0], "skip": [1, 0]}
    assert score["flags"] == {"desc": [1, 0]}
    assert (score["precision"], score["recall"], score["missing"]) == (1.0, 1.0, 1)

    replay_labels(db_session, fake, [m["id"] for m in labels])
    assert len(fake.messages.calls) == calls, "a rerun must read extraction_chunks back"

    assert replay_labels(db_session, fake, [sank], half=1 - content % 2) == ({}, [])


@pytest.mark.db
def test_a_failed_judge_is_reported_not_scored_as_keeping_everything(db_session):
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=mmmmmmmmmmm', 'youtube', 'mmmmmmmmmmm') "
            "RETURNING id"
        )
    ).scalar()
    memory = _memory(db_session, content, "Maskot, Copenhagen", "The crawl starts here.")
    db_session.commit()

    kept, failed = replay_labels(db_session, FakeAnthropic({"not": "verdicts"}), [memory])
    assert (kept, failed) == ({memory: True}, [content])
