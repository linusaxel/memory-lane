"""The #words of a description are its tags. mobile/src/hashtags.test.ts reads
the same cases, so the app highlights exactly what the server stores."""

import json
import pathlib

import pytest

from pipeline.tags import from_text

CASES = json.loads((pathlib.Path(__file__).parent / "fixtures/hashtags.json").read_text())


@pytest.mark.parametrize(("text", "tags"), CASES)
def test_hashtags(text, tags):
    assert from_text(text) == tags
