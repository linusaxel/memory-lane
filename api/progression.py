"""XP, level and loot, counted from finished walks and never stored, like the
streak. Nothing here is ever sold. docs/10, "Walks earn XP; rare memories wait
for a level"."""

import zlib
from math import isqrt

from sqlalchemy import text

from api.models import Item
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

# Append only: a walk's drop is its index into this, so a reorder would hand
# everyone different loot. ponytail: derived inventory, a table once items are
# equipped or traded.
ITEMS = [
    ("Tram ticket", "tram.fill", "Punched on a line that no longer runs."),
    ("Harbour stamp", "ferry.fill", "Smells faintly of tar."),
    ("Pressed leaf", "leaf.fill", "From a tree older than the street."),
    ("Brass key", "key.fill", "Opens nothing. Fits somewhere."),
    ("Lamplighter's match", "flame.fill", "Struck once, at dusk."),
    ("Postcard: the square", "photo.fill", "Wish you were here."),
    ("Gull feather", "bird.fill", "Left on a bollard."),
    ("Rain-spotted map", "map.fill", "Someone else's route, in pencil."),
    ("Bicycle bell", "bell.fill", "Two rings, then quiet."),
    ("Old coin", "dollarsign.circle.fill", "Worn smooth by pockets."),
    ("Cinema stub", "film.fill", "Row 7, seat 12."),
    ("Church bell note", "music.note", "Rung on the hour."),
    ("Cobblestone chip", "square.fill", "From a street being relaid."),
    ("Paper boat", "sailboat.fill", "Folded from a timetable."),
    ("Postcard: the lake", "water.waves", "Calm, for once."),
    ("Night bus token", "moon.stars.fill", "Last one home."),
    ("Bakery string", "birthday.cake.fill", "Still tied in a bow."),
    ("Compass", "safari.fill", "Points the way you came."),
]


def level(xp: int) -> int:
    return isqrt(xp // XP_STEP) + 1


def walk_xp(stops: int, budget_meters: int) -> int:
    return stops * XP_PER_STOP + budget_meters // METERS_PER_XP


def drop(route_id: int, levelled: bool) -> int | None:
    """Which item a finished walk left, if any: one walk in three, by surprise,
    and always on a level up. Hashed from the walk, so every device agrees."""
    h = zlib.crc32(str(route_id).encode())
    return h % len(ITEMS) if levelled or h % 3 == 0 else None


def progress(walks) -> tuple[int, list[Item]]:
    """(xp, items found) from finished walks, oldest first."""
    xp = 0
    counts: dict[int, int] = {}
    for w in walks:
        before = level(xp)
        xp += walk_xp(w.stops, w.budget_meters)
        found = drop(w.id, level(xp) > before)
        if found is not None:
            counts[found] = counts.get(found, 0) + 1
    items = [
        Item(index=i, name=ITEMS[i][0], glyph=ITEMS[i][1], line=ITEMS[i][2], count=n)
        for i, n in sorted(counts.items())
    ]
    return xp, items


def progress_of(session, device: str) -> tuple[int, list[Item]]:
    return progress(session.execute(text(FINISHED_WALKS_QUERY), {"device_id": device}))
