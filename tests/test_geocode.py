"""The geocoder chain places what the model names, and one guard decides which
answers count. Every case here was found against the live APIs on 2026-09-26.
No network: geocoders are faked, and the providers' parsers read saved shapes."""

import io
import json

import pytest
from sqlalchemy import text

from pipeline import geocode
from pipeline.extract import save_memories
from pipeline.geocode import Hit

COPENHAGEN = (55.676, 12.568)


class Fake:
    def __init__(self, hits, source="fake", handles=("address", "venue"), countries=None):
        self.hits, self.source = hits, source
        self.handles, self.countries = frozenset(handles), countries and frozenset(countries)
        self.asked = []

    def search(self, text, locality, near):
        self.asked.append(text)
        return self.hits


def _chain(monkeypatch, *geocoders):
    monkeypatch.setattr(geocode, "GEOCODERS", list(geocoders))


def _poi(name, lat=55.668, lng=12.544, kind="poi"):
    return Hit(lat, lng, name, None, None, kind, "fake")


def test_a_venue_is_placed_by_its_own_name(monkeypatch):
    _chain(monkeypatch, Fake([_poi("Vega")]))
    assert geocode.place(None, "Vega", "Copenhagen", "DK", COPENHAGEN, None) == (
        55.668,
        12.544,
        50,
        "fake",
    )


def test_a_different_building_with_a_fuzzy_match_is_refused(monkeypatch):
    """Photon answered "Blaagaardsgade 12" with Moltkes Palæ."""
    moltke = Hit(55.683, 12.588, "Moltkes Palæ", "Dronningens Tværgade", None, "poi", "fake")
    _chain(monkeypatch, Fake([moltke]))
    assert (
        geocode.place("Blaagaardsgade 12", "Kielderen", "Copenhagen", "DK", COPENHAGEN, None)
        is None
    )


def test_a_city_centre_is_not_a_place_so_the_next_geocoder_answers(monkeypatch):
    """Photon placed CBGB, closed in 2006, on the centre of New York; Wikidata knows it."""
    nyc = (40.72, -73.99)
    photon = Fake([_poi("New York", 40.7128, -74.006, kind="city")], source="photon")
    wikidata = Fake([_poi("CBGB", 40.7253, -73.9919)], source="wikidata")
    _chain(monkeypatch, photon, wikidata)
    assert geocode.place(None, "CBGB", "New York City", "US", nyc, None)[3] == "wikidata"


def test_a_same_name_place_far_from_the_models_guess_is_refused(monkeypatch):
    _chain(monkeypatch, Fake([_poi("Vega", 59.33, 18.06)]))  # a Vega in Stockholm
    assert geocode.place(None, "Vega", "Copenhagen", "DK", COPENHAGEN, None) is None


@pytest.mark.parametrize(("year", "metres"), [(2001, 50), (None, 50), (1856, 200)])
def test_a_house_number_before_1900_is_only_the_street(monkeypatch, year, metres):
    """Copenhagen renumbered its houses in 1859: Gothersgade 330 then is not 330 now."""
    _chain(monkeypatch, Fake([Hit(55.682, 12.583, None, "Gothersgade", "330", "house", "fake")]))
    assert geocode.place("Gothersgade 330", None, "Copenhagen", "DK", COPENHAGEN, year)[2] == metres


def test_a_street_the_address_did_not_name_is_refused(monkeypatch):
    """DAWA answered "Nonexistentgade 999" with Vestergade 9, Nibe."""
    _chain(monkeypatch, Fake([Hit(55.68, 12.56, None, "Vestergade", "9", "house", "fake")]))
    assert geocode.place("Nonexistentgade 999", None, "Copenhagen", "DK", COPENHAGEN, None) is None


def test_the_number_may_come_first():
    assert geocode._split_address("726 St Peter Street, New Orleans") == ("St Peter Street", "726")
    assert geocode._split_address("Vesterbro 47 A") == ("Vesterbro", "47")


def test_a_national_geocoder_only_hears_its_own_country(monkeypatch):
    dk = Fake([], countries={"DK"})
    _chain(monkeypatch, dk)
    geocode.place("Bourbon Street 1", None, "New Orleans", "US", None, None)
    assert dk.asked == []


def _serve(monkeypatch, *bodies):
    answers = iter(bodies)
    monkeypatch.setattr(
        geocode.urllib.request,
        "urlopen",
        lambda req, timeout: io.BytesIO(json.dumps(next(answers)).encode()),
    )


def test_photon_reads_a_named_house_as_a_place_and_a_city_as_a_city(monkeypatch):
    monkeypatch.setattr(geocode.time, "sleep", lambda s: None)
    feature = lambda name, kind, xy: {  # noqa: E731
        "geometry": {"coordinates": xy},
        "properties": {"name": name, "type": kind, "street": "Rejsbygade"},
    }
    _serve(
        monkeypatch,
        {
            "features": [
                feature("Vega", "house", [12.544, 55.668]),
                feature("København", "city", [12.57, 55.68]),
            ]
        },
    )
    vega, city = geocode.Photon().search("Vega", "Copenhagen", None)
    assert (vega.kind, vega.lat, vega.name) == ("poi", 55.668, "Vega")
    assert city.kind == "city"


def test_wikidata_takes_coordinates_from_P625_and_skips_items_without(monkeypatch):
    _serve(
        monkeypatch,
        {"search": [{"id": "Q1"}, {"id": "Q2"}]},
        {
            "entities": {
                "Q1": {
                    "labels": {"en": {"value": "CBGB"}},
                    "claims": {
                        "P625": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {"latitude": 40.7253, "longitude": -73.9919}
                                    }
                                }
                            }
                        ]
                    },
                },
                "Q2": {"labels": {"en": {"value": "CBGB (film)"}}, "claims": {}},
            }
        },
    )
    assert geocode.Wikidata().search("CBGB", None, None) == [
        Hit(40.7253, -73.9919, "CBGB", None, None, "poi", "wikidata")
    ]


def _memory(**over):
    return {
        "venue": "Vega",
        "locality": "Copenhagen",
        "region": "Denmark",
        "country": "DK",
        "lat": 55.6761,
        "lng": 12.5683,
        "summary": "A band played the upstairs room in 1978.",
        "tags": ["music"],
        "confidence": "high",
        "location_precision": "city",
        **over,
    }


def _content(db_session):
    return db_session.execute(
        text(
            "INSERT INTO content (url, platform, source_type) VALUES ('u', 'text', 'newspaper') RETURNING id"
        )
    ).scalar()


def _place(db_session):
    return db_session.execute(
        text(
            "SELECT geocode_status, precision_meters, ST_Y(coordinates::geometry) AS lat FROM places"
        )
    ).one()


@pytest.mark.db
def test_a_geocoded_place_replaces_the_models_centroid(monkeypatch, db_session):
    _chain(monkeypatch, Fake([_poi("Vega")], source="photon"))
    save_memories(db_session, _content(db_session), [_memory()])
    assert tuple(_place(db_session)) == ("photon", 50, pytest.approx(55.668))


@pytest.mark.db
def test_no_accepted_hit_keeps_the_models_coordinate(monkeypatch, db_session):
    _chain(monkeypatch, Fake([]))
    save_memories(db_session, _content(db_session), [_memory()])
    assert tuple(_place(db_session)) == ("llm", 10000, pytest.approx(55.6761))
