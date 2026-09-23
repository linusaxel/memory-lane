"""Memories you can actually walk to, for development.

    python -m pipeline.seed_dev            # plant them
    python -m pipeline.seed_dev --clear    # take them away

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
import datetime
import pathlib
import struct
import subprocess
import tempfile
import zlib

from sqlalchemy import text

from api.gate import meters_between
from api.media import MEDIA_DIR
from api.models import Coordinates
from api.queries import PLACE_INSERT, SUBMISSION_INSERT
from pipeline.db import get_session
from pipeline.extract import save_memories

# mobile/App.tsx FALLBACK_REGION. tests/test_seed_dev.py fails if they drift:
# the whole point is that the app's no-permission map, the documented simctl
# coordinate and this cluster are one place rather than three.
LAT, LNG = 40.7484, -73.9857

DEV_SEED_URL = "memorylane://dev-seed"
PLACE_PREFIX = "dev-seed:"
# Fixed so re-running replaces rather than accumulates.
SEED_USER = "5eed0000-0000-4000-8000-00000000d0c5"
SEED_DEVICE = "5eed0000-0000-4000-8000-00000000d5e1"

# 0.0001 degrees is ~11m of latitude and only ~8m of longitude at 40.7N, and a
# place sharing a snapped cell with another one is ungated. Every coordinate
# below is at least 0.0008 degrees from its neighbours except where the sharing
# is the point.
#
# Every one a route may pick sits within the 20m gate of a walkable way (OSRM
# `nearest`), or a street-routed walk would drop it: a pin in the middle of the
# Empire State Building can never be stood on. `sealed` is the exception - it
# is never a stop - and sits inside the gate of the dev coordinate itself.
#
# The five stops are one clean loop round the blocks between 33rd and 35th,
# 5th Ave and Broadway: walked from the start in .maestro/walk-and-unlock.yml
# it retraces ~4m of street (api/streets.py, retraced_meters).
OFFSETS = {
    "reach": (0.00036, 0.00118),  # ~105m - 5th Ave above 34th
    "walk": (0.00132, 0.00001),  # ~147m - along 35th, locked and worth walking to
    "stack": (0.000374, -0.001793),  # ~155m - Broadway at 34th, one place, three memories
    "centroid": (0.0006, -0.0013),  # ~130m - two places, so neither is gated
    "filed": (-0.00035, 0.00068),  # ~70m - 5th Ave below 34th, submitted, photo and voice
    "sealed": (-0.00012, 0.00012),  # ~16m - a time capsule: in reach and still shut
    "nightspot": (0.002, -0.0015),  # ~260m - 6th Ave at 35th, a second submission
}


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
            "The bench outside, dev seed",
            "We sat here for an hour arguing about whether the pretzel cart was "
            "the same pretzel cart. It was not, and the man knew it.",
            ["food", "strange"],
        ),
        memory(
            "walk",
            "Along 35th Street, dev seed",
            "The night the power went out on this block and somebody wheeled a "
            "piano into the street. Nobody could agree who it belonged to.",
            ["music", "nightlife"],
        ),
        memory(
            "stack",
            "The corner, dev seed",
            "First of three at this exact point: the taxi that reversed the "
            "whole length of the block rather than admit the turn was missed.",
            ["strange"],
        ),
        memory(
            "stack",
            "The corner, dev seed",
            "Second of three: a wedding party queued outside for forty minutes "
            "in the rain, and the bride was the only one who found it funny.",
            ["family"],
        ),
        memory(
            "stack",
            "The corner, dev seed",
            "Third of three: the fire escape somebody had turned into a garden, "
            "four storeys of tomatoes nobody was allowed to touch.",
            ["nature"],
        ),
        memory(
            "centroid",
            "Somewhere around here, dev seed",
            "Filed to the middle of the neighbourhood because the transcript "
            "never said where. Open to everyone - walking to a guess is a lie.",
            ["history"],
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
    content_id = session.execute(
        text("SELECT id FROM content WHERE url = :u"), {"u": DEV_SEED_URL}
    ).scalar()
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
    with tempfile.TemporaryDirectory() as tmp:
        aiff = pathlib.Path(tmp) / "clip.aiff"
        spoken = (
            "This is a seeded recording. If you can hear this, the audio player "
            "in the memory sheet is working."
        )
        try:
            subprocess.run(["say", "-o", str(aiff), spoken], check=True, capture_output=True)
            subprocess.run(
                ["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(destination)],
                check=True,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

    probe = subprocess.run(
        ["afinfo", str(destination)], capture_output=True, text=True, check=False
    )
    for line in probe.stdout.splitlines():
        if "estimated duration" in line:
            return round(float(line.split(":")[1].strip().split()[0]), 1)
    return None


def filed_by_a_person(session) -> tuple[int, list[str]]:
    """The submission-shaped memory: an author, the stranger layer, and media.

    Always gated, whatever its neighbours do - `user_id IS NOT NULL` is the other
    half of is_gated. Written through the same INSERTs api/write.py uses.
    """
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
            "opens_at": None,
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


def sealed_until_a_date(session) -> int:
    """A time capsule, deliberately planted *inside* the unlock radius.

    ~129m, so it is the one seed that proves what F23 is actually about:
    standing close enough does not open it. A sealed memory 400m away would
    demonstrate nothing the padlock at `walk` does not already.

    Reuses SEED_USER, so it also needs no new device or user row - and a
    submission is always gated, which keeps this independent of whatever its
    neighbours do.
    """
    lat, lng = at("sealed")
    place_id = session.execute(
        text(PLACE_INSERT),
        {
            "name": "A letter to whoever is here later, dev seed",
            "place_query": f"{PLACE_PREFIX}sealed",
            "lat": lat,
            "lng": lng,
            "precision_meters": 25,
        },
    ).scalar()
    return session.execute(
        text(SUBMISSION_INSERT),
        {
            "place_id": place_id,
            "summary": "You are standing where I stood. By the time this opens the "
            "bench will probably be gone, and that is rather the point of it.",
            "tags": ["strange"],
            "happened_at": None,
            "happened_precision": None,
            # Computed, never a literal: a hard-coded date rots into the past
            # and the seed then silently stops demonstrating a seal at all.
            # A day offset rather than .replace(year=...), which raises on 29
            # February - the seed has to run on any day of the year.
            "opens_at": datetime.date.today() + datetime.timedelta(days=365 * 5),
            "user_id": SEED_USER,
        },
    ).scalar()


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
            "opens_at": None,
            "user_id": SEED_USER,
        },
    ).scalar()


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


def seed(session) -> dict:
    clear(session)

    content_id = session.execute(
        text("""
            INSERT INTO content (url, platform, platform_id, source_type, source_name, title,
                                 transcript_fetched, memories_extracted)
            VALUES (:u, 'dev', 'dev-seed', 'video', 'Dev Seed', 'Seeded for development',
                    TRUE, TRUE)
            RETURNING id
        """),
        {"u": DEV_SEED_URL},
    ).scalar()

    save_memories(session, content_id, extracted())
    centroid_twin(session)
    filed_id, media = filed_by_a_person(session)
    sealed_id = sealed_until_a_date(session)
    nightspot_id = a_second_submission(session)

    return {
        "content_id": content_id,
        "filed_id": filed_id,
        "sealed_id": sealed_id,
        "nightspot_id": nightspot_id,
        "media": media,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--clear", action="store_true", help="remove the seed and stop")
    args = parser.parse_args()

    with get_session() as session:
        if args.clear:
            print(f"removed {clear(session)} seeded places and everything hanging off them")
            return
        made = seed(session)

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
    print("  sealed until a date, in reach and still shut: sealed")
    print()
    print("point the Simulator at it:")
    print(f"  xcrun simctl location booted set {LAT},{LNG}")
    print("or skip that entirely, in mobile/.env:")
    print(f"  EXPO_PUBLIC_DEV_LOCATION={LAT},{LNG}")


if __name__ == "__main__":
    main()
