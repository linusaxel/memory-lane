"""Extract location-based memories from transcripts using Claude."""

import hashlib
import json
import logging

import anthropic
from sqlalchemy import text

from pipeline import geocode
from pipeline.config import (
    ANTHROPIC_API_KEY,
    CHUNK_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    EXTRACTION_MODEL,
)
from pipeline.db import get_session
from pipeline.tags import TAGS
from pipeline.tags import clean as clean_tags
from pipeline.transcripts import LONG_ENOUGH

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You extract location-based memories from video transcripts.

A memory is something that HAPPENED at a SPECIFIC PHYSICAL LOCATION.

QUALIFIES as a memory:
- Personal experiences: "I proposed to my wife on this bridge"
- Specific events: "We had dinner at a restaurant in the Latin Quarter"
- Vivid recollections: "I got lost in the medina and found this incredible spice market"

Does NOT qualify:
- Hypotheticals: "I want to visit Paris someday"
- Vague references: "Somewhere in Europe"
- General facts: "Paris is the capital of France"
- Recommendations without personal experience: "You should check out the Eiffel Tower"
- ANNOUNCEMENTS AND PROMOS. "I'm playing the Fillmore on the 14th, come out" is a
  ticket ad, not a memory. If it has not happened yet, it is not a memory, however
  specific the venue. This is the single most common mistake: a tour date names a
  real place and reads like an event, and it is worthless to somebody standing
  there. If the only thing anchoring the place is an upcoming show, return nothing.
- THE PLACE IS INCIDENTAL. The reader is standing on the pin. Ask: would this
  story lose anything if it were pinned somewhere else? How someone got a
  nickname, where someone lives, who sponsors what, a trip mentioned in passing -
  all fail. So does anything that happened at a place the transcript does not
  name: never pin it to a guess.

For each memory, extract:
- venue: The proper name of the specific place - the business, building, park
  or landmark, exactly as you would say it to someone standing nearby. Not a
  description ("a bar", "the venue", "a local brown pub") and not the whole
  address. It is somewhere a walker could find on a map. An event, a parade
  or a pub crawl is not a venue, and nor is the event's own name ("Trip
  Nørrebro"): name the street or bar it happened at, or return nothing. Nor
  is an institution named only by what it is ("the emergency room",
  "Skadestuen"). Two different
  venues on the same street must get different venue names even when nothing
  else about them differs - this is the field a duplicate check keys on, so it
  cannot mean "the neighborhood" or "the block".
- locality: The city or town the venue is in. Always this level - never a
  neighborhood, borough or street, even when the transcript names one and even
  when that is how you would say it in everyday speech. "Chelsea, Manhattan"
  becomes locality "New York City", not "Chelsea": consistency here matters
  more than specificity, because it is the second half of the same duplicate
  check, and the same venue mentioned twice must produce the same locality
  both times.
- region: State/province and/or country, whichever a mapmaker would need to
  find the locality unambiguously ("California, USA" for West Hollywood,
  "Denmark" for Copenhagen - no state needed there). Null only if you
  genuinely do not know.

<example>
  <venue>Andaz West Hollywood</venue>
  <locality>West Hollywood</locality>
  <region>California, USA</region>
  <why>The hotel's own name happens to contain "West Hollywood" - that text is
       part of the venue, not the locality. The Comedy Store sits two blocks
       away on the same street, in the same locality. Sharing a locality is
       normal and expected; venue is the only field allowed to tell them
       apart. If you cannot name the real place, return nothing rather than
       inventing a plausible one.</why>
</example>

- country: ISO 3166 two-letter code of the country the venue is in ("US",
  "DK"). Null only if you genuinely do not know.
- address: The street and house number, if the transcript names one, written in
  today's spelling even when the transcript uses an old one ("Blaagaardsgade 12"
  becomes "Blågårdsgade 12"). Null if no street is named. A geocoder places
  the pin from this and the venue; your lat / lng is only the fallback.
