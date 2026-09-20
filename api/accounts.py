"""Who a device is, and how it proves it on a second phone.

No session tokens in either direction - the device id stays the only credential
and signing in binds devices.user_id. docs/10-decisions.md#identity.
"""

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import text

from api.auth import apple_identity, google_identity
from api.models import DEVICE_PATTERN, DeviceRequest, Profile, ProfileRequest, SignInRequest
from api.queries import UNLOCK_COUNT_QUERY
from pipeline.db import get_session

router = APIRouter()


def touch_device(session, device: str) -> None:
    """Every write path needs the device row to exist first, and all of them
    want last_seen moved."""
    session.execute(
        text("""
            INSERT INTO devices (id, last_seen) VALUES (CAST(:id AS uuid), CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET last_seen = CURRENT_TIMESTAMP
        """),
        {"id": device},
    )


def user_for_device(session, device: str) -> str:
    """The user this device acts as, creating one the first time it needs to.

    Created lazily and never on a read: a device that only ever walks around
    unlocking things should not leave a user row behind.
    """
    touch_device(session, device)
    existing = session.execute(
        text("SELECT user_id FROM devices WHERE id = CAST(:id AS uuid)"), {"id": device}
    ).scalar()
    if existing is not None:
        return str(existing)

    fresh = str(uuid.uuid4())
    session.execute(text("INSERT INTO users (id) VALUES (CAST(:id AS uuid))"), {"id": fresh})
    session.execute(
        text("UPDATE devices SET user_id = CAST(:user AS uuid) WHERE id = CAST(:id AS uuid)"),
        {"user": fresh, "id": device},
    )
    return fresh


def set_display_name(session, user_id: str, name: str | None) -> None:
    """Separate from user_for_device because None is two different answers.

    A submission that carries no name is saying nothing about it and must leave
    the existing one alone; a PUT with a blank one is saying "stop calling me
    that", and clearing it has to be possible - the name is the one thing here
    other people see.
    """
    session.execute(
        text("UPDATE users SET display_name = :name WHERE id = CAST(:id AS uuid)"),
        {"name": name, "id": user_id},
    )


def clean_name(raw: str | None) -> str | None:
    """Blank and whitespace are the same thing as not being named."""
    name = (raw or "").strip()
    return name or None


def profile_of(session, device: str) -> Profile:
    """Who this device is, read once and shared by every endpoint that has just
    changed it. Creates nothing."""
    row = session.execute(
        text("""
            SELECT u.id, u.display_name,
                (SELECT COUNT(*) FROM memories m WHERE m.user_id = u.id) AS submitted,
                COALESCE(
                    (SELECT array_agg(i.provider ORDER BY i.created_at)
                     FROM identities i WHERE i.user_id = u.id),
                    ARRAY[]::varchar[]
                ) AS providers
            FROM devices d JOIN users u ON d.user_id = u.id
            WHERE d.id = CAST(:device_id AS uuid)
        """),
        {"device_id": device},
    ).fetchone()
    unlocked = session.execute(text(UNLOCK_COUNT_QUERY), {"device_id": device}).scalar() or 0

    if not row:
        return Profile(unlocked=unlocked)
    return Profile(
        user_id=str(row.id),
        display_name=row.display_name,
        submitted=row.submitted,
        unlocked=unlocked,
        providers=list(row.providers),
    )


