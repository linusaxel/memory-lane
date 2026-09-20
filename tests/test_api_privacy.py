"""The privacy policy route.

This exists to delete a human blocker: both App Store Connect and Play Console
require a publicly reachable privacy policy URL, and the API already has an
HTTPS host. Serving it here means no separate site to host and keep alive.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_privacy_page_is_served():
    r = client.get("/privacy")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<html" in r.text


def test_privacy_page_discloses_location_use():
    """The app requests precise location, so the policy must say so - a vague
    policy is a rejection at review."""
    body = client.get("/privacy").text.lower()
    assert "location" in body


def test_privacy_page_explains_what_signing_in_does_and_does_not_do():
    """This used to be named ..._states_there_are_no_accounts and assert the
    substring "account", which stayed true when the sentence under it flipped."""
    body = client.get("/privacy").text.lower()
    assert "without signing in" in body, "using the app signed out has to stay stated"
    assert "never ask for a password" in body
    assert "there are none" not in body


def test_privacy_page_says_what_a_posted_memory_exposes():
    """The app now publishes what people write, where they were standing, and
    any photo they attach. A policy written for a read-only app is not a small
    inaccuracy here - it is the disclosure the whole feature needs."""
    body = client.get("/privacy").text.lower()
    assert "public" in body
    assert "display name" in body
    assert "photo" in body and "recording" in body
    assert "report" in body, "how to get something taken down"


def test_privacy_page_covers_the_three_new_permissions():
    body = client.get("/privacy").text.lower()
    for permission in ("camera", "photos", "microphone"):
        assert permission in body


def test_privacy_page_says_what_signing_in_hands_over():
    """Sign-in means a third party tells us something about somebody. What that
    is, and what it emphatically is not, has to be on the page."""
    body = client.get("/privacy").text.lower()
    assert "google" in body and "apple" in body
    assert "email" in body
    assert "password" in body, "that we never ask for one is the point"
    assert "sign out" in body
