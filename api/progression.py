"""XP and level, counted from finished walks and never stored, like the
streak. Nothing here is ever sold. docs/10, "Walks earn XP; rare memories wait
for a level"."""

from math import isqrt

from sqlalchemy import text

from api.queries import FINISHED_WALKS_QUERY

# A stop is worth ten, a kilometre of walk ten.
XP_PER_STOP = 10
METERS_PER_XP = 100
# Level n+1 at 50·n² XP: a first walk is a level, then each takes longer.
XP_STEP = 50
# The rare tier: the best-scored stories (about the top tenth) join a walk
# only from this level. The gate is unchanged; this only plans the walk.
RARE_SCORE = 0.9
RARE_LEVEL = 4


def level(xp: int) -> int:
    return isqrt(xp // XP_STEP) + 1


def walk_xp(stops: int, budget_meters: int) -> int:
    return stops * XP_PER_STOP + budget_meters // METERS_PER_XP


def xp_of(session, device: str) -> int:
    walks = session.execute(text(FINISHED_WALKS_QUERY), {"device_id": device})
    return sum(walk_xp(w.stops, w.budget_meters) for w in walks)
