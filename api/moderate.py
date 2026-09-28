"""What reports took down, and putting a memory back.

    python -m api.moderate                # hidden memories, newest report first
    python -m api.moderate --restore 42   # show it again; its reports stop counting

A report is kept when it is cleared, so a dispute can still be answered.
docs/10-decisions.md#posts-are-screened-reports-need-an-account.
"""

import argparse

from sqlalchemy import text

from pipeline.db import get_session

HIDDEN = """
    SELECT m.id, m.summary, u.display_name,
           COUNT(r.device_id) FILTER (WHERE r.cleared_at IS NULL) AS reports,
           array_remove(array_agg(DISTINCT r.reason), NULL) AS reasons,
           max(r.created_at) AS last_report
    FROM memories m
    LEFT JOIN users u ON u.id = m.user_id
    LEFT JOIN reports r ON r.memory_id = m.id
    WHERE m.hidden
    GROUP BY m.id, u.display_name
    ORDER BY last_report DESC NULLS LAST
"""


def restore(session, memory_id: int) -> bool:
    session.execute(
        text(
            "UPDATE reports SET cleared_at = CURRENT_TIMESTAMP"
            " WHERE memory_id = :id AND cleared_at IS NULL"
        ),
        {"id": memory_id},
    )
    return bool(
        session.execute(
            text("UPDATE memories SET hidden = FALSE WHERE id = :id AND hidden RETURNING id"),
            {"id": memory_id},
        ).scalar()
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", type=int, metavar="MEMORY_ID")
    args = parser.parse_args()
    with get_session() as session:
        if args.restore:
            print("restored" if restore(session, args.restore) else "not hidden")
            return
        for r in session.execute(text(HIDDEN)):
            reasons = ", ".join(r.reasons) or "no reason given"
            print(f"{r.id}  {r.reports} report(s): {reasons}  by {r.display_name or 'Anonymous'}")
            print(f"    {r.summary[:160]}")


if __name__ == "__main__":
    main()
