"""mobile/src/story.test.ts reads the same cases, so the share card shows the
words the app shows."""

import json
import pathlib

import pytest

from api.story import plain

CASES = json.loads((pathlib.Path(__file__).parent / "fixtures/story.json").read_text())


@pytest.mark.parametrize(("md", "words"), CASES)
def test_plain(md, words):
    assert plain(md) == words
