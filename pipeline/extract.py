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
    EXTRACTION_EFFORT,
    EXTRACTION_MODEL,
    LAUNCH_BBOX,
)
from pipeline.db import get_session
from pipeline.tags import TAGS
from pipeline.tags import clean as clean_tags
from pipeline.transcripts import LONG_ENOUGH, forget

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
- summary: in English whatever the source's language, past tense, written for a stranger who has never seen the video and
  is standing on the spot. As long as the story earns: 60-180 words. Past about
  90 words, split it into two paragraphs with a blank line. A small story stays
  small; never pad: past 90 words, every sentence adds a
  new detail of the same scene, not the years around it.
  * Open with the most interesting thing about this spot, in one sentence that
    would make someone stop walking.
  * Then the scene, in order: who was there, when, what happened, and the turn
    it took. Keep every concrete detail the transcript gives - names, numbers,
    prices, objects, what someone said or did - because the details are what
    make it worth reading on the spot.
  * Then what came of it. If the transcript names something still visible
    from the spot - the trees out front, the empty lot, the stream under the
    street - end on it: it is what the reader looks up at.
  * Name people, with their nicknames where the transcript uses them ("Mark",
    "Maleren, the painter"), and say who they are in a few words the first
    time. With no name, give a role - "a ski guide", "one regular". Every
    sentence has a subject.
  * The first time an event or series appears, say what it is in a few words
    of your own, from the brief - never just "the pub crawl". A walker reads
    several of these in a row, so vary the wording.
  * THE VIBE: what made it worth telling - the funny turn, the mishap.
  * Tell what happened, not what was said: the reader does not know there is a
    recording, so no "he describes", "notes that", "they mentioned",
    "the speaker", "the host".
  * Richness is the source's own details, never yours. Add no example, name,
    image, adjective or superlative it does not give: if it says "a great
    battle", do not name one; if it says "decorated", do not say "carved".
  * Every detail comes from the transcript or the brief. Length comes from the
    teller's details, never from general knowledge or atmosphere you add: if
    the transcript gives three facts, write three facts.
  * One story about one spot. A second story at the same spot is a second
    memory.
- quote: The best line about this moment, copied exactly as spoken, at most 25
  words, in the language it was said in. It is shown under the summary in the
  teller's own voice, so it is something someone said about what happened - a
  punch line, a feeling, a detail - not the words that name the place. Most
  good stories have one: look for it. Null when no line is worth reading on its
  own. Code checks it is in the transcript; a paraphrase is dropped.
- quote_by: Who said it, by name, from the transcript or the brief. Null if
  you cannot tell.
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
newspaper clippings, local archive entries, memoirs, venue and concert records,
registries.

A memory is something that HAPPENED at a SPECIFIC PHYSICAL LOCATION, told so
that a stranger standing on that spot, reading it on a phone, gets something
from being exactly there.

QUALIFIES:
- Events: "Bowie played this room in 1978, 400 capacity"
- Things that stood here: "The bakery was on that corner until '78"
- Documented incidents: "The tram derailed outside the pharmacy in March 1931"
- A thing still there with a life of its own: an odd, working or strange
  feature a stranger can look up and see, whose story has dated turns - made,
  stopped, restored, moved. "Gilded figures on this tower have told the weather
  since 1936; they stood still for decades and moved again in 2024." The turns
  are the events.

Does NOT qualify - reject these as firmly as you would reject a hypothetical:
- Static description: "this building was constructed in 1902", "four storeys, tiled roof"
  A building EXISTING is not something that HAPPENED. If you cannot name an event,
  there is no memory here. A tower, a spire or a carved portal is not a thing
  with a life of its own; a build date and a style are not turns in a story.
- Architectural or stylistic commentary: "a fine example of the national romantic style"
- Encyclopaedia facts: "Copenhagen is the capital of Denmark"
- A visit: "X visited the cathedral", "X dined at the palace". Someone famous
  passing through is not an event at the place unless something happened there.
- Anything you are inferring rather than reading. If the text does not say it
  happened, it did not happen. Do not fill gaps with plausible history.

This is third-party material, so write it straight. Do NOT use the chatty,
first-person register you would use for someone telling a story about themselves:
no invented emotions, no invented names, no "you can just picture it". Say what
happened, where, and when, and let the fact carry it.

Fields, in the order you fill them. The first three decide whether there is a
memory at all; answer them before you name a venue or write a word of summary.
- place_words: The words of the text that name the place, copied exactly,
  old spelling included. Code checks they are in the text; a paraphrase is dropped.
- happened_there: One line - what happened at that place, and nowhere else.
- spot_test: "pass" if the place is the point, "fail" if the story would be the
  same pinned anywhere, the text only mentions the place in passing, or it is a
  visit. Moved to another place of the same kind, would it tell the same? A
  story the place only holds - how a prisoner was treated in a cell, a dinner
  in a hall - fails however true; one this place's own feature, purpose or
  history is part of passes. Only "pass" is kept, so a "fail" costs nothing.
