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

import io
import pathlib
import uuid

import pytest
from PIL import Image
from sqlalchemy import text

import api.main as m
import api.media as media
import api.write as write
from pipeline.extract import HISTORICAL_SYSTEM_PROMPT, SYSTEM_PROMPT
from pipeline.tags import TAGS
from pipeline.tags import clean as extract_clean
from tests.conftest import on_walk

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


def signed_in(session) -> str:
    """A device on an account with a Google sign-in: the only kind whose report
    counts."""
    dev, user = device(), str(uuid.uuid4())
    for sql in (
        "INSERT INTO users (id) VALUES (CAST(:user AS uuid))",
        "INSERT INTO identities (provider, subject, user_id) VALUES ('google', :dev, CAST(:user AS uuid))",
        "INSERT INTO devices (id, user_id) VALUES (CAST(:dev AS uuid), CAST(:user AS uuid))",
    ):
        session.execute(text(sql), {"user": user, "dev": dev})
    return dev


@pytest.fixture
def client(api_client):
    """conftest's, under the shorter name every test here already uses."""
    return api_client


def submission(**overrides) -> dict:
    body = {
        "device": device(),
        "lat": LAT,
        "lng": LNG,
        "place_name": "The bench by the harbour",
        "summary": "We sat here until it got light and nobody wanted to say so. #drink #music",
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
    walker = device()
    on_walk(db_session, walker, memory["id"])
    opened = client.post(
        f"/v1/memories/{memory['id']}/unlock",
        json={"device": walker, "lat": LAT, "lng": LNG},
    ).json()
    assert opened["locked"] is False
    assert "until it got light" in opened["summary"]


def test_the_tags_are_the_hashtags_in_the_description(client):
    """Written, not picked: any #word, lowercased, first use first. The #word
    stays in the text, where the app highlights it."""
    memory = submit(client, summary="Tacos at 2am #Food #smørrebrød, then #food again")
    assert memory["tags"] == ["food", "smørrebrød"]
    assert "#Food" in memory["summary"]


def test_a_tags_field_is_not_how_tags_arrive(client):
    """An app from before hashtags still posts; its chips are ignored."""
    memory = submit(client, summary="Nothing tagged here.", tags=["music"])
    assert memory["tags"] == []


def test_a_date_without_a_precision_is_a_full_date(client):
    memory = submit(client, happened_at="1998-07-12")
    assert memory["happened_at"] == "1998-07-12"


@pytest.mark.parametrize(
    "bad",
    [
        {"summary": ""},
        {"place_name": ""},
        {"lat": 91},
        {"device": "not-a-uuid"},
    ],
)
def test_a_malformed_submission_is_refused(client, bad):
    assert client.post("/v1/memories", json=submission(**bad)).status_code == 422


# -- who filed it -------------------------------------------------------------


def test_naming_yourself_signs_the_memory(client):
    dev = device()
    client.put("/v1/me", json={"device": dev, "display_name": "  Lise  "})
    assert submit(client, device=dev)["author"]["name"] == "Lise"


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
    assert empty == {
        "user_id": None,
        "display_name": None,
        "avatar_url": None,
        "submitted": 0,
        "hearts_received": 0,
        "unlocked": 0,
        "streak": 0,
        "providers": [],
        "subscribed": False,
        "subscribed_until": None,
        "xp": 0,
        "level": 1,
        "xp_level": 0,
        "xp_next": 50,
        "steps": 0,
        "steps_counted_until": None,
        "on_board": True,
    }
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
    with Image.open(tmp_path / uploaded["url"].removeprefix("/media/")) as stored:
        assert (stored.format, stored.size) == ("PNG", (1, 1))

    memory = submit(client, device=dev, media_ids=[uploaded["id"]])
    assert [item["url"] for item in memory["media"]] == [uploaded["url"]]
    assert memory["media_count"] == 1


def set_avatar(client, dev, data=PNG, mime="image/png"):
    return client.post(
        "/v1/me/avatar", data={"device": dev}, files={"file": ("face.png", data, mime)}
    )


def test_a_profile_photo_signs_what_you_file(client, tmp_path):
    dev = device()
    response = set_avatar(client, dev)
    assert response.status_code == 200, response.text
    url = response.json()["avatar_url"]
    assert (tmp_path / url.removeprefix("/media/")).exists()

    memory = submit(client, device=dev)
    assert memory["author"]["avatar_url"] == url


def test_a_new_profile_photo_takes_the_old_file_with_it(client, tmp_path):
    dev = device()
    first = set_avatar(client, dev).json()["avatar_url"]
    second = set_avatar(client, dev).json()["avatar_url"]

    assert first != second
    assert not (tmp_path / first.removeprefix("/media/")).exists()

    cleared = client.delete("/v1/me/avatar", params={"device": dev}).json()
    assert cleared["avatar_url"] is None
    assert not (tmp_path / second.removeprefix("/media/")).exists()


def test_deleting_the_account_deletes_the_profile_photo(client, tmp_path):
    dev = device()
    url = set_avatar(client, dev).json()["avatar_url"]

    assert client.delete("/v1/me", params={"device": dev}).status_code == 204
    assert not (tmp_path / url.removeprefix("/media/")).exists()


def test_a_recording_is_not_a_profile_photo(client, tmp_path):
    response = set_avatar(client, device(), data=M4A, mime="audio/mp4")
    assert response.status_code == 415
    assert list(tmp_path.iterdir()) == []


def test_a_recording_keeps_the_length_the_phone_measured(client):
    """The server does not decode the file to find out, so the client is the
    only thing that knows - and only for audio."""
    dev = device()
    sound = upload(client, dev, M4A, "audio/m4a", "a.m4a", duration_seconds="41.5").json()
    assert sound["kind"] == "audio"
    assert sound["duration_seconds"] == pytest.approx(41.5)

    photo = upload(client, dev, duration_seconds="41.5").json()
    assert photo["duration_seconds"] is None, "a photograph has no length"


def test_a_photo_loses_where_it_was_taken(client, tmp_path):
    """A memory is public, so a phone photo's EXIF - GPS to the metre, the
    camera, the time - would be too. The orientation tag goes with the rest,
    so a sideways camera shot has to come back already turned."""
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90 to display
    exif[0x0110] = "iPhone 17"  # Model
    exif.get_ifd(0x8825)[2] = (55.0, 40.0, 33.2)  # GPSLatitude
    shot = io.BytesIO()
    Image.new("RGB", (40, 20), "red").save(shot, "JPEG", exif=exif)

    uploaded = upload(client, device(), shot.getvalue(), "image/jpeg", "a.jpg").json()
    with Image.open(tmp_path / uploaded["url"].removeprefix("/media/")) as stored:
        assert not stored.getexif()
        assert stored.size == (20, 40)


def test_a_file_that_only_starts_like_a_photo_is_refused(client, tmp_path):
    response = upload(client, device(), PNG[:16] + b"\x00" * 64)
    assert response.status_code == 415
    assert list(tmp_path.iterdir()) == []


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

    for _ in range(write.REPORT_THRESHOLD - 1):
        assert (
            client.post(
                f"/v1/memories/{mid}/report", json={"device": signed_in(db_session)}
            ).json()["hidden"]
            is False
        )

    assert client.post(f"/v1/memories/{mid}/report", json={"device": signed_in(db_session)}).json()[
        "hidden"
    ]

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


def test_it_leaves_the_collection_of_the_person_who_filed_it(client, db_session):
    dev = device()
    memory = submit(client, device=dev)
    for _ in range(write.REPORT_THRESHOLD):
        client.post(f"/v1/memories/{memory['id']}/report", json={"device": signed_in(db_session)})
    assert client.get(f"/v1/unlocks?device={dev}").json()["memories"] == []


def test_one_device_cannot_report_three_times(client, db_session):
    """The threshold counts people, not presses."""
    memory = submit(client)
    dev = signed_in(db_session)
    for _ in range(write.REPORT_THRESHOLD + 2):
        last = client.post(f"/v1/memories/{memory['id']}/report", json={"device": dev}).json()
    assert last == {"reports": 1, "hidden": False}


def test_a_reinstated_memory_needs_fresh_reports_to_go_again(client, db_session):
    from api.moderate import restore

    memory = submit(client)
    mid = memory["id"]
    for _ in range(write.REPORT_THRESHOLD):
        client.post(f"/v1/memories/{mid}/report", json={"device": signed_in(db_session)})
    assert client.get(f"/v1/memories/{mid}").status_code == 404

    assert restore(db_session, mid)
    assert client.get(f"/v1/memories/{mid}").status_code == 200
    again = client.post(f"/v1/memories/{mid}/report", json={"device": signed_in(db_session)})
    assert again.json() == {"reports": 1, "hidden": False}
    # Cleared, not deleted: the dispute can still be answered.
    total = db_session.execute(text("SELECT COUNT(*) FROM reports")).scalar()
    assert total == write.REPORT_THRESHOLD + 1


def test_devices_without_a_sign_in_cannot_take_a_memory_down(client):
    """A device id is self-issued: one person can mint as many as they like."""
    memory = submit(client)
    for _ in range(write.REPORT_THRESHOLD + 2):
        last = client.post(f"/v1/memories/{memory['id']}/report", json={"device": device()}).json()
    assert last == {"reports": 0, "hidden": False}


def test_a_blocked_author_is_gone_for_the_blocker_only(client, db_session):
    author, walker = device(), device()
    memory = submit(client, device=author)
    near = f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1"

    blocked = client.post(f"/v1/users/{memory['author']['id']}/block", json={"device": walker})
    assert blocked.status_code == 204

    assert client.get(f"{near}&device={walker}").json()["meta"]["total"] == 0
    assert client.get(near).json()["meta"]["total"] == 1
    opened = client.post(
        f"/v1/memories/{memory['id']}/unlock", json={"device": walker, "lat": LAT, "lng": LNG}
    )
    assert opened.status_code == 404


def test_blocking_nobody_is_a_404(client):
    missing = client.post(f"/v1/users/{uuid.uuid4()}/block", json={"device": device()})
    assert missing.status_code == 404


def test_reporting_something_that_does_not_exist_is_a_404(client):
    assert client.post("/v1/memories/424242/report", json={"device": device()}).status_code == 404


# -- the cap ------------------------------------------------------------------


def test_one_person_cannot_file_forever(client, monkeypatch):
    """A loop with a device id is the failure this cap exists for."""
    monkeypatch.setattr(write, "DAILY_MEMORIES", 2)
    dev = device()
    submit(client, device=dev)
    submit(client, device=dev)

    refused = client.post("/v1/memories", json=submission(device=dev))
    assert refused.status_code == 429
    # Refused before anything was written: no orphan place row for a memory
    # that does not exist.
    assert (
        client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()["meta"]["total"]
        == 2
    )

    # Somebody else's allowance is their own.
    submit(client, device=device())


def test_the_cap_follows_the_person_not_the_phone(client, db_session, monkeypatch):
    """A second phone on one account is a second device, not a second
    allowance - which is why the count is on the user and not the device."""
    monkeypatch.setattr(write, "DAILY_MEMORIES", 1)
    first, second = device(), device()
    submit(client, device=first)

    user_id = db_session.execute(
        text("SELECT user_id FROM devices WHERE id = CAST(:d AS uuid)"), {"d": first}
    ).scalar()
    # What POST /v1/auth/google does once both phones prove the same account.
    db_session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
        {"d": second, "u": user_id},
    )

    assert client.post("/v1/memories", json=submission(device=second)).status_code == 429


