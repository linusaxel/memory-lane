"""Filing a memory, attaching media to it, and taking one down.

api/media.py decides what an upload may be; this module decides what a
submission may say and who it belongs to.
"""

import os
import uuid

from fastapi import APIRouter, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import text

import api.media
from api.accounts import touch_device, user_for_device
from api.gate import (
    SURPRISE_EVERY_DAYS,
    SURPRISE_MINUTES,
    SURPRISE_RADIUS_M,
    is_gated,
    meters_between,
    notes_response,
    row_coordinates,
    row_to_memory,
    today,
)
from api.media import media_url, save_upload
from api.models import (
    DEVICE_PATTERN,
    Coordinates,
    DeviceRequest,
    HeartResponse,
    MediaItem,
    Memory,
    MemoryEditRequest,
    NoteRequest,
    NotesResponse,
    ReportRequest,
    ReportResponse,
    SubmissionRequest,
    SurpriseRequest,
    SurpriseResponse,
    UnlockRequest,
)
from api.moderation import screen
from api.queries import (
    DELETE_ORPHAN_SUBMITTED_PLACE,
    EARNED_QUERY,
    MEDIA_ATTACH,
    MEDIA_DETACH_QUERY,
    MEMORY_NOTES_QUERY,
    MY_DEVICES,
    NOTE_ALLOWED_QUERY,
    NOTE_HIDE_QUERY,
    ON_TODAYS_ROUTE_QUERY,
    OWNED_MEMORY_QUERY,
    PLACE_INSERT,
    ROUTE_COMPLETED_QUERY,
    SINGLE_MEMORY_QUERY,
    SUBMISSION_INSERT,
    SURPRISE_OPEN_QUERY,
    SURPRISED_LATELY_QUERY,
)
from pipeline.db import get_session
from pipeline.tags import from_text as hashtags

router = APIRouter()

# reinstatement, no human queue. See docs/10-decisions.md#writing.
REPORT_THRESHOLD = int(os.getenv("REPORT_THRESHOLD", "3"))


# ponytail: the device id is a bearer token in the request body, so anyone
# holding yours can post as you. OAuth did not replace this - see
# docs/10-decisions.md#no-session-tokens-signed-in-or-not.

# A phone's GPS in a street, honestly stated rather than flattered.
SUBMITTED_PRECISION_METERS = 25

# The hard cap the brief asks for on user-submitted ingestion. It is not a
# defence against a determined attacker - the device id is self-issued, so a
# loop can mint a fresh identity per request - it is the bound that stops a
# retry loop or a stuck client from filling the disk, which is the failure that
# actually happens. Counted per person rather than per device, so a second
# phone on one account does not double the allowance.
# ponytail: a COUNT over a rolling day, and since the check has to happen again
# under a lock to survive concurrent requests, three extra queries on the write
# path rather than two. A token bucket if this ever needs to be per-minute
# rather than per-day; the lock is what a bucket would have to replace, not
# just the counting.
DAILY_MEMORIES = int(os.getenv("DAILY_MEMORY_LIMIT", "20"))
DAILY_UPLOAD_BYTES = int(os.getenv("DAILY_UPLOAD_BYTES", str(64 * 1024 * 1024)))

SPENT_TODAY = """
    SELECT COALESCE(SUM(bytes), 0) FROM media
    WHERE device_id = CAST(:device AS uuid)
      AND created_at > LOCALTIMESTAMP - INTERVAL '1 day'
"""

# Serialises one user's submissions against each other, and nobody else's.
# FOR UPDATE and not an advisory lock: the row already exists by this point
# (user_for_device is idempotent and ran above), and a row lock is released by
# the transaction ending however it ends.
LOCK_USER = "SELECT id FROM users WHERE id = :user_id FOR UPDATE"

FILED_TODAY = """
    SELECT COUNT(*) FROM memories
    WHERE user_id = :user_id
      AND created_at > LOCALTIMESTAMP - INTERVAL '1 day'
"""


def refuse_over_quota(used: int, limit: int, what: str) -> None:
    """Refuse once the allowance is gone, and say when it comes back.

    Checked before the write rather than after, so the row or the file that
    would breach the cap is never created. The last accepted upload may still
    cross the byte limit by up to one file - bounding it exactly would mean
    reading the body to find its size, which is the disk write we are avoiding.
    """
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily {what} limit reached. Try again tomorrow.",
        )