- venue: The proper name of the specific place - the business, building, park,
  street or landmark - as today's local map names it, in the local language,
  even when the text uses an old or foreign name ("Frauenkirche" is "Vor Frue
  Kirke", "Friedrichsberger Allee" is "Frederiksberg Allé"). Not a description
  and not the whole address. This is the field a duplicate check keys on, so
  two different venues must get different names even when they are close
  together. If the old name could be two places (Frederiksborg is a castle in
  Hillerød; Frederiksberg is in Copenhagen), set confidence low. It is a spot
  a walker can stand at: "the ramparts", "the city walls" or a district is no
  venue unless the text names the stretch.
- locality: The city or town the venue is in. Always this level - never a
  neighborhood or street, even when the source names one. Consistency matters
  more than specificity: the same venue named in two different records must
  produce the same locality both times.
- region: State/province and/or country, whichever disambiguates the
  locality. Null only if genuinely unknown.
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
- summary: in English whatever the source's language, past tense, written for a stranger who has never read the source
  and is standing on the spot. As long as the story earns: 60-180 words. Past
  about 90 words, split it into two paragraphs with a blank line. A small
  story stays small; never pad: past 90 words, every sentence adds a
  new detail of the same scene, not the years around it.
  * Open with the most surprising thing that happened on this spot, in one
    sentence that would make someone stop walking.
  * Then the scene, in order: who was there, when, what happened, and the turn
    it took. Keep every concrete detail the text gives - names, dates,
    numbers, objects, what someone said or did - because the details are what
    make it worth reading on the spot.
  * Then what came of it. If the text names something still visible from the
    spot - the avenue's trees, the stage, the stair - end on it: it is what
    the reader looks up at.
  * Give every named person a role the first time ("Rahbek, the critic",
    "Oehlenschläger, the poet, then a boy"). With no name, give a role.
  * Tell what happened, not what was written: no "the author describes", "he
    recalls", "the text says".
  * Richness is the source's own details, never yours. Add no example, name,
    image, adjective or superlative it does not give: if it says "a great
    battle", do not name one; if it says "decorated", do not say "carved".
  * Every detail comes from the text. Length comes from the source's details,
    never from general knowledge or atmosphere you add: if the text gives
    three facts, write three facts.
  * One scene. A second scene at the same spot is a second memory.
- quote: The best line about this moment, copied exactly from the text, old
  spelling included, at most 40 words, in its own language. It is shown under
  the summary in its own voice, so it is somebody's voice - words a person
  said or wrote, a memoirist's own line - not the words that name the place. A
  register or report stating the facts has no voice: null. So is a line that
  only says again what the summary says. Code checks it is in the text; a
  paraphrase is dropped.
- quote_by: Who wrote or said it, by name, if the text tells you. Null otherwise.
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

<examples>
Real cases, shown with the deciding fields and the summary (the rest omitted).

<example>
{"place_words": "in der Friedrichsberger Allee",
 "happened_there": "A grocer hanged himself from a willow and nobody would cut him down.",
 "spot_test": "pass", "venue": "Frederiksberg Allé", "locality": "Copenhagen",
 "summary": "A grocer hanged himself from a willow on this avenue, with a note nailed to a linden opposite blaming his unfaithful wife. Oehlenschläger, the poet, then a boy, was brought by his father to see the body, which nobody dared cut down until the district judge came and touched its shoulder."}
</example>

<example>
{"place_words": "In =Halberstadt= sah ich zum ersten Mal in meinem Leben ein katholisches Kloster",
 "happened_there": "Oehlenschläger toured a monastery and nearly missed his coach.",
 "spot_test": "fail", "venue": "Halberstadt", "summary": "..."}
Fail: a visit on a journey. Nothing happened to the place; the story would be
the same at any monastery on the road.
</example>

<example>
{"place_words": "Bei dem prächtigen Krönungsfeste war ich auf dem Schlosse Zuschauer",
 "happened_there": "Oehlenschläger watched the king and queen anointed.",
 "spot_test": "fail", "venue": "Frederiksborg Slot", "summary": "..."}
Fail: a spectator at a famous event. And "the castle in a lake" is
Frederiksborg in Hillerød, not Frederiksberg: never move a place to the
nearest similar name.
</example>

<example>
{"place_words": "in the citadel, where I lay that winter",
 "happened_there": "A captured officer was kept on bread and water and wrote letters never sent.",
 "spot_test": "fail", "venue": "Kastellet", "summary": "..."}
Fail: set inside. The hardship is the officer's; any fortress's cell would
tell it the same.
</example>
</examples>

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
                    "quote": _NULLABLE_STRING,
                    "quote_by": _NULLABLE_STRING,
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
    current = []  # (start, line)
    chunk_start_time = 0

    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()
        if not text:
            continue

        if start >= chunk_start_time + chunk_seconds:
            if current:
                chunks.append("\n".join(line for _, line in current))
            chunk_start_time = start - overlap_seconds
            # The overlap is repeated text, so a story told across a boundary
            # is whole in one chunk; merge_nearby_memories folds the retelling.
            current = [(s, line) for s, line in current if s >= chunk_start_time]

        current.append((start, f"[{start:.1f}] {text}"))

    if current:
        chunks.append("\n".join(line for _, line in current))

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
        f"write {u.cache_creation_input_tokens}, uncached {u.input_tokens}, "
        f"output {u.output_tokens}"
        + (
            f", searches {n}"
            if (n := getattr(getattr(u, "server_tool_use", None), "web_search_requests", 0))
            else ""
        )
    )


