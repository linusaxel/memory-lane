"""Extract location-based memories from transcripts using Claude."""

import json
import logging

import anthropic
from sqlalchemy import text

from pipeline.config import (
    ANTHROPIC_API_KEY,
    CHUNK_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    EXTRACTION_MODEL,
)
from pipeline.db import get_session

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

For each memory, extract:
- place_name: Human-readable name (e.g., "Cafe de Flore, Paris")
- place_query: Search string for geocoding (e.g., "Cafe de Flore Saint-Germain Paris France")
- lat: Latitude estimate (decimal degrees, e.g., 48.8566)
- lng: Longitude estimate (decimal degrees, e.g., 2.3522)
- timestamp_start: When place is first mentioned (from [timestamp] markers in input)
- summary: 2-4 sentences capturing the STORY, not just facts. Include:
  * WHO: Use names when mentioned (e.g., "Mark and Joe" not "the hosts")
  * WHAT HAPPENED: Specific anecdotes, funny moments, mishaps
  * THE VIBE: Emotions, reactions, humor, what made it memorable
  * Keep it conversational and human, like you're telling a friend
  Bad: "He performed comedy at a theater in Boulder."
  Good: "Mark did three sold-out shows at this old 1909 theater in Boulder, joking about how the marquee had survived prohibition, the depression, and now had to endure his act."
- tags: 1-5 from: food, travel, history, culture, adventure, romance, nightlife, nature, art, music, sports, business, personal
- location_precision: exact (~50m), street (~200m), neighborhood (~1km), city (~10km)
  BE HONEST ABOUT THIS. If you are returning the coordinates of a city because you
  do not know the address, say "city". Only say "exact" when you know the specific
  building or street address. A wrong "exact" is worse than an honest "city": it
  puts a pin on the wrong doorstep and claims 50m accuracy while doing it.
- confidence: high (clear location + definite event), medium (somewhat vague), low (uncertain)

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
- place_name: Human-readable name ("Vega, Vesterbro")
- place_query: Search string for geocoding ("Vega Enghavevej Vesterbro Copenhagen Denmark")
- lat / lng: Decimal degrees
- happened_at: ISO date of the EVENT - "1978-06-17", "1978-06", or "1978". Null if
  the text gives no date. This is when it happened, not when it was written about.
- happened_precision: day | month | year | decade - how much of happened_at to trust
- summary: 2-4 sentences. What happened, who was involved if named, what the place
  was at the time. Concrete and sourced, not atmospheric.
- attribution: the source as it should be credited on a card, if the text names one
- tags: 1-5 from: food, travel, history, culture, adventure, romance, nightlife,
  nature, art, music, sports, business, personal
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


USER_PROMPT_TEMPLATE = """Extract memories from this transcript chunk:

{chunk}

Return only valid JSON."""


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


PENDING_EXTRACTION = """
FROM content c
JOIN transcripts t ON c.id = t.content_id
WHERE c.memories_extracted = FALSE
  AND c.extraction_failed = FALSE
  AND c.transcript_fetched = TRUE
"""


class BillingError(Exception):
    """Raised when API call fails due to billing issues."""

    pass


def extract_memories_from_chunk(
    client: anthropic.Anthropic, chunk: str, system_prompt: str = SYSTEM_PROMPT
) -> list[dict]:
    """Send chunk to Claude and extract memories."""
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(chunk=chunk)}],
        )

        content = response.content[0].text

        try:
            data = json.loads(content)
            return data.get("memories", [])
        except json.JSONDecodeError:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                data = json.loads(json_str)
                return data.get("memories", [])
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                data = json.loads(json_str)
                return data.get("memories", [])
            logger.warning(f"Failed to parse JSON from response: {content[:200]}")
            return []

    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            raise BillingError(
                "API credit balance too low. Please add credits at console.anthropic.com"
            ) from e
        logger.error(f"Error calling Claude API: {e}")
        return []
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        return []


def merge_nearby_memories(memories: list[dict], threshold_seconds: float = 60) -> list[dict]:
    """Merge memories for the same place within threshold_seconds."""
    if not memories:
        return []

    sorted_memories = sorted(
        memories, key=lambda m: (m.get("place_query", ""), m.get("timestamp_start", 0))
    )

    merged = []
    current = None

    for mem in sorted_memories:
        if current is None:
            current = mem.copy()
            continue

        same_place = current.get("place_query", "").lower() == mem.get("place_query", "").lower()
        time_diff = abs(mem.get("timestamp_start", 0) - current.get("timestamp_start", 0))

        if same_place and time_diff <= threshold_seconds:
            # Merge: extend time range, combine summaries, dedupe tags
            current["timestamp_end"] = max(
                current.get("timestamp_end", current.get("timestamp_start", 0)),
                mem.get("timestamp_start", 0),
            )
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
    return [m for m in memories if m.get("confidence", "low") in ("high", "medium")]


