"""Text sources fetch records; ingest_records writes them. No network: urlopen
is replaced with a saved-shape KB Labs CSV."""

import io

import pytest
from sqlalchemy import text

from crawler import kb_aviser
from crawler.sources import SOURCES
from pipeline.ingest import ingest_records

ARTICLE = "En Kielder er tilleie i Blaagaardsgade 12. " * 10
CSV = (
    '"link","recordID","timestamp","familyId","fulltext_org"\n'
    f'"https://example.invalid/p1","doc:uuid:ab-segment_1","1856-04-01T01:00:00","adresseavisen1759","{ARTICLE}"\n'
    '"https://example.invalid/p2","r2","1856-04-02T01:00:00","adresseavisen1759","Anvises."\n'
)


@pytest.fixture
def kb(monkeypatch):
    asked = []

    def _urlopen(url, timeout):
        asked.append(url)
        return io.BytesIO(CSV.encode())

    monkeypatch.setattr(kb_aviser.urllib.request, "urlopen", _urlopen)
    return asked


def test_a_kb_row_becomes_a_danish_record_and_a_scrap_is_dropped(kb):
    records = list(SOURCES["kb-aviser"].fetch("Blaagaardsgade", 5))
    assert records == [
        {
            "source_url": "https://example.invalid/p1#segment_1",
            "title": "adresseavisen1759 1856-04-01",
            "text": ARTICLE.strip(),
            "language": "da",
        }
    ]
    assert "query=Blaagaardsgade" in kb[0] and "max=5" in kb[0]


@pytest.mark.db
def test_a_source_ingests_as_its_own_type(kb, ingest_into, db_session):
    src = SOURCES["kb-aviser"]
    ingest_records(src.fetch("x", 5), source_name=src.source_name, source_type=src.source_type)
    row = db_session.execute(
        text(
            "SELECT c.source_type, t.language FROM content c JOIN transcripts t ON t.content_id = c.id"
        )
    ).one()
    assert (row.source_type, row.language) == ("newspaper", "da")


def test_only_the_text_around_the_street_is_kept():
    page = "x" * 5000 + " Blaagaardsgade 12 " + "y" * 5000
    kept = kb_aviser._windows(page, "blaagaardsgade")
    assert "Blaagaardsgade 12" in kept
    assert len(kept) < 2 * kb_aviser.WINDOW_CHARS + 100


def test_two_close_mentions_are_one_window_and_no_mention_keeps_everything():
    page = "a" * 3000 + "Gade" + "b" * 100 + "Gade" + "c" * 3000
    assert "…" not in kb_aviser._windows(page, "Gade")
    assert kb_aviser._windows("nothing here", "Gade") == "nothing here"


SITEMAP = (
    "<urlset><url><loc>https://historiskatlas.dk/Sabotage_mod_Værft,_16.01.1944_(19000)</loc></url>"
    "<url><loc>https://historiskatlas.dk/Stüler_&amp;_Co_(19266)</loc></url></urlset>"
)
PAGE = (
    'window.passed = {\n geo: {"geoid":19000,"title":"Sabotage mod Værft, 16.01.1944",'
    '"intro":"3 bomber blev anbragt på en tagkran.","latitude":57.05,"longitude":9.94,'
    '"contents":null}, \n collection: null };'
)


def test_an_atlas_story_matched_by_title_carries_its_point(monkeypatch):
    from crawler import historisk_atlas

    asked = []

    def _urlopen(request, timeout):
        asked.append(request.full_url)
        return io.BytesIO((SITEMAP if request.full_url.endswith(".xml") else PAGE).encode())

    monkeypatch.setattr(historisk_atlas.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(historisk_atlas.time, "sleep", lambda s: None)
    records = list(SOURCES["historisk-atlas"].fetch("sabotage", 5))
    assert asked[1] == "https://historiskatlas.dk/Sabotage_mod_V%C3%A6rft,_16.01.1944_(19000)"
    assert len(asked) == 2 and len(records) == 1
    assert records[0]["title"] == "Sabotage mod Værft, 16.01.1944"
    assert records[0]["text"].endswith("places this at 57.05, 9.94.")
