"""A copy of everything one person has here, for a GDPR access request.

Answered by email, not in the app (docs/10-decisions.md#data-export-is-on-request):

    python -m api.my_data --device <uuid> > their-data.json

Covers what DELETE /v1/me deletes, from the same definition of "theirs".
Media files are listed, not embedded; send them alongside from MEDIA_DIR.
"""

import argparse
import json

from sqlalchemy import text

from api.accounts import OWNED_DEVICES, OWNED_MEMORIES
from pipeline.db import get_session

BY_DEVICE = (
    "unlocks",
    "memory_hearts",
    "memory_notes",
    "reports",
    "blocks",
    "daily_routes",
    "media",
)
BY_USER = ("identities", "subscriptions", "surprises")


def my_data(session, device: str) -> dict:
    user_id = session.execute(
        text("SELECT user_id FROM devices WHERE id = CAST(:id AS uuid)"), {"id": device}
    ).scalar()
    owner = {"user": str(user_id) if user_id else None, "device": device}

    def rows(sql: str) -> list:
        return [r[0] for r in session.execute(text(sql), owner)]

    out = {
        "user": rows("SELECT to_jsonb(u) FROM users u WHERE id = CAST(:user AS uuid)"),
        "devices": rows(f"SELECT to_jsonb(d) FROM devices d WHERE id IN {OWNED_DEVICES}"),
        "memories": rows(f"""
            SELECT to_jsonb(m) - 'search_vector' || jsonb_build_object(
                'place', p.name,
                'lat', ST_Y(p.coordinates::geometry), 'lng', ST_X(p.coordinates::geometry))
            FROM memories m JOIN places p ON p.id = m.place_id
            WHERE m.id IN {OWNED_MEMORIES}"""),
    }
    for table in BY_DEVICE:
        out[table] = rows(f"SELECT to_jsonb(t) FROM {table} t WHERE device_id IN {OWNED_DEVICES}")
    for table in BY_USER:
        out[table] = rows(f"SELECT to_jsonb(t) FROM {table} t WHERE user_id = CAST(:user AS uuid)")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, help="any device on the account")
    args = parser.parse_args()
    with get_session() as session:
        print(json.dumps(my_data(session, args.device), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
