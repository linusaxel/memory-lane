"""The Haiku pre-filter must not hide a broken CLASSIFIER_MODEL.

CLASSIFIER_MODEL shipped as "claude-haiku-3-20240307" - a transposition of the
real ID, and a retired model besides. Every call 404'd, `except Exception:
return True` swallowed it, and so every chunk was classified as having memories
and billed to Sonnet. The pre-filter is the entire cost rationale for the queue
path, and it had never once filtered. These tests pin the distinction that was
missing: a config error is permanent and must be loud, a transient error is not.
"""

import anthropic
import httpx
import pytest

from pipeline.extract import ModelUnusableError, TransientAPIError
from pipeline.tasks import classify_chunk


def _raising(exc):
    class _Messages:
        def create(self, **kwargs):
            raise exc

    class _Client:
        messages = _Messages()

    return _Client()


def _api_error(cls):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(404, request=request)
    return cls("nope", response=response, body=None)


@pytest.mark.parametrize(
    "exc_cls",
    [anthropic.NotFoundError, anthropic.AuthenticationError, anthropic.PermissionDeniedError],
)
def test_an_unusable_model_is_not_swallowed(exc_cls):
    with pytest.raises(ModelUnusableError, match="CLASSIFIER_MODEL"):
        classify_chunk(_raising(_api_error(exc_cls)), "a chunk")


def test_a_transient_error_retries_then_fails_open():
    """A throttled Haiku must not pass every chunk to Sonnet, but once the
    retries are spent over-extracting one chunk still beats dropping it."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    transient = anthropic.APIConnectionError(request=request)
    with pytest.raises(TransientAPIError):
        classify_chunk(_raising(transient), "a chunk", last_attempt=False)
    assert classify_chunk(_raising(transient), "a chunk")[0] is True


def test_unparseable_json_still_fails_open():
    class _Messages:
        def create(self, **kwargs):
            class _R:
                content = [type("C", (), {"text": "not json"})()]

            return _R()

    class _Client:
        messages = _Messages()

    assert classify_chunk(_Client(), "a chunk")[0] is True


def test_an_unusable_model_is_not_retried(monkeypatch):
    """Retried, it held a burst worker 12 minutes on a 30/120/600 s schedule."""
    from pipeline import tasks

    class Job:
        retries_left = 3

    job = Job()

    def unusable(*args, **kwargs):
        raise ModelUnusableError("CLASSIFIER_MODEL='gone' is not usable")

    monkeypatch.setattr(tasks, "get_current_job", lambda: job)
    monkeypatch.setattr(tasks, "classify_chunk", unusable)
    with pytest.raises(ModelUnusableError):
        tasks.task_classify_chunk(1, 0, 1, "a chunk")
    assert job.retries_left == 0
