"""Review extracted memories by hand; the verdicts are the known-good set.

    python -m pipeline.review                          # 20 unreviewed, spread over sources
    python -m pipeline.review --accept 12,13 --reject 14 [--person]
    python -m pipeline.review --edit 15 "Mark and Joe got thrown out of Katz's."
    python -m pipeline.review --stats                  # edit rate by month and reviewer

Accepted is a positive, rejected a negative (and hidden from every endpoint),
and edited a before/after pair. The share of reviews that needed an edit or a
reject is the quality number: pipeline/quality.py's regexes are the cheap first
pass, this is what a person actually changed. Reviews outlive the memory they
judge, so reprocessing a video does not throw them away. A later accept does
not un-hide a reject: `hidden` is shared with reports, and this cannot tell
which one set it. A verdict is an agent's unless --person says otherwise: an
agent's label passed off as a person's would tune the judge on itself.
"""

import argparse

from sqlalchemy import text

from pipeline.db import get_session
from pipeline.quality import CHECKS


def unreviewed(session, limit: int):
    return session.execute(
        text("""
            SELECT m.id, p.name, m.summary
            FROM memories m
            JOIN places p ON p.id = m.place_id
            LEFT JOIN memory_reviews r ON r.memory_id = m.id
            WHERE m.content_id IS NOT NULL AND NOT m.hidden AND r.id IS NULL
            ORDER BY md5(m.id::text)
            LIMIT :n
        """),
        {"n": limit},
    ).fetchall()


def review(
    session, memory_id: int, verdict: str, after: str | None = None, reviewer: str = "agent"
):
    """Record one verdict. A second review of the same memory replaces the
    verdict but keeps the original `before`: that is the model's own text."""
    row = session.execute(
        text("SELECT content_id, summary, created_at FROM memories WHERE id = :id"),
        {"id": memory_id},
    ).fetchone()
    if row is None or row.content_id is None:
        raise SystemExit(f"memory {memory_id}: no such extracted memory")

    session.execute(
        text("""
            INSERT INTO memory_reviews
                (memory_id, content_id, verdict, before, after, extracted_at, reviewer)
            VALUES (:id, :content_id, :verdict, :before, :after, :extracted_at, :reviewer)
            ON CONFLICT (memory_id) DO UPDATE SET
                verdict = EXCLUDED.verdict,
                after = EXCLUDED.after,
                reviewer = EXCLUDED.reviewer,
                reviewed_at = CURRENT_TIMESTAMP
        """),
        {
            "id": memory_id,
            "content_id": row.content_id,
            "verdict": verdict,
            "before": row.summary,
            "after": after,
            "extracted_at": row.created_at,
            "reviewer": reviewer,
        },
    )
    if verdict == "edit":
        session.execute(
            text("UPDATE memories SET summary = :s WHERE id = :id"), {"s": after, "id": memory_id}
        )
    elif verdict == "reject":
        session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": memory_id})


def stats(session):
    return session.execute(
        text("""
            SELECT to_char(extracted_at, 'YYYY-MM') AS month, reviewer,
                   COUNT(*) AS reviewed,
                   COUNT(*) FILTER (WHERE verdict = 'accept') AS accepted,
                   COUNT(*) FILTER (WHERE verdict = 'edit') AS edited,
                   COUNT(*) FILTER (WHERE verdict = 'reject') AS rejected
            FROM memory_reviews
            GROUP BY 1, 2
            ORDER BY 1, 2
        """)
    ).fetchall()


def _ids(spec: str) -> list[int]:
    try:
        return [int(x) for x in spec.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"expected comma-separated memory ids, got {spec!r}") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept", metavar="ID,...", default="")
    parser.add_argument("--reject", metavar="ID,...", default="")
    parser.add_argument("--edit", nargs=2, action="append", metavar=("ID", "SUMMARY"), default=[])
    parser.add_argument("--person", action="store_true", help="a person gave these verdicts")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    with get_session() as session:
        if args.stats:
            for r in stats(session):
                changed = (r.edited + r.rejected) * 100 // r.reviewed
                print(
                    f"{r.month or 'unknown'}  {r.reviewer:<6}  {r.reviewed:>4} reviewed  "
                    f"{r.accepted:>4} ok  {r.edited:>4} edited  {r.rejected:>4} rejected  "
                    f"{changed}% changed"
                )
            return

        decided = [(i, "accept", None) for i in _ids(args.accept)]
        decided += [(i, "reject", None) for i in _ids(args.reject)]
        decided += [(_ids(i)[0], "edit", s) for i, s in args.edit]
        for memory_id, verdict, after in decided:
            review(session, memory_id, verdict, after, "person" if args.person else "agent")
        if decided:
            print(f"{len(decided)} reviews recorded")
            return

        for r in unreviewed(session, args.limit):
            flags = [name for name, test, _ in CHECKS if test(r.summary)]
            print(f"[{r.id}] {r.name}" + (f"  ({', '.join(flags)})" if flags else ""))
            print(f"  {r.summary}\n")


if __name__ == "__main__":
    main()
