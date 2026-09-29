"""Memories you can actually walk to, for development.

    python -m pipeline.seed_dev            # plant them
    python -m pipeline.seed_dev --clear    # take them away
    python -m pipeline.seed_dev --dense 300 --seed 1   # plus a full map to route over
    python -m pipeline.seed_dev --routes bimodal       # one route scenario, alone

The corpus cannot demonstrate its own mechanic. Every dense point in it is a
model-guessed centroid and therefore deliberately ungated (F7), and the memories
that *are* gated are by construction the scattered ones - so no round-number
coordinate is near any of them, and the Simulator opens on a map where the
nearest thing you could unlock is kilometres away. Setting the location does not
help; there is nothing there to reach.

This plants a cluster at FALLBACK_REGION - the coordinate the app already falls
back to and the one every doc tells you to give the Simulator - covering each
state the app can render. Idempotent: run it as often as you like.

Nothing here is true, and none of it may reach a real corpus. Everything it
writes is marked: one content row at DEV_SEED_URL, places whose place_query
starts with `dev-seed:`, and a fixed user and device. `--clear` removes exactly
those and nothing else.
"""

import argparse
import functools
import json
import math
import pathlib
import random
import struct
import subprocess
import tempfile
import zlib

from sqlalchemy import text

from api.gate import UNLOCK_RADIUS_METERS, meters_between
from api.media import MEDIA_DIR
from api.models import Coordinates
from api.queries import PLACE_INSERT, SUBMISSION_INSERT
from pipeline.db import get_session
from pipeline.extract import save_memories
from pipeline.tags import TAGS

# mobile/App.tsx FALLBACK_REGION. tests/test_seed_dev.py fails if they drift:
# the whole point is that the app's no-permission map, the documented simctl
# coordinate and this cluster are one place rather than three.
LAT, LNG = 55.67886, 12.57586

DEV_SEED_URL = "memorylane://dev-seed"
PLACE_PREFIX = "dev-seed:"
# Fixed so re-running replaces rather than accumulates.
SEED_USER = "5eed0000-0000-4000-8000-00000000d0c5"
SEED_DEVICE = "5eed0000-0000-4000-8000-00000000d5e1"

# 0.0001 degrees is ~11m of latitude and only ~6m of longitude at 55.7N, and a
# place sharing a snapped cell with another one is ungated. Every coordinate
# below is at least 0.0008 degrees from its neighbours except where the sharing
# is the point.
#
# Every one a route may pick sits within the 20m gate of a walkable way (OSRM
# `nearest`), or a street-routed walk would drop it: a pin in the middle of a
# courtyard can never be stood on.
#
# The five stops are one clean loop round the Latin Quarter blocks north of
# Strøget, Gråbrødretorv in the middle: walked from the start in
# .maestro/walk-and-unlock.yml it is ~1.3 km and retraces no street
# (api/streets.py, retraced_meters).
OFFSETS = {
    "reach": (0.001044, 0.000784),  # ~126m - Niels Hemmingsens Gade
    "walk": (0.00146, 0.000042),  # ~163m - further up it, locked and worth walking to
    "stack": (0.000013, -0.00241),  # ~151m - Skindergade, one place, three memories
    "centroid": (0.000584, -0.001794),  # ~130m - two places, so neither is gated
    "filed": (-0.000216, 0.001048),  # ~70m - Amagertorv, submitted, photo and voice
    "nightspot": (0.001756, -0.002856),  # ~265m - Fiolstræde, a second submission
}


# The places a walk may stop at: every seed but the ungated centroid pair.
STOPS = ("reach", "walk", "stack", "filed", "nightspot")


def move_to(lat: float, lng: float) -> None:
    """Plant the cluster round lat, lng instead (`--at`, e2e/run.sh's random
    start): each stop moved to the walkable way nearest its offset there. A
    layout that breaks a rule the seed stands on - a stop inside the start's
    gate, two places in one cell, `reach` not a few steps off - raises
    ValueError, and the caller picks another start."""
    global LAT, LNG
    from api.streets import _osrm

    LAT, LNG = lat, lng
    for key in STOPS:
        dlat, dlng = OFFSETS[key]
        near = Coordinates(lat=lat + dlat, lng=lng + dlng)
        slng, slat = _osrm("nearest", [near], "number=1")["waypoints"][0]["location"]
        OFFSETS[key] = (round(slat - lat, 6), round(slng - lng, 6))
    here = Coordinates(lat=lat, lng=lng)
    away = {k: meters_between(here, Coordinates(lat=a, lng=b)) for k in STOPS for a, b in [at(k)]}
    if min(away.values()) <= UNLOCK_RADIUS_METERS + 5:
        raise ValueError(f"a stop is inside the start's gate: {away}")
    if away["reach"] >= 200:
        raise ValueError(f"reach is {away['reach']:.0f}m off, not a few steps")
    cells = [cell(*at(k)) for k in OFFSETS]
    if len(set(cells)) < len(cells):
        raise ValueError("two seeded places share a grid cell, which ungates both")


