"""What happens when a person writes into the corpus instead of reading it.

Three things are being protected here and they are not the same thing.

**The gate.** A submission arrives with a precise coordinate and mints its own
place row, which is exactly the shape that used to mean "this coordinate is
shared, so nothing at it is worth walking to". Filing a memory next to Katz's
must not unlock Katz's, and a submission must still lock for everybody who was
not there.

**The upload.** The filename, the extension and the claim about what the bytes
are all come from a phone we do not control, and the file is served back from
our own origin. None of the three is trusted.

**The takedown.** Anything anybody can post needs a way to remove it, and it has
to remove it from every endpoint at once - the search, the counts and the card
included, not just the one somebody complained about.
"""

import pathlib
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import api.card as card
import api.main as m
import api.media as media

pytestmark = pytest.mark.db

# Rådhuspladsen, and a point ~1.1km north.
LAT, LNG = 55.6759, 12.5655
FAR_LAT = LAT + 0.01

# The smallest thing that is genuinely a PNG: the signature is what save_upload
# checks, and a fixture that only pretends would pass the test it is here for.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT\x78\x9c\x63\x00"
    b"\x01\x00\x00\x05\x00\x01\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
M4A = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00" + b"\x00" * 64


def device() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def client(db_session, monkeypatch, tmp_path):
    @contextmanager
    def _session():
        # Rolls back like pipeline.db.get_session does. Without it a refused
        # submission would leave its half-written rows behind in the test and
        # nowhere else, which is the wrong way round for a fixture.
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    monkeypatch.setattr(m, "get_session", _session)
    monkeypatch.setattr(card, "get_session", _session)
    # Uploads must not land in the repo. MEDIA_DIR is read at call time, so this
    # is enough - the mount in api.main is never exercised by these tests.
    monkeypatch.setattr(media, "MEDIA_DIR", tmp_path)
    return TestClient(m.app)


def submission(**overrides) -> dict:
    body = {
        "device": device(),
        "lat": LAT,
        "lng": LNG,
        "place_name": "The bench by the harbour",
        "summary": "We sat here until it got light and nobody wanted to say so.",
        "tags": ["drink", "music"],
    }
    body.update(overrides)
    return body


def submit(client, **overrides):
    response = client.post("/v1/memories", json=submission(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, dev, data=PNG, mime="image/png", name="a.png", **form):
    return client.post(
        "/v1/media", data={"device": dev, **form}, files={"file": (name, data, mime)}
    )


def extracted_memory(session, name, lat, lng):
    """A memory the pipeline would have produced: its own place, a content row,
    no user. The thing a submission must not be able to unlock."""
    place = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :q, ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
        ),
        {"n": name, "q": f"{name} query", "lat": lat, "lng": lng},
    ).scalar()
    content = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES (:u, 'youtube', :p) RETURNING id"
        ),
        {"u": f"https://e.invalid/{name}", "p": name[:11]},
    ).scalar()
    memory = session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence) VALUES (:p, :c, 0, :s, 'high') RETURNING id"
        ),
        {"p": place, "c": content, "s": f"something happened at {name}"},
    ).scalar()
    session.commit()
    return memory


# -- the memory itself --------------------------------------------------------


def test_a_submission_becomes_a_readable_memory(client):
    memory = submit(client)

    assert memory["locked"] is False
    assert memory["summary"].startswith("We sat here")
    assert memory["layer"] == "stranger"
    assert memory["place"]["name"] == "The bench by the harbour"
    assert memory["tags"] == ["drink", "music"]
    # Nothing to link out to, and the author carries the credit instead.
    assert memory["content"] is None
    assert memory["author"]["name"] == "Anonymous"


def test_filing_a_memory_puts_it_in_your_collection(client):
    """Submitting is standing there. Making somebody walk back to read what they
    just wrote would be absurd, so the unlock is recorded with the insert."""
    dev = device()
    memory = submit(client, device=dev)

    collected = client.get(f"/v1/unlocks?device={dev}").json()["memories"]
    assert [item["id"] for item in collected] == [memory["id"]]
    assert collected[0]["locked"] is False


def test_a_submission_is_locked_for_everybody_who_was_not_there(client):
    """The whole mechanic, applied to the new content. A submitted coordinate is
    a real one - somebody's phone was at it - so it gates even though its place
    row is brand new and shares its grid cell with nothing."""
    memory = submit(client)

    seen = client.get(f"/v1/memories/{memory['id']}").json()
    assert seen["locked"] is True
    assert seen["summary"] == ""
    assert seen["author"]["name"] == "Anonymous", "who filed it is not the secret"


def test_the_map_does_not_hand_out_a_submission(client):
    submit(client)
    listed = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()["memories"]
    assert len(listed) == 1
    assert listed[0]["locked"] is True
    assert listed[0]["summary"] == ""


