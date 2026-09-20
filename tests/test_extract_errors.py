"""A model that cannot be called must stop the run, not empty the backlog.

extract_memories_from_chunk caught every exception and returned []. A wrong
EXTRACTION_MODEL, a bad key or a revoked key therefore looked exactly like a
chunk containing no memories - so extract_all_pending saved nothing, set
memories_extracted = TRUE, and moved to the next video. One bad model ID would
have marked all 25 pending videos successfully extracted with zero memories,
and nothing would have said so.

Transient failures still return [] on purpose: one lost chunk is cheaper than
abandoning a run that is otherwise working.
"""

import anthropic
import httpx
import pytest

from pipeline.extract import BillingError, ModelUnusableError, extract_memories_from_chunk


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


def test_a_transient_error_still_yields_an_empty_chunk():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    transient = anthropic.APIConnectionError(request=request)
    assert extract_memories_from_chunk(_client_raising(transient), "a chunk") == []


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