def at(key: str) -> tuple[float, float]:
    dlat, dlng = OFFSETS[key]
    return round(LAT + dlat, 6), round(LNG + dlng, 6)


def memory(key: str, name: str, summary: str, tags: list[str], **extra) -> dict:
    """One dict in the shape save_memories reads."""
    lat, lng = at(key)
    return {
        "lat": lat,
        "lng": lng,
        "place_name": name,
        # The marker, and what --clear matches on.
        "place_query": f"{PLACE_PREFIX}{key}",
        "location_precision": "exact",
        "summary": summary,
        "tags": tags,
        "confidence": "high",
        "timestamp_start": 0,
        **extra,
    }


def extracted() -> list[dict]:
    """The podcast-shaped memories: a content row, no author.

    `stack` appears three times with the same place_query on purpose.
    save_memories does ON CONFLICT (place_query), so that is one place with
    three memories - which stacks the pin while leaving the coordinate unshared,
    and so still gated. Three *places* at one point would stack the pin too and
    silently ungate all three.
    """
    return [
        memory(
            "reach",
            "Ringkaféen, dev seed",
            "Ringkaféen has stood on Folmer Bendtsens Plads since the 1930s and sank into "
            "the ground after metro construction broke through to the old Lygteå stream "
            "running beneath the asphalt. Cracks were visible in the building's facade "
            "until recently, and the owners hail from Montenegro, giving the corner bar a "
            "faint Balkan-meets-Paris feel.",
            ["history", "drink", "culture"],
        ),
        memory(
            "walk",
            "Nørrebrogade bridge, dev seed",
            "One year during Trip Nørrebro, the annual pub crawl, participants stripped off "
            "their clothes at the bridge on Nørrebrogade, jumped into the water, swam to the "
            "other side, and got dressed again. Maleren, the crawl's founder, recalled it as "
            "one of the era's wilder stunts.",
            ["nightlife", "strange", "adventure"],
        ),
        memory(
            "stack",
            "Woodstock, dev seed",
            "During the 'værtshuskrigen', when the state tried stripping Christiania's bars "
            "of alcohol licenses and equipment, Woodstock was completely gutted, with "
            "truckloads of bar stools, bottles and beer crates hauled away. But the bar "
            "counter itself stayed standing, since a customer had mortared it in with a "
            "technique so solid even police with the right tools couldn't remove it.",
            ["history", "strange", "drink"],
        ),
        memory(
            "stack",
            "Woodstock, dev seed",
            "At Woodstock, deceased regulars are remembered with a breakfast tray bearing "
            "their name hung on a 'mindeparaply', a memorial umbrella. Customers toss spare "
            "coins onto it as tips, and the money goes to the bereaved for flowers or "
            "funeral costs; in hard times three trays have hung there at once.",
            ["culture", "personal", "history"],
        ),
        memory(
            "stack",
            "Woodstock, dev seed",
            "The wooden building that houses Woodstock was built by the German military "
            "during World War II, when they occupied the barracks and needed a motorcycle "
            "repair workshop of their own between the larger existing structures. They "
            "built this small shed to service their military motorcycles, and it later "
            "became the bar.",
            ["history", "drink"],
        ),
        memory(
            "centroid",
            "Hedebygade, dev seed",
            "Tove Ditlevsen grew up on Hedebygade, a hard working-class street on Vesterbro "
            "at the time. This is the street she immortalized as 'barndommens gade' (the "
            "street of childhood) in her book Barndom, writing unsparingly about what it "
            "meant to be a child here.",
            ["history", "culture", "personal"],
        ),
    ]


def centroid_twin(session) -> None:
    """A second place on the centroid's exact coordinate, which is what makes it
    ungated. Nothing else in the seed shares a snapped cell."""
    lat, lng = at("centroid")
    place_id = session.execute(
        text(PLACE_INSERT),
        {
            "name": "The same rough spot, dev seed",
            "place_query": f"{PLACE_PREFIX}centroid-twin",
            "lat": lat,
            "lng": lng,
            "precision_meters": 10000,
        },
    ).scalar()
    content_id = content_id_of(session)
    session.execute(
        text("""
            INSERT INTO memories (place_id, content_id, timestamp_start, summary,
                                  tags, extraction_confidence, layer)
            VALUES (:p, :c, 0, :s, CAST(:t AS varchar[]), 'high', 'historical')
        """),
        {
            "p": place_id,
            "c": content_id,
            "s": "The second memory filed to this same guessed coordinate. Two "
            "places on one point is exactly what leaves both of them open.",
            "t": ["culture"],
        },
    )


