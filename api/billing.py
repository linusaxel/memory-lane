"""Who has paid. RevenueCat sells the subscription and the keys; this writes
`subscriptions`, which the unlock and the walk limit read, and credits each key
pack once through `key_purchases`.

Every event is treated as "something changed for this user": the subscriber is
read back from RevenueCat and the row made to match. Duplicate, late or
out-of-order events then cannot leave a wrong row, and purchase, renewal,
refund and expiry are one code path.

Why RevenueCat, and why its app_user_id is users.id:
docs/10-decisions.md#revenuecat-sells-it-our-table-decides.
"""

import hmac
import json
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from api.accounts import profile_of
from api.models import DeviceRequest, Profile
from pipeline import config
from pipeline.db import get_session

router = APIRouter()

ENTITLEMENT = "map"
REVENUECAT_URL = "https://api.revenuecat.com/v1/subscribers/"
# A grant with no end (a promotional lifetime from the RevenueCat dashboard).
FOREVER = datetime(9999, 1, 1)
# The store's consumables, and how many keys each is. docs/10, "Keys open a
# lock, and today's walk is free".
KEY_PRODUCTS = {"keys_1": 1, "keys_5": 5, "keys_15": 15, "keys_40": 40}


def fetch_subscriber(app_user_id: str) -> dict:
    """RevenueCat's subscriber record. Patched in tests, which never reach it."""
    request = urllib.request.Request(
        REVENUECAT_URL + urllib.parse.quote(app_user_id, safe=""),
        headers={"Authorization": f"Bearer {config.REVENUECAT_API_KEY}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def expires_at(subscriber: dict) -> datetime | None:
    """When the entitlement ends, in naive UTC like every TIMESTAMP here. None
    when it was never granted. A lapsed one keeps its past date, and the
    subscription reads as expired, which is what it is."""
    grant = subscriber.get("subscriber", {}).get("entitlements", {}).get(ENTITLEMENT)
    if grant is None:
        return None
    if grant.get("expires_date") is None:
        return FOREVER
    ends = datetime.fromisoformat(grant["expires_date"].replace("Z", "+00:00"))
    return ends.astimezone(UTC).replace(tzinfo=None)


def key_packs(subscriber: dict) -> list[tuple[str, int]]:
    """Every key pack RevenueCat says was bought: (transaction id, keys)."""
    bought = subscriber.get("subscriber", {}).get("non_subscriptions", {})
    return [
        (purchase["id"], KEY_PRODUCTS[product])
        for product, purchases in bought.items()
        if product in KEY_PRODUCTS
        for purchase in purchases
    ]


def credit_keys(session, user_id: str, packs: list[tuple[str, int]]) -> None:
    """Add each pack not credited before. The transaction id is the key, so a
    webhook retry or a second read-back adds nothing."""
    # ponytail: a refunded pack is not taken back; add it on the CANCELLATION
    # event if refunds show up.
    for transaction_id, keys in packs:
        new = session.execute(
            text("""
                INSERT INTO key_purchases (transaction_id, user_id, keys)
                VALUES (:t, CAST(:u AS uuid), :k)
                ON CONFLICT (transaction_id) DO NOTHING
                RETURNING keys
            """),
            {"t": transaction_id, "u": user_id, "k": keys},
        ).scalar()
        if new:
            session.execute(
                text("UPDATE users SET keys = keys + :k WHERE id = CAST(:u AS uuid)"),
                {"k": new, "u": user_id},
            )


def sync(session, user_id: str) -> None:
    """Make this user's row say what RevenueCat says, and credit new keys."""
    if not config.REVENUECAT_API_KEY:
        raise HTTPException(status_code=503, detail="Subscriptions are not configured")
    subscriber = fetch_subscriber(user_id)
    credit_keys(session, user_id, key_packs(subscriber))
    ends = expires_at(subscriber)
    if ends is None:
        session.execute(
            text("DELETE FROM subscriptions WHERE user_id = CAST(:u AS uuid)"), {"u": user_id}
        )
        return
    session.execute(
        text("""
            INSERT INTO subscriptions (user_id, expires_at) VALUES (CAST(:u AS uuid), :ends)
            ON CONFLICT (user_id) DO UPDATE SET expires_at = EXCLUDED.expires_at
        """),
        {"u": user_id, "ends": ends},
    )


@router.post("/v1/billing/revenuecat")
def revenuecat_webhook(body: dict, authorization: str = Header("")):
    """RevenueCat's webhook. The shared secret is the only credential, compared
    in constant time. Unset, it refuses: a webhook that trusts anybody lets
    anybody subscribe."""
    secret = config.REVENUECAT_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=503, detail="Subscriptions are not configured")
    if not hmac.compare_digest(authorization.encode(), f"Bearer {secret}".encode()):
        raise HTTPException(status_code=401, detail="Not RevenueCat")

    # Answered 200 for an id that is not one of our users (RevenueCat's own
    # $RCAnonymousID, a test event): refused, RevenueCat retries it for days.
    app_user_id = str((body.get("event") or {}).get("app_user_id") or "")
    try:
        user_id = str(uuid.UUID(app_user_id))
    except ValueError:
        return {"ok": True}
    with get_session() as session:
        known = session.execute(
            text("SELECT 1 FROM users WHERE id = CAST(:u AS uuid)"), {"u": user_id}
        ).scalar()
        if known:
            sync(session, user_id)
    return {"ok": True}


@router.post("/v1/me/subscription", response_model=Profile)
def refresh_subscription(body: DeviceRequest):
    """Read this account's subscription and keys back now. The app calls it
    straight after a purchase or a restore, so an unlock a second later is not
    refused while the webhook is still on its way."""
    with get_session() as session:
        user_id = session.execute(
            text("SELECT user_id FROM devices WHERE id = CAST(:d AS uuid)"), {"d": body.device}
        ).scalar()
        if user_id is not None:
            sync(session, str(user_id))
        return profile_of(session, body.device)