- lat: Latitude estimate (decimal degrees, e.g., 48.8566)
- lng: Longitude estimate (decimal degrees, e.g., 2.3522)
- timestamp_start: When place is first mentioned (from [timestamp] markers in input)
- summary: 2-3 sentences, 40-70 words, capturing the STORY rather than the facts.
  This is read by somebody standing on the spot, on a phone, outdoors. It is the
  whole product. Rules, in order of how often they are broken:

  * NEVER write "the speaker", "the host", "the hosts", "the comedian" or
    "the narrator". Use the name if the transcript gives one. If it does not,
    write the sentence without a subject label - "someone", or just start with
    what happened. Half of a previous run began "The speaker...", which reads
    like a machine describing a recording instead of a thing that happened here.
  * PAST TENSE. Always. "Mark drove the van into a ditch", never "Mark is
    driving" or "Mark talks about driving". You are reporting an event, not
    narrating a transcript.
  * NEVER refer to the recording. No "they mentioned", "he describes", "they
    were discussing". The listener does not know there is a recording, and does
    not care. Write what happened, not what was said about it.
  * 2-3 sentences. If it runs past 70 words you are summarising the conversation
    rather than the event. Cut the setup and keep the thing that happened.
  * WHO, with names - nicknames too, when that is what the transcript uses.
    "Someone" only when it names nobody at all. WHAT HAPPENED - the anecdote,
    the mishap, the funny turn. THE VIBE - what made it worth telling.
  * Lead with what happened HERE, not the frame around it (the tour, the pub
    crawl, "the fourth of 25 stops").
  * If the transcript names something the reader can still see or picture from
    the spot - the trees out front, the empty lot, the stream under the street -
    put it in. That is what makes standing there pay off.

  Bad: "The speaker describes performing at a theater in Boulder and mentions it
       was built in 1909."
  Good: "Mark did three sold-out nights at this 1909 theatre, joking that the
        marquee had survived prohibition, the depression, and now his act."

<examples>
Every one of these is taken from a real run and is the mistake, not a
hypothetical. Match the "good" column.

<example>
  <bad>The speaker performed at Joe List's downtown comedy showcase called
       'Sesh' - described as the best show in North America.</bad>
  <good>Mark played Joe's downtown showcase, Sesh, and called it the best room
        in North America.</good>
  <why>"The speaker" names nobody, and Joe List is the other host - the context
       above the transcript says so. "Described as" reports the recording.</why>
</example>

<example>
  <bad>The speaker is performing at Falls View Casino in Niagara on the 14th,
       making a joke about Marilyn Monroe.</bad>
  <good></good>
  <why>Nothing happened there. A tour date names a real venue and reads like an
       event, and is worthless to somebody standing outside it. Return nothing.</why>
</example>

<example>
  <bad>(venue: Levinho aprés-ski bar) On his very first ski trip, Kansas
       couldn't stand up on skis. In the après-ski bar the instructor called
       out 'Kansas, come over here' and the nickname stuck.</bad>
  <good></good>
  <why>A fine story about a person, not a place. The transcript never named
       the bar, so the venue was a guess, and nobody standing outside it would
       learn anything about where they are. Return nothing.</why>
</example>

<example>
  <bad>The bar crawl reached its fourth of 25 stops at Folmer Bendtsens Plads,
       stopping into Ringkaféen, a 1930s bar that sank into the ground during
       metro construction.</bad>
  <good>Ringkaféen, open since the 1930s, sank into the ground when the metro
        works broke through to the old Lygteå stream still running under the
        street.</good>
  <why>Cut the crawl logistics and lead with what happened to this building -
       the stream under the reader's feet is the payoff.</why>
</example>
</examples>
- why_here: One line on what this spot adds to the story - "the bar itself
  sank", "the lot where it stood is still empty". It must be something that
  happened AT this place, or something still visible there. "The crawl stopped
  here" or "he kept coming back to the crawl" is a stop, not a story. An empty
  string if nothing qualifies, and then the memory is dropped: that is the spot
  test, answered.
- tags: 1-5 from: {TAG_LIST}. Anything else is dropped.
- location_precision: exact (~50m), street (~200m), neighborhood (~1km), city (~10km)
  BE HONEST ABOUT THIS. If you are returning the coordinates of a city because you
  do not know the address, say "city". Only say "exact" when you know the specific
  building or street address. A wrong "exact" is worse than an honest "city": it
  puts a pin on the wrong doorstep and claims 50m accuracy while doing it.
- confidence: high (clear location + definite event), medium (somewhat vague), low (uncertain)

<uncertainty>
An empty list is a correct and common answer. Most of a conversation is not
about a place. If you are unsure whether something happened, or where, or to
whom, leave it out - a missing memory costs nothing, and an invented one is
indistinguishable from a real one once it is a row in the database and a pin on
a map somebody walked to.
</uncertainty>

