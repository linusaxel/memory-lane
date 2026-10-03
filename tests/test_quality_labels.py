"""The label replay: the pipeline's judge over labelled memories, paid for once."""

import json

import pytest
from sqlalchemy import text

from pipeline.quality import read_whole, replay_labels, score_labels, score_whole, visible
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


@pytest.mark.db
def test_visible_is_what_one_source_type_still_shows(db_session):
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://www.gutenberg.org/ebooks/1#1', 'gutenberg', 'g1', 'book') "
            "RETURNING id"
        )
    ).scalar()
    shown = _memory(db_session, content, "Blåtårn", "Kept in the tower.")
    hidden = _memory(db_session, content, "Kastellet", "Held in a cell.")
    db_session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": hidden})
    db_session.commit()

    assert [r.id for r in visible(db_session, "book")] == [shown]
    assert shown not in [r.id for r in visible(db_session, "video")]


@pytest.mark.db
def test_a_whole_video_is_one_stored_request_scored_against_the_labels(db_session):
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, title, source_name) "
            "VALUES ('https://www.youtube.com/watch?v=wwwwwwwwwww', 'youtube', 'wwwwwwwwwww', "
            "'Byens bikse', 'Københavnerliv') RETURNING id"
        )
    ).scalar()
    segments = [{"start": s, "text": f"Ringkaféen line {s}"} for s in range(0, 3600, 60)]
    db_session.execute(
        text(
            "INSERT INTO transcripts (content_id, segments, full_text) "
            "VALUES (:c, CAST(:s AS jsonb), 'x')"
        ),
        {"c": content, "s": json.dumps(segments)},
    )
    db_session.commit()
    memory = {
        "place_words": "Ringkaféen",
        "spot_test": "pass",
        "venue": "Ringkaféen",
        "locality": "Copenhagen",
        "summary": "The café sank into a stream under Nørrebro.",
        "location_precision": "exact",
        "confidence": "high",
    }
    fake = FakeAnthropic(
        {
            "brief": "A pub crawl.",
            "memories": [memory],
            "verdicts": [{"index": 0, "note": "sank", **dict.fromkeys(QUESTIONS, True)}],
        }
    )

    kept = read_whole(db_session, fake, content)
    assert [m["venue"] for m in kept] == ["Ringkaféen"]
    stored = db_session.execute(
        text("SELECT count(*) FROM extraction_chunks WHERE content_id = :c AND chunk_index = -5"),
        {"c": content},
    ).scalar()
    assert stored == 1, "an hour of video is one request"
    calls = len(fake.messages.calls)
    read_whole(db_session, fake, content)
    assert len(fake.messages.calls) == calls, "a rerun must read extraction_chunks back"

    labelled = [
        {"id": 1, "verdict": "walk", "venue": "Ringkaféen, Copenhagen", "summary": "It sank."},
        {"id": 2, "verdict": "walk", "venue": "Maskot, Copenhagen", "summary": "The crawl starts."},
        {"id": 3, "verdict": "skip", "venue": "Maskot, Copenhagen", "summary": "The crawl starts."},
    ]
    score = score_whole(labelled, kept)
    assert (score["walks"], score["walks_found"]) == (2, 1)
    assert (score["chunked"]["dups"], score["whole"]["dups"]) == (1, 0)
