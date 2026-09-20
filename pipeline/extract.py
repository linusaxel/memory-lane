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
- confidence: high (clear location + definite event), medium (somewhat vague), low (uncertain)

Return JSON: {"memories": [...]}
Return {"memories": []} if no memories found."""

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

        # Check if we need to start a new chunk
        if start >= chunk_start_time + chunk_seconds:
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
            # Start new chunk with overlap
            chunk_start_time = start - overlap_seconds
            current_chunk_lines = []

        current_chunk_lines.append(f"[{start:.1f}] {text}")

    # Don't forget the last chunk
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


def extract_memories_from_chunk(client: anthropic.Anthropic, chunk: str) -> list[dict]:
    """Send chunk to Claude and extract memories."""
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(chunk=chunk)}],
        )

        content = response.content[0].text

        # Parse JSON from response
        try:
            data = json.loads(content)
            return data.get("memories", [])
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
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

    # Sort by place_query and timestamp
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
    """Remove low confidence memories."""
    return [m for m in memories if m.get("confidence", "low") in ("high", "medium")]


def precision_to_meters(precision: str) -> int:
    """Convert precision string to meters."""
    mapping = {"exact": 50, "street": 200, "neighborhood": 1000, "city": 10000}
    return mapping.get(precision, 200)


def save_memories(session, content_id: int, memories: list[dict]):
    """Save memories and places to database."""
    for mem in memories:
        lat = mem.get("lat")
        lng = mem.get("lng")
        has_coords = lat is not None and lng is not None

        # Insert or get place (with LLM coordinates if available)
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
            # Place already exists, fetch its id
            existing = session.execute(
                text("SELECT id FROM places WHERE place_query = :query"),
                {"query": mem.get("place_query", mem.get("place_name", "Unknown"))},
            ).fetchone()
            place_id = existing[0] if existing else None

        if not place_id:
            logger.warning(f"Could not get place_id for: {mem.get('place_name')}")
            continue

        # Insert memory
        session.execute(
            text("""
                INSERT INTO memories (place_id, content_id, timestamp_start, timestamp_end, summary, tags, extraction_confidence)
                VALUES (:place_id, :content_id, :ts_start, :ts_end, :summary, :tags, :confidence)
            """),
            {
                "place_id": place_id,
                "content_id": content_id,
                "ts_start": mem.get("timestamp_start", 0),
                "ts_end": mem.get("timestamp_end"),
                "summary": mem.get("summary", ""),
                "tags": mem.get("tags", []),
                "confidence": mem.get("confidence", "medium"),
            },
        )


def extract_all_pending():
    """Extract memories from all pending transcripts."""
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return {"extracted": 0, "failed": 0}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    extracted = 0
    failed = 0

    with get_session() as session:
        # Get content with transcripts ready for extraction
        pending = session.execute(
            text(f"SELECT c.id, c.title, t.segments {PENDING_EXTRACTION}")
        ).fetchall()

        logger.info(f"Found {len(pending)} videos pending extraction")

        for row in pending:
            content_id, title, segments_json = row
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
                        memories = extract_memories_from_chunk(client, chunk)
                        all_memories.extend(memories)
                    except BillingError as e:
                        logger.error(str(e))
                        return {"extracted": extracted, "failed": failed, "error": "billing"}

                # Merge and filter
                merged = merge_nearby_memories(all_memories)
                filtered = filter_low_confidence(merged)

                logger.info(
                    f"  Found {len(all_memories)} raw, {len(merged)} merged, {len(filtered)} after filtering"
                )

                # Save to database
                save_memories(session, content_id, filtered)

                # Mark as extracted
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