Return JSON: {"memories": [...]}
Return {"memories": []} if no memories found."""

HISTORICAL_SYSTEM_PROMPT = """You extract location-based memories from archival text:
newspaper clippings, local archive entries, venue and concert records, registries.

A memory is something that HAPPENED at a SPECIFIC PHYSICAL LOCATION.

QUALIFIES:
- Events: "Bowie played this room in 1978, 400 capacity"
- Things that stood here: "The bakery was on that corner until '78"
- Documented incidents: "The tram derailed outside the pharmacy in March 1931"

Does NOT qualify - reject these as firmly as you would reject a hypothetical:
- Static description: "this building was constructed in 1902", "four storeys, tiled roof"
  A building EXISTING is not something that HAPPENED. If you cannot name an event,
  there is no memory here.
- Architectural or stylistic commentary: "a fine example of the national romantic style"
- Encyclopaedia facts: "Copenhagen is the capital of Denmark"
- Anything you are inferring rather than reading. If the text does not say it
  happened, it did not happen. Do not fill gaps with plausible history.

This is third-party material, so write it straight. Do NOT use the chatty,
first-person register you would use for someone telling a story about themselves:
no invented emotions, no invented names, no "you can just picture it". Say what
happened, where, and when, and let the fact carry it.

For each memory, extract:
- venue: The proper name of the specific place - the business, building, park
  or landmark. Not a description and not the whole address. This is the field
  a duplicate check keys on, so two different venues must get different names
  even when they are close together.
- locality: The city or town the venue is in. Always this level - never a
  neighborhood or street, even when the source names one. Consistency matters
  more than specificity: the same venue named in two different records must
  produce the same locality both times.
- region: State/province and/or country, whichever disambiguates the
  locality. Null only if genuinely unknown.

<example>
  <venue>Vega</venue>
  <locality>Copenhagen</locality>
  <region>Denmark</region>
  <why>Vesterbro, the neighborhood the source names, is not the locality -
       Copenhagen is. Keeping locality at the city level is what lets a second
       archive record naming the same room years later collide with this one
       instead of minting a new place.</why>
</example>

- country: ISO 3166 two-letter code of the country the venue is in ("US",
  "DK"). Null only if you genuinely do not know.
- address: The street and house number, if the text names one, written in
  today's spelling even when the text uses an old one ("Blaagaardsgade 12"
  becomes "Blågårdsgade 12"). Null if no street is named. A geocoder places
  the pin from this and the venue; your lat / lng is only the fallback.
- lat / lng: Decimal degrees
- happened_at: ISO date of the EVENT - "1978-06-17", "1978-06", or "1978". Null if
  the text gives no date. This is when it happened, not when it was written about.
- happened_precision: day | month | year | decade - how much of happened_at to trust
- summary: 2-4 sentences. What happened, who was involved if named, what the place
  was at the time. Concrete and sourced, not atmospheric.
- why_here: One line on what this spot adds - usually the event itself. An empty
  string if the text only mentions the place in passing, and then it is dropped.
- attribution: the source as it should be credited on a card, if the text names one
- tags: 1-5 from: {TAG_LIST}. Anything else is dropped.
- location_precision: exact (~50m), street (~200m), neighborhood (~1km), city (~10km)
  BE HONEST. If you are returning a city's coordinates because you do not know the
  address, say "city". Only "exact" when you know the building. A wrong "exact"
  puts a pin on the wrong doorstep and claims 50m accuracy while doing it.
- confidence: high (clear location + definite event), medium (somewhat vague),
  low (uncertain)
- contrast_score: 0.0 to 1.0. How far this is from what a person standing there
  TODAY would see. This decides what gets shown first, so it matters more than
  historical importance:
    0.9-1.0  the place is unrecognisable - a 400-capacity music room that is now
             a bank branch, a bakery that is now a car park
    0.5-0.8  same use, changed character - a pub that is still a pub but was the
             one the dockers drank in
    0.1-0.4  the place is essentially as it was
    0.0      you cannot tell what is there now
  A cathedral's founding date is famous and scores LOW: it is still a cathedral.
  A jazz club that became a bank lobby scores HIGH. Fame is not contrast.
- contrast_note: one line naming both sides of that gap - "a 400-capacity music
  room above a bicycle shop; a bank branch since 1994". Null if you do not know
  what is there now. Do not guess what is there now.

