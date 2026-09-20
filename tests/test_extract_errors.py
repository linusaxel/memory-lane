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
