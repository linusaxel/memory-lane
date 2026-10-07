"""Enrichment keeps only what a page we fetched says (pipeline/enrich.py)."""

from pipeline.enrich import source_pictures, verified

PAGE = "Olaf Sæther-Nielsen (1891-1967) decorated the Alexandra cinema in 1942."
URL = "https://example.org/alexandra"


def _fetch(url):
    from pipeline.extract import _squash

    return _squash(PAGE) if url == URL else None


def _found(**overrides):
    return {"people": [], "quotes": [], "then_now": [], "asides": []} | overrides


def test_an_item_stays_only_when_its_passage_is_on_its_page():
    kept = verified(
        _found(
            asides=[
                {"text": "He decorated it.", "url": URL, "passage": "decorated the Alexandra"},
                {"text": "He carved it.", "url": URL, "passage": "carved the Alexandra"},
                {"text": "Elsewhere.", "url": "https://example.org/gone", "passage": "decorated"},
            ]
        ),
        fetch=_fetch,
    )
    assert [a["text"] for a in kept["asides"]] == ["He decorated it."]


def test_a_person_needs_their_name_on_the_page_and_a_quote_its_words():
    person = {"name": "Olaf Sæther-Nielsen", "url": URL, "passage": "(1891-1967)"}
    stranger = dict(person, name="Hans Hansen")
    quote = {"text": "decorated the Alexandra cinema", "url": URL, "passage": "in 1942"}
    made_up = dict(quote, text="the finest cinema in town")
    kept = verified(_found(people=[person, stranger], quotes=[quote, made_up]), fetch=_fetch)
    assert kept["people"] == [person]
    assert kept["quotes"] == [quote]


def test_an_empty_passage_or_a_non_web_url_proves_nothing():
    kept = verified(
        _found(
            then_now=[
                {"then": "a cinema", "now": "a club", "url": URL, "passage": ""},
                {"then": "a cinema", "now": "a club", "url": "file:///etc/passwd", "passage": "x"},
            ]
        ),
        fetch=_fetch,
    )
    assert kept["then_now"] == []


def test_a_thin_record_with_nothing_found_seeds_nothing(monkeypatch):
    from pipeline import enrich

    monkeypatch.setattr(enrich, "research", lambda *a, **k: None)
    assert enrich.seed(None, "A plaque", "HER FALDT STYRMAND EJLER HAUBIRK") == ""


def test_a_seed_is_the_passages_on_their_pages(monkeypatch):
    import json

    from pipeline import enrich

    asides = [
        {"text": "He decorated it.", "url": URL, "passage": "decorated the Alexandra"},
        {"text": "He carved it.", "url": URL, "passage": "carved the Alexandra"},
    ]
    monkeypatch.setattr(enrich, "research", lambda *a, **k: "notes")
    monkeypatch.setattr(enrich, "_request", lambda *a, **k: json.dumps(_found(asides=asides)))
    monkeypatch.setattr(enrich, "verified", lambda found: verified(found, fetch=_fetch))
    assert enrich.seed(None, "Alexandra", "a cinema") == f'From {URL}: "decorated the Alexandra"'


def test_a_source_page_gives_its_photos_not_its_logos():
    page = """<img src="/img/logo.svg" alt="Logo"><img src="/flags/da.png">
    <img src="data:image/gif;base64,R0l"><img src="/tiny.jpg" width="40">
    <figure><img src="/ph.gif" data-flickity-lazyload="/files/beatles.jpg" alt="">
    <figcaption>The Beatles, 4 June 1964</figcaption></figure>
    <img src="/files/08briannielsen.jpg">"""
    found = source_pictures("https://kbhallen.dk/history/#0", "K.B. Hallen", fetch=lambda u: page)
    assert [(p["url"], p["caption"]) for p in found] == [
        ("https://kbhallen.dk/files/beatles.jpg", "The Beatles, 4 June 1964"),
        ("https://kbhallen.dk/files/08briannielsen.jpg", "08briannielsen"),
    ]
    assert found[0]["license"] == "© K.B. Hallen" and found[0]["source"]
    assert source_pictures("https://youtube.com/watch?v=x", "Y", fetch=lambda u: page) == []