def pay_for_unlock(session, device: str, memory_id: int, here: bool) -> bool:
    """Whether this account may open this memory.

    Already opened, it is theirs. Otherwise only a stop of today's walk in
    progress opens, or an unexpired surprise, and only standing on it; anything
    else is refused 403 `not_on_walk` (docs/10, "A walk planner, nothing else",
    "A surprise, once a week").

    Under the user's row lock, so two presses on one memory record one unlock.
    """
    user_id = user_for_device(session, device)
    session.execute(text(LOCK_USER), {"user_id": user_id})
    binds = {"device_id": device, "memory_id": memory_id}
    if session.execute(text(EARNED_QUERY), binds).scalar():
        return True
    if not here:
        return False
    if session.execute(text(ON_TODAYS_ROUTE_QUERY), {**binds, "today": today()}).scalar():
        return True
    if session.execute(text(SURPRISE_OPEN_QUERY), binds).scalar():
        return True
    raise HTTPException(status_code=403, detail={"reason": "not_on_walk"})


@router.post("/v1/memories/{memory_id}/unlock", response_model=Memory)
def unlock_memory(memory_id: int, body: UnlockRequest):
    """Earn a memory, and record that it was earned.

    POST rather than GET because it creates something. The gate is the same one
    every read goes through - this endpoint cannot return a summary the plain
    read would have withheld - but it is the only one that writes an unlock, and
    unlocking is the one thing in this product that is supposed to be an act.
    """
    with get_session() as session:
        row = session.execute(
            text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id, "device_id": body.device}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")

        at = (
            None
            if body.lat is None or body.lng is None
            else Coordinates(lat=body.lat, lng=body.lng)
        )
        memory = row_to_memory(row, at, include_distance=False)
        here = not memory.locked
        # Nothing to pay for a memory the gate never closes.
        if is_gated(row) and not pay_for_unlock(session, body.device, memory_id, here):
            # Say how far off, rather than only refusing: the app turns this
            # into "try a few steps nearer".
            if at is not None and memory.place.coordinates is not None:
                memory.distance_meters = meters_between(at, memory.place.coordinates)
            return memory
        if not here:
            # Already earned, read at its own spot, as get_unlocks does.
            memory = row_to_memory(row, row_coordinates(row), include_distance=False)

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO unlocks (device_id, memory_id)
                VALUES (CAST(:device AS uuid), :memory_id)
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"device": body.device, "memory_id": memory_id},
        )
        # The last stop of today's walk marks it walked (the journal, metrics).
        session.execute(
            text(ROUTE_COMPLETED_QUERY),
            {"device_id": body.device, "memory_id": memory_id, "today": today()},
        )

    return memory


@router.post("/v1/surprise", response_model=SurpriseResponse, status_code=201)
def grant_surprise(body: SurpriseRequest):
    """Open one locked memory off a walk, for half an hour, once a week.

    Asked by the phone's background geofence when it passes near one. The
    phone only says where it was; the server decides, so a loop of these
    cannot open the map. Any refusal is the same 409 `not_now`, and the phone
    then stays quiet. docs/10-decisions.md#a-surprise-once-a-week.
    """
    refused = HTTPException(status_code=409, detail={"reason": "not_now"})
    with get_session() as session:
        row = session.execute(
            text(SINGLE_MEMORY_QUERY), {"memory_id": body.memory_id, "device_id": body.device}
        ).fetchone()
        if not row or not is_gated(row):
            raise refused
        coords = row_coordinates(row)
        at = Coordinates(lat=body.lat, lng=body.lng)
        if coords is None or meters_between(at, coords) > SURPRISE_RADIUS_M:
            raise refused

        user_id = user_for_device(session, body.device)
        session.execute(text(LOCK_USER), {"user_id": user_id})
        binds = {"device_id": body.device, "memory_id": body.memory_id}
        if session.execute(text(EARNED_QUERY), binds).scalar():
            raise refused
        lately = {"user_id": user_id, "days": SURPRISE_EVERY_DAYS}
        if session.execute(text(SURPRISED_LATELY_QUERY), lately).scalar():
            raise refused

        expires_at = session.execute(
            text("""
                INSERT INTO surprises (user_id, memory_id, expires_at)
                VALUES (:user_id, :memory_id, LOCALTIMESTAMP + make_interval(mins => :minutes))
                RETURNING expires_at AT TIME ZONE 'UTC'
            """),
            {"user_id": user_id, "memory_id": body.memory_id, "minutes": SURPRISE_MINUTES},
        ).scalar()

    return SurpriseResponse(memory_id=body.memory_id, place=row.place_name, expires_at=expires_at)


