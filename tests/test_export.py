"""What a customer is allowed to receive.

Every assertion here is a term of the deal rather than a formatting preference.
The corpus is quoted material: the product may point at it and must not resell
it, so what leaves this module is snippets, credit and links. A test that only
checked the JSON shape would pass while handing over the whole thing.
"""

import json

import pytest
from sqlalchemy import text

from pipeline import export as ex

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655

LONG_SUMMARY = (
    "They played the basement room until four in the morning and nobody left. "
    "The piano was a semitone flat and the trumpet player kept apologising for "
    "it between numbers, which somehow made the whole night funnier than it "
    "had any right to be."
)


def _place(session, name, lat=LAT, lng=LNG):
    return session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :q, ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
        ),
        {"n": name, "q": f"{name} query", "lat": lat, "lng": lng},
    ).scalar()


def _content(session, url, **kw):
    cols = {
        "url": url,
        "platform": "youtube",
        "platform_id": url[-11:],
        "source_name": "Tuesdays with Stories",
        **kw,
    }
    names = ", ".join(cols)
    binds = ", ".join(f":{k}" for k in cols)
    return session.execute(
        text(f"INSERT INTO content ({names}) VALUES ({binds}) RETURNING id"), cols
    ).scalar()


def _memory(session, place_id, content_id=None, summary=LONG_SUMMARY, **kw):
    cols = {
        "place_id": place_id,
        "content_id": content_id,
        "summary": summary,
        "extraction_confidence": "high",
        **kw,
    }
    names = ", ".join(cols)
    binds = ", ".join(f":{k}" for k in cols)
    return session.execute(
        text(f"INSERT INTO memories ({names}) VALUES ({binds}) RETURNING id"), cols
    ).scalar()


@pytest.fixture
def seeded(db_session, monkeypatch):
    """One exportable memory, wired to the ephemeral database."""
    monkeypatch.setattr(ex, "get_session", _sessions(db_session))
    place = _place(db_session, "Jazzhus Montmartre")
    content = _content(db_session, "https://youtube.com/watch?v=aaaaaaaaaaa")
    _memory(db_session, place, content, timestamp_start=724.0)
    db_session.commit()
    return db_session


def _sessions(db_session):
    from contextlib import contextmanager

    @contextmanager
    def _session():
        yield db_session

    return _session


# -- the terms ----------------------------------------------------------------


def test_a_snippet_is_not_the_summary(seeded):
    only = ex.export()["memories"][0]
    assert only["snippet"] != LONG_SUMMARY
    assert len(only["snippet"]) <= ex.SNIPPET_CHARS + 1
    assert "apologising" not in only["snippet"], "the whole story must not come along"


def test_a_snippet_stops_at_a_sentence_when_there_is_one():
    assert ex.snippet("A short night. And then a longer one that goes on.") == "A short night."


def test_a_cut_snippet_says_it_was_cut():
    cut = ex.snippet("word " * 200)
    assert cut.endswith("…")
    assert not cut.endswith(" …"), "cut at a word, not mid-token with a dangling space"


def test_every_row_deep_links_to_the_second_it_came_from(seeded):
    only = ex.export()["memories"][0]
    assert only["source_url"] == "https://youtube.com/watch?v=aaaaaaaaaaa&t=724"
    assert only["attribution"] == "Tuesdays with Stories"


def test_a_row_that_cannot_say_where_it_came_from_is_not_exported(db_session, monkeypatch):
    """Not exported bare, and not exported with a blank credit. Attribution is
    the term of the deal, so a row without one is not ours to hand over."""
    monkeypatch.setattr(ex, "get_session", _sessions(db_session))
    place = _place(db_session, "Nowhere")
    _memory(db_session, place)  # no content row at all
    db_session.commit()

    assert ex.export()["memories"] == []


def test_a_memory_somebody_filed_is_never_in_it(db_session, monkeypatch):
    """A submission is that person's, not the buyer's. There is no consent in
    the submit flow that says otherwise, so the layer is the whole filter."""
    monkeypatch.setattr(ex, "get_session", _sessions(db_session))
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    place = _place(db_session, "The bench by the harbour")
    _memory(
        db_session, place, summary="We sat here until it got light.", layer="stranger", user_id=user
    )
    db_session.commit()

    assert ex.export()["memories"] == []


def test_a_hidden_memory_stays_hidden_here_too(seeded):
    seeded.execute(text("UPDATE memories SET hidden = TRUE"))
    seeded.commit()
    assert ex.export()["memories"] == []


def test_a_radius_bounds_what_a_customer_paid_for(seeded):
    far = _place(seeded, "Aarhus", LAT + 1.5, LNG)
    content = _content(seeded, "https://youtube.com/watch?v=bbbbbbbbbbb")
    _memory(seeded, far, content, timestamp_start=0.0)
    seeded.commit()

    assert ex.export()["count"] == 2
    inside = ex.export(lat=LAT, lng=LNG, radius_km=2)
    assert [m["place"]["name"] for m in inside["memories"]] == ["Jazzhus Montmartre"]


def test_the_terms_travel_with_the_file(seeded):
    payload = ex.export()
    assert "attribution" in payload["terms"]
    assert payload["generated_at"].endswith("+00:00")


def test_a_card_link_is_omitted_rather_than_pointed_at_localhost(seeded, monkeypatch):
    monkeypatch.setattr(ex, "PUBLIC_BASE_URL", "")
    assert ex.export()["memories"][0]["card_url"] is None

    monkeypatch.setattr(ex, "PUBLIC_BASE_URL", "https://memorylane.example")
    url = ex.export()["memories"][0]["card_url"]
    assert url.startswith("https://memorylane.example/v1/memories/")
    assert url.endswith("/card")


# -- the CLI ------------------------------------------------------------------


def test_the_cli_writes_json_a_customer_can_open(seeded, tmp_path, capsys):
    out = tmp_path / "corpus.json"
    assert ex.main(["--all", "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["count"] == 1
    assert payload["memories"][0]["place"]["name"] == "Jazzhus Montmartre"


def test_the_cli_refuses_half_a_radius(seeded):
    """--lat with no --radius-km is an export of everything wearing a filter."""
    with pytest.raises(SystemExit):
        ex.main(["--lat", str(LAT), "--lng", str(LNG)])
