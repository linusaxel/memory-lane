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


def _inception(*times):
    """wbgetentities' shape for Børsen (Q1060870), one P571 claim per (time, precision)."""
    claims = [{"mainsnak": {"datavalue": {"value": {"time": t, "precision": p}}}} for t, p in times]
    return {"entities": {"Q1060870": {"claims": {"P571": claims}}}}


BORSEN = {"name": "Børsen", "amenity": "stock_exchange", "wikidata": "Q1060870"}


def _both(monkeypatch, area, wikidata):
    overpass = {"elements": [{"tags": area}]}
    monkeypatch.setattr(
        geocode, "_get_json", lambda url: wikidata if "wikidata.org" in url else overpass
    )


def test_the_wikidata_tag_dates_what_stands_there(monkeypatch):
    _both(
        monkeypatch, BORSEN, _inception(("+1640-00-00T00:00:00Z", 9), ("+1619-00-00T00:00:00Z", 9))
    )
    found = now.now_at(55.6758, 12.5833, "Børsen")
    assert found["since"] == 1619, "the earliest inception"
    assert now.clause(found) == "Still Børsen, a stock exchange, since 1619."


def test_a_century_is_no_year_and_no_tag_reads_as_before(monkeypatch):
    _both(monkeypatch, BORSEN, _inception(("+1600-00-00T00:00:00Z", 7)))
    assert now.clause(now.now_at(55.6758, 12.5833, "Børsen")) == "Still Børsen, a stock exchange."
    _both(monkeypatch, {k: v for k, v in BORSEN.items() if k != "wikidata"}, None)
    assert "since" not in now.now_at(55.6758, 12.5833, "Børsen")


def test_a_silent_wikidata_is_retried_not_stored(monkeypatch):
    _both(monkeypatch, BORSEN, None)
    with pytest.raises(now.LookupFailed):
        now.now_at(55.6758, 12.5833, "Børsen")


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


def _areas_then_points(monkeypatch, areas, points):
    """is_in answers with the areas, the `around` query with the points."""
    monkeypatch.setattr(
        geocode,
        "_get_json",
        lambda url: {"elements": [{"tags": t} for t in (points if "around" in url else areas)]},
    )


def test_a_bar_stored_as_a_point_is_still_there(monkeypatch):
    """Café Lille Peter is an OSM node; the pin stands inside no named area."""
    _areas_then_points(
        monkeypatch,
        [REGION],
        [{"name": "Café Lille Peter", "amenity": "bar"}, {"name": "Stefansgade"}],
    )
    found = now.now_at(55.6958, 12.5439, "Café Lille Peter")
    assert now.clause(found) == "Still Café Lille Peter, a bar."


def test_another_bar_nearby_is_not_a_change(monkeypatch):
    """25 m holds the bar next door too, so only a name match counts."""
    _areas_then_points(monkeypatch, [REGION], [{"name": "Andre Wine Bar", "amenity": "bar"}])
    assert now.now_at(55.6958, 12.5439, "Café Lille Peter") == {}


def test_a_silent_point_query_is_not_stored_as_nothing_there(monkeypatch):
    monkeypatch.setattr(
        geocode, "_get_json", lambda url: None if "around" in url else {"elements": []}
    )
    with pytest.raises(now.LookupFailed):
        now.now_at(55.6958, 12.5439, "Café Lille Peter")


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

    assert now.look_up(db_session, content_id=content_id + 1) == {}
    assert list(now.look_up(db_session, content_id=content_id).values()) == [
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
