"""Collapse places that are one real venue split across several rows.

`db/migrations/001_places_unique.sql` made `place_query` unique, which stopped
the same exact string minting a new row every time. What it cannot catch is the
same venue described two ways. Live example, and the one this module is measured
against:

    [108] Gotham Comedy Club New York City           6 memories  40.75890, -73.98510
    [211] Gotham Comedy Club Chelsea New York City   1 memory    40.74310, -73.99670

One venue, two pins, 1.8km apart. That distance is the interesting part: both
rows claim 50m precision, so the obvious rule - collapse places whose
coordinates fall within their combined precision - would never fire. The model
disagreed with itself about where Gotham is. Names are the reliable signal here
and coordinates are only a sanity bound.

Naive token-subset matching is far too eager: it finds 148 pairs among 194
places, because "New Orleans Louisiana" is a subset of every venue in New
Orleans and would be absorbed by the first one it met. The fix needs no
gazetteer - a token that shows up in many places is a location or filler word,
and a token that shows up in few is the venue's actual name. Both sides must
therefore contribute a distinctive token, which is exactly what a bare city
reference cannot do.

Deliberately conservative: a wrong merge destroys data and is invisible
afterwards, while a missed merge is a duplicate pin somebody can see. Running
this module prints proposals and changes nothing; `--apply` performs them.

About a quarter of the proposals are wrong, and not in a way more tuning fixes -
the failures are things like a bar and a restaurant on the same block, or the
Andaz and the Comedy Store on the same stretch of Sunset. So `--apply` alone is
the wrong tool: it is all 25 or none. `--only` takes the pairs a human accepted
and refuses anything that is not in the current proposal set, which keeps the
review honest - you cannot use this to merge two rows it never suggested.
"""

import argparse
import math
import re
from collections import Counter

from sqlalchemy import text

from pipeline.db import get_session

# Words that never identify a venue: they describe a kind of place, or glue.
STOPWORDS = frozenset(
    """
a an the of at in on and or for to
bar pub club lounge cafe coffee restaurant grill diner deli bakery
theater theatre cinema venue stage arena stadium hall room house
hotel motel inn casino resort airport station museum gallery park
comedy music festival concert show
""".split()
)

# A token in at least this share of all places is a location or filler, not a
# name. 0.02 of 194 places is 4 rows - "orleans" and "manhattan" clear it
# easily, "gotham" and "carolines" do not.
COMMON_TOKEN_SHARE = 0.02

# Same venue, different guess at its coordinates. Wide because the model's
# disagreement (1.8km for Gotham) dwarfs the stated precision, but not so wide
# that two same-named venues in different cities can meet.
MAX_MERGE_KM = 8.0


def tokens(place_query: str) -> frozenset[str]:
    """Lowercase word set with stopwords and single characters removed.

    Apostrophes are dropped rather than split on, so "Caroline's" and "Carolines"
    are the same token.
    """
    cleaned = place_query.lower().replace("'", "").replace("’", "")
    return frozenset(
        w for w in re.findall(r"[a-z0-9]+", cleaned) if len(w) > 1 and w not in STOPWORDS
    )


def common_tokens(all_queries: list[str], share: float = COMMON_TOKEN_SHARE) -> frozenset[str]:
    """Tokens frequent enough across the corpus to be location or filler."""
    if not all_queries:
        return frozenset()
    counts = Counter()
    for q in all_queries:
        counts.update(tokens(q))
    threshold = max(2, math.ceil(len(all_queries) * share))
    return frozenset(t for t, n in counts.items() if n >= threshold)


def distinctive(place_query: str, common: frozenset[str]) -> frozenset[str]:
    """What is left of a name once shared location words are removed."""
    return tokens(place_query) - common


def city_level(place_query, all_queries, common):
    """True when this row names an area rather than a venue.

    Frequency alone does not catch these. "Ottawa Ontario Canada" appears twice
    in the corpus, so every one of its tokens looks distinctive, and subset
    matching then happily absorbs the city into Southam Hall. What actually
    marks an area is that its whole token set turns up inside several other
    places - things are *in* it. A venue name is contained by at most its own
    variants.
    """
    mine = distinctive(place_query, common)
    if not mine:
        return True
    containing = sum(1 for q in all_queries if q != place_query and mine < distinctive(q, common))
    return containing >= 2


def same_place(a_query, b_query, common, a_coords=None, b_coords=None, max_km=MAX_MERGE_KM):
    """True when two rows are one venue.

    Both sides must contribute a distinctive token, and one side's distinctive
    set must contain the other's, within a sanity distance.
    """
    da, db = distinctive(a_query, common), distinctive(b_query, common)
    if not da or not db:
        return False
    if not (da <= db or db <= da):
        return False
    km = distance_km(a_coords, b_coords)
    return km is None or km <= max_km


def distance_km(a, b):
    """Rough great-circle distance. None when either side lacks coordinates.

    ponytail: equirectangular, good to ~0.1% at city scale. Use PostGIS if this
    ever needs to be exact.
    """
    if not a or not b or None in a or None in b:
        return None
    (lat_a, lng_a), (lat_b, lng_b) = a, b
    dy = (lat_a - lat_b) * 111.0
    dx = (lng_a - lng_b) * 111.0 * math.cos(math.radians((lat_a + lat_b) / 2))
    return math.hypot(dx, dy)