def prompt_for(source_type: str | None) -> str:
    """Archival text and someone telling a story need different instructions.

    The personal prompt asks for WHO and THE VIBE, which invites invention when
    pointed at a newspaper clipping - exactly what must not happen to third-party
    material.
    """
    return SYSTEM_PROMPT if (source_type or "video") == "video" else HISTORICAL_SYSTEM_PROMPT


def layer_for(source_type: str | None) -> str:
    """Everything ingested so far is public, permanent content. Friend and
    stranger memories arrive through a write path that does not exist yet."""
    return "historical"


def precision_to_meters(precision: str) -> int:
    mapping = {"exact": 50, "street": 200, "neighborhood": 1000, "city": 10000}
    return mapping.get(precision, 200)


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
        # Kept exploded with a trailing comma on purpose: `ruff format` in this
        # repo rewrites a single-line `except (A, B):` into `except A, B:`,
        # which is Python 2 and does not compile. The magic trailing comma stops
        # it collapsing the tuple back onto one line. See TODO.md.
        logger.warning("Unusable contrast_score %r, storing null", raw)
        return None


def save_memories(session, content_id: int, memories: list[dict], layer: str = "historical"):
    for mem in memories:
        lat = mem.get("lat")
        lng = mem.get("lng")
        has_coords = lat is not None and lng is not None

        if has_coords:
            place_result = session.execute(
                text("""
                    INSERT INTO places (name, place_query, precision_meters, coordinates, geocode_status)
                    VALUES (:name, :query, :precision, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 'llm')
                    ON CONFLICT (place_query) DO NOTHING
                    RETURNING id
                """),
                {
                    "name": mem.get("place_name", "Unknown"),
                    "query": mem.get("place_query", mem.get("place_name", "Unknown")),
                    "precision": precision_to_meters(mem.get("location_precision", "street")),
                    "lat": lat,
                    "lng": lng,
                },
            )
        else:
            place_result = session.execute(
                text("""
                    INSERT INTO places (name, place_query, precision_meters)
                    VALUES (:name, :query, :precision)
                    ON CONFLICT (place_query) DO NOTHING
                    RETURNING id
                """),
                {
                    "name": mem.get("place_name", "Unknown"),
                    "query": mem.get("place_query", mem.get("place_name", "Unknown")),
                    "precision": precision_to_meters(mem.get("location_precision", "street")),
                },
            )
        row = place_result.fetchone()

        if row:
            place_id = row[0]
        else:
            # ponytail: exact-string dedup only. "Oslo Norway" and "comedy club Oslo
            # Norway" remain separate places. Normalizing would mean changing this
            # SELECT and idx_places_place_query together - if they ever disagree,
            # place_id comes back None and the memory is silently dropped below.
            existing = session.execute(
                text("SELECT id FROM places WHERE place_query = :query"),
                {"query": mem.get("place_query", mem.get("place_name", "Unknown"))},
            ).fetchone()
            place_id = existing[0] if existing else None

        if not place_id:
            logger.warning(f"Could not get place_id for: {mem.get('place_name')}")
            continue

        session.execute(
            text("""
                INSERT INTO memories (
                    place_id, content_id, timestamp_start, timestamp_end, summary, tags,
                    extraction_confidence, layer, happened_at, happened_precision,
                    attribution, source_url, contrast_score, contrast_note
                )
                VALUES (
                    :place_id, :content_id, :ts_start, :ts_end, :summary, :tags,
                    :confidence, :layer, CAST(:happened_at AS DATE), :happened_precision,
                    :attribution, :source_url, :contrast_score, :contrast_note
                )
            """),
            {
                "place_id": place_id,
                "content_id": content_id,
                "ts_start": mem.get("timestamp_start", 0),
                "ts_end": mem.get("timestamp_end"),
                "summary": mem.get("summary", ""),
                "tags": mem.get("tags", []),
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
            text(f"SELECT c.id, c.title, t.segments, c.source_type {PENDING_EXTRACTION}")
        ).fetchall()

        logger.info(f"Found {len(pending)} videos pending extraction")

        for row in pending:
            content_id, title, segments_json, source_type = row
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
                        memories = extract_memories_from_chunk(
                            client, chunk, prompt_for(source_type)
                        )
                        all_memories.extend(memories)
                    except BillingError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "billing"}

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
                extracted += 1

            except Exception as e:
                logger.error(f"  Extraction failed: {e}")
                session.execute(
                    text("UPDATE content SET extraction_failed = TRUE WHERE id = :id"),
                    {"id": content_id},
                )
                failed += 1

    logger.info(f"Extraction complete: {extracted} extracted, {failed} failed")
    return {"extracted": extracted, "failed": failed}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extract_all_pending()
