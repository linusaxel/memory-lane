"""Store listing copy.

Asserts the store's hard limits here rather than discovering them in App Store
Connect, and keeps the shipped privacy policy honest about what the app does.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LISTING = ROOT / "mobile" / "store" / "listing.md"
PRIVACY = ROOT / "mobile" / "store" / "privacy.md"

pytestmark = pytest.mark.skipif(not LISTING.exists(), reason="store copy not written yet")


def section(path: pathlib.Path, heading: str) -> str:
    """Body text under a '## heading', up to the next heading."""
    text = path.read_text()
    m = re.search(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert m, f"no '## {heading}' section in {path.name}"
    return m.group(1).strip()


def test_app_name_fits_the_store_limit():
    """30 characters on both stores."""
    name = section(LISTING, "Name (max 30)")
    assert 0 < len(name) <= 30, f"name is {len(name)} chars: {name!r}"


def test_subtitle_fits_the_store_limit():
    subtitle = section(LISTING, "Subtitle / short description (max 30)")
    assert 0 < len(subtitle) <= 30, f"subtitle is {len(subtitle)} chars: {subtitle!r}"


def test_ios_keywords_fit_100_characters():
    keywords = section(LISTING, "Keywords (iOS, max 100 chars, comma separated)")
    assert len(keywords) <= 100, f"keywords are {len(keywords)} chars"
    assert " ," not in keywords and ", " not in keywords, "spaces waste keyword budget"


def test_description_is_substantial():
    body = section(LISTING, "Description")
    assert len(body) > 300, "too thin for a store listing"
    assert len(body) <= 4000, "App Store caps the description at 4000 characters"


def test_privacy_copy_matches_what_the_app_actually_does():
    """The app requests precise location and has no accounts. A policy that
    fails to say so is a review rejection."""
    body = PRIVACY.read_text().lower()
    assert "location" in body
    assert "account" in body
    assert "youtube" in body, "the app hands off to YouTube - disclose it"


def test_served_privacy_policy_agrees_with_the_source_of_truth():
    """api/main.py serves the HTML twin. Keep the claims in sync."""
    served = (ROOT / "api" / "main.py").read_text().lower()
    for claim in ("location", "account", "youtube"):
        assert claim in served, f"the served /privacy page never mentions {claim}"