def png(width: int, height: int) -> bytes:
    """A real PNG, written by hand rather than adding Pillow for one image.

    Not a 1x1: the sheet renders photos at 4:3 and a single pixel proves nothing
    about layout. This is a warm gradient with a darker band, so it is obvious on
    screen that an actual image loaded.
    """

    def row(y: int) -> bytes:
        top = y / height
        band = 0.55 < top < 0.62
        return b"".join(
            bytes(
                (40, 36, 32)
                if band
                else (
                    int(200 - 60 * top + 30 * (x / width)),
                    int(150 - 40 * top + 20 * (x / width)),
                    int(110 - 30 * top),
                )
            )
            for x in range(width)
        )

    raw = b"".join(b"\x00" + row(y) for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def recording(destination: pathlib.Path) -> float | None:
    """A real spoken AAC clip via macOS `say` and `afconvert`.

    A silent placeholder would not tell you whether playback works. There is no
    ffmpeg here; where these two are absent the seed skips the audio rather than
    writing something that will not play. Returns the duration in seconds.
    """
    spoken = _spoken()
    if spoken is None:
        return None
    destination.write_bytes(spoken[0])
    return spoken[1]


@functools.cache
def _spoken() -> tuple[bytes, float] | None:
    """Made once per process: ~1.8s of subprocesses, and every test that
    seeds used to pay it again."""
    with tempfile.TemporaryDirectory() as tmp:
        destination = pathlib.Path(tmp) / "clip.m4a"
        aiff = pathlib.Path(tmp) / "clip.aiff"
        words = (
            "This is a seeded recording. If you can hear this, the audio player "
            "in the memory sheet is working."
        )
        try:
            # A wedged speech daemon hangs `say` for ever, and the e2e run with it.
            subprocess.run(
                ["say", "-o", str(aiff), words], check=True, capture_output=True, timeout=20
            )
            subprocess.run(
                ["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(destination)],
                check=True,
                capture_output=True,
                timeout=20,
            )
        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return None

        probe = subprocess.run(
            ["afinfo", str(destination)], capture_output=True, text=True, check=False
        )
        for line in probe.stdout.splitlines():
            if "estimated duration" in line:
                seconds = round(float(line.split(":")[1].strip().split()[0]), 1)
                return destination.read_bytes(), seconds
    return None


def seed_user(session) -> None:
    """The author every seeded submission is filed under."""
    session.execute(
        text(
            "INSERT INTO users (id, display_name) VALUES (CAST(:id AS uuid), :n) "
            "ON CONFLICT (id) DO UPDATE SET display_name = :n"
        ),
        {"id": SEED_USER, "n": "Dev Seed"},
    )
    session.execute(
        text(
            "INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), CAST(:u AS uuid)) "
            "ON CONFLICT (id) DO UPDATE SET user_id = CAST(:u AS uuid)"
        ),
        {"d": SEED_DEVICE, "u": SEED_USER},
    )


def filed_by_a_person(session) -> tuple[int, list[str]]:
    """The submission-shaped memory: an author, the stranger layer, and media.

    Always gated, whatever its neighbours do - `user_id IS NOT NULL` is the other
    half of is_gated. Written through the same INSERTs api/write.py uses.
    """
    seed_user(session)

    lat, lng = at("filed")
    place_id = session.execute(
        text(PLACE_INSERT),
        {
            "name": "Where I was standing, dev seed",
            "place_query": f"{PLACE_PREFIX}filed",
            "lat": lat,
            "lng": lng,
            "precision_meters": 25,
        },
    ).scalar()
    memory_id = session.execute(
        text(SUBMISSION_INSERT),
        {
            "place_id": place_id,
            "summary": "I filed this one myself, standing right here, so it has a "
            "name under it and a Report control that the extracted ones do not.",
            "tags": ["personal", "strange"],
            "happened_at": None,
            "happened_precision": None,
            "user_id": SEED_USER,
        },
    ).scalar()

    made = []
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    photo = MEDIA_DIR / "dev-seed-photo.png"
    photo.write_bytes(png(480, 360))
    session.execute(
        text("""
            INSERT INTO media (memory_id, device_id, kind, path, mime, bytes)
            VALUES (:m, CAST(:d AS uuid), 'photo', :p, 'image/png', :b)
        """),
        {"m": memory_id, "d": SEED_DEVICE, "p": photo.name, "b": photo.stat().st_size},
    )
    made.append("photo")

    clip = MEDIA_DIR / "dev-seed-clip.m4a"
    seconds = recording(clip)
    if seconds is None:
        clip.unlink(missing_ok=True)
        made.append("no audio (needs macOS say + afconvert)")
    else:
        session.execute(
            text("""
                INSERT INTO media (memory_id, device_id, kind, path, mime, bytes,
                                   duration_seconds)
                VALUES (:m, CAST(:d AS uuid), 'audio', :p, 'audio/m4a', :b, :s)
            """),
            {
                "m": memory_id,
                "d": SEED_DEVICE,
                "p": clip.name,
                "b": clip.stat().st_size,
                "s": seconds,
            },
        )
        made.append(f"{seconds:.0f}s recording")

    return memory_id, made


def a_second_submission(session) -> int:
    """A second stranger-layer memory, ~200m out - locked, and tagged unlike
    the first one. `filed` alone gave the seed exactly one submission, which
    is enough to demonstrate the layer but not enough to demonstrate mixing
    them, which anything choosing across both layers (a route, a tag glyph
    on a submission) needs at least two of to show.
    """
    lat, lng = at("nightspot")
    place_id = session.execute(
        text(PLACE_INSERT),
        {
            "name": "Where the night went long, dev seed",
            "place_query": f"{PLACE_PREFIX}nightspot",
            "lat": lat,
            "lng": lng,
            "precision_meters": 25,
        },
    ).scalar()
    return session.execute(
        text(SUBMISSION_INSERT),
        {
            "place_id": place_id,
            "summary": "Somebody put the jukebox on shuffle at midnight and refused "
            "to explain the last three songs it picked.",
            "tags": ["drink", "nightlife"],
            "happened_at": None,
            "happened_precision": None,
            "user_id": SEED_USER,
        },
    ).scalar()


# Walkable points over central Copenhagen, each already snapped to a way by OSRM `nearest`
# and each in its own 0.0001-degree cell, so --dense stays offline. Written by
# --snap-pool against a running sidecar; re-run it only to change the area.
POOL = pathlib.Path(__file__).with_name("cph_ways.json")
POOL_BOX = (0.007, 0.0125)  # half-height, half-width in degrees: ~1.5km square at 55.7N


def cell(lat: float, lng: float) -> tuple[int, int]:
    """The snapped grid cell COORDINATE_IS_UNIQUE compares on."""
    return round(lat / 0.0001), round(lng / 0.0001)


def snap_pool(tries: int = 4000) -> list[list[float]]:
    from api.streets import _osrm

    rng = random.Random(0)
    taken = {cell(*at(k)) for k in OFFSETS}
    pool = []
    for _ in range(tries):
        here = Coordinates(
            lat=LAT + rng.uniform(-POOL_BOX[0], POOL_BOX[0]),
            lng=LNG + rng.uniform(-POOL_BOX[1], POOL_BOX[1]),
        )
        lng, lat = _osrm("nearest", [here], "number=1")["waypoints"][0]["location"]
        lat, lng = round(lat, 6), round(lng, 6)
        if cell(lat, lng) not in taken:
            taken.add(cell(lat, lng))
            pool.append([lat, lng])
    return pool


# Real summaries (extracted 2026-09-27, Københavnerliv) for the --dense and
# --routes filler, so a full map reads like the product. Picked by index, not
# rng, so a --seed keeps planting the same map.
REAL = (
    "The crawl's second stop sits down Nordre Fasanvej from Maskot, an old inn from the "
    "early 1900s that once held a royal charter and stabled the king's horses. New owners "
    "now mix events and youthful crowds with the old regulars, who still smoke in one end "
    "and play the jukebox in the other.",
    "This is where Trip Nørrebro, the yearly pub crawl through Nørrebro's old brown bars, "
    "began in 1996. It started quiet and small, just crates of beer and a beer relay among "
    "friends, before escalating over the following two or three years into the massive "
    "30-year tradition it became.",
    "Jørgen Leth sat in this chair every Wednesday for a clean shave with hot towels and a "
    "blade, right up until near the end of his life. On his last visit he forgot his "
    "glasses, which his barber left in place, turned toward the chair, so that Leth's eyes "
    "still watch him work each day.",
    "The barbershop where Jørgen Leth was a longtime customer was founded in 1937, the same "
    "year he was born, originally set up so Egmont's executives next door could be groomed. "
    "Its black glass fittings and chairs are still the originals from that year.",
    "In his last years, Jørgen Leth arrived here by taxi around 12:30 and was led in with "
    "his cane and jacket by his barber of many years. Too frail to climb into the tall, old "
    "leather barber chair alone, he was lifted up only when the barber pressed a foot "
    "against his to hoist him together.",
    "Woodstock had been painted classic red for decades, after starting out light green, "
    "until the team decided last summer it needed color. Nico Hageman, a Copenhagen "
    "graffiti artist based on Christiania, took on the job and covered the whole exterior "
    "in his distinctive spray style, adding patterns, flowers and smiling smileys.",
    "Tove Ditlevsen spent her entire childhood on the fourth floor of this Hedebygade "
    "building. Standing by the very entrance gate, a passage from her memoir Barndom was "
    "read aloud, describing the reek of beer and urine on the stairs and a neighbor, Fru "
    "Poulsen, beckoning her inside.",
    "Tove Ditlevsen, the Vesterbro-born poet and author, was buried from Kristkirken on "
    "Enghaveplads nearly 50 years ago. Not a single seat inside was empty, as mostly women "
    "came to say a proper farewell to the writer whose work had guided how they thought "
    "about living a life.",
    "Copenhagen named this square after Tove Ditlevsen and set lines of her poetry into the "
    "paving stones around it, including 'the one is him I love, the other loves me' - her "
    "poetry at its simplest and purest.",
    "Tove Ditlevsen's funeral packed the church while several hundred more people waited "
    "outside. When the coffin emerged, the women present spontaneously bowed as if she were "
    "royalty, and a procession followed it away, an almost state-like farewell rare for a "
    "Danish writer.",
    "Fuglereden, standing in an old corner building with a small tower on Frederiksborgvej, "
    "was one of the last of its kind in Nordvest after the landowner tried to tear it down "
    "to build four-story youth housing. Local protests forced a compromise, sparing the "
    "1886 building while the owner built on nearby garages on Porsvej instead.",
    "Dennis fell in love with this corner building in 1998 and wanted to run a pub there, "
    "but the liquor authority initially refused because a school stood right opposite. He "
    "later got it going anyway with encouragement from the property owner.",
    "A bar once called Glashuset, in Nordvest, got converted into a more standard beer bar, "
    "and in the process lost its billiard table, its jukebox and its cigarettes. What "
    "remained felt sterile compared to before, marking a shift in the neighborhood's "
    "character.",
    "After new owners took over Glendekroen, they pushed out some of the old regulars, "
    "banned smoking inside, and began hosting bingo nights and karaoke while showing "
    "football. Anders said the change made the bar more welcoming to people who once felt "
    "intimidated by the old crowd of smokers and drinkers.",
)


def plant(session, content_id, rng, label, i, lat, lng, stranger=None, memories=1, name=None):
    """One place for --dense or --routes carrying `memories` memories: a
    submission a third of the time unless `stranger` says, random tags and a
    random contrast_score. The draws stay in this order so a --seed keeps
    planting the same map."""
    key = f"{PLACE_PREFIX}{label.lower()}-{i}"
    name = f"{name or label.capitalize()} {i}, dev seed"
    summaries = [REAL[(i + j) % len(REAL)] for j in range(memories)]
    tags = rng.sample(TAGS, rng.randint(1, 2))
    if stranger is None:
        stranger = rng.random() < 1 / 3
    if stranger:
        place_id = session.execute(
            text(PLACE_INSERT),
            {"name": name, "place_query": key, "lat": lat, "lng": lng, "precision_meters": 25},
        ).scalar()
        for summary in summaries:
            session.execute(
                text(SUBMISSION_INSERT),
                {
                    "place_id": place_id,
                    "summary": summary,
                    "tags": tags,
                    "happened_at": None,
                    "happened_precision": None,
                    "user_id": SEED_USER,
                },
            )
    else:
        # One place_query, so a stack is one place with several memories.
        save_memories(
            session,
            content_id,
            [
                memory("reach", name, summary, tags, lat=lat, lng=lng, place_query=key)
                for summary in summaries
            ],
        )
    session.execute(
        text("""
            UPDATE memories SET contrast_score = :c WHERE place_id =
                (SELECT id FROM places WHERE place_query = :q)
        """),
        {"c": round(rng.random(), 2), "q": key},
    )


def content_id_of(session) -> int:
    return session.execute(
        text("SELECT id FROM content WHERE url = :u"), {"u": DEV_SEED_URL}
    ).scalar()


def dense(session, n: int, seed: int) -> int:
    """`n` memories from POOL, chosen and dressed by `random.Random(seed)`: a
    map full enough that a route has to choose its five. A third are
    submissions, the rest extracted; tags and contrast_score at random."""
    rng = random.Random(seed)
    points = rng.sample(json.loads(POOL.read_text()), n)
    content_id = content_id_of(session)
    for i, (lat, lng) in enumerate(points):
        plant(session, content_id, rng, "dense", i, lat, lng)
    return n


# --routes: maps shaped to tell one solver from another, each planted alone -
# a scenario on top of the cluster above would route through the cluster.
# Four sample POOL; the two outside it are committed in SCENARIOS, written by
# --snap-scenarios against a running sidecar.
ROUTE_SCENARIOS = {
    "sparse": "2 stops 250-400m out: a walk that cannot fill",
    "dense": "40 stops in the 1 km square round the start",
    "bimodal": "two clusters either side of the harbour, where crow-flies lies most",
    "linear": "stops strung along Nørrebrogade, the lakes to Frederikssundsvej",
    "one-layer": "20 stops, every one historical: nothing for the layer mix to do",
    "stack-heavy": "8 places carrying 3-6 memories each",
    "lakes": "Copenhagen: round the three lakes from Olufsvej, ~9 km, named by lake",
}
SCENARIOS = pathlib.Path(__file__).with_name("route_scenarios.json")
# Amaliegade and Holmen, facing each other across Inderhavnen: ~500 m apart
# and ~2.2 km to walk, round by Inderhavnsbroen.
HARBOUR_SIDES = ((55.6875, 12.5965), (55.6850, 12.6025))
# Nørrebrogade from Dronning Louises Bro, Nørrebros Runddel, Nørrebro
# station, on up Frederikssundsvej: ~3.8 km on OSRM.
NØRREBROGADE = (
    (55.6868, 12.5617),
    (55.6930, 12.5490),
    (55.7007, 12.5378),
    (55.7055, 12.5290),
)
# Olufsvej, then down the city banks to the tip of Sankt Jørgens Sø and back up
# the far ones: Øster Søgade, Nørre Søgade, Vester Søgade, Svineryggen, Peblinge
# and Sortedam Dossering. Measured on OSRM at ~9.1 km, under the slider's 10.
OLUFSVEJ = (55.7007, 12.5759)
LAKES_LOOP = (
    OLUFSVEJ,
    (55.6955, 12.5790),
    (55.6875, 12.5670),
    (55.6828, 12.5622),
    (55.6748, 12.5600),
    (55.6775, 12.5565),
    (55.6856, 12.5609),
    (55.6930, 12.5708),
    OLUFSVEJ,
)
# Each lake as a line from its north-east end to its south-west one: they are
# long and thin, and a point at one end of Sortedams Sø is nearer the middle of
# Peblinge Sø than the middle of its own lake.
LAKES = {
    "Sortedams Sø": ((55.6970, 12.5795), (55.6872, 12.5645)),
    "Peblinge Sø": ((55.6870, 12.5630), (55.6815, 12.5595)),
    "Sankt Jørgens Sø": ((55.6810, 12.5585), (55.6745, 12.5595)),
}


def lake_of(lat: float, lng: float) -> str:
    """The lake a point is on the bank of, or where it is on the way down."""

    def off(end_a, end_b) -> float:
        # Flat metres: the lakes are 3 km across, so the error is centimetres.
        k = math.cos(math.radians(lat))
        ax, ay, bx, by = end_a[1] * k, end_a[0], end_b[1] * k, end_b[0]
        px, py = lng * k, lat
        t = max(
            0,
            min(
                1,
                ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2),
            ),
        )
        return math.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay)) * 111_320

    lake, metres = min(((name, off(*ends)) for name, ends in LAKES.items()), key=lambda x: x[1])
    if metres < 200:
        return lake
    here = Coordinates(lat=lat, lng=lng)
    home = meters_between(here, Coordinates(lat=OLUFSVEJ[0], lng=OLUFSVEJ[1]))
    return "Olufsvej" if home < 150 else "On the way to the lakes"


