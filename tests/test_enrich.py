"""Enrichment keeps only what a page we fetched says (pipeline/enrich.py)."""

from pipeline.enrich import verified

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