def _load_places(session):
    rows = session.execute(
        text("""
            SELECT p.id, p.place_query, p.coordinates IS NOT NULL AS has_coords,
                   ST_Y(p.coordinates::geometry) AS lat, ST_X(p.coordinates::geometry) AS lng,
                   count(m.id) AS memories
            FROM places p
            LEFT JOIN memories m ON m.place_id = p.id
            GROUP BY p.id, p.place_query, p.coordinates
            ORDER BY p.id
        """)
    ).fetchall()
    return [
        {
            "id": r.id,
            "place_query": r.place_query,
            "coords": (r.lat, r.lng) if r.has_coords else None,
            "memories": r.memories,
        }
        for r in rows
    ]


def propose(places):
    """Pairs to merge, as (keeper, loser). Most memories wins; ties go to lowest id.

    The keeper is chosen by evidence, not by accuracy - there is no way to tell
    which of two disagreeing coordinates is right. For Gotham that means keeping
    the six-memory row even though the one-memory row is the better located of
    the two. See `geocode_status = 'conflict'` in `apply`.
    """
    queries = [p["place_query"] for p in places]
    common = common_tokens(queries)
    areas = {p["place_query"] for p in places if city_level(p["place_query"], queries, common)}

    merges, spoken_for = [], set()
    for i, a in enumerate(places):
        for b in places[i + 1 :]:
            if a["place_query"] in areas or b["place_query"] in areas:
                continue
            if not same_place(a["place_query"], b["place_query"], common, a["coords"], b["coords"]):
                continue
            keeper, loser = sorted([a, b], key=lambda p: (-p["memories"], p["id"]))
            # One row must not be both kept and dropped: chains like A<-B<-C
            # would repoint memories onto a row that is itself about to go.
            if keeper["id"] in spoken_for or loser["id"] in spoken_for:
                continue
            spoken_for.update({keeper["id"], loser["id"]})
            merges.append((keeper, loser))
    return merges


def apply(session, merges):
    """Repoint memories onto the keeper, then delete the orphaned loser.

    Same order as 001_places_unique.sql and for the same reason:
    memories.place_id is ON DELETE CASCADE, so deleting a place that still has
    memories silently destroys them. The NOT EXISTS guard turns a bug here into
    a row that stays behind instead of data that quietly vanishes.
    """
    applied = 0
    for keeper, loser in merges:
        if keeper["id"] == loser["id"]:
            continue
        session.execute(
            text("UPDATE memories SET place_id = :k WHERE place_id = :l"),
            {"k": keeper["id"], "l": loser["id"]},
        )
        # Coordinates disagreed by more than either row claimed to be accurate
        # to, and nothing here can tell which is right. Flag rather than guess.
        km = distance_km(keeper["coords"], loser["coords"])
        if km is not None and km * 1000 > 100:
            session.execute(
                text("UPDATE places SET geocode_status = 'conflict' WHERE id = :k"),
                {"k": keeper["id"]},
            )
        deleted = session.execute(
            text("""
                DELETE FROM places
                WHERE id = :l AND NOT EXISTS (SELECT 1 FROM memories WHERE place_id = :l)
            """),
            {"l": loser["id"]},
        )
        applied += deleted.rowcount
    return applied


def parse_only(spec: str, merges):
    """`--only 108:211,10:113` -> the subset of `merges` a human signed off.

    Every pair must be one this run proposed, in the same direction. Anything
    else is a typo or a stale list from a previous run against different data,
    and merging on either would be exactly the invisible data loss the rest of
    this module is arranged to avoid.
    """
    wanted = set()
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        try:
            keep, drop = (int(x) for x in pair.split(":"))
        except ValueError:
            raise SystemExit(f"--only: expected keeper:loser, got {pair!r}") from None
        wanted.add((keep, drop))

    proposed = {(k["id"], v["id"]): (k, v) for k, v in merges}
    unknown = wanted - set(proposed)
    if unknown:
        raise SystemExit(
            "--only: not proposed by this run: "
            + ", ".join(f"{k}:{v}" for k, v in sorted(unknown))
            + "\nRe-read the proposals; the data may have changed since the review."
        )
    return [proposed[pair] for pair in sorted(wanted)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="perform the merges")
    parser.add_argument(
        "--only",
        metavar="KEEP:DROP,...",
        help="apply just these reviewed pairs, instead of every proposal",
    )
    args = parser.parse_args()

    with get_session() as session:
        places = _load_places(session)
        merges = propose(places)

        for keeper, loser in merges:
            km = distance_km(keeper["coords"], loser["coords"])
            gap = "coords unknown" if km is None else f"{km:.2f}km apart"
            print(f"  keep [{keeper['id']}] {keeper['place_query']} ({keeper['memories']} mem)")
            print(f"  drop [{loser['id']}] {loser['place_query']} ({loser['memories']} mem, {gap})")
            print()

        print(f"{len(places)} places, {len(merges)} merges proposed")

        chosen = parse_only(args.only, merges) if args.only else merges
        if args.only:
            print(f"{len(chosen)} of them selected by --only")
        if args.apply:
            print(f"{apply(session, chosen)} places merged")
        else:
            print("nothing changed - pass --apply to perform them")


if __name__ == "__main__":
    main()