Return JSON: {"memories": [...]}
Return {"memories": []} if no memories found. An empty list is the right answer
for a page of architectural description, and is always better than an invention."""


# Substituted rather than interpolated: both prompts show JSON, so an f-string
# would need every brace in them doubled.
SYSTEM_PROMPT = SYSTEM_PROMPT.replace("{TAG_LIST}", ", ".join(TAGS))
HISTORICAL_SYSTEM_PROMPT = HISTORICAL_SYSTEM_PROMPT.replace("{TAG_LIST}", ", ".join(TAGS))


_NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}

# One schema for both prompts: the fields every memory needs are required, the
# ones only the archival prompt asks for are optional. Enforced by the API, so
# a reply is always parseable JSON of this shape - unless max_tokens cuts it.
MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "venue": {"type": "string"},
                    "locality": {"type": "string"},
                    "region": _NULLABLE_STRING,
                    "address": _NULLABLE_STRING,
                    "country": _NULLABLE_STRING,
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "timestamp_start": {"type": "number"},
                    "summary": {"type": "string"},
                    "why_here": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string", "enum": list(TAGS)}},
                    "location_precision": {
                        "type": "string",
                        "enum": ["exact", "street", "neighborhood", "city"],
                    },
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "happened_at": _NULLABLE_STRING,
                    "happened_precision": {
                        "anyOf": [
                            {"type": "string", "enum": ["day", "month", "year", "decade"]},
                            {"type": "null"},
                        ]
                    },
                    "attribution": _NULLABLE_STRING,
                    "contrast_score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    "contrast_note": _NULLABLE_STRING,
                },
                "required": [
                    "venue",
                    "locality",
                    "region",
                    "lat",
                    "lng",
                    "summary",
                    "why_here",
                    "tags",
                    "location_precision",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["memories"],
    "additionalProperties": False,
}

USER_PROMPT_TEMPLATE = """{context}Extract memories from this transcript chunk:

{chunk}

Return only valid JSON."""

# Who is talking, as far as anything knows. A transcript is a wall of unattributed
# speech, so with no context the model had nobody to name and wrote "the speaker"
# in over half the corpus. The show and episode title are usually enough to
# recover the names - "Tuesdays with Stories with Mark Normand and Joe List" puts
# them in the transcript's own vocabulary.
SOURCE_CONTEXT_TEMPLATE = """This transcript is from {source}{title}.

Use it to work out who is speaking. If the transcript or this context names the
people, use their names. If neither does, write the sentence without a subject
label - never "the speaker", "the host" or "the narrator".

"""


def source_context(source_name: str | None, title: str | None) -> str:
    """The lead-in for a chunk, or nothing when we know nothing about the source."""
    if not source_name:
        return ""
    return SOURCE_CONTEXT_TEMPLATE.format(
        source=source_name,
        title=f', episode "{title}"' if title else "",
    )


def chunk_transcript(
    segments: list,
    chunk_minutes: int = CHUNK_MINUTES,
    overlap_seconds: int = CHUNK_OVERLAP_SECONDS,
) -> list[str]:
    """Split transcript segments into overlapping time-based chunks with timestamp markers."""
    if not segments:
        return []

    chunk_seconds = chunk_minutes * 60
    chunks = []
    current_chunk_lines = []
    chunk_start_time = 0

    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue

        if start >= chunk_start_time + chunk_seconds:
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
            chunk_start_time = start - overlap_seconds
            current_chunk_lines = []

        current_chunk_lines.append(f"[{start:.1f}] {text}")

    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))

    return chunks


# Here as well as before the transcript fetch: a clip's transcript may predate
# the filter.
PENDING_EXTRACTION = f"""
FROM content c
JOIN transcripts t ON c.id = t.content_id
WHERE c.memories_extracted = FALSE
  AND c.extraction_failed = FALSE
  AND c.transcript_fetched = TRUE
  AND {LONG_ENOUGH}
