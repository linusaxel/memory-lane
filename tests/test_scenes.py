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
