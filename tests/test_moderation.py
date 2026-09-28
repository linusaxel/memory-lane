"""What people post is screened before a stranger can read it (App Store 1.2)."""

import pytest
from sqlalchemy import text

import api.moderation as moderation
from tests.fakes import FakeAnthropic
from tests.test_api_submit import submission

pytestmark = pytest.mark.db


@pytest.fixture
def screening(monkeypatch):
    def with_verdict(fake):
        monkeypatch.setattr(moderation, "SCREEN_POSTS", True)
        monkeypatch.setattr(moderation, "client", fake)
        return fake

    return with_verdict


def test_a_refused_post_is_never_stored(api_client, db_session, screening):
    fake = screening(FakeAnthropic({"ok": False}))
    body = submission()
    assert api_client.post("/v1/memories", json=body).status_code == 422
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 0
    sent = fake.messages.calls[0]["messages"][0]["content"]
    assert body["summary"] in sent and body["place_name"] in sent


def test_a_passed_post_is_stored(api_client, screening):
    screening(FakeAnthropic({"ok": True}))
    assert api_client.post("/v1/memories", json=submission()).status_code == 201


def test_nothing_is_published_when_nobody_could_judge_it(api_client, db_session, screening):
    class Down:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise ConnectionError("no route to Anthropic")

    screening(Down())
    assert api_client.post("/v1/memories", json=submission()).status_code == 503
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 0
