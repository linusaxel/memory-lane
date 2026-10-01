"""Who a device is, and how it proves it on a second phone.

No session tokens in either direction - the device id stays the only credential
and signing in binds devices.user_id. docs/10-decisions.md#identity.
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import text

import api.media
from api.auth import apple_identity, either_identity, google_identity
from api.gate import today
from api.models import (
    DEVICE_PATTERN,
    FREE_PER_DAY,
    DeviceRequest,
    Profile,
    ProfileRequest,
    SignInRequest,
    StepsRequest,
)
from api.moderation import screen
from api.queries import (
    CREDIT_STEPS,
    DELETE_ORPHAN_SUBMITTED_PLACE,
    STREAK_DAYS_QUERY,
    UNLOCK_COUNT_QUERY,
)
from pipeline.config import PUBLIC_HOST
from pipeline.db import get_session

router = APIRouter()


def current_streak(days: list[date], today: date) -> int:
    """Consecutive calendar days, newest first, ending today or yesterday.

    A gap anywhere older breaks it; a day skipped entirely (nothing unlocked
    yesterday or today) means the streak is over, not merely paused.
    """
    if not days or days[0] < today - timedelta(days=1):
        return 0
    count = 0
    expected = days[0]
    for d in days:
        if d != expected:
            break
        count += 1
        expected -= timedelta(days=1)
    return count


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
            SELECT u.id, u.display_name, u.avatar_path,
                (SELECT COUNT(*) FROM memories m WHERE m.user_id = u.id) AS submitted,
                (SELECT COUNT(*) FROM memory_hearts mh JOIN memories m ON m.id = mh.memory_id
                 WHERE m.user_id = u.id) AS hearts_received,
                COALESCE(
                    (SELECT array_agg(i.provider ORDER BY i.created_at)
                     FROM identities i WHERE i.user_id = u.id),
                    ARRAY[]::varchar[]
                ) AS providers,
                s.expires_at AS subscribed_until,
                COALESCE(s.expires_at > CURRENT_TIMESTAMP, false) AS subscribed,
                CASE WHEN u.free_day = CAST(:today AS date)
                    THEN GREATEST(:per_day - u.free_used, 0) ELSE :per_day END AS free_unlocks,
                u.steps, u.steps_counted_until
            FROM devices d JOIN users u ON d.user_id = u.id
            LEFT JOIN subscriptions s ON s.user_id = u.id
            WHERE d.id = CAST(:device_id AS uuid)
        """),
        {"device_id": device, "today": today(), "per_day": FREE_PER_DAY},
    ).fetchone()
    unlocked = session.execute(text(UNLOCK_COUNT_QUERY), {"device_id": device}).scalar() or 0
    streak_days = [
        r.d for r in session.execute(text(STREAK_DAYS_QUERY), {"device_id": device}).fetchall()
    ]
    streak = current_streak(streak_days, date.today())

    if not row:
        return Profile(unlocked=unlocked, streak=streak)
    return Profile(
        user_id=str(row.id),
        display_name=row.display_name,
        avatar_url=api.media.media_url(row.avatar_path) if row.avatar_path else None,
        submitted=row.submitted,
        hearts_received=row.hearts_received,
        unlocked=unlocked,
        streak=streak,
        providers=list(row.providers),
        subscribed=row.subscribed,
        subscribed_until=row.subscribed_until,
        free_unlocks=row.free_unlocks,
        steps=row.steps,
        steps_counted_until=row.steps_counted_until,
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
    name = clean_name(body.display_name)
    screen(name)
    with get_session() as session:
        user_id = user_for_device(session, body.device)
        set_display_name(session, user_id, name)
        return profile_of(session, body.device)


# The old path, read under the row lock, so two racing uploads each take the
# file they replaced with them.
SWAP_AVATAR = """
    UPDATE users u SET avatar_path = :path
    FROM (SELECT id, avatar_path FROM users WHERE id = CAST(:id AS uuid) FOR UPDATE) old
    WHERE u.id = old.id
    RETURNING old.avatar_path
"""


def swap_avatar(device: str, path: str | None) -> Profile:
    """Point the user at `path` and delete the file it replaces. No upload
    quota: a user holds one photo, so replacing it costs the disk nothing."""
    try:
        with get_session() as session:
            user_id = user_for_device(session, device)
            previous = session.execute(text(SWAP_AVATAR), {"path": path, "id": user_id}).scalar()
            profile = profile_of(session, device)
    except Exception:
        if path:
            (api.media.MEDIA_DIR / path).unlink(missing_ok=True)
        raise
    # File after row, as delete_memory does: sweep reaps what a crash leaves.
    if previous:
        (api.media.MEDIA_DIR / previous).unlink(missing_ok=True)
    return profile


@router.post("/v1/me/avatar", response_model=Profile)
async def set_avatar(file: UploadFile, device: str = Form(..., pattern=DEVICE_PATTERN)):
    """A profile photo, shown beside the name on what you file. Through the
    same checks and EXIF strip as a memory's photo (api/media.py)."""
    path, kind, _, _ = await api.media.save_upload(file)
    if kind != "photo":
        (api.media.MEDIA_DIR / path).unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="A profile photo has to be a photo")
    return swap_avatar(device, path)