@router.post("/v1/media", response_model=MediaItem, status_code=201)
async def upload_media(
    # Annotation-only, which is how FastAPI recognises an upload; File(...) in a
    # default is the same thing and ruff's B008 rejects it.
    file: UploadFile,
    device: str = Form(..., pattern=DEVICE_PATTERN),
    duration_seconds: float | None = Form(None, ge=0, le=600),
):
    """Take one photo or recording and hold it until a submission claims it.

    Separate from the submission itself because a phone uploads a 4 MB photo
    while the person is still typing, and because a failed upload should cost
    the text nothing. api/media.py does the deciding about what a file may be.
    """
    with get_session() as session:
        spent = session.execute(text(SPENT_TODAY), {"device": device}).scalar()
    refuse_over_quota(spent, DAILY_UPLOAD_BYTES, "upload")

    path, kind, mime, size = await save_upload(file)

    # From here the bytes are on the disk, so every way out of this block has
    # to take them with it.
    try:
        with get_session() as session:
            # touch_device's ON CONFLICT DO UPDATE is the lock this device's
            # other uploads serialise against. Re-checked under it - see
            # docs/10-decisions.md#a-quota-checked-before-the-write-is-not-a-quota.
            touch_device(session, device)
            spent = session.execute(text(SPENT_TODAY), {"device": device}).scalar()
            refuse_over_quota(spent, DAILY_UPLOAD_BYTES, "upload")

            media_id = session.execute(
                text("""
                    INSERT INTO media (device_id, kind, path, mime, bytes, duration_seconds)
                    VALUES (CAST(:device AS uuid), :kind, :path, :mime, :bytes, :duration)
                    RETURNING id
                """),
                {
                    "device": device,
                    "kind": kind,
                    "path": path,
                    "mime": mime,
                    "bytes": size,
                    # Only meaningful for audio, and only the client knows it -
                    # the server does not decode the file to find out.
                    "duration": duration_seconds if kind == "audio" else None,
                },
            ).scalar()
    except Exception:
        # A refusal or a failed insert both leave a file nothing will ever
        # reference. Orphans here are invisible: they cost disk for ever and
        # appear in no query.
        # Read off the module rather than bound at import: the tests point
        # MEDIA_DIR at a tmp_path, and a stale binding would delete nothing
        # while looking like it had.
        (api.media.MEDIA_DIR / path).unlink(missing_ok=True)
        raise

    return MediaItem(
        id=media_id,
        kind=kind,
        url=media_url(path),
        duration_seconds=duration_seconds if kind == "audio" else None,
    )


def check_locket(session, locket: str | None) -> None:
    """Any author picks any locket; an unknown one is refused.
    docs/10-decisions.md#lockets-one-per-memory-chosen-by-its-author-earned-by-level."""
    if locket is None:
        return
    if not session.execute(text("SELECT 1 FROM lockets WHERE id = :id"), {"id": locket}).scalar():
        raise HTTPException(status_code=422, detail="Unknown locket")