"""


class BillingError(Exception):
    """Raised when API call fails due to billing issues."""

    pass


def is_billing_error(e: Exception) -> bool:
    """An empty balance, which no retry and no other chunk will get past.

    The API reports it as a 400 with the reason in the message rather than as
    its own class, so this is a string match - narrow, and asserted in
    tests/test_extract_errors.py so a wording change fails loudly rather than
    silently turning a hard stop back into a fail-open.
    """
    return isinstance(e, anthropic.BadRequestError) and "credit balance" in str(e).lower()


class ModelUnusableError(Exception):
    """The configured model cannot be called at all: wrong ID, bad or revoked key,
    or a request shape (schema, parameter) it rejects.

    Distinct from a transient API error because it will fail identically on
    every chunk of every video. Swallowing it returns zero memories per chunk,
    which the caller cannot tell from a chunk that genuinely had none - so it
    marks the video extracted and moves on, quietly burning the whole backlog.
    """

    pass


class TransientAPIError(Exception):
    """A 429, a 5xx or a dropped connection that outlived the SDK's own retries.

    Same trap as ModelUnusableError, one video at a time: returned as [] it is a
    chunk with no memories, the video is marked extracted, and "never
    re-extract" makes the gap permanent. Raised, the video stays pending.
    """

    pass


def is_transient(e: Exception) -> bool:
    if isinstance(e, anthropic.APIConnectionError):
        return True
    return isinstance(e, anthropic.APIStatusError) and (
        e.status_code == 429 or e.status_code >= 500
    )


def _request(client: anthropic.Anthropic, system_prompt: str, user: str) -> str | None:
    """The model's raw reply, or None for an error no retry will fix."""
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            # The system prompt is ~1.2k tokens and is resent for every chunk -
            # 22 chunks a video, 55 videos. Cached reads cost 10% of input and a
            # write costs 1.25x, so this pays for itself on the second chunk.
            # The variable part (context + chunk) is in the message, after this,
            # which is the order caching requires.
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user}],
            # Sonnet 5 thinks by default: billed output, eats max_tokens, and
            # puts a thinking block at content[0].
            thinking={"type": "disabled"},
            output_config={"format": {"type": "json_schema", "schema": MEMORY_SCHEMA}},
        )
        return response.content[0].text

    except anthropic.BadRequestError as e:
        if is_billing_error(e):
            raise BillingError(
                "API credit balance too low. Please add credits at console.anthropic.com"
            ) from e
        # A rejected schema or parameter is rejected for every chunk, so it
        # stops the run rather than emptying the backlog one [] at a time.
        raise ModelUnusableError(f"EXTRACTION_MODEL={EXTRACTION_MODEL!r} rejected: {e}") from e
    except (
        anthropic.NotFoundError,
        anthropic.AuthenticationError,
        anthropic.PermissionDeniedError,
    ) as e:
        raise ModelUnusableError(f"EXTRACTION_MODEL={EXTRACTION_MODEL!r} is not usable: {e}") from e
    except Exception as e:
        if is_transient(e):
            raise TransientAPIError(str(e)) from e
        logger.error(f"Error calling Claude API: {e}")
        return None


def parse_memories(content: str) -> list[dict]:
    try:
        return json.loads(content)["memories"]
    except Exception:
        logger.warning(f"Failed to parse JSON from response: {content[:200]}")
        return []


def extract_memories_from_chunk(
    client: anthropic.Anthropic,
    chunk: str,
    system_prompt: str = SYSTEM_PROMPT,
    context: str = "",
) -> list[dict]:
    raw = _request(client, system_prompt, USER_PROMPT_TEMPLATE.format(context=context, chunk=chunk))
    return [] if raw is None else parse_memories(raw)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def extract_chunk_stored(
    session,
    client: anthropic.Anthropic,
    content_id: int,
    chunk_index: int,
    chunk: str,
    system_prompt: str = SYSTEM_PROMPT,
    context: str = "",
) -> list[dict]:
    """extract_memories_from_chunk, paid for once per exact request.

    Keyed on video + model + schema + system prompt + user message, so a
    prompt edit misses and a retry, a re-merge or a crashed run hits.
    Committed as soon as it lands: the reply is the expensive part and must
    outlive whatever fails next.
    """
    user = USER_PROMPT_TEMPLATE.format(context=context, chunk=chunk)
    schema = json.dumps(MEMORY_SCHEMA, sort_keys=True)
    key = _sha256(f"{content_id}\0{EXTRACTION_MODEL}\0{schema}\0{system_prompt}\0{user}")

    raw = session.execute(
        text("SELECT response FROM extraction_chunks WHERE request_hash = :k"), {"k": key}
    ).scalar()
    if raw is None:
        raw = _request(client, system_prompt, user)
        if raw is None:
            return []
        session.execute(
            text("""
                INSERT INTO extraction_chunks
                    (request_hash, content_id, chunk_index, prompt_hash, model, response)
                VALUES (:k, :content_id, :chunk_index, :prompt_hash, :model, :response)
                ON CONFLICT (request_hash) DO NOTHING
            """),
            {
                "k": key,
                "content_id": content_id,
                "chunk_index": chunk_index,
                "prompt_hash": _sha256(system_prompt),
                "model": EXTRACTION_MODEL,
                "response": raw,
            },
        )
        session.commit()
    return parse_memories(raw)


