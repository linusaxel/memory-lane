"""Turning a database row into a Memory, redacted unless you are standing there.

The gate lives in `row_to_memory` rather than in an endpoint, so every
memory-shaped response is filtered by the same code - search and
places/nearby\'s sample_memory reach the same rows and would otherwise be side
doors. `api/card.py` renders HTML and cannot use `row_to_memory`, so it calls
`is_locked` itself.

Rules and reasoning: docs/10-decisions.md#the-gate.
"""

import os
from datetime import UTC, date, datetime
from math import asin, cos, radians, sin, sqrt

from api.media import media_url
from api.models import (
    Author,
    ContentRef,
    Coordinates,
    MediaItem,
    Memory,
    Note,
    NotesResponse,
    Place,
    Source,
)

# The locket a memory with none chosen is drawn as. docs/10, "Lockets".
LOCKET_DEFAULT = "hunter-compass"

# How close you have to stand to read a memory: on the spot, not down the
# street. See docs/10-decisions.md#20-m.
UNLOCK_RADIUS_METERS = int(os.getenv("UNLOCK_RADIUS_METERS", "20"))

# A surprise: how near it has to find you, how long it stays open, and how
# often one comes. See docs/10-decisions.md#a-surprise-once-a-week.
SURPRISE_RADIUS_M = int(os.getenv("SURPRISE_RADIUS_M", "200"))
SURPRISE_MINUTES = int(os.getenv("SURPRISE_MINUTES", "30"))
SURPRISE_EVERY_DAYS = int(os.getenv("SURPRISE_EVERY_DAYS", "7"))

# How near a walk's mystery stop has to find you before its place is sent.
# See docs/10-decisions.md#a-mystery-stop.
MYSTERY_REACH_METERS = 100


def row_source(row) -> Source | None:
    """None for every submission - they have no content row - and for the four
    hand-listed videos whose channel the config never names. A name with no link
    is still worth showing; a link with no name is not."""
    name = getattr(row, "source_name", None)
    if not name:
        return None
    return Source(
        name=name,
        url=getattr(row, "source_channel_url", None),
        icon_url=getattr(row, "source_icon_url", None),
    )


def row_coordinates(row) -> Coordinates | None:
    """A place with no coordinates is filtered out of most queries, not all."""
    if row.lat is None or row.lng is None:
        return None
    return Coordinates(lat=row.lat, lng=row.lng)


def viewer_position(lat: float | None, lng: float | None) -> Coordinates | None:
    """Half a position is no position."""
    return Coordinates(lat=lat, lng=lng) if lat is not None and lng is not None else None


def meters_between(a: Coordinates, b: Coordinates) -> float:
    """Haversine. Postgres could do this, but the row already carries the
    coordinate, and this keeps the viewer's position out of every query's binds."""
    lat1, lat2 = radians(a.lat), radians(b.lat)
    dlat, dlng = lat2 - lat1, radians(b.lng - a.lng)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


def is_gated(row) -> bool:
    """Whether this memory is worth making somebody walk to.

    Two ways to qualify. An extracted memory needs a trustworthy coordinate -
    see COORDINATE_IS_UNIQUE, and most do not have one. A submitted memory
    always has one: it was filed from the phone of somebody standing there, so
    there is no centroid problem to protect anyone from.

    Either way a place with no coordinates has nowhere to walk to.
    """
    if row_coordinates(row) is None:
        return False
    return getattr(row, "user_id", None) is not None or bool(
        getattr(row, "coordinate_is_unique", False)
    )


def today() -> date:
    """The server's one opinion of what day it is, in UTC.

    There were two. This function used `date.today()`, which is the host's
    local date, while `ANNIVERSARY` in api/queries.py asked the database for
    CURRENT_DATE, which is the database's. On a laptop in CEST against a
    container in UTC those disagree for two hours every night - long enough
    that today's walk and "on this day" disagreed about the date, and long
    enough to fail a test at 00:04 with no code changed.

    UTC rather than either machine's local time, because neither machine's
    local time means anything to the person holding the phone. A viewer's own
    date is the honest answer to "on this day" and the server cannot know it;
    picking one clock at least makes the two rules agree with each other. If
    that is ever worth fixing properly the client has to send its date.

    tests/test_clock.py holds the two halves together.
    """
    return datetime.now(UTC).date()


def is_locked(row, at: Coordinates | None) -> bool:
    """A client-side gate is not a gate. The summary does not leave the server
    until the caller asks for this one memory from inside the radius, so every
    memory-shaped response goes through here rather than the one endpoint the
    app happens to call.

    The list endpoints never pass `at`, and that is the rule: walking into range
    must *offer* the unlock, not perform it, or there is no moment to press. The
    single read, the unlock, the submission and the card all do pass it;
    get_unlocks passes a memory's own coordinates to force it open.

    ponytail: the position is self-reported, so this stops curl and not a
    determined spoofer. docs/10-decisions.md#the-position-is-self-reported.
    """
    if not is_gated(row):
        return False
    coords = row_coordinates(row)
    return at is None or coords is None or meters_between(at, coords) > UNLOCK_RADIUS_METERS


def row_author(row) -> Author | None:
    """A submission with no display name is still somebody. "Anonymous" is the
    honest rendering of a blank one, and it is decided here rather than in the
    app so the card and the API cannot disagree about it."""
    user_id = getattr(row, "user_id", None)
    if user_id is None:
        return None
    return Author(id=str(user_id), name=getattr(row, "author_name", None) or "Anonymous")


def notes_response(rows) -> NotesResponse:
    """Only ever called behind NOTE_ALLOWED_QUERY - a note is gated with its memory."""
    return NotesResponse(
        notes=[
            Note(
                id=r.id,
                body=r.body,
                author=r.display_name or "Anonymous",
                created_at=r.created_at,
                mine=r.mine,
            )
            for r in rows
        ]
    )


