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
from api.models import Author, ContentRef, Coordinates, MediaItem, Memory, Place, Source

# How close you have to stand to read a memory. 150 and not 50: see
# docs/10-decisions.md#150-m-not-50-m.
UNLOCK_RADIUS_METERS = int(os.getenv("UNLOCK_RADIUS_METERS", "150"))

# ponytail: this threshold is the whole moderation system - no appeal, no


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
    that a time capsule could be open while "on this day" still thought it was
    yesterday, and long enough to fail a test at 00:04 with no code changed.

    UTC rather than either machine's local time, because neither machine's
    local time means anything to the person holding the phone. A viewer's own
    date is the honest answer to "on this day" and the server cannot know it;
    picking one clock at least makes the two rules agree with each other. If
    that is ever worth fixing properly the client has to send its date.

    tests/test_clock.py holds the two halves together.
    """
    return datetime.now(UTC).date()


def not_yet_open(row) -> bool:
    """A time capsule that has not come due.

    A different question from the proximity gate and a stricter one: proximity
    asks whether you are here, this asks whether it is time, and no amount of
    standing in the right place answers it. Because it is checked first, it also
    survives the two places that deliberately force a memory open - the
    collection, which passes a memory its own coordinates, and the unlock
    endpoint, which records having walked there.
    """
    opens = getattr(row, "opens_at", None)
    return opens is not None and opens > today()


def is_locked(row, at: Coordinates | None) -> bool:
    """A client-side gate is not a gate. The summary does not leave the server
    until the caller asks for this one memory from inside the radius, so every
    memory-shaped response goes through here rather than the one endpoint the
    app happens to call.

    The list endpoints never pass `at`, and that is the rule: walking into range
    must *offer* the unlock, not perform it, or there is no moment to press. The
    single read, the unlock, the submission and the card all do pass it;
    get_unlocks passes a memory's own coordinates to force it open.

    A time lock is checked first and is not about position at all: see
    not_yet_open.

    ponytail: the position is self-reported, so this stops curl and not a
    determined spoofer. docs/10-decisions.md#the-position-is-self-reported.
    """
    if not_yet_open(row):
        return True
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


def locked_memory(row, coords: Coordinates | None, distance_meters: float | None) -> Memory:
    """Where it is, how far away, who filed it and how much is waiting - enough
    to decide whether to walk there, which is the only decision a locked memory
    has to support. The photo itself stays behind the gate with the text."""
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
        tags=[],
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        author=row_author(row),
        media_count=len(getattr(row, "media", None) or []),
        locked=True,
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
        anniversary=bool(getattr(row, "anniversary", False)),
        # Only while it is shut. Afterwards the date is just a date, and the
        # app would have to work out for itself that it no longer means
        # anything.
        opens_at=getattr(row, "opens_at", None) if not_yet_open(row) else None,
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
        started = row.timestamp_start or 0
        timestamp_url = row.content_url
        if "youtube.com" in row.content_url or "youtu.be" in row.content_url:
            separator = "&" if "?" in row.content_url else "?"
            timestamp_url = f"{row.content_url}{separator}t={int(started)}"
        content = ContentRef(
            id=row.content_id,
            title=row.content_title,
            url=row.content_url,
            timestamp_start=started,
            timestamp_url=timestamp_url,
            source=row_source(row),
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
        tags=row.tags or [],
        # Set on open memories too, not just locked ones: the app needs the
        # radius to draw the reach circle, and a viewport with nothing locked in
        # it used to leave it guessing.
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        happened_at=getattr(row, "happened_at", None),
        attribution=getattr(row, "attribution", None),
        source_url=getattr(row, "source_url", None),
        contrast_score=getattr(row, "contrast_score", None),
        contrast_note=getattr(row, "contrast_note", None),
        anniversary=bool(getattr(row, "anniversary", False)),
    )