@router.delete("/v1/me/avatar", response_model=Profile)
def remove_avatar(device: str = Query(..., pattern=DEVICE_PATTERN)):
    return swap_avatar(device, None)


# Faster than anyone walks, sustained: a count over it is shaken or made up.
MAX_STEPS_PER_SECOND = 3


@router.post("/v1/me/steps", response_model=Profile)
def credit_steps(body: StepsRequest):
    """Add the steps the phone counted since the watermark, and move it to now.

    A `since` that is no longer the watermark credits nothing and answers the
    profile as it is, whose watermark the next sync starts from: a retry or a
    second phone racing this one is counted once.
    """
    with get_session() as session:
        user_id = user_for_device(session, body.device)
        session.execute(
            text(CREDIT_STEPS),
            {
                "user_id": user_id,
                "since": body.since.replace(tzinfo=None),
                "steps": body.steps,
                "max_rate": MAX_STEPS_PER_SECOND,
            },
        )
        return profile_of(session, body.device)


if not PUBLIC_HOST:

    @router.post("/v1/dev/steps", response_model=Profile)
    def dev_steps(
        device: str = Query(..., pattern=DEVICE_PATTERN),
        steps: int = Query(500, ge=1, le=10_000),
    ):
        """Steps for nothing, off the public host only: the app's dev teleport
        gives 500, so testing the steps gate needs no walking."""
        with get_session() as session:
            session.execute(
                text("UPDATE users SET steps = steps + :s WHERE id = CAST(:u AS uuid)"),
                {"s": steps, "u": user_for_device(session, device)},
            )
            return profile_of(session, device)


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
    # Before the delete, whose cascade would take the subscription with it. Of
    # the two, the one that runs longer.
    session.execute(
        text("""
            INSERT INTO subscriptions (user_id, expires_at)
            SELECT CAST(:new AS uuid), expires_at FROM subscriptions
            WHERE user_id = CAST(:old AS uuid)
            ON CONFLICT (user_id) DO UPDATE
                SET expires_at = GREATEST(subscriptions.expires_at, EXCLUDED.expires_at)
        """),
        {"new": new_user, "old": old_user},
    )
    session.execute(text("DELETE FROM users WHERE id = CAST(:id AS uuid)"), {"id": old_user})