@router.post("/v1/memories", response_model=Memory, status_code=201)
def submit_memory(body: SubmissionRequest):
    """File a memory of where you are standing.

    It lands in the `stranger` layer, gated like everything else with a real
    coordinate - including for the person who wrote it, which is why the unlock
    is recorded here too. Filing something is standing there, so re-locking it
    the moment they walk away would be absurd.
    """
    screen(body.place_name, body.summary)
    tags = hashtags(body.summary)
    # A date with no stated precision is a full date, which is what a phone's
    # date picker produces; the field exists for the 1978 case.
    precision = body.happened_precision or ("day" if body.happened_at else None)

    # Its own transaction, so a refusal rolls nothing back and holds no write
    # lock. user_for_device is idempotent, so claiming the user here costs the
    # block below nothing.
    with get_session() as session:
        check_locket(session, body.locket)
        user_id = user_for_device(session, body.device)
        filed = session.execute(text(FILED_TODAY), {"user_id": user_id}).scalar()
    refuse_over_quota(filed, DAILY_MEMORIES, "submission")

    with get_session() as session:
        # LOCK_USER serialises one person's submissions, so this recheck is
        # the one that's true - see
        # docs/10-decisions.md#a-quota-checked-before-the-write-is-not-a-quota.
        session.execute(text(LOCK_USER), {"user_id": user_id})
        filed = session.execute(text(FILED_TODAY), {"user_id": user_id}).scalar()
        refuse_over_quota(filed, DAILY_MEMORIES, "submission")

        place_id = session.execute(
            text(PLACE_INSERT),
            {
                "name": body.place_name.strip(),
                "place_query": f"user:{uuid.uuid4()}",
                "lat": body.lat,
                "lng": body.lng,
                "precision_meters": SUBMITTED_PRECISION_METERS,
            },
        ).scalar()

        memory_id = session.execute(
            text(SUBMISSION_INSERT),
            {
                "place_id": place_id,
                "summary": body.summary.strip(),
                "tags": tags,
                "happened_at": body.happened_at,
                "happened_precision": precision,
                "user_id": user_id,
                "locket": body.locket,
            },
        ).scalar()

        if body.media_ids:
            attached = session.execute(
                text(MEDIA_ATTACH),
                {"memory_id": memory_id, "ids": body.media_ids, "device": body.device},
            ).rowcount
            if attached != len(set(body.media_ids)):
                # Silently posting a memory without the photograph somebody
                # chose is worse than refusing: they would never know.
                raise HTTPException(
                    status_code=400, detail="Some attachments are unknown or already used"
                )

        session.execute(
            text("""
                INSERT INTO unlocks (device_id, memory_id)
                VALUES (CAST(:device AS uuid), :memory_id)
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"device": body.device, "memory_id": memory_id},
        )

        row = session.execute(
            text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id, "device_id": body.device}
        ).fetchone()

    return row_to_memory(row, Coordinates(lat=body.lat, lng=body.lng), include_distance=False)


@router.post("/v1/memories/{memory_id}/heart", response_model=HeartResponse)
def heart_memory(memory_id: int, body: DeviceRequest):
    """Say this one mattered. One heart per device; unheart_memory takes it back.

    No position: unlike unlock, hearting isn't gated by standing there again -
    only rendered by the app once a memory is already unlocked. Same shape as
    report_memory below: an existence check, an idempotent insert, a count.
    """
    with get_session() as session:
        memory = session.execute(
            text("""
                SELECT user_id IS NOT NULL
                   AND user_id = (SELECT user_id FROM devices WHERE id = CAST(:device AS uuid))
                   AS own
                FROM memories WHERE id = :id FOR UPDATE
            """),
            {"id": memory_id, "device": body.device},
        ).fetchone()
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        if memory.own:
            raise HTTPException(status_code=403, detail="You can't heart your own memory")

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO memory_hearts (memory_id, device_id)
                VALUES (:memory_id, CAST(:device AS uuid))
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"memory_id": memory_id, "device": body.device},
        )
        count = session.execute(
            text("SELECT COUNT(*) FROM memory_hearts WHERE memory_id = :id"), {"id": memory_id}
        ).scalar()

    return HeartResponse(heart_count=count)


@router.delete("/v1/memories/{memory_id}/heart", response_model=HeartResponse)
def unheart_memory(memory_id: int, device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Take a heart back: every one this account gave it, since /v1/unlocks
    reports hearted for the account, not the device. Nothing hearted is a no-op."""
    with get_session() as session:
        session.execute(
            text(f"DELETE FROM memory_hearts WHERE memory_id = :id AND device_id IN {MY_DEVICES}"),
            {"id": memory_id, "device_id": device},
        )
        count = session.execute(
            text("SELECT COUNT(*) FROM memory_hearts WHERE memory_id = :id"), {"id": memory_id}
        ).scalar()
    return HeartResponse(heart_count=count)


@router.post("/v1/memories/{memory_id}/note", response_model=NotesResponse)
def leave_note(memory_id: int, body: NoteRequest):
    """Leave a note on a memory you unlocked, and get every note back. One per
    device; posting again rewrites it. No unlock, no note - docs/10-decisions.md#notes-are-gated-like-a-purchase.
    """
    note = body.body.strip()
    if not note:
        raise HTTPException(status_code=422, detail="A note needs some words")
    screen(note)
    with get_session() as session:
        exists = session.execute(
            text("SELECT 1 FROM memories WHERE id = :id AND NOT hidden FOR UPDATE"),
            {"id": memory_id},
        ).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Memory not found")

        allowed = session.execute(
            text(NOTE_ALLOWED_QUERY), {"memory_id": memory_id, "device_id": body.device}
        ).scalar()
        if not allowed:
            raise HTTPException(status_code=403, detail="Stand here first")

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO memory_notes (memory_id, device_id, body)
                VALUES (:memory_id, CAST(:device AS uuid), :body)
                ON CONFLICT (device_id, memory_id) DO UPDATE SET body = EXCLUDED.body
            """),
            {"memory_id": memory_id, "device": body.device, "body": note},
        )
        rows = session.execute(
            text(MEMORY_NOTES_QUERY), {"memory_id": memory_id, "device_id": body.device}
        ).fetchall()

    return notes_response(rows)


# ponytail: author-only moderation. Note reports + REPORT_THRESHOLD if authors
# abandon their memories or notes turn abusive.
@router.delete("/v1/memories/{memory_id}/notes/{note_id}", status_code=204)
def hide_note(memory_id: int, note_id: int, device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Take a note down: its writer, or the memory's author, who is the whole
    moderation for notes. Hidden, not deleted, like a reported memory."""
    with get_session() as session:
        hidden = session.execute(
            text(NOTE_HIDE_QUERY),
            {"note_id": note_id, "memory_id": memory_id, "device_id": device},
        ).fetchone()
    if not hidden:
        raise HTTPException(status_code=404, detail="Note not found")
    return Response(status_code=204)


# Accounts, not devices, and only ones signed in with Google or Apple: an
# anonymous user is one PUT /v1/me away. A cleared report is kept, not counted.
REPORTING_ACCOUNTS = """
    SELECT COUNT(DISTINCT d.user_id) FROM reports r JOIN devices d ON d.id = r.device_id
    WHERE r.memory_id = :id AND r.cleared_at IS NULL
      AND EXISTS (SELECT 1 FROM identities i WHERE i.user_id = d.user_id)
"""

# A claim about the law, not a dislike: one signed-in account is enough. See
# docs/10-decisions.md#a-legal-report-hides-at-once.
LEGAL_REASONS = {"privacy", "defamation", "copyright"}
SIGNED_IN_DEVICE = """
    SELECT 1 FROM devices d JOIN identities i ON i.user_id = d.user_id
    WHERE d.id = CAST(:device AS uuid) LIMIT 1
"""


@router.post("/v1/memories/{memory_id}/report", response_model=ReportResponse)
def report_memory(memory_id: int, body: ReportRequest):
    """Say this should not be here.

    One report per device, counted rather than acted on individually, and at
    REPORT_THRESHOLD the memory stops being served by every endpoint at once.
    Only signed-in accounts count: a device id is self-issued, so three of them
    are one person. A legal reason from one of them hides it at once.
    A reviewer reinstates with `python -m api.moderate`.
    The row stays: a takedown that destroys the evidence makes the next dispute
    unanswerable.
    """
    with get_session() as session:
        # See docs/10-decisions.md#a-report-count-needs-a-lock-too.
        exists = session.execute(
            text("SELECT 1 FROM memories WHERE id = :id FOR UPDATE"), {"id": memory_id}
        ).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Memory not found")

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO reports (memory_id, device_id, reason)
                VALUES (:memory_id, CAST(:device AS uuid), :reason)
                ON CONFLICT (memory_id, device_id) DO NOTHING
            """),
            {"memory_id": memory_id, "device": body.device, "reason": body.reason},
        )
        count = session.execute(text(REPORTING_ACCOUNTS), {"id": memory_id}).scalar()

        hidden = count >= REPORT_THRESHOLD or (
            body.reason in LEGAL_REASONS
            and session.execute(text(SIGNED_IN_DEVICE), {"device": body.device}).scalar() == 1
        )
        if hidden:
            session.execute(
                text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": memory_id}
            )

    return ReportResponse(reports=count, hidden=hidden)


@router.post("/v1/users/{user_id}/block", status_code=204)
def block_user(user_id: uuid.UUID, body: DeviceRequest):
    """Never be shown this person's memories or notes again, on any phone on
    this account. Nobody is told; the other person's words stay up for
    everyone else. There is no unblock yet."""
    with get_session() as session:
        if not session.execute(
            text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id}
        ).scalar():
            raise HTTPException(status_code=404, detail="Nobody by that id")
        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO blocks (device_id, blocked_user_id)
                VALUES (CAST(:device AS uuid), :user)
                ON CONFLICT DO NOTHING
            """),
            {"device": body.device, "user": user_id},
        )
    return Response(status_code=204)


