"""A model that cannot be called must stop the run, not empty the backlog.

extract_memories_from_chunk caught every exception and returned []. A wrong
EXTRACTION_MODEL, a bad key or a revoked key therefore looked exactly like a
chunk containing no memories - so extract_all_pending saved nothing, set
memories_extracted = TRUE, and moved to the next video. One bad model ID would
have marked all 25 pending videos successfully extracted with zero memories,
and nothing would have said so.

A transient failure (429, 5xx, dropped connection) has the same shape one video
at a time: [] marked the video extracted with a hole in it, permanently. It now
raises TransientAPIError, the run moves on, and the video stays pending.
"""

from contextlib import contextmanager

import anthropic
import httpx
import pytest
from sqlalchemy import text

from pipeline import extract
from pipeline.extract import (
    BillingError,
    ModelUnusableError,
    TransientAPIError,
    extract_memories_from_chunk,
)
from tests.fakes import FakeAnthropic


def _client_raising(exc):
    class _Messages:
        def create(self, **kwargs):
            raise exc

    class _Client:
        messages = _Messages()

    return _Client()


def _api_error(cls, status):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("nope", response=httpx.Response(status, request=request), body=None)


@pytest.mark.parametrize(
    "cls,status",
    [
        (anthropic.NotFoundError, 404),
        (anthropic.AuthenticationError, 401),
        (anthropic.PermissionDeniedError, 403),
    ],
)
def test_an_unusable_model_stops_the_run(cls, status):
    with pytest.raises(ModelUnusableError, match="EXTRACTION_MODEL"):
        extract_memories_from_chunk(_client_raising(_api_error(cls, status)), "a chunk")


def test_the_error_names_the_model_so_the_fix_is_obvious():
    with pytest.raises(ModelUnusableError) as caught:
        extract_memories_from_chunk(_client_raising(_api_error(anthropic.NotFoundError, 404)), "x")
    assert "EXTRACTION_MODEL=" in str(caught.value)


@pytest.mark.parametrize(
    "exc",
    [
        anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        ),
        _api_error(anthropic.RateLimitError, 429),
        _api_error(anthropic.InternalServerError, 500),
        _api_error(anthropic.OverloadedError, 529),
    ],
    ids=["connection", "429", "500", "529"],
)
def test_a_transient_error_is_not_an_empty_chunk(exc):
    with pytest.raises(TransientAPIError):
        extract_memories_from_chunk(_client_raising(exc), "a chunk")


class _FailsOnSecondCall:
    """One video's chunk succeeds, the next call raises `exc`."""

    def __init__(self, exc):
        self._ok = FakeAnthropic({"memories": FakeAnthropic().messages._payload}).messages
        self._exc = exc
        self.messages = self

    def create(self, **kwargs):
        if self._ok.calls:
            raise self._exc
        return self._ok.create(**kwargs)


def _pending_video(db_session, vid, segments='[{"start": 0, "text": "hello"}]'):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, transcript_fetched) "
            "VALUES (:url, 'youtube', :vid, TRUE) RETURNING id"
        ),
        {"url": f"https://www.youtube.com/watch?v={vid}", "vid": vid},
    ).scalar()
    db_session.execute(
        text(
            "INSERT INTO transcripts (content_id, segments, full_text) "
            "VALUES (:id, CAST(:segments AS JSONB), 'x')"
        ),
        {"id": content_id, "segments": segments},
    )
    db_session.commit()


def _two_pending_videos(db_session):
    _pending_video(db_session, "aaaaaaaaaaa")
    _pending_video(db_session, "bbbbbbbbbbb")