def _thinking(think: bool, model: str = EXTRACTION_MODEL) -> dict:
    """Thinking is billed output, eats max_tokens, and puts a block ahead of
    the text, so a call runs without it unless it asks. Sonnet 5.5 turns it
    off with between_tools, Sonnet 5 with disabled; Haiku 4.5 is off unless
    asked; Opus 5.5 and Fable can't, see _effort."""
    if think or _lowered(model) or model.startswith("claude-haiku"):
        return {}
    off = "disabled" if model == "claude-sonnet-5" else "between_tools"
    return {"thinking": {"type": off}}


def _lowered(model: str = EXTRACTION_MODEL) -> bool:
    return model.startswith(("claude-opus-5-5", "claude-fable-"))


def _effort(think: bool, model: str = EXTRACTION_MODEL) -> dict:
    return {"effort": EXTRACTION_EFFORT} if _lowered(model) and not think else {}


def _model_key(model: str = EXTRACTION_MODEL) -> str:
    """The model as a stored reply knows it: Opus at two efforts is two models."""
    return f"{model}@{EXTRACTION_EFFORT}" if _lowered(model) else model


CACHE = {"type": "ephemeral", "ttl": "1h"}


def _params(
    system_prompt: str,
    user: str,
    schema: dict,
    context: str,
    max_tokens: int,
    think: bool,
    model: str = EXTRACTION_MODEL,
) -> dict:
    """One request's body, as _request sends it and pipeline/batch.py batches it.

    `context` is what every chunk of one video shares (source, brief). It goes
    ahead of `user` with a second breakpoint, so from chunk two it is read at
    10% along with the system prompt. `think` lets the model think first: for
    a check where a miss costs more than the tokens.
    """
    content = (
        [
            {"type": "text", "text": context, "cache_control": CACHE},
            {"type": "text", "text": user},
        ]
        if context
        else user
    )
    return dict(
        model=model,
        max_tokens=max_tokens,
        # The system prompt is ~3.8k tokens with its schema and is resent for
        # every chunk. A read costs 10% of input; an hour's write costs 2x, so
        # it pays for itself on the third chunk, and outlives a batch, which
        # can take longer than the default five minutes.
        # The chunk is last, after this and the context, which is the
        # order caching requires.
        system=[{"type": "text", "text": system_prompt, "cache_control": CACHE}],
        messages=[{"role": "user", "content": content}],
        **_thinking(think, model),
        output_config={"format": {"type": "json_schema", "schema": schema}} | _effort(think, model),
    )


def reply_text(response) -> str | None:
    """The reply's text, or None for one cut at max_tokens: a cut reply is no
    JSON, and stored it would be read back for ever."""
    if response.stop_reason == "max_tokens":
        logger.warning(f"Reply cut at max_tokens={response.usage.output_tokens}; not used")
        return None
    return next(b.text for b in response.content if b.type == "text")