# The lock and ownership check edit and delete share. FOR UPDATE on the row
# itself - report_memory's exact idiom - and the ownership predicate is baked
# into the WHERE rather than checked after, so a memory that isn't yours reads
# as 404, the same as one that doesn't exist.
OWN_MEMORY_LOCK = """
    SELECT place_id FROM memories
    WHERE id = :id
      AND user_id = (SELECT user_id FROM devices WHERE id = CAST(:device AS uuid))
    FOR UPDATE
"""


@router.put("/v1/memories/{memory_id}", response_model=Memory)
def edit_memory(memory_id: int, body: MemoryEditRequest):
    """Change what you filed.

    Ownership is the only lock checked here - no position, because fixing a
    typo does not require standing where it happened again, only filing a new
    memory does.
    """
    screen(body.place_name, body.summary)
    tags = hashtags(body.summary)
    precision = body.happened_precision or ("day" if body.happened_at else None)

    with get_session() as session:
        owned = session.execute(
            text(OWN_MEMORY_LOCK), {"id": memory_id, "device": body.device}
        ).fetchone()
        if not owned:
            raise HTTPException(status_code=404, detail="Memory not found")
        check_locket(session, body.locket)

        session.execute(
            text("UPDATE places SET name = :name WHERE id = :place_id"),
            {"name": body.place_name.strip(), "place_id": owned.place_id},
        )
        session.execute(
            text("""
                UPDATE memories SET
                    summary = :summary,
                    tags = CAST(:tags AS varchar[]),
                    happened_at = :happened_at,
                    happened_precision = :happened_precision,
                    locket = COALESCE(:locket, locket)
                WHERE id = :id
            """),
            {
                "id": memory_id,
                "locket": body.locket,
                "summary": body.summary.strip(),
                "tags": tags,
                "happened_at": body.happened_at,
                "happened_precision": precision,
            },
        )

        # media_ids is the final desired set, not a diff - reconciled against
        # what is already attached rather than asking the client to say which
        # half of the change each id belongs to.
        current_ids = {
            row.id
            for row in session.execute(
                text("SELECT id FROM media WHERE memory_id = :id"), {"id": memory_id}
            )
        }
        wanted_ids = set(body.media_ids)
        to_attach = list(wanted_ids - current_ids)
        to_detach = list(current_ids - wanted_ids)

        if to_attach:
            # Same query and the same rule submit_memory uses: only this
            # device's own unclaimed uploads can be adopted.
            attached = session.execute(
                text(MEDIA_ATTACH),
                {"memory_id": memory_id, "ids": to_attach, "device": body.device},
            ).rowcount
            if attached != len(to_attach):
                raise HTTPException(
                    status_code=400, detail="Some attachments are unknown or already used"
                )

        removed_paths = []
        if to_detach:
            removed_paths = [
                row.path
                for row in session.execute(
                    text(MEDIA_DETACH_QUERY), {"ids": to_detach, "memory_id": memory_id}
                )
            ]

        row = session.execute(
            text(OWNED_MEMORY_QUERY), {"memory_id": memory_id, "device": body.device}
        ).fetchone()

    # File after row, same order as pipeline/sweep.py: a crash between commit
    # and unlink leaves a stray file sweep already knows how to reap.
    for path in removed_paths:
        (api.media.MEDIA_DIR / path).unlink(missing_ok=True)

    return row_to_memory(row, row_coordinates(row), include_distance=False)


@router.delete("/v1/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: int, device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Take down something you filed.

    A real delete, not the report path's hidden flag: that flag exists so a
    moderation dispute stays answerable, and there is no dispute when the
    author is the one asking to remove their own words and photographs.
    Cascades unlocks and reports, which is what takes it out of everyone's
    collection at once, and cleans up the place a submission always mints for
    itself - see docs/10-decisions.md#a-submission-mints-its-own-place.
    """
    with get_session() as session:
        owned = session.execute(
            text(OWN_MEMORY_LOCK), {"id": memory_id, "device": device}
        ).fetchone()
        if not owned:
            raise HTTPException(status_code=404, detail="Memory not found")

        paths = [
            row.path
            for row in session.execute(
                text("SELECT path FROM media WHERE memory_id = :id"), {"id": memory_id}
            )
        ]
        session.execute(text("DELETE FROM memories WHERE id = :id"), {"id": memory_id})
        session.execute(text(DELETE_ORPHAN_SUBMITTED_PLACE), {"place_id": owned.place_id})

    for path in paths:
        (api.media.MEDIA_DIR / path).unlink(missing_ok=True)

    return Response(status_code=204)
