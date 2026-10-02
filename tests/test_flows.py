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
the two layers cannot disagree about what "Ringkaféen" means.
"""

import json
import pathlib
import random
import re
import uuid

import pytest
import yaml
from sqlalchemy import text

import pipeline.seed_dev as seed_dev
from api.gate import UNLOCK_RADIUS_METERS, meters_between
from api.models import ROUTE_BUDGET_MAX_METERS, ROUTE_BUDGET_MIN_METERS, Coordinates
from api.route_solver import _path_meters, _route_size
from api.streets import walking_matrix
from pipeline.route_bench import START_BOX
from pipeline.seed_dev import at, seed
from tests.conftest import on_walk

pytestmark = pytest.mark.db

ROOT = pathlib.Path(__file__).resolve().parents[1]

DEVICE = "e2e0e2e0-0000-4000-8000-00000000e2e0"
OTHER_DEVICE = "e2e0e2e0-0000-4000-8000-00000000beef"

# .maestro/walk-and-unlock.yml starts here: seed_dev's own coordinate, on the seed's
# loop and outside every stop's 20m gate.
START = (seed_dev.LAT, seed_dev.LNG)


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
        "/v1/memories/nearby", params={"lat": seed_dev.LAT, "lng": seed_dev.LNG, "radius_km": 1}
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
        assert m["media"] == []
        assert m["content"] is None
        # Enough to decide whether to walk there, and no more.
        assert m["place"]["coordinates"] is not None


def test_f7_refused_at_300m_then_earned_by_standing_there(seeded, db_session):
    """F13 -> F7, as one sequence.

    The refusal is a 200 carrying a distance, not an error: the app turns it
    into "try a few steps nearer" rather than into a failure state.
    """
    lat, lng = at("reach")
    memory_id = seeded_id(db_session, "reach")
    on_walk(db_session, DEVICE, memory_id)

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
    assert "Lygteå" in opened.json()["summary"]


def test_f15_the_collection_is_this_device_and_not_another(seeded, db_session):
    """F15: unlocking is permanent, and it is permanent for one device."""
    lat, lng = at("reach")
    memory_id = seeded_id(db_session, "reach")
    on_walk(db_session, DEVICE, memory_id)
    seeded.post(f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": lat, "lng": lng})

    mine = seeded.get("/v1/unlocks", params={"device": DEVICE}).json()["memories"]
    assert [m["id"] for m in mine] == [memory_id]
    # The collection forces its own rows open - that is what makes it readable
    # from the train with no position at all.
    assert "Lygteå" in mine[0]["summary"]

    assert seeded.get("/v1/unlocks", params={"device": OTHER_DEVICE}).json()["memories"] == []
    assert seeded.get("/v1/me", params={"device": DEVICE}).json()["unlocked"] == 1


def test_f5_a_filed_memory_comes_back_already_open(seeded):
    """F5 + F21: file where you are standing, and it is yours immediately."""
    # ~45m north of START, so START below is one step too far away.
    lat, lng = seed_dev.LAT + 0.0004, seed_dev.LNG
    draft = {
        "device": DEVICE,
        "lat": lat,
        "lng": lng,
        "place_name": "The steps on the north side",
        "summary": "Somebody had left a whole birthday cake on the step, uncut. #food",
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


def test_f25_a_random_walk_on_a_full_map_can_be_walked(seeded, db_session, route_seed):
    """F25 from starts and lengths nobody chose, over `seed_dev --dense`.

    walk-and-unlock.yml asserts one walk by name; this asserts only what every
    walk owes the person on it: about a stop a km, within the slider, the same
    walk once accepted, and each stop opened by standing on it.
    """
    rng = random.Random(route_seed)
    seed_dev.dense(db_session, 300, route_seed)
    db_session.commit()
    for _ in range(5):
        device = str(uuid.UUID(int=rng.getrandbits(128), version=4))
        start = Coordinates(
            lat=seed_dev.LAT + rng.uniform(-START_BOX[0], START_BOX[0]),
            lng=seed_dev.LNG + rng.uniform(-START_BOX[1], START_BOX[1]),
        )
        body = {
            "device": device,
            "lat": start.lat,
            "lng": start.lng,
            "budget_meters": rng.randint(ROUTE_BUDGET_MIN_METERS, ROUTE_BUDGET_MAX_METERS),
        }
        preview = seeded.get("/v1/routes/preview", params=body).json()
        stops = preview["memories"]
        ids = [m["id"] for m in stops]
        assert 1 <= preview["meta"]["size"] == len(ids) <= _route_size(body["budget_meters"]), body
        assert len(set(ids)) == len(ids), body

        points = [start] + [Coordinates(**m["place"]["coordinates"]) for m in stops]
        walk = _path_meters(
            list(range(1, len(points))), walking_matrix(points), preview["meta"]["loop"]
        )
        assert walk <= body["budget_meters"], body

        accepted = seeded.post("/v1/routes/today", json=body).json()
        assert [m["id"] for m in accepted["memories"]] == ids, body
        again = seeded.post("/v1/routes/today", json={**body, "budget_meters": 1000}).json()
        assert [m["id"] for m in again["memories"]] == ids, body

        for m, here in zip(stops, points[1:], strict=True):
            assert m["locked"] is True, body
            opened = seeded.post(
                f"/v1/memories/{m['id']}/unlock",
                json={"device": device, "lat": here.lat, "lng": here.lng},
            ).json()
            assert opened["locked"] is False, body
        earned = seeded.get("/v1/unlocks", params={"device": device}).json()["memories"]
        assert {m["id"] for m in earned} == set(ids), body


def test_f30_f31_a_finished_walk_is_finished_once_and_kept(seeded, db_session):
    """F30 then F31: walk today's loop to the end, then find it in Walks."""
    body = {"device": DEVICE, "lat": START[0], "lng": START[1], "budget_meters": 4000}
    stops = seeded.post("/v1/routes/today", json=body).json()["memories"]
    assert stops, "the seed should make a walk from the start"

    def completed_at():
        return db_session.execute(
            text("SELECT completed_at FROM daily_routes WHERE device_id = CAST(:d AS uuid)"),
            {"d": DEVICE},
        ).scalar()

    for m in stops:
        assert completed_at() is None, "finished before the last stop"
        seeded.post(
            f"/v1/memories/{m['id']}/unlock", json={"device": DEVICE, **m["place"]["coordinates"]}
        )
    finished = completed_at()
    assert finished is not None
    last = stops[-1]
    seeded.post(
        f"/v1/memories/{last['id']}/unlock", json={"device": DEVICE, **last["place"]["coordinates"]}
    )
    assert completed_at() == finished, "set once, never moved"

    [walk] = seeded.get("/v1/routes/walked", params={"device": DEVICE}).json()["walks"]
    assert [m["id"] for m in walk["memories"]] == [m["id"] for m in stops]
    assert walk["meta"]["earned"] == walk["meta"]["size"] == len(stops)
    assert walk["meta"]["completed_at"] is not None
    assert all(not m["locked"] and m["summary"] for m in walk["memories"])