def _request(
    client: anthropic.Anthropic,
    system_prompt: str,
    user: str,
    schema: dict = MEMORY_SCHEMA,
    context: str = "",
    max_tokens: int = 2000,
    think: bool = False,
    model: str = EXTRACTION_MODEL,
) -> str | None:
    """The model's raw reply, or None for an error no retry will fix."""
    try:
        response = client.messages.create(
            **_params(system_prompt, user, schema, context, max_tokens, think, model)
        )
        log_cache(response)
        return reply_text(response)

    except anthropic.BadRequestError as e:
        if is_billing_error(e):
            raise BillingError(
                "API credit balance too low. Please add credits at console.anthropic.com"
            ) from e
        # A rejected schema or parameter is rejected for every chunk, so it
        # stops the run rather than emptying the backlog one [] at a time.
        raise ModelUnusableError(f"EXTRACTION_MODEL={model!r} rejected: {e}") from e
    except (
        anthropic.NotFoundError,
        anthropic.AuthenticationError,
        anthropic.PermissionDeniedError,
    ) as e:
        raise ModelUnusableError(f"EXTRACTION_MODEL={model!r} is not usable: {e}") from e
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
    # Several stories of up to 180 words each; a cut reply is no JSON at all.
    max_tokens: int = 8000,
) -> list[dict]:
    """extract_memories_from_chunk, paid for once per exact request.

    Keyed on video + model + schema + system prompt + user message, so a
    prompt edit misses and a retry, a re-merge or a crashed run hits.
    Committed as soon as it lands: the reply is the expensive part and must
    outlive whatever fails next.
    """
    user = USER_PROMPT_TEMPLATE.format(chunk=chunk)
    raw = _stored_request(
        session,
        client,
        content_id,
        chunk_index,
        system_prompt,
        user,
        context=context,
        max_tokens=max_tokens,
    )
    if raw is None:
        return []
    # The chunk rides along for check_all, which runs only on what the judge keeps.
    return [
        m | {"chunk": chunk, "chunk_index": chunk_index}
        for m in grounded(parse_memories(raw), chunk)
    ]


UNSUPPORTED_PROMPT = """The text is a source passage, with what is known about its
source, then a story written from it for someone standing at the place. List
every claim the story makes that the passage and the source do not support: a
fact, name, role, number, date, event, object, image, adjective or superlative
the story adds, or gives differently. Only additions and contradictions:
leaving something out is fine, and so are translation, tense, wording, order
and a plain inference (a bar is in the city the passage is about). Each is a
`fact` (something a reader would repeat as true) or `colour` (an image or a
flourish). Name each claim by the fewest words that carry it, never a span
that also holds what the source does say: in "fell fighting for Denmark's
freedom under the occupation", where the source has only the fight for
freedom, the claim is "under the occupation". An empty list means the story
is faithful."""

UNSUPPORTED_SCHEMA = {
    "type": "object",
    "properties": {
        "unsupported": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "kind": {"type": "string", "enum": ["fact", "colour"]},
                },
                "required": ["claim", "kind"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["unsupported"],
    "additionalProperties": False,
}

TRIM_PROMPT = """The text is a story told at a place, then claims in it that its source
does not support. Remove exactly those claims and nothing else: keep every
other sentence and detail word for word, in its order and paragraphs. Cut the
claim, not the sentence, where the sentence still stands without it, and cut
the fewest words that remove it. Return the story itself, never a description
of it."""

TRIM_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def unsupported(
    session, client, content_id, chunk_index, chunk, context, summary, model=EXTRACTION_MODEL
):
    """What the summary says that its chunk doesn't, as [{claim, kind}], or None
    for no usable answer. It thinks first: a miss here is an invention on a pin."""
    user = f"Passage:\n\n{chunk}\n\nStory:\n\n{summary}"
    raw = _stored_request(
        session,
        client,
        content_id,
        chunk_index,
        UNSUPPORTED_PROMPT,
        user,
        UNSUPPORTED_SCHEMA,
        context,
        max_tokens=16000,
        think=True,
        model=model,
    )
    try:
        return json.loads(raw)["unsupported"] if raw else None
    except (
        ValueError,
        KeyError,
    ):
        return None


def check_all(session, client, content_id, context, memories: list[dict]) -> list[dict]:
    """Each kept memory checked against the chunk it came from, the chunk let go.
    After the filters and the judge: a thinking call on a memory they drop is
    money spent on nothing."""
    kept = []
    for m in memories:
        if (chunk := m.pop("chunk", None)) is not None:
            m = checked(session, client, content_id, m["chunk_index"], chunk, context, m)
        kept.append(m)
    return kept


def checked(session, client, content_id, chunk_index, chunk, context, memory: dict) -> dict:
    """The memory with what its chunk doesn't say cut from the summary.

    A longer summary is where invention creeps in, and a prompt rule against
    it was not enough (docs/04, *A longer card*). Only a memory that passed
    its spot test is checked, the rest are dropped anyway, and only what the
    check names is cut: a rewrite of the whole summary cut its richness too.
    Both calls are stored like a chunk, so a rerun is free.
    """
    if memory.get("spot_test") != "pass" or not memory.get("summary"):
        return memory
    claims = unsupported(
        session, client, content_id, chunk_index, chunk, context, memory["summary"]
    )
    if not claims:
        return memory
    listed = "\n".join(f"- {c['claim']}" for c in claims)
    user = f"Story:\n\n{memory['summary']}\n\nUnsupported:\n{listed}"
    raw = _stored_request(session, client, content_id, chunk_index, TRIM_PROMPT, user, TRIM_SCHEMA)
    try:
        summary = json.loads(raw)["summary"].strip() if raw else ""
    except (
        ValueError,
        KeyError,
    ):
        summary = ""
    return {**memory, "summary": summary} if summary else memory


class Collect:
    """A batch pass: model calls with no stored reply, held back instead of
    sent (pipeline/batch.py). Only a content's first stage to miss is
    collected, so a stage is never paid for on what an earlier one, still
    unanswered, would have dropped."""

    def __init__(self):
        self.requests: dict[str, dict] = {}  # request_hash: {params, content_id, ...}
        self.stage: dict[int, str] = {}  # content_id: the system prompt it waits on


#: Set by pipeline/batch.py for one pass; None sends every call as it comes.
COLLECT: Collect | None = None


def store(
    session, key, content_id, chunk_index, system_prompt_hash, raw, model=EXTRACTION_MODEL
) -> None:
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
            "prompt_hash": system_prompt_hash,
            "model": _model_key(model),
            "response": raw,
        },
    )
    session.commit()


