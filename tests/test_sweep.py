"""The reaper for uploads nothing ever claimed.

A photo goes up the moment it is picked, so the wait happens while somebody is
still typing. Close the sheet and the row keeps memory_id IS NULL and the file
stays on the disk for ever, referenced by nothing. The allowance is 64MB per
device per day, so uploading to it and cancelling costs a device nothing.

Destructive, and pointed at a directory, which is why the tests are as much
about what it leaves alone as what it takes.
"""

import pytest
from sqlalchemy import text

import api.media
from pipeline.sweep import sweep

pytestmark = pytest.mark.db

OLD = "LOCALTIMESTAMP - INTERVAL '3 days'"


@pytest.fixture
def media_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(api.media, "MEDIA_DIR", tmp_path)
    import pipeline.sweep

    monkeypatch.setattr(pipeline.sweep, "MEDIA_DIR", tmp_path)
    return tmp_path


def _device(session):
    device = "5eed0000-0000-4000-8000-0000000005ee"
    session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT DO NOTHING"),
        {"d": device},
    )
    return device


def _upload(session, media_dir, name, *, claimed_by=None, aged=False):
    (media_dir / name).write_bytes(b"x" * 10)
    session.execute(
        text(
            "INSERT INTO media (device_id, kind, path, mime, bytes, memory_id, created_at) "
            f"VALUES (CAST(:d AS uuid), 'photo', :p, 'image/png', 10, :m, {OLD if aged else 'LOCALTIMESTAMP'})"
        ),
        {"d": _device(session), "p": name, "m": claimed_by},
    )


def _memory(session):
    place = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Here', 'sweep:here', ST_MakePoint(12.5, 55.6)::geography, 25) RETURNING id"
        )
    ).scalar()
    return session.execute(
        text("INSERT INTO memories (place_id, summary) VALUES (:p, 'kept') RETURNING id"),
        {"p": place},
    ).scalar()


def test_an_abandoned_upload_is_taken(db_session, media_dir):
    _upload(db_session, media_dir, "abandoned.png", aged=True)

    rows, stray = sweep(db_session, hours=24, apply=True)

    assert (rows, stray) == (1, 0)
    assert not (media_dir / "abandoned.png").exists()
    assert db_session.execute(text("SELECT COUNT(*) FROM media")).scalar() == 0


def test_an_upload_somebody_is_still_writing_is_left_alone(db_session, media_dir):
    """The ordinary case: picked a photo, still typing. Nothing younger than
    the window is in scope, or the reaper races the person."""
    _upload(db_session, media_dir, "in-progress.png", aged=False)

    assert sweep(db_session, hours=24, apply=True) == (0, 0)
    assert (media_dir / "in-progress.png").exists()
    assert db_session.execute(text("SELECT COUNT(*) FROM media")).scalar() == 1


def test_a_claimed_upload_is_left_alone_however_old(db_session, media_dir):
    """The thing it must never take: somebody's photograph."""
    _upload(db_session, media_dir, "claimed.png", claimed_by=_memory(db_session), aged=True)

    assert sweep(db_session, hours=24, apply=True) == (0, 0)
    assert (media_dir / "claimed.png").exists()
    assert db_session.execute(text("SELECT COUNT(*) FROM media")).scalar() == 1


def test_a_file_with_no_row_is_taken_once_it_is_old(db_session, media_dir):
    """A process killed between writing the file and inserting the row. The
    refusal path cleans up after itself; a SIGKILL cannot."""
    import os
    import time

    stray = media_dir / "crashed.png"
    stray.write_bytes(b"x" * 10)
    old = time.time() - 3 * 24 * 3600
    os.utime(stray, (old, old))

    assert sweep(db_session, hours=24, apply=True) == (0, 1)
    assert not stray.exists()