@router.get("/v1/me", response_model=Profile)
def get_profile(device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Who this device is and what it has done. Creates nothing - a device that
    only walks around unlocking things leaves no user row behind."""
    with get_session() as session:
        return profile_of(session, device)


@router.put("/v1/me", response_model=Profile)
def set_profile(body: ProfileRequest):
    """Name yourself, or stop being named. This is the one call that creates a
    user without a submission attached, because choosing the name before writing
    the memory is the order people do it in."""
    with get_session() as session:
        user_id = user_for_device(session, body.device)
        set_display_name(session, user_id, clean_name(body.display_name))
        return profile_of(session, body.device)


# Signing in binds devices.user_id and issues no token. api/auth.py verifies the
# ID tokens; docs/10-decisions.md#identity has the why.


def absorb(session, old_user: str, new_user: str) -> None:
    """Fold a device's anonymous user into the account it just signed into.

    Somebody who files a memory and then signs in expects it to come with them.
    Only ever an *anonymous* user: one with its own identity is a real account
    and merging two of those is a decision nobody here is in a position to make,
    so the device simply switches and both accounts keep what is theirs.
    """
    if old_user == new_user:
        return
    has_identity = session.execute(
        text("SELECT 1 FROM identities WHERE user_id = CAST(:id AS uuid) LIMIT 1"),
        {"id": old_user},
    ).scalar()
    if has_identity:
        return

    session.execute(
        text("UPDATE memories SET user_id = CAST(:new AS uuid) WHERE user_id = CAST(:old AS uuid)"),
        {"new": new_user, "old": old_user},
    )
    session.execute(
        text("UPDATE devices SET user_id = CAST(:new AS uuid) WHERE user_id = CAST(:old AS uuid)"),
        {"new": new_user, "old": old_user},
    )
    session.execute(text("DELETE FROM users WHERE id = CAST(:id AS uuid)"), {"id": old_user})


def sign_in(session, device: str, provider: str, subject: str, email, name) -> Profile:
    """Bind this device to the account behind a verified identity.

    Three cases, and the middle one is the one worth reading twice:

      new identity, no user     create a user and attach the identity
      new identity, has a user  attach it to the user this device already is,
                                which is how a name and any memories filed
                                before signing in survive the transition
      known identity            point the device at that user, and absorb the
                                anonymous one it was using
    """
    touch_device(session, device)
    known = session.execute(
        text("SELECT user_id FROM identities WHERE provider = :p AND subject = :s"),
        {"p": provider, "s": subject},
    ).scalar()
    current = session.execute(
        text("SELECT user_id FROM devices WHERE id = CAST(:id AS uuid)"), {"id": device}
    ).scalar()

    if known is None:
        user_id = str(current) if current else user_for_device(session, device)
        session.execute(
            text("""
                INSERT INTO identities (provider, subject, user_id, email)
                VALUES (:p, :s, CAST(:user AS uuid), :email)
            """),
            {"p": provider, "s": subject, "user": user_id, "email": email},
        )
    else:
        user_id = str(known)
        if current:
            absorb(session, str(current), user_id)

    session.execute(
        text("UPDATE devices SET user_id = CAST(:user AS uuid) WHERE id = CAST(:id AS uuid)"),
        {"user": user_id, "id": device},
    )

    # Never overwrites. The name is the one thing here other people see, and
    # somebody who chose "Bo" does not want Google renaming them.
    chosen = clean_name(name)
    if chosen:
        session.execute(
            text("""
                UPDATE users SET display_name = :name
                WHERE id = CAST(:id AS uuid) AND display_name IS NULL
            """),
            {"name": chosen, "id": user_id},
        )

    return profile_of(session, device)


@router.post("/v1/auth/google", response_model=Profile)
def sign_in_with_google(body: SignInRequest):
    subject, email, name = google_identity(body.id_token)
    with get_session() as session:
        return sign_in(session, body.device, "google", subject, email, body.display_name or name)


@router.post("/v1/auth/apple", response_model=Profile)
def sign_in_with_apple(body: SignInRequest):
    subject, email = apple_identity(body.id_token)
    with get_session() as session:
        return sign_in(session, body.device, "apple", subject, email, body.display_name)


@router.post("/v1/auth/signout", response_model=Profile)
def sign_out(body: DeviceRequest):
    """Unlink this device from the account. Nothing is deleted.

    Unlocks were recorded against the device and stay readable on it; memories
    filed under the account stay with the account. Signing back in reattaches
    both. There is no token to revoke, because there was never one issued.
    """
    with get_session() as session:
        session.execute(
            text("UPDATE devices SET user_id = NULL WHERE id = CAST(:id AS uuid)"),
            {"id": body.device},
        )
        return profile_of(session, body.device)