def _stored_request(
    session,
    client,
    content_id,
    chunk_index,
    system_prompt,
    user,
    schema=MEMORY_SCHEMA,
    context="",
    max_tokens=2000,
    think=False,
    model=EXTRACTION_MODEL,
) -> str | None:
    key_schema = json.dumps(schema, sort_keys=True)
    # context + user is the message as it was before it was split in two, so
    # rows stored then still hit.
    key = _sha256(
        f"{content_id}\0{_model_key(model)}\0{key_schema}\0{system_prompt}\0{context}{user}"
    )

    raw = session.execute(
        text("SELECT response FROM extraction_chunks WHERE request_hash = :k"), {"k": key}
    ).scalar()
    if raw is not None:
        return raw
    if COLLECT is not None:
        if COLLECT.stage.setdefault(content_id, system_prompt) == system_prompt:
            COLLECT.requests[key] = {
                "params": _params(system_prompt, user, schema, context, max_tokens, think, model),
                "content_id": content_id,
                "chunk_index": chunk_index,
                "prompt_hash": _sha256(system_prompt),
                "stage": stage(system_prompt),
            }
        return None
    raw = _request(client, system_prompt, user, schema, context, max_tokens, think, model)
    if raw is not None:
        store(session, key, content_id, chunk_index, _sha256(system_prompt), raw, model)
    return raw


def stage(system_prompt: str) -> str:
    """The pipeline stage a system prompt belongs to, for log lines."""
    return {
        BRIEF_PROMPT: "brief",
        UNSUPPORTED_PROMPT: "check",
        TRIM_PROMPT: "trim",
        JUDGE_PROMPT: "judge",
        SAME_VENUE_PROMPT: "same venue",
        SAME_EVENT_PROMPT: "same event",
    }.get(system_prompt, "extract")


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
    kept = [m for m in memories if (q := _squash(m.get("place_words") or "")) and q in text_]
    # A quote is held to the same rule, but losing it costs only the quote.
    for m in kept:
        if not ((q := _squash(m.get("quote") or "")) and q in text_):
            m["quote"] = m["quote_by"] = None
    return kept


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
    return brief_from(raw) if raw else ""


def brief_from(raw: str) -> str:
    """The brief, without the spiral a curly quote starts. The model sometimes
    ends it with ” instead of ", which leaves it inside the JSON string, and it
    keeps trying to close: `”}} 434 words? no.` or `”}]}}}}` up to max_tokens,
    unterminated. What it meant to write ends at the ”."""
    head, cut, _ = raw.partition("”}")
    try:
        return json.loads(head + '"}' if cut else raw)["brief"]
    except (ValueError, KeyError):
        logger.warning(f"Unusable brief, chunks go without one: {raw[:200]}")
        return ""