def _venue_locality_key(mem: dict) -> tuple[str, str]:
    return (
        (mem.get("venue") or "").strip().lower(),
        (mem.get("locality") or "").strip().lower(),
    )


def merge_nearby_memories(memories: list[dict], threshold_seconds: float = 60) -> list[dict]:
    """Merge memories for the same place within threshold_seconds.

    Keyed on (venue, locality), W4-02 - the model no longer returns
    place_query. Folded the same way save_memories folds it, so a chunk
    boundary that capitalizes a name differently still merges.
    """
    if not memories:
        return []

    sorted_memories = sorted(
        memories, key=lambda m: (_venue_locality_key(m), m.get("timestamp_start", 0))
    )

    merged = []
    current = None

    for mem in sorted_memories:
        if current is None:
            current = mem.copy()
            continue

        same_place = _venue_locality_key(current) == _venue_locality_key(mem)
        time_diff = abs(mem.get("timestamp_start", 0) - current.get("timestamp_start", 0))

        if same_place and time_diff <= threshold_seconds:
            if mem.get("summary") and mem["summary"] not in current.get("summary", ""):
                current["summary"] = current.get("summary", "") + " " + mem["summary"]
            current_tags = set(current.get("tags", []))
            current_tags.update(mem.get("tags", []))
            current["tags"] = list(current_tags)
        else:
            merged.append(current)
            current = mem.copy()

    if current:
        merged.append(current)

    return merged


def filter_low_confidence(memories: list[dict]) -> list[dict]:
    """Drop what nobody could stand on: unsure, city-wide, or failing the spot test.
    See docs/10-decisions.md#a-memory-must-need-its-spot."""
    return [
        m
        for m in memories
        if m.get("confidence", "low") in ("high", "medium")
        and m.get("location_precision") != "city"
        and (m.get("why_here") or "").strip()
    ]


def prompt_for(source_type: str | None) -> str:
    """Archival text and someone telling a story need different instructions.

    The personal prompt asks for WHO and THE VIBE, which invites invention when
    pointed at a newspaper clipping - exactly what must not happen to third-party
    material.
    """
    return SYSTEM_PROMPT if (source_type or "video") == "video" else HISTORICAL_SYSTEM_PROMPT


def layer_for(source_type: str | None) -> str:
    """Everything the pipeline ingests is public, permanent content. The
    `stranger` layer is written by POST /v1/memories, never from here."""
    return "historical"


def precision_to_meters(precision: str) -> int:
    mapping = {"exact": 50, "street": 200, "neighborhood": 1000, "city": 10000}
    return mapping.get(precision, 200)


def _place_name(venue: str | None, locality: str | None) -> str:
    """Display string for places.name. Derived, not asked for: this is what
    used to let place_name and place_query disagree with each other."""
    if venue and locality:
        return f"{venue}, {locality}"
    return venue or locality or "Unknown"


def _place_query(
    venue: str | None,
    locality: str | None,
    region: str | None,
    legacy_query: str | None,
    legacy_name: str | None,
) -> str:
    """place_query is NOT NULL and UNIQUE for every writer of this table,
    including api/write.py's human submissions - it cannot disappear. Derived
    from the structured fields when they exist; falls back to whatever the
    caller supplied before W4-02 for anything that still looks like that."""
    parts = [p for p in (venue, locality, region) if p]
    if parts:
        return ", ".join(parts)
    return legacy_query or legacy_name or "Unknown"


def _happened_at(mem: dict):
    """Normalise the model's date to something DATE accepts, or None.

    It is told to answer "1978-06-17", "1978-06" or "1978", and a partial date
    is the honest answer when a clipping only gives a year - so widen it to the
    first of the period and let happened_precision carry how much to trust.
    """
    raw = (mem.get("happened_at") or "").strip()
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) == 1 and len(parts[0]) == 4:
        return f"{parts[0]}-01-01"
    if len(parts) == 2:
        return f"{raw}-01"
    return raw if len(parts) == 3 else None


