"""The `sources` table: what ingest polls, what bulk extraction may bill, what
discovery adds, and what screening spends. Real PostGIS; no network (the
crawler and Haiku are faked)."""

from contextlib import contextmanager

import pytest
from sqlalchemy import text

from crawler.gutenberg import windows
from pipeline import ingest, sources, tasks
from pipeline.extract import PENDING_EXTRACTION

pytestmark = pytest.mark.db


def _source(session, locator, status, kind="youtube_channel", name="S"):
    return session.execute(
        text("""
            INSERT INTO sources (kind, locator, name, status)
            VALUES (:kind, :locator, :name, :status) RETURNING id
        """),
        {"kind": kind, "locator": locator, "name": name, "status": status},
    ).scalar()


@pytest.fixture
def one_session(ingest_into, monkeypatch):
    """pipeline.sources opens its own sessions too."""

    @contextmanager
    def _session():
        yield ingest_into

    monkeypatch.setattr(sources, "get_session", _session)
    return ingest_into


def test_only_active_channels_are_polled(ingest_into):
    active = _source(ingest_into, "https://www.youtube.com/channel/A", "active")
    _source(ingest_into, "https://www.youtube.com/channel/B", "trial")
    _source(ingest_into, "https://www.youtube.com/channel/C", "candidate")
    _source(ingest_into, "gutenberg:1 x", "active", kind="book")

    polled = ingest.load_config()["sources"]
    assert [s["id"] for s in polled] == [active]
    assert polled[0]["channel"] == "https://www.youtube.com/channel/A"


def test_an_ingested_video_remembers_its_source(ingest_into):
    sid = _source(ingest_into, "https://www.youtube.com/channel/A", "trial")
    config = {
        "sources": [{"id": sid, "name": "S", "videos": [{"url": "https://youtu.be/aaaaaaaaaaa"}]}]
    }
    ingest.ingest_content(config)
    assert ingest_into.execute(text("SELECT source_id FROM content")).scalar() == sid


def test_a_candidates_items_are_never_billed_in_bulk(ingest_into):
    """Screening ingests a candidate's videos; `enqueue --all` must not then
    send them to Sonnet."""
    for status in ("candidate", "rejected", "trial", None):
        sid = _source(ingest_into, f"loc-{status}", status or "active") if status else None
        cid = ingest_into.execute(
            text("""
                INSERT INTO content (url, platform, source_id, transcript_fetched, title)
                VALUES (:url, 'youtube', :sid, TRUE, :t) RETURNING id
            """),
            {"url": f"https://x/{status}", "sid": sid, "t": str(status)},
        ).scalar()
        ingest_into.execute(
            text("INSERT INTO transcripts (content_id, segments) VALUES (:id, '[]')"), {"id": cid}
        )
    pending = sorted(
        r[0] for r in ingest_into.execute(text(f"SELECT c.title {PENDING_EXTRACTION}"))
    )
    assert pending == ["None", "trial"]


def _search(results):
    def search(query, limit):
        return results.get(query, [])

    return search


def _hit(channel, minutes=40, title="Nørrebro"):
    return {
        "url": "https://www.youtube.com/watch?v=x",
        "title": title,
        "duration_seconds": minutes * 60,
        "channel": channel,
        "channel_url": f"https://www.youtube.com/channel/{channel}",
    }


def test_discovery_adds_each_new_channel_once_and_skips_known_clips_and_off_topic(ingest_into):
    _source(ingest_into, "https://www.youtube.com/channel/REJECTED", "rejected")
    search = _search(
        {
            "q1": [
                _hit("NEW", title="Blågårdsgade 1970"),
                _hit("REJECTED"),
                _hit("CLIPS", 3),
                _hit("TAROT", title="Fuldmåne i Vædderen"),
            ],
            "q2": [_hit("NEW")],
        }
    )

    new = sources.discover(ingest_into, ["q1", "q2"], search)
    again = sources.discover(ingest_into, ["q1", "q2"], search)

    assert [(n["name"], n["hits"]) for n in new] == [("NEW", 2)]
    assert again == []
    row = ingest_into.execute(
        text("SELECT status, found_via, note FROM sources WHERE name = 'NEW'")
    ).one()
    assert row.status == "candidate" and row.found_via == "search:q1"
    assert "Blågårdsgade 1970" in row.note


class _Haiku:
    """Says yes to a chunk that mentions a street."""

    class messages:
        calls = 0

        @classmethod
        def create(cls, **kwargs):
            cls.calls += 1
            has = "gade" in kwargs["messages"][0]["content"]
            reply = f'{{"has_memories": {str(has).lower()}, "reason": "r"}}'
            return type("R", (), {"content": [type("C", (), {"text": reply})()], "usage": None})()


def test_screening_spends_haiku_only_and_reports_the_pass_rate(one_session, monkeypatch):
    import crawler.sources

    sid = _source(one_session, "fake:query", "candidate", kind="book")

    class Fake:
        source_type = "book"

        def fetch(self, query, limit):
            yield {"source_url": "https://x/1", "text": "Vi boede i Blaagaardsgade."}
            yield {"source_url": "https://x/2", "text": "Nothing here."}

    monkeypatch.setattr(crawler.sources, "SOURCES", {"fake": Fake()})
    monkeypatch.setattr(tasks, "log_cache", lambda r: None)

    assert sources.screen(sid, sample=2, client=_Haiku()) == pytest.approx(0.5)
    assert one_session.execute(text("SELECT count(*) FROM extraction_chunks")).scalar() == 0
    # A rerun screens nothing new: the verdicts are already there.
    calls = _Haiku.messages.calls
    sources.screen(sid, sample=2, client=_Haiku())
    assert _Haiku.messages.calls == calls


def test_a_book_is_cut_to_the_windows_that_name_the_place():
    raw = (
        "Title: Letters\n*** START OF THE BOOK ***\n\n"
        + "\n\n".join(["Stockholm is cold. " * 300, "Copenhagen burned. " * 300, "Oslo."])
        + "\n\n*** END OF THE BOOK ***\nlicence text Copenhagen"
    )
    kept = windows(raw, "copenhagen")
    assert len(kept) == 1 and kept[0].startswith("Copenhagen burned.")
    assert "licence" not in "".join(windows(raw))
