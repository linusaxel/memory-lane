"""Extract location-based memories from transcripts using Claude."""

import hashlib
import json
import logging
import re

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

A memory is something that happened at a specific, named place, told so that a
stranger standing on that spot, reading it on a phone, gets something from
being exactly there. It is the whole product.

What qualifies:
- It already happened: a personal experience, an event, a mishap, something
  that stood here. An announcement is not a memory: "I'm playing the Fillmore on
  the 14th" is a ticket ad, and a tour date is the most common way a real venue
  sneaks in with nothing having happened there.
- The transcript names the place. A place you would have to guess is not one.
- The place is the point. Would the story lose anything pinned somewhere else?
  How someone got a nickname, how they met or joined something, where someone
  lives, who sponsors what, a trip mentioned in passing: these are stories
  about people, and fail.
- It is concrete. Hypotheticals, recommendations, general facts and "somewhere
  in Europe" are not memories.

Fields, in the order you fill them. The first three decide whether there is a
memory at all; answer them before you name a venue or write a word of summary.
- place_words: The words of the transcript that name where it happened, copied
  exactly as spoken, misspellings included ("ringkafen her"). Code checks these
  are in the transcript; a paraphrase is dropped.
- happened_there: One line - what happened at that place, and nowhere else.
- spot_test: "pass" if the place is the point, "fail" if the story would be the
  same pinned anywhere. Only "pass" is kept, so a "fail" costs nothing.