def sign_in(session, device: str, provider: str, subject: str, email, name, proof=None) -> Profile:
    """Bind this device to the account behind a verified identity.

    Three cases, and the middle one is the one worth reading twice:

      new identity, no user     create a user and attach the identity
      new identity, has a user  attach it to the user this device already is,
                                which is how a name and any memories filed
                                before signing in survive the transition. If
                                that user already has a sign-in, `proof` (a
                                verified (provider, subject)) must be one of
                                them: otherwise a stolen device id would let
                                anyone bind their own identity to the account
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
        if current and not linked_with_proof(session, str(current), proof):
            raise HTTPException(
                status_code=403, detail="Sign in to this account again to add another sign-in"
            )
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


def linked_with_proof(session, user_id: str, proof) -> bool:
    """True if the user has no sign-in yet, or `proof` is one of theirs."""
    identities = session.execute(
        text("SELECT provider, subject FROM identities WHERE user_id = CAST(:id AS uuid)"),
        {"id": user_id},
    ).fetchall()
    return not identities or proof in {(i.provider, i.subject) for i in identities}


def link_proof(body: SignInRequest):
    return either_identity(body.link_token, body.device) if body.link_token else None


@router.post("/v1/auth/google", response_model=Profile)
def sign_in_with_google(body: SignInRequest):
    subject, email, name = google_identity(body.id_token, body.device)
    proof = link_proof(body)
    with get_session() as session:
        return sign_in(
            session, body.device, "google", subject, email, body.display_name or name, proof
        )


@router.post("/v1/auth/apple", response_model=Profile)
def sign_in_with_apple(body: SignInRequest):
    subject, email = apple_identity(body.id_token, body.device)
    proof = link_proof(body)
    with get_session() as session:
        return sign_in(session, body.device, "apple", subject, email, body.display_name, proof)


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


# What is someone's, given {user, device}: deletion removes it and api/my_data.py
# hands a copy of it, so the two cannot drift apart.
OWNED_DEVICES = """(SELECT id FROM devices
    WHERE user_id = CAST(:user AS uuid) OR id = CAST(:device AS uuid))"""
OWNED_MEMORIES = "(SELECT id FROM memories WHERE user_id = CAST(:user AS uuid))"


@router.delete("/v1/me", status_code=204)
def delete_account(device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Delete the account this device is signed into, and everything it made.

    Its memories and their media, its sign-ins and subscription row, and every
    device on it with what those devices did: unlocks, hearts, notes, walks,
    reports. Walkers lose those memories, which is the point: the person asked
    for their words and photographs to be gone. A store subscription is the
    store's to cancel; the app says so before asking.
    """
    with get_session() as session:
        user_id = session.execute(
            text("SELECT user_id FROM devices WHERE id = CAST(:id AS uuid)"), {"id": device}
        ).scalar()
        owner = {"user": str(user_id) if user_id else None, "device": device}
        devices, mine = OWNED_DEVICES, OWNED_MEMORIES

        paths = [
            row.path
            for row in session.execute(
                text(f"SELECT path FROM media WHERE memory_id IN {mine} OR device_id IN {devices}"),
                owner,
            )
        ]
        places = [
            row.place_id
            for row in session.execute(
                text("SELECT DISTINCT place_id FROM memories WHERE user_id = CAST(:user AS uuid)"),
                owner,
            )
        ]
        avatar = session.execute(
            text("SELECT avatar_path FROM users WHERE id = CAST(:user AS uuid)"), owner
        ).scalar()
        if avatar:
            paths.append(avatar)
        session.execute(text(f"DELETE FROM media WHERE device_id IN {devices}"), owner)
        session.execute(text("DELETE FROM memories WHERE user_id = CAST(:user AS uuid)"), owner)
        for place_id in places:
            session.execute(text(DELETE_ORPHAN_SUBMITTED_PLACE), {"place_id": place_id})
        session.execute(text(f"DELETE FROM devices WHERE id IN {devices}"), owner)
        session.execute(text("DELETE FROM users WHERE id = CAST(:user AS uuid)"), owner)

    # File after row, as delete_memory does: sweep reaps what a crash leaves.
    for path in paths:
        (api.media.MEDIA_DIR / path).unlink(missing_ok=True)

    return Response(status_code=204)
