"""Do people come back? Read from the tables we already keep, no analytics SDK
(TODO, Launch playbook 2: PostHog would break the "no collected data" privacy
manifest).

    python -m api.metrics

A device is active on a day it planned a walk or opened a memory. D1 and D7
count, per weekly cohort of `devices.first_seen`, the devices active exactly
one and seven days after their first, out of those old enough to have had
that day. Stories left counts, around each device's last walk, the visible
memories within 2 km it has not opened yet: when that nears one walk's worth,
nothing brings the walker back (TODO, *The retention risk none of this
fixes*). It ignores the planner's finer rules, so it is a ceiling.
"""

from datetime import date
from statistics import median

from sqlalchemy import text

from api.queries import VISIBLE
from pipeline.db import get_session

NEAR_M = 2000

ACTIVE = """
    SELECT device_id, unlocked_at::date AS day FROM unlocks
    UNION SELECT device_id, route_date FROM daily_routes"""


def metrics(session, today: date) -> dict:
    def returned(n: int) -> str:
        return f"""
            count(*) FILTER (WHERE d.first_seen::date + {n} < :today) AS eligible_d{n},
            count(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM active a
                WHERE a.device_id = d.id AND a.day = d.first_seen::date + {n})) AS d{n}"""

    cohorts = session.execute(
        text(f"""
            WITH active AS ({ACTIVE})
            SELECT date_trunc('week', d.first_seen)::date AS week, count(*) AS devices,
                   {returned(1)}, {returned(7)}
            FROM devices d GROUP BY 1 ORDER BY 1"""),
        {"today": today},
    ).mappings()

    walks = (
        session.execute(
            text("""
            SELECT count(*) AS walks,
                   count(DISTINCT device_id) AS walkers,
                   count(*) FILTER (WHERE completed_at IS NOT NULL) AS finished,
                   count(*) - count(DISTINCT (device_id, route_date)) AS second_walks,
                   coalesce(avg(cardinality(memory_ids) - (mystery_id IS NOT NULL)::int), 0)
                       AS stops_per_walk
            FROM daily_routes""")
        )
        .mappings()
        .one()
    )

    # An open counts for the walk it was a stop of, while that walk was on.
    opened = session.execute(
        text("""
            SELECT coalesce(avg(n), 0) FROM (
                SELECT count(u.memory_id) AS n
                FROM daily_routes r
                LEFT JOIN unlocks u
                  ON u.device_id = r.device_id AND u.memory_id = ANY(r.memory_ids)
                 AND u.unlocked_at >= r.created_at
                 AND u.unlocked_at < coalesce(r.ended_at, r.completed_at, 'infinity')
                GROUP BY r.id) w""")
    ).scalar()

    left = (
        session.execute(
            text(f"""
            WITH last AS (
                SELECT DISTINCT ON (device_id) device_id, memory_ids
                FROM daily_routes ORDER BY device_id, created_at DESC),
            centre AS (
                SELECT l.device_id,
                       ST_Centroid(ST_Collect(p.coordinates::geometry))::geography AS at
                FROM last l
                JOIN memories m ON m.id = ANY(l.memory_ids)
                JOIN places p ON p.id = m.place_id
                GROUP BY l.device_id)
            SELECT (SELECT count(*) FROM memories m JOIN places p ON p.id = m.place_id
                    WHERE {VISIBLE} AND ST_DWithin(p.coordinates, c.at, {NEAR_M})
                      AND NOT EXISTS (SELECT 1 FROM unlocks u
                                      WHERE u.device_id = c.device_id AND u.memory_id = m.id))
            FROM centre c""")
        )
        .scalars()
        .all()
    )

    return {
        "cohorts": [dict(c) for c in cohorts],
        "walks": {**walks, "opened_per_walk": float(opened)},
        "stories_left": sorted(left),
    }


def _share(hit: int, of: int) -> str:
    return f"{hit}/{of} ({hit / of:.0%})" if of else "-"


def main():
    with get_session() as session:
        m = metrics(session, date.today())
    print("Cohort      devices  D1             D7")
    for c in m["cohorts"]:
        d1 = _share(c["d1"], c["eligible_d1"])
        d7 = _share(c["d7"], c["eligible_d7"])
        print(f"{c['week']}  {c['devices']:>7}  {d1:<13}  {d7}")
    w = m["walks"]
    print(
        f"\n{w['walks']} walks by {w['walkers']} devices, {w['finished']} finished, "
        f"{w['second_walks']} a second walk that day"
    )
    print(f"Opened {w['opened_per_walk']:.1f} of {float(w['stops_per_walk']):.1f} stops a walk")
    left = m["stories_left"]
    if left:
        print(
            f"Stories left within {NEAR_M} m of the last walk: median {median(left):g}, "
            f"fewest {left[0]}, {sum(n < 4 for n in left)} of {len(left)} under one walk"
        )


if __name__ == "__main__":
    main()