- venue: The place place_words names - a business, building, park, street or
  landmark - as you would say it to someone standing nearby, in today's
  spelling. If place_words gives no name ("an old bodega"), there is no venue
  and no memory; never take a name from the brief. Somewhere a walker could find on a map: an event or its name ("Trip
  Nørrebro", a pub crawl, a parade) is context for the summary, and the venue
  is the street or bar it happened at. Name an institution by its name, not by
  what it is ("the emergency room"). Two venues on one street get different
  names: a duplicate check keys on this field.
- locality: The city or town, always at that level - "Chelsea, Manhattan" is
  "New York City". The same venue must get the same locality every time; it is
  the other half of the duplicate check. Two venues sharing a locality is
  normal (Andaz West Hollywood and the Comedy Store are both in West Hollywood).
- region: State and/or country, whatever a mapmaker needs ("California, USA",
  "Denmark"). Null only if you do not know.
- country: ISO 3166 two-letter code ("US", "DK"). Null only if you do not know.
- address: Street and house number if the transcript names one, in today's
  spelling ("Blaagaardsgade 12" is "Blågårdsgade 12"). Null otherwise. A
  geocoder places the pin from this and the venue.
- lat, lng: Decimal degrees; only the fallback if the geocoder misses.
- timestamp_start: When the place is first mentioned, from the [timestamp] markers.
- summary: 2-3 sentences, 40-70 words and never more, past tense, written for a stranger who
  has never seen the video:
  * Lead with the most interesting thing about this spot.
  * Name people, with their nicknames where the transcript uses them ("Mark",
    "Maleren, the painter"). With no name, give a role - "a ski guide", "one
    regular". Every sentence has a subject.
  * The first time an event or series appears, say what it is in a few words
    of your own, from the brief - never just "the pub crawl". A walker reads
    several of these in a row, so vary the wording.
  * THE VIBE: what made it worth telling - the funny turn, the mishap.
  * If the transcript names something still visible from the spot - the trees
    out front, the empty lot, the stream under the street - put it in.
  * Tell what happened, not what was said: the reader does not know there is a
    recording, so no "he describes", "they mentioned", "the speaker", "the host".
  * One idea. Past 70 words you are summarising the conversation; cut the setup
    and keep what happened.
- tags: 1-5 from: {TAG_LIST}. Anything else is dropped.
- location_precision: exact (~50m), street (~200m), neighborhood (~1km), city
  (~10km). Only say "exact" when you know the building; if you are giving a
  city's coordinates, say "city". A false "exact" puts a pin on the wrong
  doorstep and claims 50m accuracy while doing it.
- confidence: high (clear place, definite event), medium (somewhat vague), low
  (uncertain).

<examples>
Real cases, shown with the deciding fields and the summary (the rest omitted).

<example>
{"place_words": "ringkafen her, den er fra 30'erne",
 "happened_there": "The bar sank when metro works broke into the stream beneath it.",
 "spot_test": "pass", "venue": "Ringkaféen",
 "summary": "Ringkaféen has poured beer here since the 1930s, and it sank into the ground when metro works broke through to the old Lygteå stream still running under the street. Cracks showed on its front until recently."}
</example>

<example>
{"place_words": "i Nørrebro Parken. Og ø der startede det",
 "happened_there": "Trip Nørrebro began here in 1996 with crates of beer.",
 "spot_test": "pass", "venue": "Nørrebroparken",
 "summary": "This is where Trip Nørrebro began, the yearly crawl that now winds through some 25 of Nørrebro's old brown bars. In 1996 it was just Maleren, a local painter, and a few friends with crates of beer and a beer relay on the grass."}
</example>

<example>
{"place_words": "Joe's downtown showcase, Sesh",
 "happened_there": "Mark played the showcase and called it the best room in North America.",
 "spot_test": "pass", "venue": "Sesh",
 "summary": "Mark Normand played Joe List's downtown showcase, Sesh, and came off stage calling it the best room in North America."}
</example>

<example>
{"place_words": "den her bar her, den aftterskibar",
 "happened_there": "An instructor shouted 'Kansas' across an après-ski bar and the nickname stuck.",
 "spot_test": "fail", "venue": "Levinho après-ski bar",
 "summary": "..."}
Fail: how Kansas got his name, and the bar is incidental - it would be the same
story pinned anywhere.
</example>

<example>
{"place_words": "Falls View Casino in Niagara on the 14th",
 "happened_there": "Nothing yet - it is a tour date.",
 "spot_test": "fail", "venue": "Fallsview Casino", "summary": "..."}
Fail: an upcoming show, so nothing has happened there.
</example>
</examples>

<uncertainty>
An empty list is a correct and common answer. Most of a conversation is not
about a place. If you are unsure whether something happened, or where, or to
whom, leave it out - a missing memory costs nothing, and an invented one is
indistinguishable from a real one once it is a pin on a map somebody walked to.
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
- place_words: The words of the text that name the place, copied exactly. Code
  checks they are in the text.
- happened_there: One line - what happened at that place.
- spot_test: "pass" if the event happened at the place, "fail" if the text only
  mentions it in passing. Only "pass" is kept.
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
                    "place_words": {"type": "string"},
                    "happened_there": {"type": "string"},
                    "spot_test": {"type": "string", "enum": ["pass", "fail"]},
                    "venue": {"type": "string"},
                    "locality": {"type": "string"},
                    "region": _NULLABLE_STRING,
                    "address": _NULLABLE_STRING,
                    "country": _NULLABLE_STRING,
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "timestamp_start": {"type": "number"},
                    "summary": {"type": "string"},
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
                    "place_words",
                    "happened_there",
                    "spot_test",
                    "venue",
                    "locality",
                    "region",
                    "lat",
                    "lng",
                    "summary",
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

# "Extract memories" presumed there were some. Most chunks have none.
USER_PROMPT_TEMPLATE = """List the place stories in this transcript chunk, if there
are any. Most chunks have none.

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


def source_context(source_name: str | None, title: str | None, brief: str = "") -> str:
    """The lead-in for a chunk, or nothing when we know nothing about the source."""
    lead = (
        SOURCE_CONTEXT_TEMPLATE.format(
            source=source_name,
            title=f', episode "{title}"' if title else "",
        )
        if source_name
        else ""
    )
    return lead + (BRIEF_TEMPLATE.format(brief=brief) if brief else "")


BRIEF_TEMPLATE = """<video_brief>
{brief}
</video_brief>
The brief covers the whole video, so use it to name the people and say what an
event is. It is context for writing, not a source of memories: every memory
comes from the transcript chunk below.

"""

BRIEF_PROMPT = """You write the brief that every later reader of one chunk of this
video's transcript gets, so that a story from minute 33 can say what was set up
in minute 1. About 120 words, in English, plain prose, facts only:

- What the video is: who made it, what happens, where.
- Every named event, series, route or group it refers to, with a one-line
  definition ("Trip Nørrebro: a yearly pub crawl through about 25 old bars on
  Nørrebro, Copenhagen, started in 1996").
- The people: names and nicknames, and who they are ("Maleren, the painter:
  the Nørrebro local who founded the crawl").

Leave out the individual places - bars, streets, stops. Each chunk names its
own, and a place listed here gets pinned to stories that happened elsewhere.

Only what the transcript says. Correct obvious caption misspellings of names
("Trip Nørbrong" is "Trip Nørrebro")."""

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {"brief": {"type": "string"}},
    "required": ["brief"],
    "additionalProperties": False,
}


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
# the filter. A candidate's items are ingested only to be screened by Haiku; one
# goes to Sonnet by `enqueue --video`, never in bulk.
PENDING_EXTRACTION = f"""
FROM content c
JOIN transcripts t ON c.id = t.content_id
WHERE c.memories_extracted = FALSE
  AND c.extraction_failed = FALSE
  AND c.transcript_fetched = TRUE
  AND {LONG_ENOUGH}
  AND NOT EXISTS (
      SELECT 1 FROM sources s
      WHERE s.id = c.source_id AND s.status IN ('candidate', 'rejected')
  )
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


def log_cache(response) -> None:
    """Both 0 means the prefix was under the model's minimum and nothing cached."""
    u = response.usage
    logger.info(
        f"{response.model}: cache read {u.cache_read_input_tokens}, "
        f"write {u.cache_creation_input_tokens}, uncached {u.input_tokens}"
    )


def _request(
    client: anthropic.Anthropic,
    system_prompt: str,
    user: str,
    schema: dict = MEMORY_SCHEMA,
    context: str = "",
) -> str | None:
    """The model's raw reply, or None for an error no retry will fix.

    `context` is what every chunk of one video shares (source, brief). It goes
    ahead of `user` with a second breakpoint, so from chunk two it is read at
    10% along with the system prompt.
    """
    content = (
        [
            {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": user},
        ]
        if context
        else user
    )
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            # The system prompt is ~1.2k tokens and is resent for every chunk -
            # 22 chunks a video, 55 videos. Cached reads cost 10% of input and a
            # write costs 1.25x, so this pays for itself on the second chunk.
            # The chunk is last, after this and the context, which is the
            # order caching requires.
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": content}],
            # Sonnet 5 thinks by default: billed output, eats max_tokens, and
            # puts a thinking block at content[0].
            thinking={"type": "disabled"},
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        log_cache(response)
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
    raw = _request(
        client, system_prompt, USER_PROMPT_TEMPLATE.format(chunk=chunk), MEMORY_SCHEMA, context
    )
    return [] if raw is None else grounded(parse_memories(raw), chunk)


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
    user = USER_PROMPT_TEMPLATE.format(chunk=chunk)
    raw = _stored_request(
        session, client, content_id, chunk_index, system_prompt, user, context=context
    )
    return [] if raw is None else grounded(parse_memories(raw), chunk)


def _stored_request(
    session, client, content_id, chunk_index, system_prompt, user, schema=MEMORY_SCHEMA, context=""
) -> str | None:
    key_schema = json.dumps(schema, sort_keys=True)
    # context + user is the message as it was before it was split in two, so
    # rows stored then still hit.
    key = _sha256(
        f"{content_id}\0{EXTRACTION_MODEL}\0{key_schema}\0{system_prompt}\0{context}{user}"
    )

    raw = session.execute(
        text("SELECT response FROM extraction_chunks WHERE request_hash = :k"), {"k": key}
    ).scalar()
    if raw is None:
        raw = _request(client, system_prompt, user, schema, context)
        if raw is None:
            return None
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
    return raw


def _squash(s: str) -> str:
    """Lowercase letters and digits only, timestamp markers gone: captions split
    and punctuate a name differently from how the model copies it."""
    return "".join(ch for ch in re.sub(r"\[[\d:.]+\]", "", s).lower() if ch.isalnum())


def grounded(memories: list[dict], chunk: str) -> list[dict]:
    """Only memories whose place_words are really in the chunk. The quote comes
    before the venue in the schema, so a venue the transcript never named - the
    invented ski bar - has nothing to quote. See
    docs/10-decisions.md#a-memory-is-decided-before-it-is-written."""
    text_ = _squash(chunk)
    return [m for m in memories if (q := _squash(m.get("place_words") or "")) and q in text_]


def video_brief(session, client, content_id: int, segments: list, source: str, title) -> str:
    """Who and what the whole video is about, for every chunk to write from.

    A chunk is four minutes; the pub crawl is introduced in minute one and
    Nørrebroparken comes up in minute 33, so without this the summary says
    "the pub crawl" to a reader who has no idea which. Stored like a chunk, at
    index -1, so it is paid for once per video.
    """
    transcript = " ".join((s.get("text") or "").strip() for s in segments)
    user = f"{source_context(source, title)}Transcript:\n\n{transcript}"
    raw = _stored_request(session, client, content_id, -1, BRIEF_PROMPT, user, BRIEF_SCHEMA)
    try:
        return json.loads(raw)["brief"] if raw else ""
    except (ValueError, KeyError):
        return ""


JUDGE_PROMPT = """You decide which of these short place stories are worth telling.
Each will be read by a stranger standing at the spot, on a phone. Judge every
candidate on its own merits; it is fine, and common, for most to fail.

For each candidate, write a one-line note first, then answer yes or no:
- only_here: Swap in another place's name. Does the story become false or
  pointless? Yes means the place is the point. Where someone lives or grew up
  is about them, not the place: no.
- breach: Does it depart from what normally happens at this kind of place or
  event? A crawl starting, a round bought, a drunk mishap is what normally
  happens: no.
- consequence: Did something change, or leave a lasting effect beyond the
  people there?
- visible_now: Can someone standing there see it or a trace of it - the
  building, the bridge, the water, the trees, the cracks, the empty plot?
- so_what: Can you say in one sentence why a stranger would care, without "it
  was fun", "it was wild" or "it's where they met"?
- stands_alone: Would a stranger understand every name and event in it?

<examples>
<example>
Ringkaféen: "Ringkaféen has poured beer since the 1930s, and sank into the
ground when metro works broke through to the old Lygteå stream still running
under the street. Cracks showed on its front until recently."
note: a bar undermined by a buried stream - the street hides a river.
only_here yes, breach yes, consequence yes, visible_now yes, so_what yes,
stands_alone yes
</example>
<example>
Under Hylden: "Under Hylden is named for the elder trees still in its front
garden, and dates from when new buildings had to include a pub for locals."
note: the name is on the trees you can see, and a forgotten law made the pub.
only_here yes, breach yes, consequence yes, visible_now yes, so_what yes,
stands_alone yes
</example>
<example>
Maskot: "Maskot is where Trip Nørrebro always starts. A few drinks go down here
before the group sets off."
note: a routine starting point; any bar could be it.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone yes
</example>
<example>
Saalbach: "Working as a ski guide, he met Maleren, who came for two weeks with
friends. That led to an invitation to join Trip Nørrebro."
note: backstory about how two people met; nothing happened at the place.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone yes
</example>
<example>
Mexibar: "One participant drank too much and was helped to throw up, then the
group carried on drinking at Mexibar."
note: a generic drunk mishap that could be any bar on any crawl.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone no
</example>
</examples>

Return one verdict per candidate, by its index."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "note": {"type": "string"},
                    **{
                        q: {"type": "boolean"}
                        for q in (
                            "only_here",
                            "breach",
                            "consequence",
                            "visible_now",
                            "so_what",
                            "stands_alone",
                        )
                    },
                },
                "required": [
                    "index",
                    "note",
                    "only_here",
                    "breach",
                    "consequence",
                    "visible_now",
                    "so_what",
                    "stands_alone",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

# Of breach, consequence, visible_now and so_what. Tuned against labelled
# stories from video 534; see docs/10-decisions.md#a-story-has-to-be-worth-telling.
TELLABLE_MIN = 2


def tellable(v: dict) -> bool:
    """The model answers the questions; the bar is here, in code."""
    rest = sum(bool(v.get(q)) for q in ("breach", "consequence", "visible_now", "so_what"))
    return bool(v.get("only_here")) and bool(v.get("stands_alone")) and rest >= TELLABLE_MIN


# The same story, judged twice, flipped: Under Hylden passed and then failed. A
# majority of three differently ordered passes also cancels position bias.
JUDGE_PASSES = 3


def _judge(session, client, content_id: int, memories: list[dict], order) -> dict | None:
    """{index: tellable} for one pass, or None if it failed or was unreadable.
    Indices are the originals whatever the order, so passes compare."""
    user = "\n\n".join(
        f"[{i}] {memories[i].get('venue')}: {memories[i].get('summary')}"
        + (
            f"\n(what happened there: {memories[i]['happened_there']})"
            if memories[i].get("happened_there")
            else ""
        )
        for i in order
    )
    try:
        raw = _stored_request(session, client, content_id, -2, JUDGE_PROMPT, user, JUDGE_SCHEMA)
        return {v["index"]: tellable(v) for v in json.loads(raw)["verdicts"]}
    except (TransientAPIError, TypeError, ValueError, KeyError):
        return None


def worth_telling(session, client, content_id: int, memories: list[dict]) -> list[dict]:
    """The memories a stranger would care about, judged together once per video.

    Per chunk, a routine stop never had to compete with a bar that sank into a
    stream. No brief on purpose: the judge reads each summary as a stranger
    would. A failed or unreadable judge keeps everything - it only filters, and
    must not empty a video. A tie drops: the point is fewer, better stories.
    """
    if not memories:
        return []
    n = len(memories)
    half = n // 2
    orders = [range(n), reversed(range(n)), [*range(half, n), *range(half)]][:JUDGE_PASSES]
    votes = [v for o in orders if (v := _judge(session, client, content_id, memories, list(o)))]
    if not votes:
        logger.warning(f"[content:{content_id}] tellability judge failed, keeping all")
        return memories

    def kept(i: int) -> bool:
        ballots = [v[i] for v in votes if i in v]
        return not ballots or 2 * sum(ballots) > len(ballots)

    return [m for i, m in enumerate(memories) if kept(i)]


def _venue_locality_key(mem: dict) -> tuple[str, str]:
    return (
        (mem.get("venue") or "").strip().lower(),
        (mem.get("locality") or "").strip().lower(),
    )


def _same_story(a: dict, b: dict, overlap: float = 0.3) -> bool:
    """Word overlap of the two summaries. A retelling shares its names and
    nouns; a different story at the same bar mostly does not."""
    words = [{w for w in re.findall(r"\w{4,}", (m.get("summary") or "").lower())} for m in (a, b)]
    union = words[0] | words[1]
    return not union or len(words[0] & words[1]) / len(union) >= overlap


def merge_nearby_memories(memories: list[dict]) -> list[dict]:
    """Merge retellings of one story at one place, anywhere in the video.

    Keyed on (venue, locality), W4-02 - the model no longer returns
    place_query. Folded the same way save_memories folds it, so a chunk
    boundary that capitalizes a name differently still merges. No time
    window: a speaker comes back to a story minutes later, and word overlap
    alone tells a retelling from a second story.
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

        # One story told twice: keep the first telling. Two different stories
        # at one bar stay two memories - gluing them made 110-word cards.
        if same_place and _same_story(current, mem):
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
    See docs/10-decisions.md#a-memory-is-decided-before-it-is-written."""
    return [
        m
        for m in memories
        if m.get("confidence", "low") in ("high", "medium")
        and m.get("location_precision") != "city"
        and m.get("spot_test") == "pass"
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
                brief = ""
                if (source_type or "video") == "video":
                    brief = video_brief(session, client, content_id, segments, source_name, title)

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
                            source_context(source_name, title, brief),
                        )
                        all_memories.extend(memories)
                    except BillingError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "billing"}
                    except ModelUnusableError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "model"}

                merged = merge_nearby_memories(all_memories)
                filtered = worth_telling(session, client, content_id, filter_low_confidence(merged))

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
