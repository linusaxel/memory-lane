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