def within(points, lat: float, lng: float, half_meters: float) -> list:
    """The points inside a square of side 2 * half_meters centred on lat, lng."""
    dlat = half_meters / 111_320
    dlng = dlat / math.cos(math.radians(lat))
    return [p for p in points if abs(p[0] - lat) <= dlat and abs(p[1] - lng) <= dlng]


def along(line, every: float, keep) -> list[list[float]]:
    """A point every `every` metres of an OSRM geometry, each in a free cell."""
    points, walked, last = [], every, None
    for lng, lat in line:
        here = Coordinates(lat=lat, lng=lng)
        if last is not None:
            walked += meters_between(last, here)
        last = here
        if walked >= every and keep(round(lat, 6), round(lng, 6)):
            points.append([round(lat, 6), round(lng, 6)])
            walked = 0.0
    return points


def snap_scenarios() -> dict:
    from api.streets import _osrm

    rng = random.Random(0)
    taken = set()

    def keep(lat, lng) -> bool:
        if cell(lat, lng) in taken:
            return False
        taken.add(cell(lat, lng))
        return True

    bimodal = []
    dlat = 150 / 111_320
    for side_lat, side_lng in HARBOUR_SIDES:
        dlng = dlat / math.cos(math.radians(side_lat))
        side = []
        while len(side) < 10:
            lat = side_lat + rng.uniform(-dlat, dlat)
            lng = side_lng + rng.uniform(-dlng, dlng)
            w = _osrm("nearest", [Coordinates(lat=lat, lng=lng)], "number=1")["waypoints"][0]
            lng, lat = (round(x, 6) for x in w["location"])
            if w["distance"] < 20 and keep(lat, lng):
                side.append([lat, lng])
        bimodal += side

    # The foot route through the street's own junctions keeps to it; a point
    # every ~80m of it.
    line = _osrm(
        "route",
        [Coordinates(lat=a, lng=b) for a, b in NØRREBROGADE],
        "overview=full&geometries=geojson",
    )["routes"][0]["geometry"]["coordinates"]
    linear = along(line, 80, keep)

    # One every ~400m of the loop, so a shorter walk has real choices. Not the
    # first, which is the doorstep.
    loop = _osrm(
        "route",
        [Coordinates(lat=a, lng=b) for a, b in LAKES_LOOP],
        "overview=full&geometries=geojson",
    )["routes"][0]["geometry"]["coordinates"]
    lakes = along(loop, 400, keep)[1:]

    return {
        "bimodal": {"start": list(HARBOUR_SIDES[0]), "points": bimodal},
        "linear": {"start": list(NØRREBROGADE[1]), "points": linear},
        "lakes": {"start": list(OLUFSVEJ), "points": lakes},
    }


