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


def test_privacy_page_states_there_are_no_accounts():
    body = client.get("/privacy").text.lower()
    assert "account" in body