JUDGE_PROMPT = """You decide which of these short place stories are worth telling.
Each will be read by a stranger standing at the spot, on a phone. Judge every
candidate on its own merits; it is fine, and common, for most to fail.

For each candidate, write a one-line note first, then answer yes or no:
- only_here: Move it to another place of the same kind - another prison, hall,
  bar or street. Does it lose something? Yes when this place's own feature,
  purpose or history is part of it: the national stage on the day it stood
  empty, the willow on this avenue, the plaque on this wall. No when the place
  only holds the people - how a prisoner was treated in a cell, a dinner in a
  hall, a talk in a room - however true. Where someone lives or grew up is
  about them, not the place: no.
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
- glad_to_know: Would a stranger standing here say "huh!" and want to tell
  someone? That takes a surprise, stakes, a human moment, or something they
  can see from here. A bare record - a name and a date, that someone died, was
  born, lived or worked here - is no, however true; so is scenery, a crowd
  cheering, or a building existing.

<examples>
<example>
Ringkaféen: "Ringkaféen has poured beer since the 1930s, and sank into the
ground when metro works broke through to the old Lygteå stream still running
under the street. Cracks showed on its front until recently."
note: a bar undermined by a buried stream - the street hides a river.
only_here yes, breach yes, consequence yes, visible_now yes, so_what yes,
stands_alone yes, glad_to_know yes
</example>
<example>
Under Hylden: "Under Hylden is named for the elder trees still in its front
garden, and dates from when new buildings had to include a pub for locals."
note: the name is on the trees you can see, and a forgotten law made the pub.
only_here yes, breach yes, consequence yes, visible_now yes, so_what yes,
stands_alone yes, glad_to_know yes
</example>
<example>
Maskot: "Maskot is where Trip Nørrebro always starts. A few drinks go down here
before the group sets off."
note: a routine starting point; any bar could be it.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone yes, glad_to_know no
</example>
<example>
Kongens Nytorv: "The king's statue in the middle of the square was cast in lead
in 1688 for want of bronze. It sagged under its own weight, was propped up
with iron for centuries, and was finally recast in bronze in 1946."
note: the thing in front of you nearly collapsed - you look up at it.
only_here yes, breach yes, consequence yes, visible_now yes, so_what yes,
stands_alone yes, glad_to_know yes
</example>
<example>
Kastellet: "A captured officer was held in a cell here through one winter,
given bread and water, and wrote letters to his wife that were never sent."
note: a hard captivity, but any fortress's cell would tell it the same.
only_here no, breach no, consequence no, visible_now no, so_what yes,
stands_alone yes, glad_to_know yes
</example>
<example>
Saalbach: "Working as a ski guide, he met Maleren, who came for two weeks with
friends. That led to an invitation to join Trip Nørrebro."
note: backstory about how two people met; nothing happened at the place.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone yes, glad_to_know no
</example>
<example>
Mexibar: "One participant drank too much and was helped to throw up, then the
group carried on drinking at Mexibar."
note: a generic drunk mishap that could be any bar on any crawl.
only_here no, breach no, consequence no, visible_now no, so_what no,
stands_alone no, glad_to_know no
</example>
<example>
Mindesmærke for Ejler Haubirk: "First mate Ejler Haubirk fell on this spot on
20 October 1944, in Denmark's fight for freedom."
note: a true death on this spot, but only a name and a date: nothing a
stranger learns or feels.
only_here yes, breach yes, consequence no, visible_now yes, so_what no,
stands_alone yes, glad_to_know no
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
                            "glad_to_know",
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
                    "glad_to_know",
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
    gates = ("only_here", "stands_alone", "glad_to_know")
    return all(v.get(q) for q in gates) and rest >= TELLABLE_MIN


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
        # One verdict per memory: a long video's judge outgrows 2000 tokens.
        raw = _stored_request(
            session, client, content_id, -2, JUDGE_PROMPT, user, JUDGE_SCHEMA, max_tokens=8000
        )
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


SAME_VENUE_PROMPT = """Each line is a place named in one video, with a story
told there. Chunks of the video were read separately, so one real place may be
named several ways: in two languages, by its owner, by its street.

Say which lines name the same real place as another line. Only when the stories
make it clear: two bars on the same street are two places. For each duplicate,
give its index and the index of the line to keep - the name a walker would find
on a map. Most videos have none; an empty list is the usual answer."""

SAME_VENUE_SCHEMA = {
    "type": "object",
    "properties": {
        "same": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"index": {"type": "integer"}, "as": {"type": "integer"}},
                "required": ["index", "as"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["same"],
    "additionalProperties": False,
}


def one_name_per_venue(session, client, content_id: int, memories: list[dict]) -> list[dict]:
    """One venue named three ways in one video is one place, not three pins:
    save_memories matches names exactly. A failed reply changes nothing. See
    docs/10-decisions.md#one-venue-one-name-per-video."""
    first = {}
    for m in memories:
        first.setdefault(_venue_locality_key(m), m)
    keys = list(first)
    if len(keys) < 2:
        return memories
    user = "\n".join(
        f"[{i}] {first[k].get('venue')}, {first[k].get('locality')}: {first[k].get('summary')}"
        for i, k in enumerate(keys)
    )
    try:
        raw = _stored_request(
            session,
            client,
            content_id,
            -3,
            SAME_VENUE_PROMPT,
            user,
            SAME_VENUE_SCHEMA,
            max_tokens=8000,
        )
        pairs = json.loads(raw)["same"]
    except (TransientAPIError, TypeError, ValueError, KeyError):
        return memories
    canonical = {}
    for p in pairs:
        i, j = p.get("index"), p.get("as")
        if i != j and all(isinstance(x, int) and 0 <= x < len(keys) for x in (i, j)):
            canonical[keys[i]] = first[keys[j]]
    out = []
    for m in memories:
        keep = canonical.get(_venue_locality_key(m))
        out.append(m | {"venue": keep["venue"], "locality": keep["locality"]} if keep else m)
    return out


