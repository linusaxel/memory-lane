"""DAWA places a Danish address, but only when it answered the question asked.
No network: urlopen returns what the live API returned on 2026-09-26."""

import io
import json

import pytest
from sqlalchemy import text

from pipeline import geocode
from pipeline.extract import save_memories


def _answer(monkeypatch, vejnavn, husnr):
    hit = {"vejnavn": vejnavn, "husnr": husnr, "x": 12.5588, "y": 55.6870, "betegnelse": "b"}
    monkeypatch.setattr(
        geocode.urllib.request,
        "urlopen",
        lambda url, timeout: io.BytesIO(json.dumps([hit]).encode()),
    )


def test_old_spelling_after_renumbering_is_exact(monkeypatch):
    _answer(monkeypatch, "Blågårdsgade", "12")
    assert geocode.dawa("Blaagaardsgade 12", "København", 1900) == (55.6870, 12.5588, 50)


@pytest.mark.parametrize("year", [1856, None])
def test_a_number_before_1859_or_undated_is_only_the_street(monkeypatch, year):
    _answer(monkeypatch, "Gothersgade", "330")
    assert geocode.dawa("Gothersgaden 330", "Kjøbenhavn", year)[2] == 200


def test_fuzzy_answering_a_different_street_is_a_miss(monkeypatch):
    _answer(monkeypatch, "Vestergade", "9")
    assert geocode.dawa("Nonexistentgade 999", "København", 1900) is None


def _memory(**over):
    return {
        "venue": "Kielderen",
        "locality": "Copenhagen",
        "region": "Denmark",
        "address": "Blaagaardsgade 12",
        "lat": 55.6761,
        "lng": 12.5683,
        "summary": "A cellar shop opened here in 1900.",
        "tags": ["history"],
        "confidence": "high",
        "location_precision": "city",
        "happened_at": "1900",
        **over,
    }


def _place(db_session):
    return db_session.execute(
        text(
            "SELECT geocode_status, precision_meters, ST_Y(coordinates::geometry) AS lat FROM places"
        )
    ).one()


@pytest.mark.db
def test_a_dawa_hit_replaces_the_models_centroid(monkeypatch, db_session):
    monkeypatch.setattr(geocode, "dawa", lambda *a: (55.6870, 12.5588, 50))
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, source_type) VALUES ('u', 'text', 'newspaper') RETURNING id"
        )
    ).scalar()
    save_memories(db_session, cid, [_memory()])
    assert tuple(_place(db_session)) == ("dawa", 50, pytest.approx(55.6870))


@pytest.mark.db
def test_a_miss_or_a_foreign_place_keeps_the_models_coordinate(monkeypatch, db_session):
    asked = []
    monkeypatch.setattr(geocode, "dawa", lambda *a: asked.append(a))
    cid = db_session.execute(
        text(
            "INSERT INTO content (url, platform, source_type) VALUES ('u', 'text', 'newspaper') RETURNING id"
        )
    ).scalar()
    save_memories(db_session, cid, [_memory(), _memory(venue="Elsewhere", region="Sweden")])
    assert len(asked) == 1
    rows = db_session.execute(text("SELECT DISTINCT geocode_status FROM places")).scalars().all()
    assert rows == ["llm"]
