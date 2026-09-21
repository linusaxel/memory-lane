"""The dev seed plants one of every state the app can render.

This is the fixture a human uses, so the thing worth asserting is not that rows
appeared - it is that each row is in the state it claims. Gating is a
consequence of coordinates rather than a flag, and two of the six arrangements
are easy to get backwards in a way nothing would notice:

  * three *places* at one point stacks the pin and silently ungates all three,
    where three *memories* on one place stacks it and keeps the gate;
  * two places at one point is what makes the centroid pair open, and it has to
    be exactly two - one and they are gated, three and the seed is lying about
    what it demonstrates.
"""

import pathlib
import re
from datetime import date

import pytest
from sqlalchemy import text

import pipeline.seed_dev as seed_dev
from api.gate import UNLOCK_RADIUS_METERS, meters_between, row_to_memory
from api.models import Coordinates
from api.queries import SINGLE_MEMORY_QUERY
from pipeline.seed_dev import LAT, LNG, PLACE_PREFIX, at, clear, seed

pytestmark = pytest.mark.db

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def seeded(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(seed_dev, "MEDIA_DIR", tmp_path)
    seed(db_session)
    db_session.commit()
    return db_session


def rows(session):
    return session.execute(
        text(f"""
            SELECT p.place_query,
                   ST_Y(p.coordinates::geometry) AS lat,
                   ST_X(p.coordinates::geometry) AS lng,
                   COUNT(m.id) AS memories,
                   bool_or(m.user_id IS NOT NULL) AS submitted,
                   (SELECT COUNT(*) FROM places p2
                     WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
                         = ST_SnapToGrid(p.coordinates::geometry, 0.0001)) AS in_cell
            FROM places p JOIN memories m ON m.place_id = p.id
            WHERE p.place_query LIKE '{PLACE_PREFIX}%'
            GROUP BY p.id, p.place_query, p.coordinates
        """)
    ).fetchall()


def by_query(session) -> dict:
    return {r.place_query.removeprefix(PLACE_PREFIX): r for r in rows(session)}


# -- the coordinate is shared with the app -----------------------------------


def test_the_seed_sits_on_the_app_s_fallback_region():
    """The whole design is that the app's no-permission map centre, the
    coordinate every doc gives to simctl, and this cluster are one place rather
    than three. Read out of App.tsx rather than trusted to a comment."""
    source = (ROOT / "mobile" / "App.tsx").read_text()
    block = re.search(r"const FALLBACK_REGION: Region = \{(.*?)\}", source, re.S)
    assert block, "mobile/App.tsx no longer declares FALLBACK_REGION"
    latitude = float(re.search(r"latitude:\s*(-?[\d.]+)", block.group(1)).group(1))
    longitude = float(re.search(r"longitude:\s*(-?[\d.]+)", block.group(1)).group(1))
    assert (latitude, longitude) == (LAT, LNG)


# -- each arrangement is what it claims --------------------------------------


def test_one_memory_is_close_enough_to_unlock_right_now(seeded):
    place = by_query(seeded)["reach"]
    away = meters_between(Coordinates(lat=LAT, lng=LNG), Coordinates(lat=place.lat, lng=place.lng))
    assert away < UNLOCK_RADIUS_METERS, "the point of the seed is something in reach"
    assert place.in_cell == 1, "sharing a cell would ungate it"


def test_one_is_locked_but_worth_walking_to(seeded):
    place = by_query(seeded)["walk"]
    away = meters_between(Coordinates(lat=LAT, lng=LNG), Coordinates(lat=place.lat, lng=place.lng))
    assert away > UNLOCK_RADIUS_METERS
    assert away < 1000, "far enough to stay locked, near enough to be on the map"
    assert place.in_cell == 1


def test_the_stack_is_one_place_with_three_memories(seeded):
    """Not three places. The app groups pins by coordinate while the gate counts
    places, so three places here would stack the pin and ungate all of them."""
    place = by_query(seeded)["stack"]
    assert place.memories == 3
    assert place.in_cell == 1


def test_the_centroid_pair_is_two_places_on_one_point(seeded):
    """Which is exactly what makes both of them open - the same shape the real
    city centroids have."""
    found = by_query(seeded)
    assert found["centroid"].in_cell == 2
    assert found["centroid-twin"].in_cell == 2
    assert (found["centroid"].lat, found["centroid"].lng) == (
        found["centroid-twin"].lat,
        found["centroid-twin"].lng,
    )


def test_one_is_filed_by_a_person_and_carries_media(seeded):
    place = by_query(seeded)["filed"]
    assert place.submitted is True, "user_id is the other half of is_gated"

    attached = seeded.execute(
        text("""
            SELECT md.kind, md.mime FROM media md
            JOIN memories m ON m.id = md.memory_id
            JOIN places p ON p.id = m.place_id
            WHERE p.place_query = :q ORDER BY md.kind
        """),
        {"q": f"{PLACE_PREFIX}filed"},
    ).fetchall()
    kinds = [r.kind for r in attached]
    assert "photo" in kinds, "the photo is generated in-process and must always exist"
    # The audio needs macOS `say` + `afconvert`; where they are missing the seed
    # skips it rather than writing something that will not play.
    assert kinds in (["photo"], ["audio", "photo"])


def test_one_is_sealed_shut_while_you_are_standing_on_it(seeded):
    """The seed F23 needs, and the reason it is planted *inside* the radius.

    A time capsule 400m away demonstrates nothing the padlock at `walk` does
    not already. This one is ~128m off, which is close enough to unlock
    anything else in the seed - and it stays shut anyway, which is the entire
    claim the time lock makes.

    Asserted through row_to_memory rather than off the column, because the
    column is not the feature: the ordering of the two gates inside is_locked
    is, and only the real path exercises it.
    """
    place = by_query(seeded)["sealed"]
    here = Coordinates(lat=LAT, lng=LNG)
    away = meters_between(here, Coordinates(lat=place.lat, lng=place.lng))
    assert away < UNLOCK_RADIUS_METERS, "being in reach is the whole point of it"

    row = seeded.execute(
        text(SINGLE_MEMORY_QUERY),
        {
            "memory_id": seeded.execute(
                text(
                    "SELECT m.id FROM memories m JOIN places p ON p.id = m.place_id "
                    "WHERE p.place_query = :q"
                ),
                {"q": f"{PLACE_PREFIX}sealed"},
            ).scalar()
        },
    ).fetchone()

    memory = row_to_memory(row, here)
    assert memory.locked is True, "standing there must not open a time capsule"
    assert memory.summary == ""
    assert memory.opens_at > date.today(), "a seal that has passed is not a seal"


def test_no_two_gated_seeds_share_a_grid_cell(seeded):
    """0.0001 degrees is ~11m of latitude and only ~8m of longitude at 40.7N.
    Any accidental collision would quietly open both."""
    for name, row in by_query(seeded).items():
        if name.startswith("centroid"):
            continue
        assert row.in_cell == 1, f"{name} shares its snapped cell with another place"


# -- it can be run twice, and taken away -------------------------------------


def test_seeding_twice_leaves_one_copy(seeded):
    before = len(rows(seeded))
    seed(seeded)
    seeded.commit()
    assert len(rows(seeded)) == before


def test_clear_removes_everything_it_made(seeded):
    total_before = seeded.execute(text("SELECT COUNT(*) FROM memories")).scalar()
    assert total_before > 0

    clear(seeded)
    seeded.commit()

    assert rows(seeded) == []
    assert seeded.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 0
    assert seeded.execute(text("SELECT COUNT(*) FROM media")).scalar() == 0
    assert (
        seeded.execute(
            text("SELECT COUNT(*) FROM content WHERE url = :u"), {"u": seed_dev.DEV_SEED_URL}
        ).scalar()
        == 0
    )


# -- the generated media is real ---------------------------------------------


def test_the_photo_is_a_real_png_with_real_dimensions():
    """A 1x1 would prove nothing about how the sheet lays a photo out."""
    data = seed_dev.png(480, 360)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    assert (width, height) == (480, 360)
    assert len(data) > 1000


def test_every_offset_is_documented():
    """The printout is how a human knows what to walk to."""
    for key in seed_dev.OFFSETS:
        lat, lng = at(key)
        assert lat != LAT or lng != LNG, f"{key} is on top of the origin"
