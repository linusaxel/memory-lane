"""RQ tasks for memory extraction pipeline."""

import json
import logging

import anthropic
from rq import Retry, get_current_job
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
    ModelUnusableError,
    TransientAPIError,
    chunk_transcript,
    extract_chunk_stored,
    filter_low_confidence,
    is_billing_error,
    is_transient,
    layer_for,
    log_cache,
    merge_nearby_memories,
    one_name_per_venue,
    prompt_for,
    save_memories,
    source_context,
    video_brief,
    worth_telling,
)
from pipeline.links import link_memories
from pipeline.now import look_up
from pipeline.queue import (
    QUEUE_AGGREGATE,
    QUEUE_CLASSIFY,
    QUEUE_EXTRACT,
    get_queue,
    get_redis,
)

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = """Analyze this transcript chunk and determine if it contains any LOCATION-BASED MEMORIES.

A location-based memory is something that already happened at a SPECIFIC, NAMED PLACE: a personal
experience, an event, a mishap, or something that once stood there. Told first-hand or as history.

Examples that QUALIFY:
- "I had the best pizza at this place in Brooklyn"
- "I proposed to my wife on the Golden Gate Bridge"
- "In 1943 the resistance blew up the factory that stood on this corner"
- "The bar counter here was mortared in so solidly the police couldn't remove it"

Examples that DO NOT qualify:
- General facts: "Paris is known for the Eiffel Tower"
- Hypotheticals: "I want to visit Japan someday"
- Announcements and listings: a tour date, an auction notice, a flat to let
- Vague references: "somewhere in Europe"

Respond with ONLY a JSON object, the reason in under 20 words:
{"has_memories": true/false, "reason": "brief explanation"}"""

CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {"has_memories": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["has_memories", "reason"],
    "additionalProperties": False,
}


FAIL_OPEN = "fail-open: "
# Same schedule as the extract retry. A throttled Haiku backs off on its own
# queue instead of failing open and sending every chunk to Sonnet.
RETRY = Retry(max=3, interval=[30, 120, 600])


def _final(job):
    """No retry: a dead model ID or an empty balance fails every attempt alike,
    and a burst worker would wait out the 12-minute schedule for nothing."""
    if job:
        job.retries_left = 0


def classify_chunk(
    client: anthropic.Anthropic, chunk: str, last_attempt: bool = True
) -> tuple[bool, str]:
    """Use Haiku to quickly determine if chunk likely contains memories.

    Returns the verdict and the model's reason. A verdict the model did not
    give - a cut-off reply, a transient error on the last attempt - is True with
    a reason starting FAIL_OPEN, so nothing auditing the classifier mistakes it
    for a judgement. A transient error before the last attempt raises
    TransientAPIError so the job is retried.
    """
    try:
        response = client.messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": f"{CLASSIFIER_PROMPT}\n\nTranscript:\n{chunk}"}],
            output_config={"format": {"type": "json_schema", "schema": CLASSIFIER_SCHEMA}},
        )
        log_cache(response)
        content = response.content[0].text
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # The schema makes this a max_tokens cut. Assume it might have
            # memories (safer)
            return True, f"{FAIL_OPEN}unparseable reply"
        has_memories = bool(data.get("has_memories", False))
        reason = data.get("reason", "")
        logger.debug(f"Classifier: {'HAS' if has_memories else 'NO'} memories - {reason[:50]}")
        return has_memories, reason
    except (
        anthropic.NotFoundError,
        anthropic.AuthenticationError,
        anthropic.PermissionDeniedError,
    ) as e:
        # docs/10-decisions.md#the-classifier-fails-loud-on-a-config-error-and-open-on-a-transient-one
        raise ModelUnusableError(f"CLASSIFIER_MODEL={CLASSIFIER_MODEL!r} is not usable: {e}") from e
    except Exception as e:
        # Same decision as above: a billing error is not transient.
        if is_billing_error(e):
            raise BillingError(
                "API credit balance too low. Please add credits at console.anthropic.com"
            ) from e
        if is_transient(e) and not last_attempt:
            raise TransientAPIError(str(e)) from e
        logger.warning(f"Classifier error, assuming has memories: {e}")
        return True, f"{FAIL_OPEN}{e}"


def record_verdict(
    session, content_id: int, chunk_index: int, has_memories: bool, reason: str, chunk_text: str
):
    """A rejected chunk otherwise leaves no trace, and the pre-filter's misses
    are unmeasurable. pipeline/classifier_audit.py reads these back."""
    session.execute(
        text("""
            INSERT INTO classifier_verdicts
                (content_id, chunk_index, model, has_memories, reason, chunk_text)
            VALUES (:content_id, :chunk_index, :model, :has_memories, :reason, :chunk_text)
            ON CONFLICT (content_id, chunk_index, model) DO UPDATE SET
                has_memories = EXCLUDED.has_memories,
                reason = EXCLUDED.reason,
                chunk_text = EXCLUDED.chunk_text,
                created_at = CURRENT_TIMESTAMP
        """),
        {
            "content_id": content_id,
            "chunk_index": chunk_index,
            "model": CLASSIFIER_MODEL,
            "has_memories": has_memories,
            "reason": reason,
            "chunk_text": chunk_text,
        },
    )


