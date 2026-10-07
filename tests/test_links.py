"""Names in a summary link to Wikipedia only when exactly one entity answers,
and the links stay behind the gate with the summary. No network: Wikidata's
two answers are faked in the shapes the live API returned."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from api.gate import row_to_memory
from api.models import Coordinates
from pipeline import geocode, links
from pipeline.extract import save_memories
from tests.fakes import FakeAnthropic

COPENHAGEN = (55.676, 12.568)
STAUNING_URL = "https://en.wikipedia.org/wiki/Thorvald_Stauning"
SUMMARY = (
    "Prime Minister Thorvald Stauning, a former cigar sorter, would walk into "
    "Christiansborg and stop here for a herring sandwich."
)


def _entity(url=None, kind=None, coord=None):
    claims = {}
    if kind:
        claims["P31"] = [{"mainsnak": {"datavalue": {"value": {"id": kind}}}}]
    if coord:
        value = {"latitude": coord[0], "longitude": coord[1]}
        claims["P625"] = [{"mainsnak": {"datavalue": {"value": value}}}]
    return {"claims": claims, "sitelinks": {"enwiki": {"url": url}} if url else {}}


def _wikidata(monkeypatch, search, entities):
    def fake(url):
        if "wbsearchentities" in url:
            return {"search": [{"id": i, "match": {"text": t}} for i, t in search]}
        return {"entities": entities}

    monkeypatch.setattr(geocode, "_get_json", fake)


def test_the_one_exact_match_is_linked(monkeypatch):
    _wikidata(
        monkeypatch,
        [("Q1", "Thorvald Stauning"), ("Q2", "Stauning")],
        {"Q1": _entity(STAUNING_URL), "Q2": _entity("https://en.wikipedia.org/wiki/Stauning")},
    )
    assert links.wikipedia_url("Thorvald Stauning", COPENHAGEN) == STAUNING_URL


def test_two_answers_is_no_link_even_when_one_has_no_article(monkeypatch):
    """Five entities are called exactly "Christiansborg"; the only one with an
    English article was a slave ship, and it was linked (live, 2026-09-30)."""
    _wikidata(
        monkeypatch,
        [("Q1", "Christiansborg"), ("Q2", "Christiansborg")],
        {"Q1": _entity(), "Q2": _entity("https://en.wikipedia.org/wiki/Christiansborg_(ship)")},
    )
    assert links.wikipedia_url("Christiansborg", COPENHAGEN) is None


def test_a_family_name_and_a_faraway_namesake_do_not_count(monkeypatch):
    """Christiansborg is also a castle in Ghana."""
    _wikidata(
        monkeypatch,
        [("Q1", "Christiansborg"), ("Q2", "Christiansborg"), ("Q3", "Christiansborg")],
        {
            "Q1": _entity("palace", coord=(55.676, 12.58)),
            "Q2": _entity("ghana", coord=(5.55, -0.18)),
            "Q3": _entity("surname", kind="Q101352"),
        },
    )
    assert links.wikipedia_url("Christiansborg", COPENHAGEN) == "palace"


def test_a_silent_wikidata_is_not_stored_as_no_links(monkeypatch):
    monkeypatch.setattr(geocode, "_get_json", lambda url: None)
    with pytest.raises(links.LookupFailed):
        links.wikipedia_url("Thorvald Stauning", COPENHAGEN)


def test_the_written_name_is_linked_and_the_full_name_is_looked_up(monkeypatch):
    monkeypatch.setattr(links, "wikipedia_url", lambda name, near: f"https://w/{name}")
    fake = FakeAnthropic(
        {
            "names": [
                {"text": "Thorvald Stauning", "name": "Thorvald Stauning"},
                {"text": "Stauning Jr.", "name": "Stauning Jr."},
                {"text": " Christiansborg ", "name": "Christiansborg Palace"},
            ]
        }
    )
    assert links.links_for(fake, SUMMARY, COPENHAGEN) == [
        {"text": "Thorvald Stauning", "url": "https://w/Thorvald Stauning"},
        {"text": "Christiansborg", "url": "https://w/Christiansborg Palace"},
    ]


@pytest.mark.db
def test_links_are_stored_once_and_left_alone_after(db_session, monkeypatch):
    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://example.invalid/l', 'text', 'l', 'archive') RETURNING id"
        )
    ).scalar()
    save_memories(
        db_session,
        content_id,
        [
            {
                "venue": "Café Nick",
                "locality": "Copenhagen",
                "lat": 55.676,
                "lng": 12.568,
                "summary": SUMMARY,
                "confidence": "high",
                "location_precision": "exact",
            }
        ],
    )
    monkeypatch.setattr(links, "wikipedia_url", lambda name, near: STAUNING_URL)
    fake = FakeAnthropic({"names": [{"text": "Thorvald Stauning", "name": "Thorvald Stauning"}]})

    first = links.link_memories(db_session, fake, content_id=content_id)
    assert list(first.values()) == [[{"text": "Thorvald Stauning", "url": STAUNING_URL}]]
    assert links.link_memories(db_session, fake, content_id=content_id) == {}
    stored = db_session.execute(text("SELECT links FROM memories")).scalar()
    assert stored == [{"text": "Thorvald Stauning", "url": STAUNING_URL}]


def _row(**over):
    return SimpleNamespace(
        **{
            "id": 1,
            "place_id": 1,
            "place_name": "Café Nick",
            "precision_meters": 50,
            "lat": 55.676,
            "lng": 12.568,
            "coordinate_is_unique": True,
            "extraction_confidence": "high",
            "summary": SUMMARY,
            "tags": [],
            "content_id": None,
            "links": [{"text": "Thorvald Stauning", "url": STAUNING_URL}],
        }
        | over
    )


def test_links_stay_behind_the_gate():
    assert row_to_memory(_row(), at=None).links == []


def test_links_come_with_the_summary():
    opened = row_to_memory(_row(), at=Coordinates(lat=55.676, lng=12.568))
    assert json.loads(opened.model_dump_json())["links"][0]["url"] == STAUNING_URL


def test_pictures_come_only_with_the_summary():
    pictures = [{"url": "https://kbhallen.dk/a.jpg", "author": "K.B. Hallen", "source": True}]
    assert row_to_memory(_row(pictures=pictures), at=None).pictures == []
    opened = row_to_memory(_row(pictures=pictures), at=Coordinates(lat=55.676, lng=12.568))
    assert [p.url for p in opened.pictures] == ["https://kbhallen.dk/a.jpg"]
