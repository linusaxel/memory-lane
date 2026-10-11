import pytest

from pipeline import scenes
from pipeline.scenes import copied, opening_fault, raw_at, reach


def test_opening_fault():
    seen = {"the old royal"}
    assert opening_fault("This was where the mill stood.", seen)
    assert opening_fault("In 1827 a rope-dancer came.", seen)
    assert opening_fault("The old Royal Theatre is gone.", seen)
    assert opening_fault("Here, on the quay, a bear cub sat.", seen)
    assert opening_fault("This drill ground was where Roat fell.", seen)
    assert opening_fault("The walker is on Østergade.", seen)
    assert opening_fault("A bear cub sat with its back to the bulwark.", seen) is None
    assert opening_fault("Heiberg laughed.", seen) is None
    assert opening_fault("Tivoli is where the night ended.", seen)
    assert opening_fault("Kongens Nytorv was where the theatre stood.", seen)
    assert opening_fault("Tivoli hired a pianist.", seen) is None


def test_reach_finds_where_the_list_stopped():
    chunk = "Første side, en scene. " + "Mere tekst. " * 50
    found = [{"end": "en scene."}]
    done = reach(found, chunk)
    assert chunk[raw_at(chunk, done) :].startswith(". Mere")
    assert reach([], chunk) == 0


def test_copied_across_a_page_break():
    passage = "paa det nye\n\nOtto Zinck: Erindringer 3\n\n34\n\nkongelige Teater, som da"
    assert copied("det nye kongelige Teater", passage)
    assert not copied("det gamle kongelige Teater", passage)
    assert not copied("det nye Teater", "det nye " + "x" * 200 + " Teater")


def test_an_unsupported_fact_is_written_again_never_cut(monkeypatch):
    from pipeline import scenes

    entry = {
        "today": "Kongens Nytorv",
        "address": None,
        "old_name": "",
        "what": "",
        "standing": "no",
    }
    sheet = {
        "where": entry,
        "who": [],
        "what": [],
        "said": [],
        "context": [],
        "excerpt": {"text": ""},
    }
    flags = {
        "first": [{"claim": "two colleagues", "kind": "fact"}],
        "second": [{"claim": "sixteen", "kind": "fact"}],
        "flourish": [{"claim": "glittering", "kind": "colour"}],
        "bad": [{"claim": "a date", "kind": "fact"}],
    }
    draws, notes = [], []

    def write(*a):
        notes.append(a[-1])
        return {"summary": draws.pop(0), "quote": None}

    monkeypatch.setattr(scenes.extract, "unsupported", lambda *a: flags.get(a[-1], []))
    monkeypatch.setattr(scenes, "write", write)

    draws[:] = ["second", "clean"]
    assert scenes.faithful(None, None, 1, "", sheet, "first", "") == "clean"
    assert "two colleagues" in notes[-1] and "sixteen" in notes[-1]

    assert scenes.faithful(None, None, 1, "", sheet, "flourish", "") == "flourish"

    draws[:] = ["bad", "bad"]
    assert scenes.faithful(None, None, 1, "", sheet, "first", "") is None

    draws[:] = ["This was second", "clean"]
    assert scenes.faithful(None, None, 1, "", sheet, "first", "") == "clean"
    assert "stock opening" in notes[-1] and "two colleagues" in notes[-1]


def test_a_venue_with_an_aside_is_looked_up_bare(monkeypatch):
    asked = []

    def place(address, venue, *rest):
        asked.append(venue)
        return (55.67, 12.58, 50, "photon") if venue == "Charlottenborg" else None

    monkeypatch.setattr(scenes.geocode, "place", place)
    sc = {
        "venue": "Charlottenborg, Kongens Nytorv",
        "address": "",
        "index_place": "",
        "place_words": "x",
    }
    entry, hit = scenes.resolve(sc, {"places": []})
    assert asked == ["Charlottenborg, Kongens Nytorv", "Charlottenborg"]
    assert hit[3] == "photon"


def test_a_claim_is_kept_only_where_its_quote_is_found():
    passage = "Han kom over Langebro.\n\nDen 14. juli 1853 faldt bogen i vandet, sagde han."
    c = scenes.claim("The book fell in", "faldt bogen i vandet", passage)
    assert passage[c["pos"]["start"] : c["pos"]["end"]] == "faldt bogen i vandet"
    assert c["quote"]["prefix"].endswith("1853 ") and c["match"] == "exact"
    assert scenes.claim("The book flew", "bogen fløj væk", passage) is None
    on = "om broen, og så om aftenen den 5. april faldt han"
    assert scenes.claim("date", "om aftenen den 5. april", on)["quote"]["exact"] == (
        "om aftenen den 5. april"
    ), "an exact quote is taken where it stands, not from an earlier 'om'"


