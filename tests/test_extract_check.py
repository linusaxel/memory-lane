"""A kept summary loses only what its chunk doesn't say (extract.checked)."""

import json

import pytest
from sqlalchemy import text

from pipeline.extract import TRIM_PROMPT, UNSUPPORTED_PROMPT, checked
from tests.fakes import _Response

STORY = "A Pegasus relief, carved in 1942, still hangs over Nørregade."


class _Checker:
    """The detector names `claims`; the trim answers with `trimmed`."""

    def __init__(self, claims):
        self.messages = self
        self.calls = []
        self.claims = claims

    def create(self, **kwargs):
        self.calls.append(kwargs)
        system = kwargs["system"][0]["text"]
        if system == UNSUPPORTED_PROMPT:
            return _Response(json.dumps({"unsupported": self.claims}))
        assert system == TRIM_PROMPT
        return _Response(json.dumps({"summary": "A Pegasus relief from 1942 hangs here."}))


def _check(db_session, client, memory, content_id=0):
    chunk = "Pegasus ... sidder der endnu fra 1942"
    return checked(db_session, client, content_id, 0, chunk, "", memory)


def _content(db_session):
    return db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.youtube.com/watch?v=ccccccccccc', 'youtube', 'ccccccccccc') "
            "RETURNING id"
        )
    ).scalar()


@pytest.mark.db
def test_only_what_the_check_names_is_trimmed_and_a_rerun_is_free(db_session):
    client = _Checker([{"claim": "carved", "kind": "colour"}])
    memory, content = {"spot_test": "pass", "summary": STORY}, _content(db_session)
    trimmed = _check(db_session, client, memory, content)["summary"]
    assert trimmed == "A Pegasus relief from 1942 hangs here."
    assert "- carved" in client.calls[1]["messages"][0]["content"]
    _check(db_session, client, memory, content)
    assert len(client.calls) == 2


@pytest.mark.db
def test_a_faithful_summary_is_left_word_for_word(db_session):
    client = _Checker([])
    memory = {"spot_test": "pass", "summary": STORY}
    assert _check(db_session, client, memory, _content(db_session))["summary"] == STORY
    assert len(client.calls) == 1


def test_a_failed_spot_test_is_not_paid_for():
    client = _Checker([])
    assert _check(None, client, {"spot_test": "fail", "summary": STORY})["summary"] == STORY
    assert client.calls == []


def test_only_what_the_judge_kept_is_checked_and_the_chunk_is_let_go(monkeypatch):
    from pipeline import extract

    seen = []
    monkeypatch.setattr(
        extract, "checked", lambda s, c, cid, i, chunk, ctx, m: seen.append(chunk) or m
    )
    kept = extract.check_all(
        None, None, 0, "", [{"summary": STORY, "chunk": "the chunk", "chunk_index": 3}]
    )
    assert seen == ["the chunk"]
    assert kept == [{"summary": STORY, "chunk_index": 3}]