def _contrast_score(mem: dict):
    """Clamp the model's 0-1 score, or None if it did not give a usable number.

    Ordering depends on this, so a stray "high" or a 7 must not become a rank.
    """
    raw = mem.get("contrast_score")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return min(1.0, max(0.0, float(raw)))
    except (
        TypeError,
        ValueError,
    ):
        # Kept exploded with a trailing comma on purpose.
        # See docs/10-decisions.md#except-a-b-stays-exploded
        logger.warning("Unusable contrast_score %r, storing null", raw)
        return None


def save_memories(session, content_id: int, memories: list[dict], layer: str = "historical"):
    for mem in memories:
        lat = mem.get("lat")
        lng = mem.get("lng")
        has_coords = lat is not None and lng is not None

        # The model brackets context onto a name: "Bopa Bar (Nørrebro pub crawl)".
        venue = geocode.unbracket(mem.get("venue") or "") or None
        locality = (mem.get("locality") or "").strip() or None
        region = (mem.get("region") or "").strip() or None
        structured = bool(venue and locality)

        precision = precision_to_meters(mem.get("location_precision", "street"))
        status = "llm"
        happened = _happened_at(mem)
        hit = geocode.place(
            (mem.get("address") or "").strip() or None,
            venue,
            locality,
            (mem.get("country") or "").strip() or None,
            (lat, lng) if has_coords else None,
            int(happened[:4]) if happened else None,
        )
        if hit:
            lat, lng, precision, status = hit
            has_coords = True

        params = {
            "name": _place_name(venue, locality)
            if structured
            else mem.get("place_name", "Unknown"),
            "query": _place_query(
                venue, locality, region, mem.get("place_query"), mem.get("place_name")
            ),
            "venue": venue,
            "locality": locality,
            "region": region,
            "precision": precision,
            "lat": lat,
            "lng": lng,
            "status": status,
        }

        place_id = _same_venue_nearby(session, params) if venue and has_coords else None
        if place_id:
            _save_memory(session, place_id, content_id, mem, layer)
            continue

        if structured:
            conflict_target = (
                "(lower(btrim(venue)), lower(btrim(locality))) "
                "WHERE venue IS NOT NULL AND locality IS NOT NULL"
            )
            fallback_sql = text(
                "SELECT id FROM places WHERE lower(btrim(venue)) = lower(btrim(:venue)) "
                "AND lower(btrim(locality)) = lower(btrim(:locality))"
            )
        else:
            # ponytail: exact-string dedup only, unchanged from before W4-02.
            # Rows missing venue/locality (a caller that never adopted the
            # structured prompt) fall back to place_query - "Oslo Norway" and
            # "comedy club Oslo Norway" remain separate places here.
            conflict_target = "(place_query)"
            fallback_sql = text("SELECT id FROM places WHERE place_query = :query")

        if has_coords:
            place_result = session.execute(
                text(f"""
                    INSERT INTO places (name, place_query, venue, locality, region, precision_meters, coordinates, geocode_status)
                    VALUES (:name, :query, :venue, :locality, :region, :precision, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :status)
                    ON CONFLICT {conflict_target} DO NOTHING
                    RETURNING id
                """),
                params,
            )
        else:
            place_result = session.execute(
                text(f"""
                    INSERT INTO places (name, place_query, venue, locality, region, precision_meters)
                    VALUES (:name, :query, :venue, :locality, :region, :precision)
                    ON CONFLICT {conflict_target} DO NOTHING
                    RETURNING id
                """),
                params,
            )
        row = place_result.fetchone()

        if row:
            place_id = row[0]
        else:
            existing = session.execute(fallback_sql, params).fetchone()
            place_id = existing[0] if existing else None

        if not place_id:
            logger.warning(f"Could not get place_id for: {venue or mem.get('place_name')}")
            continue

        _save_memory(session, place_id, content_id, mem, layer)


def _same_venue_nearby(session, params: dict) -> int | None:
    """The place this venue already is, in whatever locality the model named
    it: "Under Hylden" came as Frederiksberg once and Copenhagen twice. Within
    10 km, and unless both sides are points: two 50 m hits apart are a chain,
    not one venue. A better placing replaces the stored one."""
    row = session.execute(
        text("""
            SELECT id, precision_meters, geocode_status FROM places
            WHERE lower(btrim(venue)) = lower(btrim(:venue))
              AND coordinates IS NOT NULL
              AND geocode_status <> 'user'
              AND ST_DWithin(
                  coordinates, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 10000
              )
              AND (precision_meters > 50 OR geocode_status = 'llm'
                   OR :precision > 50 OR :status = 'llm')
            ORDER BY (geocode_status = 'llm'), precision_meters
            LIMIT 1
        """),
        params,
    ).fetchone()
    if not row:
        return None
    if params["status"] != "llm" and (
        row.geocode_status == "llm" or params["precision"] < row.precision_meters
    ):
        session.execute(
            text("""
                UPDATE places SET
                    coordinates = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    precision_meters = :precision, geocode_status = :status
                WHERE id = :id
            """),
            {**params, "id": row.id},
        )
    return row.id


