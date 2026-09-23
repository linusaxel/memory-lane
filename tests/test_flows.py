"""The user flows, end to end, with no app in the way.

The headless twin of `.maestro/`. Each test here walks the same sequence of
requests the app makes in the flow it is named after, so when a Maestro flow
goes red the gate has already said whether the API moved or the app did.

What is new is the *sequence*. `test_api_unlock.py`, `test_api_submit.py` and
`test_api_timelock.py` already assert each of these rules on its own; nothing
asserts that standing 300m away, walking in, unlocking, and coming back
tomorrow compose into one collection. Keep this file to whole flows - a rule
that fits in one request belongs beside its siblings, not here.

The fixture is `pipeline.seed_dev`, the same corpus the simulator run uses, so
the two layers cannot disagree about what "the bench outside" means.
"""

import pathlib
import re
from datetime import timedelta

import pytest
import yaml
from sqlalchemy import text

import pipeline.seed_dev as seed_dev
from api.gate import UNLOCK_RADIUS_METERS, meters_between, today
from api.models import Coordinates
from pipeline.seed_dev import at, seed

pytestmark = pytest.mark.db

ROOT = pathlib.Path(__file__).resolve().parents[1]

DEVICE = "e2e0e2e0-0000-4000-8000-00000000e2e0"
OTHER_DEVICE = "e2e0e2e0-0000-4000-8000-00000000beef"

# .maestro/walk-and-unlock.yml starts here: the 33rd St pavement, on the seed's
# loop and outside every stop's 20m gate.
START = (40.748054, -73.985885)


