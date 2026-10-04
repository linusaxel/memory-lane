"""How much does the Haiku pre-filter throw away?

    python -m pipeline.classifier_audit              # 20 rejected chunks
    python -m pipeline.classifier_audit --sample 50
    python -m pipeline.classifier_audit --against old_prompt.txt

Re-extracts a sample of the chunks the classifier rejected and counts the ones
that still yield a memory the pipeline would keep. Bills the extractor once per
sampled chunk (~$0.003 each): the sample is stable and every reply lands in
extraction_chunks, so a rerun over the same sample is free.

--against replays stored chunks, kept and rejected, through an old classifier
prompt and the current one, and counts the flips per source. Nothing caches a
classifier reply: every run bills two Haiku calls a chunk.
"""

import argparse
import logging

import anthropic
from sqlalchemy import text

from pipeline.config import ANTHROPIC_API_KEY
from pipeline.db import get_session
from pipeline.extract import extract_chunk_stored, filter_low_confidence, prompt_for, source_context
from pipeline.tasks import FAIL_OPEN, classify_chunk


def audit(session, client, sample: int) -> tuple[int, list]:
    rows = session.execute(
        text("""
            SELECT v.content_id, v.chunk_index, v.chunk_text, v.reason,
                   c.source_type, c.source_name, c.title
            FROM classifier_verdicts v
            JOIN content c ON c.id = v.content_id
            WHERE NOT v.has_memories
            ORDER BY md5(v.content_id || '-' || v.chunk_index)
            LIMIT :n
        """),
        {"n": sample},
    ).fetchall()

    missed = []
    for r in rows:
        memories = extract_chunk_stored(
            session,
            client,
            r.content_id,
            r.chunk_index,
            r.chunk_text,
            prompt_for(r.source_type),
            source_context(r.source_name, r.title),
        )
        kept = filter_low_confidence(memories)
        if kept:
            missed.append((r, kept))
    return len(rows), missed


def flips(session, client, old_prompt: str, sample: int) -> dict[str, dict[str, int]]:
    """{source: {"lost", "gained", "same"}}: lost is kept by the old prompt and
    rejected by the current one. A fail-open answer on either side is no verdict,
    so its chunk is left out. Stored verdicts are never rewritten."""
    rows = session.execute(
        text("""
            SELECT v.chunk_text, COALESCE(c.source_name, '(no source)') AS source
            FROM classifier_verdicts v
            JOIN content c ON c.id = v.content_id
            ORDER BY md5(v.content_id || '-' || v.chunk_index)
            LIMIT :n
        """),
        {"n": sample},
    ).fetchall()
    counts = {}
    for r in rows:
        old, old_reason = classify_chunk(client, r.chunk_text, prompt=old_prompt)
        new, new_reason = classify_chunk(client, r.chunk_text)
        if old_reason.startswith(FAIL_OPEN) or new_reason.startswith(FAIL_OPEN):
            continue
        kind = "same" if old == new else "lost" if old else "gained"
        counts.setdefault(r.source, {"lost": 0, "gained": 0, "same": 0})[kind] += 1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--against", metavar="PROMPT_FILE", help="an old classifier prompt")
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if args.against:
        with get_session() as session:
            counts = flips(session, client, open(args.against).read(), args.sample)
        for source, c in sorted(counts.items()):
            print(f"{source}: {c['lost']} lost, {c['gained']} gained, {c['same']} unchanged")
        lost = sum(c["lost"] for c in counts.values())
        gained = sum(c["gained"] for c in counts.values())
        print(f"total: {lost} kept by the old prompt and rejected now, {gained} the other way")
        return
    with get_session() as session:
        total, missed = audit(session, client, args.sample)

    if not total:
        print("no rejected chunks recorded")
        return
    print(f"{len(missed)} of {total} rejected chunks had a memory the pipeline would keep")
    for r, kept in missed:
        print(f"\ncontent {r.content_id} chunk {r.chunk_index} - rejected as: {r.reason}")
        for m in kept:
            print(f"  {m.get('venue')}: {(m.get('summary') or '')[:120]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