def _save_memory(session, place_id: int, content_id: int, mem: dict, layer: str):
    session.execute(
        text("""
            INSERT INTO memories (
                place_id, content_id, timestamp_start, summary, tags,
                extraction_confidence, layer, happened_at, happened_precision,
                attribution, source_url, contrast_score, contrast_note
            )
            VALUES (
                :place_id, :content_id, :ts_start, :summary, :tags,
                :confidence, :layer, CAST(:happened_at AS DATE), :happened_precision,
                :attribution, :source_url, :contrast_score, :contrast_note
            )
        """),
        {
            "place_id": place_id,
            "content_id": content_id,
            # No default: the historical prompt never asks for an offset,
            # and a 0 here would be a fabricated second zero rather than a
            # missing one. api.gate.source_link reads the difference.
            "ts_start": mem.get("timestamp_start"),
            "summary": mem.get("summary", ""),
            # Filtered here and not trusted from the model: it emitted
            # five tags that were never on its own menu.
            "tags": clean_tags(mem.get("tags")),
            "confidence": mem.get("confidence", "medium"),
            "layer": layer,
            "happened_at": _happened_at(mem),
            "happened_precision": mem.get("happened_precision"),
            "attribution": mem.get("attribution"),
            "source_url": mem.get("source_url"),
            "contrast_score": _contrast_score(mem),
            "contrast_note": mem.get("contrast_note"),
        },
    )


def extract_all_pending():
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"extracted": 0, "failed": 0}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    extracted = 0
    failed = 0

    with get_session() as session:
        pending = session.execute(
            text(
                "SELECT c.id, c.title, t.segments, c.source_type, c.source_name "
                f"{PENDING_EXTRACTION}"
            )
        ).fetchall()

        logger.info(f"Found {len(pending)} videos pending extraction")

        for row in pending:
            content_id, title, segments_json, source_type, source_name = row
            logger.info(f"Extracting memories from: {title or content_id}")

            try:
                segments = (
                    segments_json if isinstance(segments_json, list) else json.loads(segments_json)
                )
                chunks = chunk_transcript(segments, CHUNK_MINUTES, CHUNK_OVERLAP_SECONDS)
                logger.info(f"  Split into {len(chunks)} chunks")

                all_memories = []
                for i, chunk in enumerate(chunks):
                    logger.info(f"  Processing chunk {i + 1}/{len(chunks)}")
                    try:
                        memories = extract_chunk_stored(
                            session,
                            client,
                            content_id,
                            i,
                            chunk,
                            prompt_for(source_type),
                            source_context(source_name, title),
                        )
                        all_memories.extend(memories)
                    except BillingError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "billing"}
                    except ModelUnusableError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "model"}

                merged = merge_nearby_memories(all_memories)
                filtered = filter_low_confidence(merged)

                logger.info(
                    f"  Found {len(all_memories)} raw, {len(merged)} merged, {len(filtered)} after filtering"
                )

                save_memories(session, content_id, filtered, layer_for(source_type))

                session.execute(
                    text("UPDATE content SET memories_extracted = TRUE WHERE id = :id"),
                    {"id": content_id},
                )
                # Per video, not per run: a crash on video 50 must not roll back
                # the 49 already paid for.
                session.commit()
                extracted += 1

            except TransientAPIError as e:
                # Left pending, not failed: the next run picks it up.
                logger.warning(f"  Transient API error, will retry next run: {e}")
                session.rollback()
                failed += 1

            except Exception as e:
                logger.error(f"  Extraction failed: {e}")
                session.rollback()
                session.execute(
                    text("UPDATE content SET extraction_failed = TRUE WHERE id = :id"),
                    {"id": content_id},
                )
                session.commit()
                failed += 1

    logger.info(f"Extraction complete: {extracted} extracted, {failed} failed")
    return {"extracted": extracted, "failed": failed}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extract_all_pending()
