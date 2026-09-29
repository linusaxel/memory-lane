"""What the app does once Railway says it is the public host, and the health
check Railway deploys against.

Imported fresh in a subprocess, because every one of these is decided at import,
and run outside the repo so the developer's .env (which the image never copies)
cannot answer for Railway.
"""

import os
import pathlib
import subprocess
import sys
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import api.main

ROOT = pathlib.Path(__file__).resolve().parents[1]

PROBE = """
from fastapi.testclient import TestClient
from api.main import app
c = TestClient(app)
print(c.get('/docs').status_code, c.get('/openapi.json').status_code, c.get('/embed.js').status_code)
"""


def run(tmp_path, **env):
    base = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "ENABLE_EMBED")}
    return subprocess.run(
        [sys.executable, "-c", PROBE],
        env={**base, "PYTHONPATH": str(ROOT), **env},
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


def test_railway_hides_the_docs_and_the_embed(tmp_path):
    out = run(tmp_path, RAILWAY_ENVIRONMENT_NAME="production", DATABASE_URL="postgresql://x@db/x")
    assert out.stdout.split() == ["404", "404", "404"], out.stderr


def test_railway_can_still_ask_for_the_embed(tmp_path):
    out = run(
        tmp_path,
        RAILWAY_ENVIRONMENT_NAME="production",
        DATABASE_URL="postgresql://x@db/x",
        ENABLE_EMBED="1",
    )
    assert out.stdout.split() == ["404", "404", "200"], out.stderr


def test_railway_without_a_database_url_refuses_to_start(tmp_path):
    """Not a fallback to the dev password: pipeline/db.py."""
    out = run(tmp_path, RAILWAY_ENVIRONMENT_NAME="production")
    assert out.returncode != 0 and "DATABASE_URL is unset" in out.stderr


@pytest.mark.db
def test_the_health_check_asks_the_database(api_client):
    """Railway's healthcheckPath points at / - this is load-bearing for deploy."""
    r = api_client.get("/")
    assert (r.status_code, r.json()) == (200, {"status": "ok", "service": "memory-lane"})


def test_a_host_that_cannot_reach_its_database_is_not_healthy(monkeypatch):
    """Otherwise a deploy with a wrong DATABASE_URL goes live and 500s."""

    @contextmanager
    def unreachable():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield

    monkeypatch.setattr(api.main, "get_session", unreachable)
    assert TestClient(api.main.app).get("/").status_code == 503