def scenario(session, name: str, seed: int) -> tuple[tuple[float, float], int]:
    """Plant one ROUTE_SCENARIOS map, alone. Returns where to stand and how many
    places it planted."""
    clear(session)
    content_row(session)
    seed_user(session)
    rng = random.Random(seed)
    pool = json.loads(POOL.read_text())
    square = within(pool, LAT, LNG, 500)
    here = Coordinates(lat=LAT, lng=LNG)
    start, stranger, stacked = (LAT, LNG), None, False
    if name == "sparse":
        ring = [
            p for p in pool if 250 <= meters_between(here, Coordinates(lat=p[0], lng=p[1])) <= 400
        ]
        points = rng.sample(ring, 2)
    elif name == "dense":
        points = rng.sample(square, 40)
    elif name == "one-layer":
        points, stranger = rng.sample(square, 20), False
    elif name == "stack-heavy":
        points, stacked = rng.sample(square, 8), True
    else:
        fixed = json.loads(SCENARIOS.read_text())[name]
        start, points = tuple(fixed["start"]), fixed["points"]

    content_id = content_id_of(session)
    for i, (lat, lng) in enumerate(points):
        memories = rng.randint(3, 6) if stacked else 1
        place = lake_of(lat, lng) if name == "lakes" else None
        plant(session, content_id, rng, name, i, lat, lng, stranger, memories, place)
    return start, len(points)