def _source_type(redis, content_id: int) -> str:
    """Redis hands back bytes, and a hash written before source_type existed has
    no such field. Both roads lead to 'video', which is what the corpus is."""
    raw = redis.hget(f"extraction:{content_id}", "source_type")
    if raw is None:
        return "video"
    return raw.decode() if isinstance(raw, bytes) else str(raw)


def _brief(redis, content_id: int) -> str:
    raw = redis.hget(f"extraction:{content_id}", "brief") or b""
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
                SELECT c.title, t.segments, c.source_type, c.source_name, c.memories_extracted
                FROM content c
                JOIN transcripts t ON c.id = t.content_id
                WHERE c.id = :id
            """),
            {"id": content_id},
        ).fetchone()

        if not row:
            logger.error(f"[content:{content_id}] No transcript found")
            return {"error": "no_transcript"}

        title, segments_json, source_type, source_name, extracted = row
        if extracted:
            # Aggregation only inserts, so a second pass is a second copy of every memory.
            logger.info(f"[content:{content_id}] Already extracted, skipping")
            return {"skipped": "already_extracted"}
        segments = segments_json if isinstance(segments_json, list) else json.loads(segments_json)
        # Archival records are short and self-contained; a video needs its frame.
        brief = ""
        if (source_type or "video") == "video":
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            brief = video_brief(session, client, content_id, segments, source_name, title)

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
            "brief": brief,
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
            retry=RETRY,
        )

    return {"content_id": content_id, "chunks_enqueued": total_chunks}


def task_classify_chunk(content_id: int, chunk_index: int, total_chunks: int, chunk_text: str):
    """
    Task: Use Haiku to classify if chunk has memories.
    If yes, enqueue for full extraction.
    """
    logger.info(f"[content:{content_id}] Classifying chunk {chunk_index + 1}/{total_chunks}")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    job = get_current_job()
    try:
        has_memories, reason = classify_chunk(
            client, chunk_text, last_attempt=not (job and job.retries_left)
        )
    except (ModelUnusableError, BillingError):
        _final(job)
        raise
    with get_session() as session:
        record_verdict(session, content_id, chunk_index, has_memories, reason, chunk_text)

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
            # extract_memories_from_chunk raises TransientAPIError rather than
            # report an empty chunk; without a retry the video never aggregates.
            retry=RETRY,
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
    try:
        with get_session() as session:
            memories = extract_chunk_stored(
                session,
                client,
                content_id,
                chunk_index,
                chunk_text,
                prompt_for(source_type),
                source_context(*_source_and_title(content_id), _brief(redis, content_id)),
            )
    except (ModelUnusableError, BillingError):
        _final(get_current_job())
        raise

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

    with get_session() as session:
        # The claim, and the lock a second aggregation of the same content waits
        # on: _check_extraction_complete can enqueue one per worker that finished
        # a last chunk, and each would insert every memory again.
        claimed = session.execute(
            text("""
                UPDATE content SET memories_extracted = TRUE
                WHERE id = :id AND NOT memories_extracted RETURNING id
            """),
            {"id": content_id},
        ).scalar()
        if claimed is None:
            logger.info(f"[content:{content_id}] Already aggregated, skipping")
            return {"skipped": "already_extracted"}

        redis = get_redis()
        redis.hset(f"extraction:{content_id}", "status", "aggregating")

        memories_hash = redis.hgetall(f"extraction:{content_id}:memories")
        all_memories = []

        for memories_json in memories_hash.values():
            all_memories.extend(json.loads(memories_json))

        logger.info(f"[content:{content_id}] Collected {len(all_memories)} raw memories")

        merged = merge_nearby_memories(all_memories)
        candidates = filter_low_confidence(merged)

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        filtered = worth_telling(session, client, content_id, candidates)
        filtered = one_name_per_venue(session, client, content_id, filtered)
        logger.info(
            f"[content:{content_id}] After merge: {len(merged)}, after filter: "
            f"{len(candidates)}, worth telling: {len(filtered)}"
        )
        save_memories(
            session, content_id, filtered, layer_for(_source_type(redis, content_id)), client
        )

    # Its own session, after the memories are committed: a failed lookup must
    # not roll them back. What it misses, `python -m pipeline.links` picks up.
    try:
        with get_session() as session:
            link_memories(session, client, content_id=content_id)
    except Exception:
        logger.exception(f"[content:{content_id}] Linking names failed; memories are saved")
    try:
        with get_session() as session:
            look_up(session)
    except Exception:
        logger.exception(f"[content:{content_id}] Looking up what is there now failed")

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