def _run(db_session, monkeypatch, client):
    @contextmanager
    def _session():
        try:
            yield db_session
            db_session.commit()
        except BaseException:
            db_session.rollback()
            raise

    monkeypatch.setattr(extract, "get_session", _session)
    monkeypatch.setattr(extract, "ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(extract.anthropic, "Anthropic", lambda **_: client)
    return extract.extract_all_pending()


def _states(db_session):
    return sorted(
        db_session.execute(
            text("SELECT memories_extracted, extraction_failed FROM content")
        ).fetchall()
    )


@pytest.mark.db
def test_a_transient_error_leaves_the_video_pending_not_failed(db_session, monkeypatch):
    _two_pending_videos(db_session)
    _run(db_session, monkeypatch, _FailsOnSecondCall(_api_error(anthropic.OverloadedError, 529)))
    assert _states(db_session) == [(False, False), (True, False)]


@pytest.mark.db
def test_a_crash_keeps_the_videos_already_extracted(db_session, monkeypatch):
    """One transaction per run used to throw away every paid-for video."""
    _two_pending_videos(db_session)
    with pytest.raises(KeyboardInterrupt):
        _run(db_session, monkeypatch, _FailsOnSecondCall(KeyboardInterrupt()))
    assert _states(db_session) == [(False, False), (True, False)]
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 1


def test_billing_still_raises_its_own_error():
    """Billing is separately recoverable - the caller reports it differently."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.BadRequestError(
        "your credit balance is too low",
        response=httpx.Response(400, request=request),
        body=None,
    )
    with pytest.raises(BillingError):
        extract_memories_from_chunk(_client_raising(err), "a chunk")


def test_unparseable_output_is_an_empty_chunk_not_a_crash():
    class _Messages:
        def create(self, **kwargs):
            return type("R", (), {"content": [type("C", (), {"text": "not json at all"})()]})()

    class _Client:
        messages = _Messages()

    assert extract_memories_from_chunk(_Client(), "a chunk") == []


# -- the classifier has the same three classes of failure ---------------------


def _billing_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.BadRequestError(
        "Your credit balance is too low to access the Anthropic API.",
        response=httpx.Response(400, request=request),
        body=None,
    )


def test_the_classifier_stops_on_an_empty_balance():
    """Observed on a real run: the classifier failed open on a billing 400, so
    all 22 chunks were reported classified, all 22 were enqueued for extraction,
    and all 22 hit the same wall. An empty balance is not transient."""
    from pipeline.tasks import classify_chunk

    with pytest.raises(BillingError):
        classify_chunk(_client_raising(_billing_error()), "a chunk")


def test_the_classifier_still_fails_open_on_a_transient_error():
    """Over-extracting one chunk beats dropping it."""
    from pipeline.tasks import classify_chunk

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    assert classify_chunk(_client_raising(anthropic.APIConnectionError(request=request)), "x")


def test_the_billing_match_is_on_the_wording_the_api_actually_uses():
    """The API reports an empty balance as a 400 with the reason in the message
    rather than as its own class, so this is a string match. Pinned, because a
    near-miss turns a hard stop back into a fail-open and nothing else notices."""
    from pipeline.extract import is_billing_error

    assert is_billing_error(_billing_error())

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    other_400 = anthropic.BadRequestError(
        "max_tokens is too large", response=httpx.Response(400, request=request), body=None
    )
    assert not is_billing_error(other_400)


@pytest.mark.db
def test_a_retried_video_only_pays_for_the_chunk_it_lost(db_session, monkeypatch):
    """Chunk 1 answered, chunk 2 hit a 529. The rerun must not bill chunk 1 again."""
    _pending_video(
        db_session,
        "ccccccccccc",
        '[{"start": 0, "text": "first"}, {"start": 600, "text": "second"}]',
    )
    _run(db_session, monkeypatch, _FailsOnSecondCall(_api_error(anthropic.OverloadedError, 529)))
    assert _states(db_session) == [(False, False)]

    rerun = FakeAnthropic({"memories": FakeAnthropic().messages._payload})
    _run(db_session, monkeypatch, rerun)
    assert len(rerun.messages.calls) == 1
    assert "second" in rerun.messages.calls[0]["messages"][0]["content"]
    assert _states(db_session) == [(True, False)]
    assert db_session.execute(text("SELECT COUNT(*) FROM extraction_chunks")).scalar() == 2