def test_the_excerpt_is_the_scene_in_whole_paragraphs():
    passage = (
        "Før.\n\nEn dag kom drengen op på broen. Han holdt bogen.\n\nDen fløj. Slut her.\n\nEfter."
    )
    sc = {"start": "drengen op på broen", "end": "Den fløj"}
    ex = scenes.excerpt(sc, passage)
    assert ex["text"] == passage, "within AROUND_CHARS of both ends: all of it"
    long = "x" * 2000 + "\n\nFør.\n\n" + passage[6:] + "\n\n" + "y" * 2000
    ex = scenes.excerpt(sc, long)
    assert ex["text"].startswith("Før.") and ex["text"].endswith("Efter.")
    assert long[ex["scene"]["start"] : ex["scene"]["end"]].startswith("drengen")


@pytest.mark.db
def test_a_saved_card_keeps_its_sheet(db_session):
    from sqlalchemy import text

    from pipeline.extract import save_memories

    content_id = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://www.gutenberg.org/ebooks/1#1', 'book', 'g1') RETURNING id"
        )
    ).scalar()
    sheet = {"schema_version": 1, "what": [{"fact": "The book fell"}]}
    card = {"place_name": "Langebro", "place_query": "Langebro", "lat": 55.67, "lng": 12.58}
    save_memories(db_session, content_id, [{**card, "summary": "s", "sheet": sheet}])
    stored = db_session.execute(text("SELECT sheet FROM memory_sheets")).scalar()
    assert stored["what"][0]["fact"] == "The book fell"


def test_render_writes_from_the_sheet_alone(monkeypatch):
    sent = []

    def request(session, client, cid, chunk, system, user, schema, ctx="", **kw):
        sent.append(user)
        return '{"summary": "Brodtkorb handed over his cigar.", "quote": null}'

    monkeypatch.setattr(scenes.extract, "_stored_request", request)
    monkeypatch.setattr(scenes.extract, "unsupported", lambda *a: [])
    where = {"today": "Amager Fælled", "address": None, "old_name": "Fælleden", "what": ""}
    sheet = {
        "where": {**where, "standing": "yes"},
        "source": {
            "title": "T",
            "kind": "memoir",
            "written": None,
            "author": "A",
            "author_life": None,
            "author_role": None,
            "why_care": "He was there.",
        },
        "who": [],
        "when": {"date": None},
        "what": [{"fact": "A mine went off", "quote": {"exact": "Minen sprang"}}],
        "said": [],
        "context": [],
        "why": "w",
        "excerpt": {"text": "Minen sprang."},
    }
    card = scenes.render(None, None, 1, "", sheet, set())
    assert card["summary"].startswith("Brodtkorb")
    assert "Minen sprang." in sent[0] and "A mine went off" in sent[0]


def test_a_book_waits_on_its_index_and_a_text_needs_none(monkeypatch):
    from types import SimpleNamespace

    from pipeline.extract import Collect

    monkeypatch.setattr(scenes.extract, "COLLECT", Collect())
    monkeypatch.setattr(
        scenes, "index_for", lambda s, c, sid, n, cid: scenes.wait_on(cid, None, "i")
    )
    books = {}
    memoir = SimpleNamespace(source_id=7, source_name="B", source_type="book", title="t")
    assert scenes.book(None, None, books, memoir, 42) is None
    assert scenes.waiting(42) and 7 not in books

    monkeypatch.setattr(scenes, "index_for", lambda *a: pytest.fail("a text has no index"))
    article = SimpleNamespace(
        source_id=8, source_name="Wikipedia", source_type="encyclopedia", title="Allotria-huset"
    )
    b = scenes.book(None, None, books, article, 43)
    assert b["index"] == scenes.NO_INDEX and b["source"]["title"] == "Allotria-huset"
    assert scenes.worded(scenes.FIND_PROMPT, "book") is scenes.FIND_PROMPT
    assert "an encyclopedia article about" in scenes.worded(scenes.FIND_PROMPT, "encyclopedia")


def test_a_spot_whose_fate_is_unknown_tells_the_writer_nothing_of_it():
    from pipeline.scenes import spot_card

    entry = {"today": "Howitzvej", "address": None, "old_name": "3 Falke Bio", "what": ""}
    assert "Now: gone." in spot_card(entry | {"standing": "no"})
    assert "Now" not in spot_card(entry | {"standing": "unknown"})


def test_a_card_that_hedges_is_written_once_more_told_to_fix_it(monkeypatch):
    from pipeline import scenes

    entry = {
        "today": "Howitzvej",
        "address": None,
        "old_name": "",
        "what": "",
        "standing": "unknown",
    }
    sheet = {
        "where": entry,
        "who": [],
        "what": [],
        "said": [],
        "context": [],
        "excerpt": {"text": ""},
    }
    cards = iter(
        [
            {
                "summary": "Spies bought a seat for his stick; it is not known if it stands.",
                "quote": None,
            },
            {"summary": "Spies bought a seat for his stick.", "quote": None},
        ]
    )
    notes = []
    monkeypatch.setattr(
        scenes, "write", lambda *a: notes.append(a[-1] if len(a) > 5 else "") or next(cards)
    )
    monkeypatch.setattr(scenes.extract, "unsupported", lambda *a: [])
    card = scenes.render(None, None, 1, "ctx", sheet, set())
    assert card["summary"] == "Spies bought a seat for his stick."
    assert notes[1].startswith("Fix: say only what is known")
