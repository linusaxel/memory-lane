"""RQ tasks for memory extraction pipeline."""

import json
import logging

import anthropic
from sqlalchemy import text

from pipeline.config import (
    ANTHROPIC_API_KEY,
    CHUNK_MINUTES,
    CHUNK_OVERLAP_SECONDS,
    CLASSIFIER_MODEL,
)
from pipeline.db import get_session
from pipeline.extract import (
    PENDING_EXTRACTION,
    BillingError,
    chunk_transcript,
    extract_memories_from_chunk,
    filter_low_confidence,
    is_billing_error,
    layer_for,
    merge_nearby_memories,
    prompt_for,
    save_memories,
    source_context,
)
from pipeline.queue import (
    QUEUE_AGGREGATE,
    QUEUE_CLASSIFY,
    QUEUE_EXTRACT,
    get_queue,
    get_redis,
)

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = """Analyze this transcript chunk and determine if it contains any LOCATION-BASED MEMORIES.

A location-based memory is when someone describes a PERSONAL EXPERIENCE at a SPECIFIC PHYSICAL PLACE.

Examples that QUALIFY:
- "I had the best pizza at this place in Brooklyn"
- "We visited the Colosseum and got lost trying to find the entrance"
- "I proposed to my wife on the Golden Gate Bridge"

Examples that DO NOT qualify:
- General facts: "Paris is known for the Eiffel Tower"
- Hypotheticals: "I want to visit Japan someday"
- Vague references: "somewhere in Europe"

Respond with ONLY a JSON object:
{"has_memories": true/false, "reason": "brief explanation"}"""


def classify_chunk(client: anthropic.Anthropic, chunk: str) -> bool:
    """Use Haiku to quickly determine if chunk likely contains memories."""
    try:
        response = client.messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": f"{CLASSIFIER_PROMPT}\n\nTranscript:\n{chunk}"}],
        )
        content = response.content[0].text
        try:
            data = json.loads(content)
            has_memories = data.get("has_memories", False)
            if has_memories:
                logger.debug(f"Classifier: HAS memories - {data.get('reason', '')[:50]}")
            else:
                logger.debug(f"Classifier: NO memories - {data.get('reason', '')[:50]}")
            return has_memories
        except json.JSONDecodeError:
            # If we can't parse, assume it might have memories (safer)
            return True
    except (
        anthropic.NotFoundError,
        anthropic.AuthenticationError,
        anthropic.PermissionDeniedError,
    ) as e:
        # A bad model ID or key fails identically on every chunk, forever. Failing
        # open here is what let CLASSIFIER_MODEL sit on a nonexistent ID with the
        # pre-filter silently disabled and every chunk billed to Sonnet.
        raise RuntimeError(f"CLASSIFIER_MODEL={CLASSIFIER_MODEL!r} is not usable: {e}") from e
    except Exception as e:
        # An empty balance is not transient. Observed on a real run: all 22
        # chunks "classified" as having memories, all 22 were enqueued for
        # extraction, and all 22 then hit the same wall - with a status page
        # reporting 22 successful classifications that never happened.
        if is_billing_error(e):
            raise BillingError(
                "API credit balance too low. Please add credits at console.anthropic.com"
            ) from e
        # Transient (429, 5xx, connection): over-extracting one chunk beats
        # dropping it, so keep failing open.
        logger.warning(f"Classifier error, assuming has memories: {e}")
        return True


def _source_type(redis, content_id: int) -> str:
    """Redis hands back bytes, and a hash written before source_type existed has
    no such field. Both roads lead to 'video', which is what the corpus is."""
    raw = redis.hget(f"extraction:{content_id}", "source_type")
    if raw is None:
        return "video"
    return raw.decode() if isinstance(raw, bytes) else str(raw)


def _source_and_title(content_id: int) -> tuple[str | None, str | None]:
    """Who published this and which episode, for the prompt's context line.

    Read from the database rather than the Redis hash: the hash would need both
    fields written at enqueue time and would then be stale for anything already
    queued, while these two columns are always right and this runs once per
    chunk against a primary key.
    """
    with get_session() as session:
        row = session.execute(
            text("SELECT source_name, title FROM content WHERE id = :id"),
            {"id": content_id},
        ).fetchone()
    return (row.source_name, row.title) if row else (None, None)


def task_enqueue_chunks(content_id: int):
    """
    Task: Fetch transcript and enqueue each chunk for classification.
    Called after transcript is fetched.
    """
    logger.info(f"[content:{content_id}] Enqueueing chunks")

    with get_session() as session:
        row = session.execute(
            text("""
                SELECT c.title, t.segments, c.source_type
                FROM content c
                JOIN transcripts t ON c.id = t.content_id
                WHERE c.id = :id
            """),
            {"id": content_id},
        ).fetchone()

        if not row:
            logger.error(f"[content:{content_id}] No transcript found")
            return {"error": "no_transcript"}

        title, segments_json, source_type = row
        segments = segments_json if isinstance(segments_json, list) else json.loads(segments_json)

    chunks = chunk_transcript(segments, CHUNK_MINUTES, CHUNK_OVERLAP_SECONDS)
    total_chunks = len(chunks)

    logger.info(f"[content:{content_id}] Split '{title}' into {total_chunks} chunks")

    redis = get_redis()
    redis.hset(
        f"extraction:{content_id}",
        mapping={
            "total_chunks": total_chunks,
            "classified": 0,
            "has_memories": 0,
            "extracted": 0,
            "status": "classifying",
            # The later tasks need this to pick a prompt and a layer. It lives
            # here because this hash is already this extraction's state, and
            # task_classify_chunk would otherwise have to forward a value it
            # never reads.
            "source_type": source_type or "video",
        },
    )

    classify_queue = get_queue(QUEUE_CLASSIFY)
    for i, chunk in enumerate(chunks):
        classify_queue.enqueue(
            task_classify_chunk,
            content_id=content_id,
            chunk_index=i,
            total_chunks=total_chunks,
            chunk_text=chunk,
            job_timeout="5m",
        )

    return {"content_id": content_id, "chunks_enqueued": total_chunks}


