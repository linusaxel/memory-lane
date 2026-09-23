"""Permanent vs transient transcript failures.

The distinction is the whole point. `fetch_transcript` returning None means
"this video will never have captions" and the caller permanently sets
transcript_failed = TRUE. Anything else - a network blip, an IP block, a
consent/age gate - must NOT reach that path, or one bad minute silently
removes a video from the pipeline forever with no record of why.

Offline: no network, no API credits. The IP-block test needs the DB.
"""

import pytest
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from pipeline import transcripts


class _Fetched:
    def __init__(self, segments):
        self._segments = segments

    def to_raw_data(self):
        return self._segments


def _api_raising(exc):
    class _Api:
        def fetch(self, video_id, languages=None):
            raise exc

    return lambda **_: _Api()


def _api_returning(segments):
    class _Api:
        def fetch(self, video_id, languages=None):
            return _Fetched(segments)

    return lambda **_: _Api()


# -- permanent: these genuinely mean "no captions, ever" ---------------------


@pytest.mark.parametrize(
    "exc",
    [
        TranscriptsDisabled("v"),
        VideoUnavailable("v"),
        NoTranscriptFound("v", ["en"], {}),
    ],
    ids=["disabled", "unavailable", "not_found"],
)
def test_permanent_failures_return_none(monkeypatch, exc):
    monkeypatch.setattr(transcripts, "YouTubeTranscriptApi", _api_raising(exc))
    assert transcripts.fetch_transcript("vvvvvvvvvvv") is None


# -- transient: these must NOT be mistaken for "no captions" -----------------


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("read timed out"),
        ConnectionError("connection reset by peer"),
        RuntimeError("blocked: too many requests from this IP"),
    ],
    ids=["timeout", "connection_reset", "ip_block"],
)
def test_transient_failures_propagate(monkeypatch, exc):
    """THE REGRESSION GUARD.

    This fails the moment someone reintroduces a bare `except Exception` in
    fetch_transcript. Before this fix, every one of these returned None and the
    caller black-holed the video permanently.
    """
    monkeypatch.setattr(transcripts, "YouTubeTranscriptApi", _api_raising(exc))

    with pytest.raises(type(exc)):
        transcripts.fetch_transcript("vvvvvvvvvvv")


def test_fetch_transcript_has_no_bare_except():
    """Belt and braces, scoped to where the bug lived.

    A bare handler in fetch_transcript collapses transient failures into
    permanent ones. The CALLER is allowed one - that is the retry path, which
    catches broadly precisely so it can leave the row pending.
    """
    import inspect

    source = inspect.getsource(transcripts.fetch_transcript)
    assert "except Exception" not in source, (
        "a bare `except Exception` here makes a network blip look identical to "
        "'this video has no captions' - catch the specific errors instead"
    )


# -- the success path --------------------------------------------------------


def test_segments_are_joined_into_full_text(monkeypatch):
    segments = [
        {"text": "we went to", "start": 0.0, "duration": 1.0},
        {"text": "Katz's", "start": 1.0, "duration": 1.0},
    ]
    monkeypatch.setattr(transcripts, "YouTubeTranscriptApi", _api_returning(segments))

    result = transcripts.fetch_transcript("vvvvvvvvvvv")

    assert result["segments"] == segments
    assert result["full_text"] == "we went to Katz's"
    assert result["language"] == "en"


# -- an IP block stops the run -----------------------------------------------


@pytest.mark.db
def test_an_ip_block_stops_the_run_and_leaves_every_row_pending(db_session, monkeypatch):
    """Every row after a block fails the same way and digs it deeper."""
    from contextlib import contextmanager

    from sqlalchemy import text
    from youtube_transcript_api._errors import IpBlocked

    for vid in ("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"):
        db_session.execute(
            text("INSERT INTO content (url, platform, platform_id) VALUES (:u, 'youtube', :v)"),
            {"u": f"https://www.youtube.com/watch?v={vid}", "v": vid},
        )
    db_session.commit()

    calls = []

    class _Api:
        def fetch(self, video_id, languages=None):
            calls.append(video_id)
            raise IpBlocked(video_id)

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(transcripts, "YouTubeTranscriptApi", lambda **_: _Api())
    monkeypatch.setattr(transcripts, "get_session", _session)

    result = transcripts.fetch_pending_transcripts()

    assert result["error"] == "blocked"
    assert len(calls) == 1
    flags = db_session.execute(
        text("SELECT transcript_fetched, transcript_failed FROM content")
    ).fetchall()
    assert set(flags) == {(False, False)}


def test_the_proxy_is_handed_to_the_client(monkeypatch):
    seen = {}

    class _Api:
        def fetch(self, video_id, languages=None):
            return _Fetched([{"text": "x", "start": 0.0, "duration": 1.0}])

    def _make(**kwargs):
        seen.update(kwargs)
        return _Api()

    monkeypatch.setattr(transcripts, "YouTubeTranscriptApi", _make)
    monkeypatch.setattr(transcripts, "TRANSCRIPT_PROXY", "http://u:p@proxy:8080")
    transcripts.fetch_transcript("vvvvvvvvvvv")

    proxies = seen["proxy_config"].to_requests_dict()
    assert proxies == {"http": "http://u:p@proxy:8080", "https": "http://u:p@proxy:8080"}
