"""Every shape the API accepts or returns.

Separate from the routers so `api/card.py` can import them without the cycle
that used to force a function-level import.
"""

from datetime import date, datetime

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


class Link(BaseModel):
    """A name in the summary, exactly as written, and its Wikipedia article."""

    text: str
    url: str


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
    # Set on a locked memory too, like media_count and anniversary: a count is
    # a passive signal, not the content the gate protects.
    heart_count: int = 0
    note_count: int = 0
    # Only on /v1/unlocks: this account hearted it.
    hearted: bool = False
    # Only on /v1/me/memories: when the newest heart came, never from whom.
    last_hearted_at: datetime | None = None
    tags: list[str]
    confidence: str
    locked: bool = False
    unlock_radius_meters: int | None = None
    layer: str = "historical"
    happened_at: date | None = None
    # day | month | year | decade: how much of happened_at to print.
    happened_precision: str | None = None
    attribution: str | None = None
    source_url: str | None = None
    contrast_score: float | None = None
    contrast_note: str | None = None
    # A line in the teller's own words. Null while locked, like the summary.
    quote: str | None = None
    quote_by: str | None = None
    # Empty while locked, like media: the names are part of what it says.
    links: list[Link] = []
    # Something happened here on today's date. Travels on a locked memory too,
    # like media_count: it is a reason to walk over, and it gives away nothing
    # the pin did not already.
    anniversary: bool = False
    # Set when enough people reported it. Only ever populated for the author's
    # own management view - every other query filters hidden rows out instead
    # of serving them with a flag.
    hidden: bool = False
    # Only on the locked shape: what a memory is, never what it says. See
    # docs/10-decisions.md#a-locked-memory-says-what-it-is-not-what-it-says.
    source_name: str | None = None
    year: int | None = None


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


DEVICE_PATTERN = r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$"