def test_uploads_stop_when_the_day_is_spent(client, monkeypatch):
    monkeypatch.setattr(write, "DAILY_UPLOAD_BYTES", len(PNG))
    dev = device()
    assert upload(client, dev).status_code == 201
    assert upload(client, dev).status_code == 429
    assert upload(client, device()).status_code == 201


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


# -- the extractor's vocabulary -----------------------------------------------


def test_the_extractor_is_held_to_the_same_list():
    """It was emitting comedy, entertainment, celebrity, theater and festival
    off its own menu, because nothing checked."""
    for prompt in (SYSTEM_PROMPT, HISTORICAL_SYSTEM_PROMPT):
        assert ", ".join(TAGS) in prompt
    assert extract_clean(["Sport", "sports", "food", "food", "nonsense"]) == ["sport", "food"]


def test_an_upload_refused_after_it_was_written_leaves_nothing_behind(client, monkeypatch):
    """The refusal that happens *after* the bytes are on the disk.

    The cheap check runs before `save_upload` and costs nothing to fail. The
    one this covers is the second: by the time it runs the file exists, and
    the only reason it runs at all is that a concurrent upload from the same
    device can spend the allowance in between. Which is simulated here, since
    two real uploads racing is not reproducible in a test.

    An orphan from this path is invisible - referenced by no row, in no query -
    so nothing would ever notice it but the disk.
    """
    from fastapi import HTTPException

    import api.media
    import api.write

    before = sorted(api.media.MEDIA_DIR.iterdir()) if api.media.MEDIA_DIR.exists() else []

    seen = {"checks": 0}

    def spent_between_the_two_checks(used, limit, what):
        seen["checks"] += 1
        if seen["checks"] >= 2:
            raise HTTPException(status_code=429, detail="Daily upload limit reached.")

    monkeypatch.setattr(api.write, "refuse_over_quota", spent_between_the_two_checks)

    response = upload(client, device())
    assert response.status_code == 429, response.text
    assert seen["checks"] == 2, "the second check never ran, so the race is still open"

    after = sorted(api.media.MEDIA_DIR.iterdir()) if api.media.MEDIA_DIR.exists() else []
    assert after == before, f"a refused upload left {set(after) - set(before)} behind"