def test_filing_next_to_a_memory_does_not_unlock_it(client, db_session):
    """The hole this feature would otherwise open.

    A gated memory is one whose coordinate no other place shares. A submission
    mints a place at the submitter's exact position, so posting outside Katz's
    would have put a second place in that grid cell and opened Katz's to
    everybody. Places carrying a submission are excluded from that count.
    """
    katz = extracted_memory(db_session, "Katz", LAT, LNG)
    assert client.get(f"/v1/memories/{katz}").json()["locked"] is True

    submit(client)

    assert client.get(f"/v1/memories/{katz}").json()["locked"] is True, (
        "a submission next door must not be a key"
    )
    # The card is the other route to the same rows, and it has its own copy of
    # the coordinate test.
    assert "something happened" not in client.get(f"/v1/memories/{katz}/card").text


def test_standing_there_still_opens_it(client, db_session):
    memory = submit(client)
    opened = client.post(
        f"/v1/memories/{memory['id']}/unlock",
        json={"device": device(), "lat": LAT, "lng": LNG},
    ).json()
    assert opened["locked"] is False
    assert "until it got light" in opened["summary"]


def test_unknown_tags_are_dropped_not_fatal(client):
    """Tags are a filing convenience. Losing one is not worth losing the memory,
    and free text would be a soup of one-offs inside a week."""
    memory = submit(client, tags=["music", "MUSIC", "  drink ", "crimes", ""])
    assert memory["tags"] == ["music", "drink"]


def test_a_date_without_a_precision_is_a_full_date(client):
    memory = submit(client, happened_at="1998-07-12")
    assert memory["happened_at"] == "1998-07-12"


@pytest.mark.parametrize(
    "bad",
    [
        {"summary": "too short"},
        {"place_name": ""},
        {"lat": 91},
        {"device": "not-a-uuid"},
        {"tags": ["music"] * 9},
    ],
)
def test_a_malformed_submission_is_refused(client, bad):
    assert client.post("/v1/memories", json=submission(**bad)).status_code == 422


# -- who filed it -------------------------------------------------------------


def test_naming_yourself_signs_the_memory(client):
    dev = device()
    client.put("/v1/me", json={"device": dev, "display_name": "  Lise  "})
    assert submit(client, device=dev)["author"]["name"] == "Lise"


def test_a_name_sent_with_the_submission_is_enough(client):
    """Signing your first memory should be one request, not two."""
    dev = device()
    assert submit(client, device=dev, display_name="Bo")["author"]["name"] == "Bo"
    assert client.get(f"/v1/me?device={dev}").json()["display_name"] == "Bo"


def test_a_blank_name_is_anonymous_again(client):
    dev = device()
    client.put("/v1/me", json={"device": dev, "display_name": "Bo"})
    client.put("/v1/me", json={"device": dev, "display_name": "   "})
    assert client.get(f"/v1/me?device={dev}").json()["display_name"] is None
    assert submit(client, device=dev)["author"]["name"] == "Anonymous"


def test_reading_a_profile_creates_nobody(client, db_session):
    """A device that only walks around unlocking things should not leave a user
    row behind, so the read has to be a read."""
    empty = client.get(f"/v1/me?device={device()}").json()
    assert empty == {"user_id": None, "display_name": None, "submitted": 0, "unlocked": 0}
    assert db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 0


def test_the_profile_counts_what_you_did(client):
    dev = device()
    submit(client, device=dev)
    submit(client, device=dev)
    profile = client.get(f"/v1/me?device={dev}").json()
    assert profile["submitted"] == 2
    assert profile["unlocked"] == 2


def test_two_submissions_from_one_device_are_one_person(client, db_session):
    dev = device()
    first = submit(client, device=dev)
    second = submit(client, device=dev)
    assert first["author"]["id"] == second["author"]["id"]
    assert db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() == 1


# -- uploads ------------------------------------------------------------------


def test_a_photo_travels_with_the_memory(client, tmp_path):
    dev = device()
    uploaded = upload(client, dev).json()
    assert uploaded["kind"] == "photo"
    assert uploaded["url"].startswith("/media/")
    assert (tmp_path / uploaded["url"].removeprefix("/media/")).read_bytes() == PNG

    memory = submit(client, device=dev, media_ids=[uploaded["id"]])
    assert [item["url"] for item in memory["media"]] == [uploaded["url"]]
    assert memory["media_count"] == 1


def test_a_recording_keeps_the_length_the_phone_measured(client):
    """The server does not decode the file to find out, so the client is the
    only thing that knows - and only for audio."""
    dev = device()
    sound = upload(client, dev, M4A, "audio/m4a", "a.m4a", duration_seconds="41.5").json()
    assert sound["kind"] == "audio"
    assert sound["duration_seconds"] == pytest.approx(41.5)

    photo = upload(client, dev, duration_seconds="41.5").json()
    assert photo["duration_seconds"] is None, "a photograph has no length"


