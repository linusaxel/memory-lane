"""The API enforces a JSON schema on every reply, so the schema is the contract.

A field the save path reads but the schema omits is one the model can no longer
return (additionalProperties is false), and a required field the fixtures lack
means the fixtures no longer look like a real reply. Offline, no credits.
"""

from pipeline.extract import (
    HISTORICAL_SYSTEM_PROMPT,
    MEMORY_SCHEMA,
    SYSTEM_PROMPT,
    extract_memories_from_chunk,
)
from pipeline.tags import TAGS
from pipeline.tasks import CLASSIFIER_SCHEMA, classify_chunk
from tests.fakes import FakeAnthropic

ITEM = MEMORY_SCHEMA["properties"]["memories"]["items"]


def test_the_extractor_sends_the_schema_for_both_prompts():
    for prompt in (SYSTEM_PROMPT, HISTORICAL_SYSTEM_PROMPT):
        fake = FakeAnthropic({"memories": []})
        extract_memories_from_chunk(fake, "chunk", prompt)
        fmt = fake.messages.calls[0]["output_config"]["format"]
        assert fmt == {"type": "json_schema", "schema": MEMORY_SCHEMA}


def test_the_classifier_sends_its_schema():
    fake = FakeAnthropic({"has_memories": False, "reason": "none"})
    assert classify_chunk(fake, "chunk") == (False, "none")
    assert fake.messages.calls[0]["output_config"]["format"]["schema"] == CLASSIFIER_SCHEMA


def test_the_fixture_reply_fits_the_schema():
    mem = FakeAnthropic().messages._payload[0]
    assert set(mem) <= set(ITEM["properties"])
    assert set(ITEM["required"]) <= set(mem)
    assert set(mem["tags"]) <= set(TAGS)


def test_every_field_the_archival_prompt_asks_for_is_allowed():
    for field in ("happened_at", "happened_precision", "attribution", "contrast_score"):
        assert field in HISTORICAL_SYSTEM_PROMPT
        assert field in ITEM["properties"]


def test_the_tag_enum_is_the_one_vocabulary():
    assert ITEM["properties"]["tags"]["items"]["enum"] == list(TAGS)


def test_the_decision_is_made_before_the_venue():
    """Claude fills fields in schema order. With venue first it commits to a place
    and then justifies it; the quote and the spot test have to come first."""
    assert list(ITEM["properties"])[:4] == ["place_words", "happened_there", "spot_test", "venue"]