def clear(session) -> int:
    """Remove exactly what seed() wrote.

    Deleting the places cascades their memories, which is why the content row
    alone is not enough - the submitted memory has no content_id at all.
    """
    removed = session.execute(
        text(f"DELETE FROM places WHERE place_query LIKE '{PLACE_PREFIX}%'")
    ).rowcount
    session.execute(text("DELETE FROM content WHERE url = :u"), {"u": DEV_SEED_URL})
    session.execute(text("DELETE FROM users WHERE id = CAST(:id AS uuid)"), {"id": SEED_USER})
    session.execute(text("DELETE FROM devices WHERE id = CAST(:id AS uuid)"), {"id": SEED_DEVICE})
    for leftover in MEDIA_DIR.glob("dev-seed-*"):
        leftover.unlink(missing_ok=True)
    return removed


def unlock_nearest(session, n: int) -> str | None:
    """Unlock the n seeded memories nearest the cluster for the device seen
    last - the app's own, self-minted id - so the journal is not empty on a
    fresh start. None when the app has not registered a device yet."""
    device = session.execute(
        text(
            "SELECT id FROM devices WHERE id <> CAST(:seed AS uuid) "
            "ORDER BY last_seen DESC NULLS LAST LIMIT 1"
        ),
        {"seed": SEED_DEVICE},
    ).scalar()
    if device is None:
        return None
    session.execute(
        text(f"""
            INSERT INTO unlocks (device_id, memory_id)
            SELECT :d, m.id FROM memories m JOIN places p ON p.id = m.place_id
            WHERE p.place_query LIKE '{PLACE_PREFIX}%'
            ORDER BY p.coordinates <-> ST_MakePoint(:lng, :lat)::geography
            LIMIT :n
            ON CONFLICT DO NOTHING
        """),
        {"d": device, "n": n, "lat": LAT, "lng": LNG},
    )
    return str(device)