def test_the_locked_card_says_there_is_a_photo_without_showing_it(client):
    """Knowing something is waiting is the pull. Handing it over is the leak -
    a photograph of the place is the memory as much as the text is."""
    dev = device()
    uploaded = upload(client, dev).json()
    memory = submit(client, device=dev, media_ids=[uploaded["id"]])

    locked = client.get(f"/v1/memories/{memory['id']}").json()
    assert locked["locked"] is True
    assert locked["media"] == []
    assert locked["media_count"] == 1


def test_html_wearing_a_png_content_type_is_refused(client, tmp_path):
    """The extension decides the Content-Type when the file is served back from
    our own origin, so the declared type has to match the actual bytes."""
    response = upload(client, device(), b"<html><script>alert(1)</script>", "image/png")
    assert response.status_code == 415
    assert list(tmp_path.iterdir()) == [], "nothing hostile reaches the disk"


def test_an_unlisted_type_is_refused(client):
    assert upload(client, device(), b"%PDF-1.4\n", "application/pdf").status_code == 415


def test_the_stored_name_owes_nothing_to_the_client(client, tmp_path):
    uploaded = upload(client, device(), name="../../etc/passwd.png").json()
    stored = pathlib.Path(uploaded["url"].removeprefix("/media/"))
    assert stored.parent == pathlib.Path("."), "no path from the client"
    assert stored.suffix == ".png"
    assert "passwd" not in stored.name


def test_an_oversized_photo_is_cut_off_at_the_limit(client, monkeypatch, tmp_path):
    monkeypatch.setattr(media, "MAX_PHOTO_BYTES", len(PNG) - 1)
    assert upload(client, device()).status_code == 413
    assert list(tmp_path.iterdir()) == [], "the partial write is cleaned up"


def test_you_cannot_attach_somebody_elses_upload(client):
    """Media ids are sequential, so without the device check a submission could
    adopt the photo another phone uploaded a second earlier."""
    theirs = upload(client, device()).json()
    response = client.post("/v1/memories", json=submission(media_ids=[theirs["id"]]))
    assert response.status_code == 400


def test_an_attachment_cannot_be_used_twice(client):
    dev = device()
    uploaded = upload(client, dev).json()
    submit(client, device=dev, media_ids=[uploaded["id"]])
    assert (
        client.post(
            "/v1/memories", json=submission(device=dev, media_ids=[uploaded["id"]])
        ).status_code
        == 400
    )


def test_a_refused_attachment_takes_the_whole_submission_with_it(client, db_session):
    """Silently posting the memory without the photograph somebody chose is
    worse than refusing: they would never find out."""
    before = db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar()
    client.post("/v1/memories", json=submission(media_ids=[9999]))
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == before


# -- taking it down -----------------------------------------------------------


def test_enough_reports_hide_it_everywhere(client, db_session):
    memory = submit(client)
    mid = memory["id"]

    for _ in range(m.REPORT_THRESHOLD - 1):
        assert (
            client.post(f"/v1/memories/{mid}/report", json={"device": device()}).json()["hidden"]
            is False
        )

    assert client.post(f"/v1/memories/{mid}/report", json={"device": device()}).json()["hidden"]

    assert client.get(f"/v1/memories/{mid}").status_code == 404
    assert client.get(f"/v1/memories/{mid}/card").status_code == 404
    assert (
        client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()["meta"]["total"]
        == 0
    )
    assert client.get("/v1/memories/search?q=harbour").json()["meta"]["total"] == 0
    assert client.get(f"/v1/places/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()["places"] == []
    # The row is still there. A takedown that destroys the evidence makes the
    # next dispute unanswerable.
    assert db_session.execute(text("SELECT COUNT(*) FROM memories")).scalar() == 1


def test_it_leaves_the_collection_of_the_person_who_filed_it(client):
    dev = device()
    memory = submit(client, device=dev)
    for _ in range(m.REPORT_THRESHOLD):
        client.post(f"/v1/memories/{memory['id']}/report", json={"device": device()})
    assert client.get(f"/v1/unlocks?device={dev}").json()["memories"] == []


def test_one_device_cannot_report_three_times(client):
    """The threshold counts people, not presses."""
    memory = submit(client)
    dev = device()
    for _ in range(m.REPORT_THRESHOLD + 2):
        last = client.post(f"/v1/memories/{memory['id']}/report", json={"device": dev}).json()
    assert last == {"reports": 1, "hidden": False}


def test_reporting_something_that_does_not_exist_is_a_404(client):
    assert client.post("/v1/memories/424242/report", json={"device": device()}).status_code == 404


def test_media_is_served_with_sniffing_switched_off(client):
    """The extension decides the Content-Type, and this is what stops a browser
    overruling it. Tested through the real mount because the header is added by
    the StaticFiles subclass, not by anything the upload path touches.

    m.MEDIA_DIR, not media.MEDIA_DIR: the mount captured the directory at import
    and the fixture's tmp_path redirect only reaches the upload.
    """
    m.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    served = m.MEDIA_DIR / "nosniff-probe.png"
    served.write_bytes(PNG)
    try:
        response = client.get("/media/nosniff-probe.png")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-type"] == "image/png"
    finally:
        served.unlink(missing_ok=True)