def test_f1_nothing_walkable_is_an_empty_preview(seeded):
    """F1: from somewhere with nothing in reach, the preview is empty, not an error."""
    # Malmö: Copenhagen has a seed now (seed_dev --routes lakes), 25 km off.
    malmo = {
        "device": DEVICE,
        "lat": 55.605,
        "lng": 13.0038,
        "budget_meters": ROUTE_BUDGET_MAX_METERS,
    }
    preview = seeded.get("/v1/routes/preview", params=malmo).json()
    assert preview["memories"] == []
    assert preview["meta"]["size"] == 0


def test_maestro_flows_still_point_at_the_seed():
    """The YAML hardcodes coordinates and place names that live in Python.

    When they drift the simulator run does not fail loudly - it shows an empty
    map, which reads as "the app is broken" and costs an afternoon. Same guard
    as this file's neighbour keeps on mobile/App.tsx's FALLBACK_REGION.
    """
    seeded_names = {
        "Ringkaféen, dev seed",
        "Nørrebrogade bridge, dev seed",
        "Woodstock, dev seed",
        "Hedebygade, dev seed",
        "The same rough spot, dev seed",
        "Where I was standing, dev seed",
        "A letter to whoever is here later, dev seed",
        "Where the night went long, dev seed",
    }
    # lakes-loop.yml names --routes lakes stops by their lake.
    lakes = json.loads(seed_dev.SCENARIOS.read_text())["lakes"]["points"]
    seeded_names |= {
        f"{seed_dev.lake_of(lat, lng)} {i}, dev seed" for i, (lat, lng) in enumerate(lakes)
    }
    known = {(round(lat, 6), round(lng, 6)) for lat, lng in (at(key) for key in seed_dev.OFFSETS)}
    # Where the app falls back to, where F1 and filing stand.
    known.add((seed_dev.LAT, seed_dev.LNG))
    # Deliberate non-seed coordinates: the walk's start, and Malmö for F1's empty case.
    known |= {START, (55.605, 13.0038)}
    # lakes-loop.yml stands where seed_dev --routes lakes starts.
    known.add(seed_dev.OLUFSVEJ)

    flows = sorted((ROOT / ".maestro").glob("*.yml"))
    assert flows, "no flows to check - did .maestro move?"

    for flow in flows:
        text_ = flow.read_text()

        for lat, lng in re.findall(
            r"(?:latitude|LAT):\s*(-?\d+\.?\d*)\s*\n\s*(?:longitude|LNG):\s*(-?\d+\.?\d*)", text_
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


def test_the_default_walk_is_as_long_as_walk_and_unlock_walks():
    """2026-09-27: one stop a km made the 4 km default four stops, and run.sh
    blamed the environment for the flow that expected five."""
    km = re.search(
        r"WALK_KM = \{[^}]*initial: ([\d.]+)", (ROOT / "mobile/src/Plan.tsx").read_text()
    )
    # walk-and-unlock.yml plans and accepts it through this step.
    flow = (ROOT / ".maestro/steps/start-walk.yml").read_text()
    stops = re.search(r'visible: "(\d+) memories · ', flow)
    assert _route_size(float(km[1]) * 1000) == int(stops[1])