def content_row(session) -> int:
    """The one content row every seeded extracted memory hangs off."""
    return session.execute(
        text("""
            INSERT INTO content (url, platform, platform_id, source_type, source_name, title,
                                 transcript_fetched, memories_extracted)
            VALUES (:u, 'dev', 'dev-seed', 'video', 'Dev Seed', 'Seeded for development',
                    TRUE, TRUE)
            RETURNING id
        """),
        {"u": DEV_SEED_URL},
    ).scalar()


def seed(session) -> dict:
    clear(session)

    content_id = content_row(session)

    save_memories(session, content_id, extracted())
    centroid_twin(session)
    filed_id, media = filed_by_a_person(session)
    nightspot_id = a_second_submission(session)

    return {
        "content_id": content_id,
        "filed_id": filed_id,
        "nightspot_id": nightspot_id,
        "media": media,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clear", action="store_true", help="remove the seed and stop")
    maps = parser.add_mutually_exclusive_group()
    maps.add_argument("--dense", type=int, metavar="N", help="also plant N random memories")
    maps.add_argument(
        "--routes",
        choices=ROUTE_SCENARIOS,
        help="plant one route scenario instead: "
        + "; ".join(f"{k}: {v}" for k, v in ROUTE_SCENARIOS.items()),
    )
    parser.add_argument(
        "--unlock",
        type=int,
        nargs="?",
        const=5,
        metavar="N",
        help="also unlock the N nearest (default 5) for the app's device",
    )
    parser.add_argument("--seed", type=int, default=1, help="which random map (--dense, --routes)")
    parser.add_argument(
        "--at", metavar="LAT,LNG", help="plant the cluster there, stops snapped (needs ROUTING_URL)"
    )
    parser.add_argument(
        "--snap-pool", action="store_true", help=f"rewrite {POOL.name} (needs ROUTING_URL)"
    )
    parser.add_argument(
        "--snap-scenarios",
        action="store_true",
        help=f"rewrite {SCENARIOS.name} (needs ROUTING_URL)",
    )
    args = parser.parse_args()

    if args.snap_scenarios:
        SCENARIOS.write_text(json.dumps(snap_scenarios(), separators=(",", ":")) + "\n")
        print(f"wrote {', '.join(json.loads(SCENARIOS.read_text()))} to {SCENARIOS}")
        return

    if args.snap_pool:
        pool = snap_pool()
        POOL.write_text(json.dumps(pool, separators=(",", ":")) + "\n")
        print(f"wrote {len(pool)} walkable points to {POOL}")
        return

    with get_session() as session:
        if args.clear:
            print(f"removed {clear(session)} seeded places and everything hanging off them")
            return
        if args.routes:
            (lat, lng), n = scenario(session, args.routes, args.seed)
            print(f"planted {args.routes}, {n} places: {ROUTE_SCENARIOS[args.routes]}")
            print(f"  stand at {lat},{lng}")
            print(f"  xcrun simctl location booted set {lat},{lng}")
            return
        if args.at:
            try:
                move_to(*(float(x) for x in args.at.split(",")))
            except ValueError as refused:
                # 3, not 1: e2e/run.sh reads it as "try another start".
                print(f"refused {args.at}: {refused}")
                raise SystemExit(3) from None
        made = seed(session)
        if args.dense:
            print(f"planted {dense(session, args.dense, args.seed)} dense memories")
        if args.unlock:
            device = unlock_nearest(session, args.unlock)
            print(
                f"unlocked {args.unlock} for device {device}"
                if device
                else "nothing unlocked: launch the app once so it registers a device"
            )

    print(f"seeded at {LAT},{LNG} — {', '.join(made['media'])}")
    here = Coordinates(lat=LAT, lng=LNG)
    for key in OFFSETS:
        lat, lng = at(key)
        # The server's own haversine, so the printed distance is the one the
        # gate will measure rather than an approximation of it.
        metres = meters_between(here, Coordinates(lat=lat, lng=lng))
        print(f"  {key:9} {lat},{lng}  {metres:>4.0f}m")
    print()
    print(
        "  in reach now: reach, stack, filed     locked: walk, nightspot     open to all: centroid"
    )
    print()
    print("point the Simulator at it:")
    print(f"  xcrun simctl location booted set {LAT},{LNG}")
    print("or skip that entirely, in mobile/.env:")
    print(f"  EXPO_PUBLIC_DEV_LOCATION={LAT},{LNG}")


if __name__ == "__main__":
    main()
