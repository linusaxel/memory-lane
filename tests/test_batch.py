"""A batch pass collects one stage per content and saves nothing; the batch's
replies are stored where the next pass reads them (pipeline/batch.py)."""

from types import SimpleNamespace as NS

import pytest
from sqlalchemy import text

from pipeline import extract
from pipeline.batch import send
from pipeline.extract import Collect, _stored_request
from tests.fakes import _Response


@pytest.fixture
def collecting():
    extract.COLLECT = Collect()
    yield extract.COLLECT
    extract.COLLECT = None


def _rows(db_session):
    return db_session.execute(text("SELECT count(*) FROM extraction_chunks")).scalar()


@pytest.mark.db
def test_a_pass_collects_only_the_first_stage_to_miss(db_session, collecting):
    assert _stored_request(db_session, None, 7, 0, "extract", "chunk one") is None
    assert _stored_request(db_session, None, 7, 1, "extract", "chunk two") is None
    # The judge would read the chunks' answers: not paid for until they exist.
    assert _stored_request(db_session, None, 7, -2, "judge", "candidates") is None
    assert collecting.stage == {7: "extract"}
    assert [r["chunk_index"] for r in collecting.requests.values()] == [0, 1]
    assert _rows(db_session) == 0


class _Batches:
    def __init__(self, replies):
        self.replies = replies

    def create(self, requests):
        self.keys = [r["custom_id"] for r in requests]
        return NS(id="b1", processing_status="ended")

    def results(self, batch_id):
        for key, reply in zip(self.keys, self.replies, strict=True):
            if reply is None:
                yield NS(custom_id=key, result=NS(type="errored"))
                continue
            message = _Response(reply[0])
            message.stop_reason = reply[1]
            yield NS(custom_id=key, result=NS(type="succeeded", message=message))


@pytest.mark.db
def test_a_batch_reply_is_stored_where_the_next_pass_reads_it(db_session, collecting):
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=bbbbbbbbbbb', 'youtube', 'bbbbbbbbbbb') "
            "RETURNING id"
        )
    ).scalar()
    for i in range(3):
        _stored_request(db_session, None, cid, i, "extract", f"chunk {i}")
    requests, extract.COLLECT = collecting.requests, None
    batches = _Batches([('{"memories": []}', "end_turn"), ('{"memo', "max_tokens"), None])
    client = NS(messages=NS(batches=batches))
    assert send(client, requests, db_session) == 1
    assert _stored_request(db_session, None, cid, 0, "extract", "chunk 0") == '{"memories": []}'
    assert _rows(db_session) == 1