def _venue_locality_key(mem: dict) -> tuple[str, str]:
    return (
        (mem.get("venue") or "").strip().lower(),
        (mem.get("locality") or "").strip().lower(),
    )


def _same_story(a: dict, b: dict, overlap: float = 0.2) -> bool:
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


SAME_EVENT_PROMPT = """The first story is new. The numbered ones are already saved
near the same spot, from this source or another.

Does the new story tell the same happening as one of them - told again, in
other words, from another source or with other details? Another story at the
same place, or another moment in the same person's life, is not the same
happening: a funeral and a childhood on one street are two.

Give the index of the one it repeats, or -1 if none. If it repeats one, say
whether the new telling is the better one for a stranger standing there: a
scene rather than a summary, more specific, more vivid."""

SAME_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "same_as": {"type": "integer"},
        "new_is_better": {"type": "boolean"},
    },
    "required": ["reason", "same_as", "new_is_better"],
    "additionalProperties": False,
}

# A retelling is pinned where its source put it; two sources put one sabotage
# 20 m apart. See docs/10-decisions.md#a-memory-is-not-saved-twice.
DUP_RADIUS_METERS = 150


def same_event(
    session, client, content_id: int, new: dict, neighbours: list[dict]
) -> tuple[int, bool] | None:
    """(index of the neighbour `new` retells, whether `new` tells it better),
    or None. Stored like the judge, at chunk_index -4, so a rerun answers the
    same. A failed or unreadable reply is None."""
    lines = "\n\n".join(
        f"[{i}] {n.get('venue')}: {n.get('summary')}" for i, n in enumerate(neighbours)
    )
    user = f"New: {new.get('venue')}: {new.get('summary')}\n\n{lines}"
    raw = _stored_request(
        session, client, content_id, -4, SAME_EVENT_PROMPT, user, SAME_EVENT_SCHEMA
    )
    try:
        reply = json.loads(raw)
        i, better = reply["same_as"], bool(reply.get("new_is_better"))
    except (TypeError, ValueError, KeyError):
        return None
    return (i, better) if isinstance(i, int) and 0 <= i < len(neighbours) else None


def nearby_memories(session, lat: float, lng: float, before: int | None = None) -> list:
    """Visible memories within DUP_RADIUS_METERS, nearest first, at most 10."""
    return session.execute(
        text("""
            SELECT m.id, p.name AS venue, m.summary
            FROM memories m JOIN places p ON p.id = m.place_id
            WHERE NOT m.hidden
              AND (CAST(:before AS int) IS NULL OR m.id < :before)
              AND ST_DWithin(
                  p.coordinates, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r
              )
            ORDER BY p.coordinates <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            LIMIT 10
        """),
        {"lat": lat, "lng": lng, "r": DUP_RADIUS_METERS, "before": before},
    ).fetchall()


def _told_already(session, client, content_id: int, mem: dict, lat: float, lng: float) -> bool:
    """True if an earlier memory already tells this better. A better telling
    is saved and hides the earlier one. It only filters: a failed check saves."""
    near = nearby_memories(session, lat, lng)
    if not near:
        return False
    try:
        hit = same_event(session, client, content_id, mem, [n._asdict() for n in near])
    except Exception as e:
        logger.warning(f"[content:{content_id}] same-event check failed, saving: {e}")
        return False
    if hit is None:
        return False
    i, better = hit
    if better:
        session.execute(
            text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": near[i].id}
        )
        logger.info(f"[content:{content_id}] tells memory {near[i].id} better, hiding it")
        return False
    logger.info(f"[content:{content_id}] retells memory {near[i].id}: {mem.get('venue')}")
    return True


def place_of(mem: dict) -> tuple[float, float, int, str] | None:
    """What the geocoders make of a memory's place, or None: it stays the model's guess."""
    lat, lng = mem.get("lat"), mem.get("lng")
    happened = _happened_at(mem)
    return geocode.place(
        (mem.get("address") or "").strip() or None,
        geocode.unbracket(mem.get("venue") or "") or None,
        (mem.get("locality") or "").strip() or None,
        (mem.get("country") or "").strip() or None,
        (lat, lng) if lat is not None and lng is not None else None,
        int(happened[:4]) if happened else None,
    )


