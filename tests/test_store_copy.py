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


# Every subject the app collects something about. A policy that omits one is a
# store rejection at best; before submissions and sign-in shipped, this file
# checked for the three substrings "location", "account" and "youtube", which
# stayed true while the policy underneath them said "Accounts. There are none."
# A guard that cannot fail is not a guard.
DISCLOSURES = {
    "precise location": ("location",),
    "background location for the proximity notification": ("background",),
    "sign-in": ("google", "apple"),
    "the email a provider hands over": ("email",),
    "the public display name": ("display name",),
    "posts being public": ("public",),
    "attached photos": ("photo",),
    "attached recordings": ("recording",),
    "the camera and microphone": ("camera", "microphone"),
    "reporting and takedown": ("report",),
    "the per-install identifier": ("identifier",),
    "handing off to youtube": ("youtube",),
}


def missing(text: str) -> list[str]:
    lowered = text.lower()
    return [
        subject
        for subject, words in DISCLOSURES.items()
        if not all(word in lowered for word in words)
    ]


def test_the_policy_covers_everything_the_app_collects():
    assert missing(PRIVACY.read_text()) == []


def test_the_served_policy_covers_it_too():
    """api/main.py serves the HTML twin, and it is the copy that actually ships
    to a phone - store/privacy.md is what a human pastes into App Store Connect.
    Both have to say the same things or one of them is a lie."""
    assert missing((ROOT / "api" / "privacy.py").read_text()) == []


def test_the_policy_no_longer_claims_there_are_no_accounts():
    """The sentence this file used to pass over. Sign-in shipped; the policy
    said otherwise for a while, and nothing caught it."""
    body = PRIVACY.read_text().lower()
    for lie in ("there are none", "no accounts", "we do not ask for your name"):
        assert lie not in body


def test_the_data_safety_answers_were_revisited_after_the_write_path():
    """Play and the App Store both ask what is collected and whether it is
    linked to the user. Those answers were written when the app was read-only,
    and submitting the old ones is a false declaration."""
    answers = section(LISTING, "Play Data safety answers").lower()
    assert "no accounts" not in answers
    for subject in ("display name", "email", "photos", "audio", "user-generated"):
        assert subject in answers, f"Data safety says nothing about {subject}"
