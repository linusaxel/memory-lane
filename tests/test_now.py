"""The "now" side of a contrast is written only when OSM names what the pin
stands inside. No network: Overpass's answers are faked in the shapes the live
API returned on 2026-09-30."""

import pytest
from sqlalchemy import text

from pipeline import geocode, now
from pipeline.extract import save_memories


def _overpass(monkeypatch, *areas):
    monkeypatch.setattr(
        geocode, "_get_json", lambda url: {"elements": [{"tags": t} for t in areas]}
    )


REGION = {"name": "Region Hovedstaden", "admin_level": "4"}


def test_a_different_place_there_now_is_a_change(monkeypatch):
    """Frederikshospitalet's pin stands inside Designmuseum Danmark."""
    _overpass(monkeypatch, REGION, {"name": "Designmuseum Danmark", "tourism": "museum"})
    found = now.now_at(55.6866, 12.5928, "Frederikshospitalet")
    assert found == {"name": "Designmuseum Danmark", "kind": "museum", "same": False}
    assert now.clause(found) == "Now Designmuseum Danmark, a museum."


def test_the_same_place_under_its_local_name_is_still_there(monkeypatch):
    """The model says "Church of Our Lady"; OSM's name is Vor Frue Kirke."""
    church = {
        "name": "Vor Frue Kirke",
        "name:en": "Church of Our Lady",
        "amenity": "place_of_worship",
    }
    _overpass(monkeypatch, church)
    found = now.now_at(55.6793, 12.5725, "Church of Our Lady")
    assert now.clause(found) == "Still Vor Frue Kirke, a place of worship."


def test_an_old_name_is_not_a_name_it_goes_by_now(monkeypatch):
    _overpass(
        monkeypatch,
        {"name": "Designmuseum Danmark", "old_name": "Frederikshospitalet", "tourism": "museum"},
    )
    assert now.now_at(55.6866, 12.5928, "Frederikshospitalet")["same"] is False


def test_a_bare_building_or_a_neighbourhood_says_nothing(monkeypatch):
    _overpass(
        monkeypatch,
        {"name": "Tivoli Food Hall", "building": "yes"},
        {"name": "Hellebæksgade Stefansgade", "landuse": "residential"},
    )
    assert now.now_at(55.674, 12.565, "Copenhagen Hotdog") == {}


def test_a_silent_overpass_is_not_stored_as_nothing_there(monkeypatch):
    monkeypatch.setattr(geocode, "_get_json", lambda url: None)
    with pytest.raises(now.LookupFailed):
        now.now_at(55.6866, 12.5928, "Frederikshospitalet")


@pytest.mark.db
def test_the_clause_replaces_the_models_guess_on_a_building_pin_only(db_session, monkeypatch):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.invalid/n', 'text', 'n', 'archive') RETURNING id"
        )
    ).scalar()
    guess = {"contrast_score": 0.7, "contrast_note": "current use unknown"}
    save_memories(
        db_session,
        content_id,
        [
            {
                "venue": venue,
                "locality": "Copenhagen",
                "lat": lat,
                "lng": 12.59,
                "summary": f"A story at {venue}.",
                "confidence": "high",
                "location_precision": "exact",
            }
            | guess
            for venue, lat in (("Frederikshospitalet", 55.686), ("Somewhere Guessed", 55.690))
        ],
    )
    db_session.execute(
        text(
            "UPDATE places SET precision_meters = 50, geocode_status = "
            "CASE WHEN venue = 'Frederikshospitalet' THEN 'dawa' ELSE 'llm' END"
        )
    )
    _overpass(monkeypatch, {"name": "Designmuseum Danmark", "tourism": "museum"})

    assert list(now.look_up(db_session).values()) == [
        {"name": "Designmuseum Danmark", "kind": "museum", "same": False}
    ]
    assert now.look_up(db_session) == {}
    rows = db_session.execute(
        text(
            "SELECT p.venue, m.contrast_note, m.contrast_score FROM memories m "
            "JOIN places p ON p.id = m.place_id ORDER BY p.venue"
        )
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ("Frederikshospitalet", "Now Designmuseum Danmark, a museum.", pytest.approx(now.CHANGED)),
        ("Somewhere Guessed", "current use unknown", pytest.approx(0.7)),
    ]