class UnlockRequest(BaseModel):
    """Everything an unlock needs, and nothing that identifies a person.

    device is a UUID the app generated for itself. The server never issues one,
    so it never hands an identifier to a client that did not already have it.
    Without a position only a free unlock can open it: that is how one opens
    from anywhere, location permission or not.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)


class UnlocksResponse(BaseModel):
    memories: list[Memory]


class RouteMeta(BaseModel):
    route_date: date
    # The route's true size, which can be short of ROUTE_SIZE in a sparse area -
    # same honesty as NearbyMeta.total rather than padding or refusing.
    size: int
    # How long a walk was asked for - the slider. Read back from the stored row.
    budget_meters: int
    # Whether the walk ends back where it started, as asked for. The start is
    # not here - the server never stores it - so the app closes the loop on
    # the position it planned from.
    loop: bool
    # legs[i] is the street shape from stop i to stop i + 1, or null with no
    # routing sidecar.
    legs: list[list[Coordinates]] | None = None
    # The street shapes from the start to stop 1 and from the last stop home.
    # Preview only: they draw the start, and the server stores no start
    # (docs/10-decisions.md § Routes). The phone keeps them next to its own.
    out_leg: list[Coordinates] | None = None
    home_leg: list[Coordinates] | None = None


# 1km still separates five stops in a dense corpus; 10km is a long day's outing.
ROUTE_BUDGET_MIN_METERS = 1000
ROUTE_BUDGET_MAX_METERS = 10_000
# The app rolls `again` below 1,000,000 for each plan and adds one per "Show me
# another" tap. Past the walks as good, it cycles.
ROUTE_AGAIN_MAX = 1_001_000


class RouteRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    budget_meters: int = Field(ge=ROUTE_BUDGET_MIN_METERS, le=ROUTE_BUDGET_MAX_METERS)
    # Unset is ROUTE_LOOP. Preview and accept must send the same, or the accept
    # plans a different walk from the one previewed.
    loop: bool | None = None
    # Times "Show me another" was tapped. The accept sends the preview's.
    again: int = Field(0, ge=0, le=ROUTE_AGAIN_MAX)
    # A memory the walk must pass ("Walk here"). The accept sends the preview's.
    include: int | None = Field(None, ge=1)
    # Where a one-way walk finishes; it makes the walk one-way. Never stored.
    end: Coordinates | None = None


class RouteResponse(BaseModel):
    # Stop order is the list index - a route never has more than a handful of
    # entries, and nothing else in this API represents order any other way.
    memories: list[Memory]
    meta: RouteMeta


class WalkedMeta(RouteMeta):
    # Stops this account has earned, of `size`. Hidden stops count in neither.
    earned: int
    # Set by the unlock that earned the last stop; null for a walk not finished.
    completed_at: datetime | None = None


class WalkedRoute(BaseModel):
    # Earned stops open, the rest locked. Walking order, like RouteResponse.
    memories: list[Memory]
    meta: WalkedMeta


class WalkedResponse(BaseModel):
    walks: list[WalkedRoute]


class AuthoredRouteResponse(BaseModel):
    id: int
    title: str
    loop: bool
    # In walking order, locked like today's stops: nobody is standing anywhere.
    memories: list[Memory]


class MyMemoriesMeta(BaseModel):
    total: int
    limit: int
    offset: int


class MyMemoriesResponse(BaseModel):
    memories: list[Memory]
    meta: MyMemoriesMeta


# docs/10, "Three free a day, then steps where you stand".
FREE_PER_DAY = 3
STEPS_PER_UNLOCK = 1000


class Profile(BaseModel):
    """What this device is, to the extent it is anybody.

    user_id is null until the person does something that needs one - the first
    submission, or naming themselves. Reading the profile does not create one.
    """

    user_id: str | None = None
    display_name: str | None = None
    submitted: int = 0
    unlocked: int = 0
    # Consecutive days, ending today or yesterday, with at least one unlock -
    # computed from `unlocks` on every read, not stored. See
    # api.accounts.current_streak.
    streak: int = 0
    # Which sign-ins are attached, oldest first. Empty means this device is
    # still only a device: everything works, but a new phone starts empty.
    providers: list[str] = []
    # Paid up now, and until when (naive UTC). A lapsed subscription keeps its
    # date and reads subscribed=false. docs/10, "A subscription opens the map".
    subscribed: bool = False
    subscribed_until: datetime | None = None
    # What opens memories: free_unlocks left today of free_per_day, from anywhere, then
    # steps_per_unlock steps each, standing there. Steps count from
    # steps_counted_until (naive UTC), null until there is a user row.
    # docs/10, "Three free a day, then steps where you stand".
    free_per_day: int = FREE_PER_DAY
    free_unlocks: int = FREE_PER_DAY
    steps: int = 0
    steps_per_unlock: int = STEPS_PER_UNLOCK
    steps_counted_until: datetime | None = None


class StepsRequest(BaseModel):
    """The steps the phone counted from `since`, which must be the watermark
    the profile last gave it. Seven days of Core Motion is at most a few
    hundred thousand; the bound is only against garbage."""

    device: str = Field(pattern=DEVICE_PATTERN)
    since: datetime
    steps: int = Field(ge=0, le=1_000_000)


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
    summary: str = Field(min_length=1, max_length=2000)
    happened_at: date | None = None
    happened_precision: str | None = Field(None, pattern="^(day|month|year|decade)$")
    media_ids: list[int] = Field(default_factory=list, max_length=6)


class MemoryEditRequest(BaseModel):
    """Changing a memory after it was filed. Everything a submission carries
    except lat/lng: the pin is where you stood when you filed it, and there is
    no map picker anywhere in this app to move it to.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    place_name: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    happened_at: date | None = None
    happened_precision: str | None = Field(None, pattern="^(day|month|year|decade)$")
    # The final desired set, like SubmissionRequest.media_ids - not a diff.
    media_ids: list[int] = Field(default_factory=list, max_length=6)


class ReportRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    reason: str | None = Field(None, max_length=40)


class ReportResponse(BaseModel):
    reports: int
    hidden: bool


class HeartResponse(BaseModel):
    heart_count: int


class NoteRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    body: str = Field(min_length=1, max_length=280)


class Note(BaseModel):
    """One visitor's note. Named by its id, never its device: a device UUID is
    a credential. `mine` is whether this account wrote it."""

    id: int
    body: str
    author: str
    created_at: datetime
    mine: bool


class NotesResponse(BaseModel):
    notes: list[Note]


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
    # Adding a second provider to a signed-in account: a fresh ID token from one
    # already on it. The device id alone can't be the proof, or anyone holding
    # it could bind their own identity to that account.
    link_token: str | None = Field(None, min_length=20, max_length=8192)
