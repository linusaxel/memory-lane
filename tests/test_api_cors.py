"""CORS and the privacy route.

Request-level via TestClient, so these assert what a browser or a store
reviewer would actually receive. No DB needed - neither endpoint touches it.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_credentials_are_not_sent_with_a_wildcard_origin():
    """allow_credentials=True alongside allow_origins=['*'] is an invalid pair
    that browsers reject outright. The mobile app sends no cookies, so the
    correct fix is dropping credentials, not narrowing to a fake origin."""
    r = client.get("/v1/stats", headers={"Origin": "https://example.com"})
    assert "access-control-allow-credentials" not in {k.lower() for k in r.headers}


def test_cors_still_allows_a_browser_client():
    r = client.get("/", headers={"Origin": "https://example.com"})
    assert r.headers.get("access-control-allow-origin") is not None


def test_health_check_shape_is_unchanged():
    """Railway's healthcheckPath points at / - this is load-bearing for deploy."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "memory-lane"}