def task_classify_chunk(content_id: int, chunk_index: int, total_chunks: int, chunk_text: str):
    """
    Task: Use Haiku to classify if chunk has memories.
    If yes, enqueue for full extraction.
    """
    logger.info(f"[content:{content_id}] Classifying chunk {chunk_index + 1}/{total_chunks}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    has_memories = classify_chunk(client, chunk_text)

    redis = get_redis()
    redis.hincrby(f"extraction:{content_id}", "classified", 1)

    if has_memories:
        redis.hincrby(f"extraction:{content_id}", "has_memories", 1)
        extract_queue = get_queue(QUEUE_EXTRACT)
        extract_queue.enqueue(
            task_extract_chunk,
            content_id=content_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_text=chunk_text,
            job_timeout="5m",
        )
    else:
        redis.hincrby(f"extraction:{content_id}", "extracted", 1)
        _check_extraction_complete(content_id, total_chunks)

    return {"content_id": content_id, "chunk_index": chunk_index, "has_memories": has_memories}


def task_extract_chunk(content_id: int, chunk_index: int, total_chunks: int, chunk_text: str):
    """
    Task: Extract memories from chunk using Sonnet.
    Store results in Redis, check if all chunks done.
    """
    logger.info(f"[content:{content_id}] Extracting chunk {chunk_index + 1}/{total_chunks}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    redis = get_redis()

    # Archival text asked for WHO and THE VIBE is an invitation to invent, which
    # is the one thing third-party material must not get. Defaults to video so a
    # hash written before this field existed still picks the old prompt.
    source_type = _source_type(redis, content_id)
    # Same context the sequential path builds, from the same two fields.
    memories = extract_memories_from_chunk(
        client,
        chunk_text,
        prompt_for(source_type),
        source_context(*_source_and_title(content_id)),
    )

    if memories:
        redis.hset(f"extraction:{content_id}:memories", str(chunk_index), json.dumps(memories))

    redis.hincrby(f"extraction:{content_id}", "extracted", 1)

    logger.info(f"[content:{content_id}] Chunk {chunk_index + 1} yielded {len(memories)} memories")

    _check_extraction_complete(content_id, total_chunks)

    return {"content_id": content_id, "chunk_index": chunk_index, "memories_found": len(memories)}


def _check_extraction_complete(content_id: int, total_chunks: int):
    redis = get_redis()
    extracted = int(redis.hget(f"extraction:{content_id}", "extracted") or 0)

    if extracted >= total_chunks:
        logger.info(f"[content:{content_id}] All chunks processed, triggering aggregation")
        aggregate_queue = get_queue(QUEUE_AGGREGATE)
        aggregate_queue.enqueue(task_aggregate_memories, content_id=content_id, job_timeout="5m")


def task_aggregate_memories(content_id: int):
    """
    Task: Collect all extracted memories, merge, filter, and save to DB.
    """
    logger.info(f"[content:{content_id}] Aggregating memories")

    redis = get_redis()
    redis.hset(f"extraction:{content_id}", "status", "aggregating")

    memories_hash = redis.hgetall(f"extraction:{content_id}:memories")
    all_memories = []

    for memories_json in memories_hash.values():
        all_memories.extend(json.loads(memories_json))

    logger.info(f"[content:{content_id}] Collected {len(all_memories)} raw memories")

    merged = merge_nearby_memories(all_memories)
    filtered = filter_low_confidence(merged)

    logger.info(f"[content:{content_id}] After merge: {len(merged)}, after filter: {len(filtered)}")

    with get_session() as session:
        save_memories(session, content_id, filtered, layer_for(_source_type(redis, content_id)))

        session.execute(
            text("UPDATE content SET memories_extracted = TRUE WHERE id = :id"), {"id": content_id}
        )

    redis.hset(
        f"extraction:{content_id}", mapping={"status": "completed", "total_memories": len(filtered)}
    )

    redis.delete(f"extraction:{content_id}:memories")

    logger.info(f"[content:{content_id}] Extraction complete: {len(filtered)} memories saved")

    return {"content_id": content_id, "memories_saved": len(filtered)}


def enqueue_all_pending():
    """Enqueue all videos that have transcripts but no extraction."""
    with get_session() as session:
        pending = session.execute(text(f"SELECT c.id, c.title {PENDING_EXTRACTION}")).fetchall()

    logger.info(f"Found {len(pending)} videos pending extraction")

    queue = get_queue(QUEUE_CLASSIFY)
    for row in pending:
        content_id, title = row
        logger.info(f"Enqueueing: {title or content_id}")
        queue.enqueue(task_enqueue_chunks, content_id=content_id, job_timeout="10m")

    return {"enqueued": len(pending)}


def get_extraction_status(content_id: int) -> dict:
    redis = get_redis()
    status = redis.hgetall(f"extraction:{content_id}")

    if not status:
        return {"status": "not_started"}

    return {
        "status": status.get(b"status", b"unknown").decode(),
        "total_chunks": int(status.get(b"total_chunks", 0)),
        "classified": int(status.get(b"classified", 0)),
        "has_memories": int(status.get(b"has_memories", 0)),
        "extracted": int(status.get(b"extracted", 0)),
        "total_memories": int(status.get(b"total_memories", 0)),
    }