def save_memories(
    session, content_id: int, memories: list[dict], layer: str = "historical", client=None
):
    """With a client, a memory that retells one already saved nearby is dropped."""
    for mem in memories:
        lat = mem.get("lat")
        lng = mem.get("lng")
        has_coords = lat is not None and lng is not None

        # The model brackets context onto a name: "Bopa Bar (Nørrebro pub crawl)".
        venue = geocode.unbracket(mem.get("venue") or "") or None
        locality = (mem.get("locality") or "").strip() or None
        region = (mem.get("region") or "").strip() or None
        structured = bool(venue and locality)
        if venue and locality and venue.casefold() == locality.casefold():
            # The city is no spot: Wollstonecraft's execution pinned on "Copenhagen".
            logger.info(f"[content:{content_id}] the venue is the city: {venue}")
            continue

        precision = precision_to_meters(mem.get("location_precision", "street"))
        status = "llm"
        hit = place_of(mem)
        if hit:
            lat, lng, precision, status = hit
            has_coords = True

        if has_coords and LAUNCH_BBOX and not _in_box(lat, lng, LAUNCH_BBOX):
            logger.info(f"[content:{content_id}] outside the launch area: {venue} ({lat}, {lng})")
            continue

        if client and has_coords:
            at = _landing(session, venue, lat, lng)
            if _told_already(session, client, content_id, mem, *at):
                continue

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
        place_id = place_id or _same_item(session, params)
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


def _in_box(lat: float, lng: float, box: tuple) -> bool:
    south, west, north, east = box
    return south <= lat <= north and west <= lng <= east


def _landing(session, venue: str | None, lat: float, lng: float) -> tuple[float, float]:
    """Where the memory will be pinned, so the retelling check looks there: the
    nearest place of the same venue within 10 km, as _same_venue_nearby snaps
    it, or its own point. The model put Kasino's King story 1 km from Kasino."""
    row = (
        session.execute(
            text("""
                SELECT ST_Y(coordinates::geometry) AS lat, ST_X(coordinates::geometry) AS lng
                FROM places
                WHERE lower(btrim(venue)) = lower(btrim(:venue)) AND coordinates IS NOT NULL
                  AND ST_DWithin(
                      coordinates, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 10000
                  )
                ORDER BY ST_Distance(
                    coordinates, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                )
                LIMIT 1
            """),
            {"venue": venue, "lat": lat, "lng": lng},
        ).fetchone()
        if venue
        else None
    )
    return (row.lat, row.lng) if row else (lat, lng)


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


def _same_item(session, params: dict) -> int | None:
    """A place already on this Wikidata point under another name: "Blue Tower"
    and "Blåtårn". The point is the item's own, so two names on it are one
    place. Not for an address point: two bars can share a building."""
    if params["status"] != "wikidata":
        return None
    return session.execute(
        text("""
            SELECT id FROM places
            WHERE geocode_status = 'wikidata'
              AND ST_DWithin(
                  coordinates, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 10
              )
            LIMIT 1
        """),
        params,
    ).scalar()


# The prompt says null when it doesn't know what is there now, and it writes
# "current use unknown" or "likely redeveloped" anyway (25 of 85 notes,
# 2026-10-04). A guess under "Then and now" reads as a fact.
HEDGE = re.compile(
    r"\b(unknown|unclear|uncertain|likely|probably|perhaps|presumably|may have|might)\b", re.I
)


def sure(note: str | None) -> str | None:
    return None if not note or HEDGE.search(note) else note


def _save_memory(session, place_id: int, content_id: int, mem: dict, layer: str):
    session.execute(
        text("""
            INSERT INTO memories (
                place_id, content_id, timestamp_start, summary, tags,
                extraction_confidence, layer, happened_at, happened_precision,
                attribution, source_url, contrast_score, contrast_note,
                quote, quote_by
            )
            VALUES (
                :place_id, :content_id, :ts_start, :summary, :tags,
                :confidence, :layer, CAST(:happened_at AS DATE), :happened_precision,
                :attribution, :source_url, :contrast_score, :contrast_note,
                :quote, :quote_by
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
            "contrast_note": sure(mem.get("contrast_note")),
            "quote": mem.get("quote"),
            "quote_by": mem.get("quote_by"),
        },
    )


def extract_all_pending(content_ids: list[int] | None = None):
    """Every pending content, or only `content_ids` of them, one after another."""
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
                f"{PENDING_EXTRACTION} AND (CAST(:ids AS int[]) IS NULL OR c.id = ANY(:ids))"
            ),
            {"ids": content_ids},
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
                filtered = one_name_per_venue(session, client, content_id, filtered)
                filtered = check_all(
                    session, client, content_id, source_context(source_name, title, brief), filtered
                )

                logger.info(
                    f"  Found {len(all_memories)} raw, {len(merged)} merged, {len(filtered)} after filtering"
                )

                save_memories(session, content_id, filtered, layer_for(source_type), client)
                if COLLECT is not None and content_id in COLLECT.stage:
                    # A stage waits on the batch: nothing kept, the next pass gets further.
                    session.rollback()
                    continue

                session.execute(
                    text("UPDATE content SET memories_extracted = TRUE WHERE id = :id"),
                    {"id": content_id},
                )
                forget(session, content_id)
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
