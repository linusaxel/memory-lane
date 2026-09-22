"""Every shape the API accepts or returns.

Separate from the routers so `api/card.py` can import them without the cycle
that used to force a function-level import.
"""

from datetime import date

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float
    lng: float


class Place(BaseModel):
    id: int
    name: str
    coordinates: Coordinates | None = None
    precision_meters: int


class Author(BaseModel):
    """Who filed this, when a person did rather than a transcript.

    Shown even while the memory is locked: "somebody stood here and wrote this
    down" is part of what makes it worth walking to, and it gives away nothing
    the summary was protecting.
    """

    id: str
    name: str


class MediaItem(BaseModel):
    """A photo or a recording hanging off a memory.

    Withheld entirely while locked - a photograph of the place is the memory as
    much as the text is. `media_count` still travels, because knowing there is a
    picture waiting is the pull, not the leak.
    """

    id: int
    kind: str
    url: str
    duration_seconds: float | None = None


class Source(BaseModel):
    """Who published the thing this memory came out of.

    Not the memory's own attribution (`Memory.attribution`, which credits an
    archive for an archival item) - this is the channel or publication, and it
    is what stops a summary reading as the app's own assertion.
    """

    name: str
    url: str | None = None
    icon_url: str | None = None


class ContentRef(BaseModel):
    id: int
    title: str | None
    # Already resolved by api.gate.source_link: an archival document, or a video
    # deep-linked to its second. There is no second URL to choose between.
    url: str
    # Seconds into the recording, and None when the source is not one. The app
    # labels the link with it, so a missing offset is the difference between
    # "Watch at 12:04" and an invented "Watch at 0:00".
    timestamp_start: float | None = None
    source: Source | None = None


class Memory(BaseModel):
    id: int
    summary: str
    place: Place
    distance_meters: float | None = None
    # Absent on a locked memory: the source is part of what standing there buys.
    content: ContentRef | None = None
    # Null for everything extracted from a video; set for what people file.
    author: Author | None = None
    # Empty while locked. media_count is not, so a locked card can say what is
    # waiting without handing any of it over.
    media: list[MediaItem] = []
    media_count: int = 0
    tags: list[str]
    confidence: str
    locked: bool = False
    unlock_radius_meters: int | None = None
    layer: str = "historical"
    happened_at: date | None = None
    attribution: str | None = None
    source_url: str | None = None
    contrast_score: float | None = None
    contrast_note: str | None = None
    # Something happened here on today's date. Travels on a locked memory too,
    # like media_count: it is a reason to walk over, and it gives away nothing
    # the pin did not already.
    anniversary: bool = False
    # Set only while a memory is time-locked, and then on the locked shape too:
    # "you cannot read this yet" is unbearable without "until when".
    opens_at: date | None = None
    # Set when enough people reported it. Only ever populated for the author's
    # own management view - every other query filters hidden rows out instead
    # of serving them with a flag.
    hidden: bool = False


class NearbyMeta(BaseModel):
    total: int
    limit: int
    offset: int
    center: Coordinates
    radius_km: float


class NearbyResponse(BaseModel):
    memories: list[Memory]
    meta: NearbyMeta


class SearchMeta(BaseModel):
    total: int
    limit: int
    offset: int
    query: str
    center: Coordinates | None = None
    radius_km: float | None = None


class SearchResponse(BaseModel):
    memories: list[Memory]
    meta: SearchMeta


class PlaceWithCount(BaseModel):
    id: int
    name: str
    coordinates: Coordinates | None = None
    distance_meters: float | None = None
    memory_count: int
    tags: list[str]
    sample_memory: str | None = None


class PlacesResponse(BaseModel):
    places: list[PlaceWithCount]
    meta: NearbyMeta


class Hotspot(BaseModel):
    """A place worth flying the map to when there is nothing where you are."""

    label: str
    lat: float
    lng: float
    memories: int


class Stats(BaseModel):
    memories: int
    # The app draws the reach circle from this. It used to read the radius off a
    # memory, which is null whenever nothing in view is locked.
    unlock_radius_meters: int
    places_with_coordinates: int
    processed_videos: int
    hotspots: list[Hotspot]


DEVICE_PATTERN = r"^[0-9a-fA-F-]{36}$"


class UnlockRequest(BaseModel):
    """Everything an unlock needs, and nothing that identifies a person.

    device is a UUID the app generated for itself. The server never issues one,
    so it never hands an identifier to a client that did not already have it.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class UnlocksResponse(BaseModel):
    memories: list[Memory]


class Profile(BaseModel):
    """What this device is, to the extent it is anybody.

    user_id is null until the person does something that needs one - the first
    submission, or naming themselves. Reading the profile does not create one.
    """

    user_id: str | None = None
    display_name: str | None = None
    submitted: int = 0
    unlocked: int = 0
    # Which sign-ins are attached, oldest first. Empty means this device is
    # still only a device: everything works, but a new phone starts empty.
    providers: list[str] = []


class ProfileRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    # Blank clears it back to Anonymous, which has to be possible: a name is the
    # one thing here that other people see.
    display_name: str = Field(max_length=60)


class SubmissionRequest(BaseModel):
    """One memory, filed by the person who was standing there.

    lat/lng is both where they are and where the memory goes - one coordinate,
    because two would only ever be used to file something somewhere else.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    place_name: str = Field(min_length=1, max_length=200)
    # Ten characters is not a quality bar, it is a fat-finger bar.
    summary: str = Field(min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    happened_at: date | None = None
    happened_precision: str | None = Field(None, pattern="^(day|month|year|decade)$")
    # A time capsule: nobody reads it before this date, the author included.
    # Not validated as future-dated - a date that has passed simply opens, which
    # is the same thing as not sending one and needs no special case.
    opens_at: date | None = None
    media_ids: list[int] = Field(default_factory=list, max_length=6)
    # Sent with the submission rather than requiring a separate profile call, so
    # signing your first memory is one request.
    display_name: str | None = Field(None, max_length=60)


class MemoryEditRequest(BaseModel):
    """Changing a memory after it was filed. Everything a submission carries
    except lat/lng and display_name.

    No position: the pin is where you stood when you filed it, and there is no
    map picker anywhere in this app to move it to. No display_name: that is a
    profile-level setting PUT /v1/me already owns.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    place_name: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    happened_at: date | None = None
    happened_precision: str | None = Field(None, pattern="^(day|month|year|decade)$")
    opens_at: date | None = None
    # The final desired set, like SubmissionRequest.media_ids - not a diff.
    media_ids: list[int] = Field(default_factory=list, max_length=6)


class ReportRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    reason: str | None = Field(None, max_length=40)


class ReportResponse(BaseModel):
    reports: int
    hidden: bool


class DeviceRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)


class SignInRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    # The provider's ID token. Not an access token: the app does the
    # interactive part and the server only decides whether this is real.
    id_token: str = Field(min_length=20, max_length=8192)
    # Apple hands the person's name to the client on the very first
    # authorization and never again, so it has to travel separately or be lost.
    display_name: str | None = Field(None, max_length=60)
