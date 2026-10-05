"""The new text sources' parsing, offline: plaques, Wikipedia, filming, feeds."""

from crawler import archive, filming, plaques, rss, wikipedia


def test_a_plaque_becomes_its_inscription_its_subject_and_its_point():
    element = {
        "type": "node",
        "id": 7,
        "lat": 55.68,
        "lon": 12.58,
        "tags": {
            "name": "Mindeplade for Politiken",
            "inscription": "I dette hus grundlagde / Viggo Hørup / Dagbladet POLITIKEN",
            "addr:street": "Østergade",
            "addr:housenumber": "11",
        },
    }
    r = plaques.record(element, ("https://da.wikipedia.org/wiki/Politiken", "Politiken er…"))
    assert r["source_url"] == "https://www.openstreetmap.org/node/7"
    assert "A plaque at Østergade 11: Mindeplade for Politiken" in r["text"]
    assert "grundlagde Viggo Hørup Dagbladet" in r["text"]
    assert "Politiken er…" in r["text"] and (r["lat"], r["lng"]) == (55.68, 12.58)
    assert plaques.record({"type": "way", "id": 1, "tags": {"name": "x"}}, None) is None


def test_the_plaque_query_asks_for_the_box():
    q = plaques.query_for("55.6,12.45,55.74,12.66")
    assert '"memorial"="plaque"' in q and "(55.6,12.45,55.74,12.66)" in q


def test_an_article_loses_its_reference_sections(monkeypatch):
    extract = "Intro.\n== Historie ==\nA fire in 1795.\n== Kilder ==\nA book.\n== Galleri ==\nx"
    monkeypatch.setattr(
        wikipedia, "_api", lambda lang, p: {"query": {"pages": [{"extract": extract}]}}
    )
    text = wikipedia.article_text("da", "Gammeltorv")
    assert "A fire in 1795." in text and "Historie" in text
    assert "A book." not in text and "Galleri" not in text


def test_the_wikipedia_query_is_language_point_and_radius_capped():
    assert wikipedia.parse_query("da 55.67,12.56 50000") == ("da", 55.67, 12.56, 10_000)


def test_a_filming_row_keeps_the_shoot_not_the_plot():
    row = {
        "film": {"value": "http://www.wikidata.org/entity/Q1"},
        "filmLabel": {"value": "Matador"},
        "loc": {"value": "http://www.wikidata.org/entity/Q2"},
        "locLabel": {"value": "Holmens Kirke"},
        "lat": {"value": "55.676"},
        "lng": {"value": "12.582"},
        "daw": {"value": "https://da.wikipedia.org/wiki/Matador"},
    }
    body = "Matador er en tv-serie.\nPlottet handler om Korsbæk.\nBrylluppet blev optaget i Holmens Kirke."
    r = filming.record(row, body)
    assert "Matador was filmed at Holmens Kirke" in r["text"]
    assert "Brylluppet blev optaget" in r["text"] and "Korsbæk" not in r["text"]
    assert r["source_url"] == "http://www.wikidata.org/entity/Q1#Q2"


FEED = b"""<?xml version="1.0"?>
<rss xmlns:podcast="https://podcastindex.org/namespace/1.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><language>da-dk</language>
<item><title>Ep 1</title><link>https://ex.dk/1</link>
  <podcast:transcript url="https://ex.dk/1.html" type="text/html"/>
  <podcast:transcript url="https://ex.dk/1.vtt" type="text/vtt"/></item>
<item><title>Ep 2</title><link>https://ex.dk/2</link>
  <content:encoded><![CDATA[<div>Menu</div><p>The bar on Istedgade burned in 1972.</p>]]></content:encoded></item>
</channel></rss>"""


def test_a_feed_item_prefers_the_plainest_transcript_and_the_article_body():
    first, second = rss.items(FEED)
    assert rss._transcript(first).get("url") == "https://ex.dk/1.vtt"
    assert rss._transcript(second) is None
    assert rss.paragraphs(rss._text(second, "content:encoded")) == (
        "The bar on Istedgade burned in 1972."
    )


def test_a_transcript_loses_its_cues_and_timings():
    vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n<v Anna>Det var her\n\n2\n00:00:04 --> 00:00:06\nbaren lå."
    assert rss.transcript_text(vtt, "text/vtt") == "Det var her baren lå."
    assert rss.transcript_text('{"segments": [{"body": "Hej"}]}', "application/json") == "Hej"


def test_an_ocr_text_mends_its_line_break_hyphens():
    raw = "mistænkte  ham  for  at  være  et  af  Struensees  Kre-\naturer, og  Gammel-  \ntorv\nLand-\n\nsknægte"
    assert (
        archive.mend(raw)
        == "mistænkte  ham  for  at  være  et  af  Struensees  Kreaturer, og  Gammeltorv\nLand-\n\nsknægte"
    )


def test_categories_merge_once_longest_first_and_skip_the_ungeotagged(monkeypatch):
    def page(title, length, geo=True):
        return {"title": title, "length": length} | (
            {"coordinates": [{"lat": 55.68, "lon": 12.58}]} if geo else {}
        )

    replies = {
        "Category:Crime": [page("Shooting", 9000), page("Stub", 100)],
        "Category:Riots": [
            page("Ungdomshuset", 30000),
            page("Shooting", 9000),
            page("Nowhere", 50000, geo=False),
        ],
    }
    monkeypatch.setattr(
        wikipedia, "_api", lambda lang, p: {"query": {"pages": replies[p["gcmtitle"]]}}
    )
    found = wikipedia.categories("en", "Crime| Riots")
    assert [f["title"] for f in found] == ["Ungdomshuset", "Shooting", "Stub"]
    assert (found[0]["lat"], found[0]["lon"]) == (55.68, 12.58)
