"""Who has paid: RevenueCat's webhook and the read-back write `subscriptions`.

RevenueCat itself is never called: `billing.fetch_subscriber` is patched with
what it would have said, the way test_api_auth.py patches `signing_key`.
"""

import uuid

import pytest
from sqlalchemy import text

from api import accounts, billing
from pipeline import config

pytestmark = pytest.mark.db

SECRET = "test-webhook-secret"
LATER = "2099-01-01T00:00:00Z"
EARLIER = "2000-01-01T00:00:00Z"


@pytest.fixture
def client(api_client):
    return api_client


@pytest.fixture
def revenuecat(monkeypatch):
    """What RevenueCat says each user's entitlement expires at; absent = never granted."""
    said: dict[str, str | None] = {}
    monkeypatch.setattr(config, "REVENUECAT_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(config, "REVENUECAT_API_KEY", "sk_test")

    def fetch(user_id):
        grants = {"map": {"expires_date": said[user_id]}} if user_id in said else {}
        return {"subscriber": {"entitlements": grants}}

    monkeypatch.setattr(billing, "fetch_subscriber", fetch)
    return said


def _account(session):
    """A device bound to a fresh user: (device, user_id)."""
    user = str(
        session.execute(
            text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
        ).scalar()
    )
    device = str(uuid.uuid4())
    session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), CAST(:u AS uuid))"),
        {"d": device, "u": user},
    )
    session.commit()
    return device, user


def _event(client, user, secret=SECRET):
    return client.post(
        "/v1/billing/revenuecat",
        json={"event": {"type": "INITIAL_PURCHASE", "app_user_id": user}},
        headers={"Authorization": f"Bearer {secret}"},
    )


def _me(client, device):
    return client.get(f"/v1/me?device={device}").json()


def test_only_revenuecat_is_believed(client, db_session, revenuecat):
    _, user = _account(db_session)
    revenuecat[user] = LATER
    assert _event(client, user, secret="guess").status_code == 401
    assert client.post("/v1/billing/revenuecat", json={}).status_code == 401
    assert db_session.execute(text("SELECT COUNT(*) FROM subscriptions")).scalar() == 0


def test_an_unconfigured_server_refuses_rather_than_accepts(client, db_session, monkeypatch):
    monkeypatch.setattr(config, "REVENUECAT_WEBHOOK_SECRET", None)
    assert _event(client, str(uuid.uuid4()), secret="None").status_code == 503


def test_an_event_makes_the_row_say_what_revenuecat_says(client, db_session, revenuecat):
    device, user = _account(db_session)
    revenuecat[user] = LATER
    assert _event(client, user).status_code == 200
    assert _me(client, device)["subscribed"] is True

    revenuecat[user] = EARLIER  # expired, or refunded to the past
    _event(client, user)
    me = _me(client, device)
    assert (me["subscribed"], me["subscribed_until"]) == (False, "2000-01-01T00:00:00")

    del revenuecat[user]  # never granted, or revoked outright
    _event(client, user)
    assert db_session.execute(text("SELECT COUNT(*) FROM subscriptions")).scalar() == 0


@pytest.mark.parametrize("user", ["$RCAnonymousID:abc", str(uuid.uuid4())])
def test_somebody_we_do_not_know_is_answered_and_ignored(client, db_session, revenuecat, user):
    revenuecat[user] = LATER
    assert _event(client, user).status_code == 200
    assert db_session.execute(text("SELECT COUNT(*) FROM subscriptions")).scalar() == 0


def test_the_app_can_ask_for_its_subscription_straight_after_buying(client, db_session, revenuecat):
    device, user = _account(db_session)
    revenuecat[user] = LATER
    assert client.post("/v1/me/subscription", json={"device": device}).json()["subscribed"]


def test_absorbing_an_anonymous_user_keeps_the_longer_subscription(db_session):
    _, old = _account(db_session)
    _, new = _account(db_session)
    for user, ends in ((old, LATER), (new, EARLIER)):
        db_session.execute(
            text("INSERT INTO subscriptions VALUES (CAST(:u AS uuid), :e)"), {"u": user, "e": ends}
        )
    accounts.absorb(db_session, old, new)
    rows = db_session.execute(text("SELECT user_id::text, expires_at FROM subscriptions")).all()
    assert [(u, e.year) for u, e in rows] == [(new, 2099)]