@pytest.fixture
def seeded(api_client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(seed_dev, "MEDIA_DIR", tmp_path)
    seed(db_session)
    db_session.commit()
    return api_client


def seeded_id(session, key):
    """The memory filed under a seeded arrangement.

    By place_query and not by proximity: several arrangements sit inside the
    smallest radius the API will accept (0.1km), so a nearby lookup would pick
    whichever one sorted first and the test would drift silently.
    """
    row = session.execute(
        text(
            "SELECT m.id FROM memories m JOIN places p ON m.place_id = p.id "
            "WHERE p.place_query = :q ORDER BY m.id LIMIT 1"
        ),
        {"q": f"{seed_dev.PLACE_PREFIX}{key}"},
    ).scalar()
    assert row is not None, f"the seed planted nothing at {key!r}"
    return row


def read_at(client, memory_id, position):
    """One memory, as somebody standing at `position` sees it."""
    lat, lng = position
    response = client.get(f"/v1/memories/{memory_id}", params={"at_lat": lat, "at_lng": lng})
    assert response.status_code == 200
    return response.json()


def test_f1_discover_answers_before_anybody_has_walked_anywhere(seeded):
    """F1: the map is populated on arrival, and none of it is readable yet."""
    response = seeded.get(
        "/v1/memories/nearby", params={"lat": 40.7484, "lng": -73.9857, "radius_km": 1}
    )
    assert response.status_code == 200
    memories = response.json()["memories"]
    assert len(memories) >= 6, "the seed should fill a 1km viewport"

    # The list endpoint never takes a position, so every gated row comes back
    # shut - that is what makes walking the only way in.
    locked = [m for m in memories if m["locked"]]
    assert locked, "a seed with nothing locked cannot demonstrate the product"
    for m in locked:
        assert m["summary"] == ""
        assert m["tags"] == []
        assert m["content"] is None
        # Enough to decide whether to walk there, and no more.
        assert m["place"]["coordinates"] is not None


def test_f7_refused_at_300m_then_earned_by_standing_there(seeded, db_session):
    """F11 -> F12 -> F13 -> F7, as one sequence.

    The refusal is a 200 carrying a distance, not an error: the app turns it
    into "try a few steps nearer" rather than into a failure state.
    """
    lat, lng = at("reach")
    memory_id = seeded_id(db_session, "reach")

    far = read_at(seeded, memory_id, START)
    assert far["locked"] is True
    assert far["summary"] == ""
    assert far["distance_meters"] > UNLOCK_RADIUS_METERS

    refused = seeded.post(
        f"/v1/memories/{memory_id}/unlock",
        json={"device": DEVICE, "lat": START[0], "lng": START[1]},
    )
    assert refused.status_code == 200
    assert refused.json()["locked"] is True
    assert refused.json()["distance_meters"] > UNLOCK_RADIUS_METERS

    # Nothing was recorded by being refused.
    assert seeded.get("/v1/unlocks", params={"device": DEVICE}).json()["memories"] == []

    opened = seeded.post(
        f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": lat, "lng": lng}
    )
    assert opened.status_code == 200
    assert opened.json()["locked"] is False
    assert "pretzel cart" in opened.json()["summary"]


def test_f15_the_collection_is_this_device_and_not_another(seeded, db_session):
    """F15: unlocking is permanent, and it is permanent for one device."""
    lat, lng = at("reach")
    memory_id = seeded_id(db_session, "reach")
    seeded.post(f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": lat, "lng": lng})

    mine = seeded.get("/v1/unlocks", params={"device": DEVICE}).json()["memories"]
    assert [m["id"] for m in mine] == [memory_id]
    # The collection forces its own rows open - that is what makes it readable
    # from the train with no position at all.
    assert "pretzel cart" in mine[0]["summary"]

    assert seeded.get("/v1/unlocks", params={"device": OTHER_DEVICE}).json()["memories"] == []
    assert seeded.get("/v1/me", params={"device": DEVICE}).json()["unlocked"] == 1


def test_f5_a_filed_memory_comes_back_already_open(seeded):
    """F5 + F21: file where you are standing, and it is yours immediately."""
    lat, lng = 40.7484, -73.9857
    draft = {
        "device": DEVICE,
        "lat": lat,
        "lng": lng,
        "place_name": "The steps on the north side",
        "summary": "Somebody had left a whole birthday cake on the step, uncut.",
        "tags": ["food"],
    }
    created = seeded.post("/v1/memories", json=draft)
    assert created.status_code == 201
    body = created.json()

    # Already unlocked: you were the one standing there.
    assert body["locked"] is False
    assert "birthday cake" in body["summary"]
    # A submission has an author and no content row to link out to.
    assert body["author"]["name"] == "Anonymous"
    assert body["content"] is None
    assert body["layer"] == "stranger"

    assert body["id"] in [
        m["id"] for m in seeded.get("/v1/unlocks", params={"device": DEVICE}).json()["memories"]
    ]
    assert seeded.get("/v1/me", params={"device": DEVICE}).json()["submitted"] == 1

    # And it is gated for everybody else, from one step too far away.
    from_afar = seeded.get(
        f"/v1/memories/{body['id']}", params={"at_lat": START[0], "at_lng": START[1]}
    )
    assert from_afar.json()["locked"] is True


def test_f23_a_seal_does_not_care_where_you_are_standing(seeded, db_session):
    """F23: not_yet_open is checked before position, so it holds for the author.

    Two halves, because only the second one is surprising: the seeded capsule
    sits *inside* the radius and still refuses, and a capsule you filed
    yourself refuses you too.
    """
    lat, lng = at("sealed")
    sealed_id = seeded_id(db_session, "sealed")
    standing_on_it = read_at(seeded, sealed_id, (lat, lng))
    assert standing_on_it["locked"] is True
    assert standing_on_it["opens_at"] is not None
    assert standing_on_it["summary"] == ""

    # Even the unlock endpoint, which is the one route that forces the question.
    refused = seeded.post(
        f"/v1/memories/{sealed_id}/unlock",
        json={"device": DEVICE, "lat": lat, "lng": lng},
    )
    assert refused.json()["locked"] is True

    mine = seeded.post(
        "/v1/memories",
        json={
            "device": DEVICE,
            "lat": lat,
            "lng": lng,
            "place_name": "A note for later",
            "summary": "Filed sealed, by somebody standing on the spot.",
            "opens_at": str(today() + timedelta(days=365)),
        },
    )
    assert mine.status_code == 201
    assert mine.json()["locked"] is True, "your own capsule is shut to you too"
    assert mine.json()["summary"] == ""


def test_f19_somewhere_else_entirely_is_told_where_to_go(seeded):
    """F19: an empty map is a dead end unless it names the nearest hotspot."""
    copenhagen = {"lat": 55.6759, "lng": 12.5655, "radius_km": 10}
    assert seeded.get("/v1/memories/nearby", params=copenhagen).json()["memories"] == []

    stats = seeded.get("/v1/stats").json()
    assert stats["hotspots"], "with no hotspot the card cannot render and F19 is a blank map"
    assert stats["unlock_radius_meters"] == UNLOCK_RADIUS_METERS


def test_maestro_flows_still_point_at_the_seed():
    """The YAML hardcodes coordinates and place names that live in Python.

    When they drift the simulator run does not fail loudly - it shows an empty
    map, which reads as "the app is broken" and costs an afternoon. Same guard
    as this file's neighbour keeps on mobile/App.tsx's FALLBACK_REGION.
    """
    seeded_names = {
        "The bench outside, dev seed",
        "Along 35th Street, dev seed",
        "The corner, dev seed",
        "Somewhere around here, dev seed",
        "The same rough spot, dev seed",
        "Where I was standing, dev seed",
        "A letter to whoever is here later, dev seed",
        "Where the night went long, dev seed",
    }
    known = {(round(lat, 6), round(lng, 6)) for lat, lng in (at(key) for key in seed_dev.OFFSETS)}
    # Where the app falls back to, where F1 and filing stand.
    known.add((seed_dev.LAT, seed_dev.LNG))
    # Deliberate non-seed coordinates: the walk's start, and Copenhagen for F19.
    known |= {START, (55.6759, 12.5655)}

    flows = sorted((ROOT / ".maestro").glob("*.yml"))
    assert flows, "no flows to check - did .maestro move?"

    for flow in flows:
        text_ = flow.read_text()

        for lat, lng in re.findall(
            r"latitude:\s*(-?\d+\.?\d*)\s*\n\s*longitude:\s*(-?\d+\.?\d*)", text_
        ):
            assert (float(lat), float(lng)) in known, (
                f"{flow.name} stands at an unseeded {lat},{lng}"
            )

        # A travel keeps to the streets, so its turns are not seed points -
        # but it has to end inside the gate of one, or the stop never opens.
        steps = [s for doc in yaml.safe_load_all(text_) if isinstance(doc, list) for s in doc]
        for step in steps:
            if not isinstance(step, dict) or "travel" not in step:
                continue
            lat, lng = map(float, step["travel"]["points"][-1].split(","))
            end = Coordinates(lat=lat, lng=lng)
            assert any(
                meters_between(end, Coordinates(lat=k[0], lng=k[1])) <= UNLOCK_RADIUS_METERS
                for k in known
            ), f"{flow.name} travels to {lat},{lng}, inside no seeded stop's gate"

        for name in re.findall(r"([A-Z][^\"\n]*?, dev seed)", text_):
            # endswith, not equality: F25's marker titles carry a "Stop N of 5."
            # prefix ahead of the place name (mobile/src/MemoryMarker.tsx), so
            # the seeded name is a suffix of what the flow actually taps on.
            assert any(name.endswith(seeded) for seeded in seeded_names), (
                f"{flow.name} names {name!r}, which the seed does not plant"
            )
