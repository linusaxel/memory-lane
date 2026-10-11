"""The #words of a description are its tags. mobile/src/hashtags.test.ts reads
the same cases, so the app highlights exactly what the server stores."""

import json
import pathlib
import re

import pytest

from pipeline.tags import TAGS, from_text

CASES = json.loads((pathlib.Path(__file__).parent / "fixtures/hashtags.json").read_text())


@pytest.mark.parametrize(("text", "tags"), CASES)
def test_hashtags(text, tags):
    assert from_text(text) == tags


def test_the_planners_themes_are_the_extractors_tags():
    """mobile/src/Plan.tsx THEME_GROUPS is what a subscriber can lean a walk on;
    the API refuses anything outside pipeline/tags.py TAGS."""
    plan = (pathlib.Path(__file__).parents[1] / "mobile/src/Plan.tsx").read_text()
    block = plan.split("const THEME_GROUPS = [", 1)[1].split("];", 1)[0]
    themes = re.findall(r"'(\w+)'", "".join(re.findall(r"themes: \[([^\]]*)\]", block)))
    assert sorted(themes) == sorted(TAGS), "in any order"
