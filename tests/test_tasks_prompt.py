"""The queue path must not hand archival text the personal prompt.

pipeline/extract.py picks a prompt from content.source_type. The RQ path did
not: it called extract_memories_from_chunk with the default, so anything but
video run through workers would be asked for WHO and THE VIBE. For third-party
archive material that is an invitation to invent, which is the one thing it
must not get.

source_type rides in the extraction:{id} Redis hash rather than as a task
kwarg, so these also pin the default for a hash written before that field
existed.
"""

import pytest

from pipeline.extract import HISTORICAL_SYSTEM_PROMPT, SYSTEM_PROMPT, prompt_for
from pipeline.tasks import _source_type


class FakeRedis:
    def __init__(self, value=None, missing=False):
        self._value = value
        self._missing = missing

    def hget(self, key, field):
        assert field == "source_type"
        return None if self._missing else self._value


def test_bytes_from_redis_are_decoded():
    assert _source_type(FakeRedis(b"historical"), 1) == "historical"


def test_str_from_redis_passes_through():
    assert _source_type(FakeRedis("historical"), 1) == "historical"


def test_a_hash_without_the_field_means_video():
    """Written before source_type existed: the corpus then was all video."""
    assert _source_type(FakeRedis(missing=True), 1) == "video"


@pytest.mark.parametrize(
    "source_type,expected",
    [("video", SYSTEM_PROMPT), (None, SYSTEM_PROMPT), ("historical", HISTORICAL_SYSTEM_PROMPT)],
)
def test_source_type_selects_the_prompt(source_type, expected):
    assert prompt_for(source_type) is expected


def test_archival_text_never_gets_asked_for_the_vibe():
    """The specific failure this guards: the personal prompt's invented-detail
    invitations must be absent from the archival one."""
    archival = prompt_for("historical")
    assert "THE VIBE" not in archival
    assert "THE VIBE" in prompt_for("video"), "the personal prompt should still ask for it"


def test_the_queue_path_resolves_a_prompt_from_redis():
    """End to end through the two helpers the task actually calls."""
    assert prompt_for(_source_type(FakeRedis(b"historical"), 7)) is HISTORICAL_SYSTEM_PROMPT
    assert prompt_for(_source_type(FakeRedis(missing=True), 7)) is SYSTEM_PROMPT