def row_media(row) -> list[MediaItem]:
    """json_agg gives back a list of dicts; the URL is built here so the stored
    path stays a path and the client never has to know where media lives."""
    return [
        MediaItem(
            id=item["id"],
            kind=item["kind"],
            url=media_url(item["path"]),
            duration_seconds=item.get("duration_seconds"),
        )
        for item in (getattr(row, "media", None) or [])
    ]


def source_link(row) -> tuple[str | None, float | None]:
    """Where a memory's source opens, and how far into it - when "into" means
    anything at all.

    An offset is seconds into a recording, so it exists only when the source is
    one. An archival source_url is a document and gets linked as-is; only a
    video takes a ?t= offset, and only YouTube is known to honour one.

    `is not None`, not truthiness: a timestamp_start of 0.0 is the start of the
    video, not a missing value. Everything that emits a source link reads this,
    so the card and the API cannot disagree about it - they did, and the card
    was the one that was right.
    """
    source_url = getattr(row, "source_url", None)
    if source_url:
        return source_url, None

    content_url = getattr(row, "content_url", None)
    if not content_url:
        return None, None

    started = getattr(row, "timestamp_start", None)
    is_youtube = "youtube.com" in content_url or "youtu.be" in content_url
    if not (is_youtube and started is not None):
        return content_url, None

    separator = "&" if "?" in content_url else "?"
    return f"{content_url}{separator}t={int(started)}", started


def locked_memory(row, coords: Coordinates | None, distance_meters: float | None) -> Memory:
    """Where it is, how far away, who filed it and how much is waiting - enough
    to decide whether to walk there, which is the only decision a locked memory
    has to support. The photo itself stays behind the gate with the text.

    Its tags, its source's name and its year say what it is, not
    what it says: docs/10-decisions.md#a-locked-memory-says-what-it-is-not-what-it-says."""
    happened = getattr(row, "happened_at", None)
    return Memory(
        id=row.id,
        summary="",
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=coords,
            precision_meters=row.precision_meters,
        ),
        distance_meters=distance_meters,
        content=None,
        tags=getattr(row, "tags", None) or [],
        source_name=getattr(row, "attribution", None) or getattr(row, "source_name", None),
        year=happened.year if happened else None,
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        locket=getattr(row, "locket", None) or LOCKET_DEFAULT,
        author=row_author(row),
        media_count=len(getattr(row, "media", None) or []),
        heart_count=getattr(row, "heart_count", 0),
        note_count=getattr(row, "note_count", 0),
        locked=True,
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
        anniversary=bool(getattr(row, "anniversary", False)),
        hidden=bool(getattr(row, "hidden", False)),
    )


def row_to_memory(row, at: Coordinates | None = None, include_distance: bool = True) -> Memory:
    coords = row_coordinates(row)
    distance = row.distance_meters if include_distance and hasattr(row, "distance_meters") else None

    if is_locked(row, at):
        return locked_memory(row, coords, distance)

    # None for a submitted memory: it came from a person, not a recording, and
    # there is nothing to link out to. `author` is what carries the credit there.
    content = None
    if getattr(row, "content_id", None) is not None:
        href, started = source_link(row)
        published = getattr(row, "published_at", None)
        content = ContentRef(
            id=row.content_id,
            title=row.content_title,
            url=href or row.content_url,
            timestamp_start=started,
            source=row_source(row),
            kind=getattr(row, "source_type", None),
            published_year=published.year if published else None,
        )

    media = row_media(row)

    return Memory(
        id=row.id,
        summary=row.summary,
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=coords,
            precision_meters=row.precision_meters,
        ),
        distance_meters=distance,
        content=content,
        author=row_author(row),
        media=media,
        media_count=len(media),
        heart_count=getattr(row, "heart_count", 0),
        note_count=getattr(row, "note_count", 0),
        hearted=bool(getattr(row, "hearted", False)),
        last_hearted_at=getattr(row, "last_hearted_at", None),
        opened_by=getattr(row, "opened_by", 0),
        tags=row.tags or [],
        # Set on open memories too, not just locked ones: the app needs the
        # radius to draw the reach circle, and a viewport with nothing locked in
        # it used to leave it guessing.
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        locket=getattr(row, "locket", None) or LOCKET_DEFAULT,
        happened_at=getattr(row, "happened_at", None),
        happened_precision=getattr(row, "happened_precision", None),
        attribution=getattr(row, "attribution", None),
        source_url=getattr(row, "source_url", None),
        contrast_score=getattr(row, "contrast_score", None),
        contrast_note=getattr(row, "contrast_note", None),
        quote=getattr(row, "quote", None),
        quote_by=getattr(row, "quote_by", None),
        links=getattr(row, "links", None) or [],
        pictures=[p for p in getattr(row, "pictures", None) or [] if p.get("url")],
        anniversary=bool(getattr(row, "anniversary", False)),
        hidden=bool(getattr(row, "hidden", False)),
    )


def mystery_memory(row, at: Coordinates | None, earned: bool = False) -> Memory:
    """A walk's mystery stop. Nothing of it, not even its id (which
    /v1/memories/{id} would place), until `at` is within MYSTERY_REACH_METERS;
    then it is a stop like any other. Once earned it stays found."""
    coords = row_coordinates(row)
    if earned:
        return row_to_memory(row, coords, include_distance=False)
    if at and coords and meters_between(at, coords) <= MYSTERY_REACH_METERS:
        return row_to_memory(row, None, include_distance=False)
    return Memory(
        id=0,
        summary="",
        place=Place(id=0, name="", precision_meters=0),
        tags=[],
        confidence="medium",
        locked=True,
    )
