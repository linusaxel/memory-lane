"""Delete the uploads nothing ever claimed.

    python -m pipeline.sweep            # say what would go
    python -m pipeline.sweep --apply    # actually go

A photo is uploaded the moment it is picked, so that the wait happens while
somebody is still typing (see api/write.py). If they then close the sheet, the
row keeps `memory_id IS NULL` and the file stays on the disk, referenced by
nothing and returned by no query, for ever. `db/schema.sql` has carried a note
about needing this since the table was written.

It is not only tidiness. The upload allowance is 64MB per device per day, and
uploading up to it and cancelling every time costs a device nothing and the
disk 64MB a day.

Two kinds of leftover, because they fail differently:

  * rows with no memory - an abandoned submission, the ordinary case;
  * files with no row - a crash between writing the file and inserting the
    row. The refusal path cleans up after itself now, but a killed process
    cannot.

Nothing younger than --hours is touched, so an upload belonging to a
submission somebody is still writing is never in scope. It defaults to a day,
which is far longer than anybody spends composing.

Destructive, so it prints and stops unless told --apply.
"""

import argparse
import datetime

from sqlalchemy import text

from api.media import MEDIA_DIR
from pipeline.db import get_session

ORPHAN_ROWS = """
    SELECT id, path, bytes
    FROM media
    WHERE memory_id IS NULL
      AND created_at < LOCALTIMESTAMP - make_interval(hours => :hours)
    ORDER BY id
"""

ALL_PATHS = (
    "SELECT path FROM media UNION SELECT avatar_path FROM users WHERE avatar_path IS NOT NULL"
)


def find(session, hours: int):
    """Returns (rows nothing claimed, files nothing references)."""
    rows = session.execute(text(ORPHAN_ROWS), {"hours": hours}).fetchall()

    known = {row[0] for row in session.execute(text(ALL_PATHS))}
    cutoff = datetime.datetime.now().timestamp() - hours * 3600
    stray = []
    if MEDIA_DIR.exists():
        for entry in sorted(MEDIA_DIR.iterdir()):
            if not entry.is_file() or entry.name in known:
                continue
            # A file being written right now has no row yet and is not a leak.
            if entry.stat().st_mtime >= cutoff:
                continue
            stray.append(entry)
    return rows, stray


def sweep(session, hours: int, apply: bool) -> tuple[int, int]:
    rows, stray = find(session, hours)

    for row in rows:
        print(f"  row {row.id:>6}  {row.path}  {row.bytes or 0:>9,} bytes")
    for path in stray:
        print(f"  file          {path.name}  {path.stat().st_size:>9,} bytes  (no row)")

    if not apply:
        return len(rows), len(stray)

    for row in rows:
        # The file first: a row with no file is invisible, a file with no row
        # is what this command exists to clean up.
        (MEDIA_DIR / row.path).unlink(missing_ok=True)
    if rows:
        session.execute(
            text("DELETE FROM media WHERE id = ANY(:ids)"), {"ids": [r.id for r in rows]}
        )
    for path in stray:
        path.unlink(missing_ok=True)

    return len(rows), len(stray)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=24, help="leave anything younger alone")
    parser.add_argument("--apply", action="store_true", help="delete, rather than describe")
    args = parser.parse_args()

    with get_session() as session:
        rows, stray = sweep(session, args.hours, args.apply)

    total = rows + stray
    if not total:
        print(f"nothing unclaimed older than {args.hours}h")
    elif args.apply:
        print(f"\ndeleted {rows} row(s) and {stray} stray file(s)")
    else:
        print(f"\n{rows} row(s) and {stray} stray file(s) would go - re-run with --apply")


if __name__ == "__main__":
    main()
