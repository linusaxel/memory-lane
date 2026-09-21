"""Filing a memory, attaching media to it, and taking one down.

api/media.py decides what an upload may be; this module decides what a
submission may say and who it belongs to.
"""

import os
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy import text

from api.accounts import clean_name, set_display_name, touch_device, user_for_device
from api.gate import meters_between, row_to_memory
from api.media import media_url, save_upload
from api.models import (
    DEVICE_PATTERN,
    Coordinates,
    MediaItem,
    Memory,
    ReportRequest,
    ReportResponse,
    SubmissionRequest,
    UnlockRequest,
)
from api.queries import MEDIA_ATTACH, PLACE_INSERT, SINGLE_MEMORY_QUERY, SUBMISSION_INSERT
from pipeline.db import get_session
from pipeline.tags import clean as clean_tags

router = APIRouter()

# reinstatement, no human queue. See docs/10-decisions.md#writing.
REPORT_THRESHOLD = int(os.getenv("REPORT_THRESHOLD", "3"))


# ponytail: the device id is a bearer token in the request body, so anyone
# holding yours can post as you. OAuth did not replace this - see
# docs/10-decisions.md#no-session-tokens-signed-in-or-not.

# The chips the app offers, chosen for somebody filing their own memory rather
# than for a podcast transcript. A subset of the vocabulary and not the
# vocabulary itself - a client sending `travel` is accepted.
SUBMISSION_TAGS = [
    "food",
    "drink",
    "music",
    "art",
    "history",
    "nature",
    "sport",
    "nightlife",
    "work",
    "family",
    "strange",
]

# A phone's GPS in a street, honestly stated rather than flattered.
SUBMITTED_PRECISION_METERS = 25

# The hard cap the brief asks for on user-submitted ingestion. It is not a
# defence against a determined attacker - the device id is self-issued, so a
# loop can mint a fresh identity per request - it is the bound that stops a
# retry loop or a stuck client from filling the disk, which is the failure that
# actually happens. Counted per person rather than per device, so a second
# phone on one account does not double the allowance.
# ponytail: a COUNT over a rolling day, two extra queries on the write path.
# A token bucket if this ever needs to be per-minute rather than per-day.
DAILY_MEMORIES = int(os.getenv("DAILY_MEMORY_LIMIT", "20"))
DAILY_UPLOAD_BYTES = int(os.getenv("DAILY_UPLOAD_BYTES", str(64 * 1024 * 1024)))

SPENT_TODAY = """
    SELECT COALESCE(SUM(bytes), 0) FROM media
    WHERE device_id = CAST(:device AS uuid)
      AND created_at > LOCALTIMESTAMP - INTERVAL '1 day'
"""

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


@router.post("/v1/memories/{memory_id}/unlock", response_model=Memory)
def unlock_memory(memory_id: int, body: UnlockRequest):
    """Earn a memory, and record that it was earned.

    POST rather than GET because it creates something. The gate is the same one
    every read goes through - this endpoint cannot return a summary the plain
    read would have withheld - but it is the only one that writes an unlock, and
    unlocking is the one thing in this product that is supposed to be an act.
    """
    with get_session() as session:
        row = session.execute(text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")

        at = Coordinates(lat=body.lat, lng=body.lng)
        memory = row_to_memory(row, at, include_distance=False)
        if memory.locked:
            # Say how far off, rather than only refusing: the app turns this
            # into "try a few steps nearer".
            if memory.place.coordinates is not None:
                memory.distance_meters = meters_between(at, memory.place.coordinates)
            return memory

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO unlocks (device_id, memory_id)
                VALUES (CAST(:device AS uuid), :memory_id)
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"device": body.device, "memory_id": memory_id},
        )

    return memory


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

    with get_session() as session:
        touch_device(session, device)
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
                # Only meaningful for audio, and only the client knows it - the
                # server does not decode the file to find out.
                "duration": duration_seconds if kind == "audio" else None,
            },
        ).scalar()

    return MediaItem(
        id=media_id,
        kind=kind,
        url=media_url(path),
        duration_seconds=duration_seconds if kind == "audio" else None,
    )


@router.post("/v1/memories", response_model=Memory, status_code=201)
def submit_memory(body: SubmissionRequest):
    """File a memory of where you are standing.

    It lands in the `stranger` layer, gated like everything else with a real
    coordinate - including for the person who wrote it, which is why the unlock
    is recorded here too. Filing something is standing there, so re-locking it
    the moment they walk away would be absurd.
    """
    tags = clean_tags(body.tags)
    # A date with no stated precision is a full date, which is what a phone's
    # date picker produces; the field exists for the 1978 case.
    precision = body.happened_precision or ("day" if body.happened_at else None)

    # Its own transaction, so a refusal rolls nothing back and holds no write
    # lock. user_for_device is idempotent, so claiming the user here costs the
    # block below nothing.
    with get_session() as session:
        user_id = user_for_device(session, body.device)
        filed = session.execute(text(FILED_TODAY), {"user_id": user_id}).scalar()
    refuse_over_quota(filed, DAILY_MEMORIES, "submission")

    with get_session() as session:
        if body.display_name is not None:
            set_display_name(session, user_id, clean_name(body.display_name))

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

        row = session.execute(text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id}).fetchone()

    return row_to_memory(row, Coordinates(lat=body.lat, lng=body.lng), include_distance=False)


@router.post("/v1/memories/{memory_id}/report", response_model=ReportResponse)
def report_memory(memory_id: int, body: ReportRequest):
    """Say this should not be here.

    One report per device, counted rather than acted on individually, and at
    REPORT_THRESHOLD the memory stops being served by every endpoint at once.
    The row stays: a takedown that destroys the evidence makes the next dispute
    unanswerable.
    """
    with get_session() as session:
        exists = session.execute(
            text("SELECT 1 FROM memories WHERE id = :id"), {"id": memory_id}
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
        count = session.execute(
            text("SELECT COUNT(*) FROM reports WHERE memory_id = :id"), {"id": memory_id}
        ).scalar()

        hidden = count >= REPORT_THRESHOLD
        if hidden:
            session.execute(
                text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": memory_id}
            )

    return ReportResponse(reports=count, hidden=hidden)
