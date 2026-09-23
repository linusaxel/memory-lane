"""How much does the Haiku pre-filter throw away?

    python -m pipeline.classifier_audit              # 20 rejected chunks
    python -m pipeline.classifier_audit --sample 50

Re-extracts a sample of the chunks the classifier rejected and counts the ones
that still yield a memory the pipeline would keep. Bills the extractor once per
sampled chunk (~$0.003 each): the sample is stable and every reply lands in
extraction_chunks, so a rerun over the same sample is free.
"""

import argparse
import logging

import anthropic
from sqlalchemy import text

from pipeline.config import ANTHROPIC_API_KEY
from pipeline.db import get_session
from pipeline.extract import extract_chunk_stored, filter_low_confidence, prompt_for, source_context


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=20)
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
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
