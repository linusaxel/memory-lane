"""The new text sources' parsing, offline: plaques, Wikipedia, filming, feeds, stones, PDFs, ADL."""

import argparse
import urllib.robotparser

import pytest

from crawler import adl, archive, filming, pdfs, plaques, rss, stolpersteine, webpages, wikipedia


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


def test_a_titled_article_keeps_only_its_copenhagen_windows(monkeypatch):
    body = "In Paris they played.\n\nIn Copenhagen they were billed as The Nobs."
    monkeypatch.setattr(wikipedia, "article_text", lambda lang, title: body)
    monkeypatch.setattr(wikipedia, "windows", lambda text: text.split("\n\n"))
    monkeypatch.setattr(wikipedia, "PAUSE_S", 0)
    got = list(wikipedia.Wikipedia().fetch("en titles:Led Zeppelin European Tour 1970", 10))
    assert [r["text"].count("Nobs") for r in got] == [1]
    assert "places this at" not in got[0]["text"]
    body = "\n\n".join(f"Copenhagen, part {n}." for n in range(5))
    monkeypatch.setattr(wikipedia, "article_text", lambda lang, title: body)
    got = list(wikipedia.Wikipedia().fetch("en titles:Freetown Christiania", 10))
    assert len(got) == wikipedia.TITLE_WINDOWS


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


def test_an_archive_item_reads_its_largest_ocr_file_whatever_its_name():
    files = [
        {"name": "x_djvu.txt", "size": "12"},
        {"name": "Bergsøe - Drenge_djvu.txt", "size": "355359"},
        {"name": "Bergsøe - Drenge.pdf", "size": "5263563"},
    ]
    assert archive.ocr_file("x", files) == "Bergsøe - Drenge_djvu.txt"
    assert archive.ocr_file("x", []) == "x_djvu.txt"


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


def test_stones_at_one_door_are_one_story_in_plain_text():
    row = (
        "\n|-\n| [[Datei:Stein.jpg|120px]]\n"
        '|style="text-align:center;"| <small>HIER WOHNTE</small><br />{name}\n'
        "| Nansensgade 19{district}<!--{{{{Coordinate|NS=}}}}-->\n"
        "| {{{{PersonZelle|{name}|Levy|fett=1}}}} floh nach [[Schweden|Südschweden]].<ref>x</ref>"
    )
    wikitext = "{|\n! Stein" + row.format(name="ABEL", district="<br><small>Kopenhagen</small>")
    wikitext += row.format(name="RUTH", district="") + "\n|}"
    assert stolpersteine.stones(wikitext) == {
        "Nansensgade 19 Kopenhagen": [
            ("HIER WOHNTE\nABEL", "ABEL Levy floh nach Südschweden."),
            ("HIER WOHNTE\nRUTH", "RUTH Levy floh nach Südschweden."),
        ]
    }


def test_pdf_links_are_absolute_once_newest_first_and_from_a_year():
    page = (
        '<a href="/pdf/2019/01-2019.pdf">a</a><a href="/pdf/2023/02-2023.PDF">b</a>'
        '<a href="https://x.dk/pdf/2019/01-2019.pdf">dup</a><a href="/om/">c</a>'
    )
    assert pdfs.pdf_links(page, "https://x.dk/arkiv/") == [
        "https://x.dk/pdf/2023/02-2023.PDF",
        "https://x.dk/pdf/2019/01-2019.pdf",
    ]
    assert pdfs.pdf_links(page, "https://x.dk/arkiv/", since=2020) == [
        "https://x.dk/pdf/2023/02-2023.PDF"
    ]


def test_pdf_links_can_pick_issue_pages_to_hop_through():
    page = '<a href="/2019/02/nabo-2/">a</a><a href="/om/">b</a><a href="/2010/04/464/">c</a>'
    assert pdfs.pdf_links(page, "https://x.dk/nabo/", since=2015, pattern=r"/20\d\d/\d\d/") == [
        "https://x.dk/2019/02/nabo-2/"
    ]


def test_an_old_homepage_without_paragraphs_reads_as_all_its_text_but_its_style():
    old = "<style>body { color: red }</style><font>Vi boede i Saxogade.<br>Skolen lå i Matthæusgade.</font><p>Menu</p>"
    assert webpages.page_text(old) == "Vi boede i Saxogade.\n\nSkolen lå i Matthæusgade.\n\nMenu"
    article = "<nav>Forside</nav><p>Le Carrousel lå på Axeltorv ved Vesterport Station.</p>"
    assert webpages.page_text(article) == "Le Carrousel lå på Axeltorv ved Vesterport Station."


def test_an_old_homepage_keeps_its_letters_in_any_of_its_encodings():
    for encoding in ("utf-8", "cp1252", "utf-16"):
        assert webpages.decoded("Fjords Allé, Nørrebro".encode(encoding)) == "Fjords Allé, Nørrebro"


def test_a_pdf_locator_is_that_one_pdf_with_no_index(monkeypatch):
    fetched = []
    monkeypatch.setattr(pdfs, "robots", lambda *a: urllib.robotparser.RobotFileParser())
    monkeypatch.setattr(pdfs, "download", lambda u, *a: fetched.append(u) or b"%PDF")
    monkeypatch.setattr(pdfs, "pdf_text", lambda data: "Lygterne på Blågårds Plads var gaslygter.")
    records = list(pdfs.Pdfs().fetch("https://x.dk/PDF%20og%20DOC/drengen.pdf", 5))
    assert fetched == ["https://x.dk/PDF%20og%20DOC/drengen.pdf"]
    assert records[0]["title"] == "drengen.pdf"
    assert records[0]["text"] == "Lygterne på Blågårds Plads var gaslygter."


def test_sitemap_urls_are_unescaped_once_and_filtered():
    xml = "<loc>https://x.dk/a?b=1&amp;c=2</loc><loc>https://x.dk/da/a</loc><loc>https://x.dk/a?b=1&amp;c=2</loc>"
    assert webpages.sitemap_urls(xml) == ["https://x.dk/a?b=1&c=2", "https://x.dk/da/a"]
    assert webpages.sitemap_urls(xml, r"x\.dk/(?!da/)") == ["https://x.dk/a?b=1&c=2"]


def test_an_adl_page_reads_as_its_paragraphs_without_links_page_numbers_or_notes():
    page = """<title>1. Del : 1812-42 - Det Kgl. Biblioteks tekstportal</title>
    <h2 class="head-in-work">FORORD</h2>
    <p class="paragraph"><span><a class="quote"><span class="symbol quote">✂ </span></a>
    </span>Nielsen spillede <em>Correggio</em>.<a class="note">*</a><span class="note_content"
    >* Denne Replik lyder anderledes.</span><span class="pageBreak"><a><small>24</small></a></span>
    Han kyssede mig.<br/></p>
    <p class="paragraph">Paa Kongens Nytorv.</p>"""
    title, text = adl.book(page)
    assert title == "1. Del : 1812-42"
    assert text == "Nielsen spillede Correggio. Han kyssede mig.\n\nPaa Kongens Nytorv."


def test_adl_refuses_a_volume_that_is_not_free():
    with pytest.raises(ValueError):
        next(adl.Adl().fetch("heibfr01val", 1))


def test_a_licence_longer_than_its_column_is_refused():
    from pipeline.sources import licence

    assert licence("CC BY-SA 4.0") == "CC BY-SA 4.0"
    with pytest.raises(argparse.ArgumentTypeError):
        licence("x" * 41)


def test_a_download_escapes_an_old_homepages_spaces_and_letters(monkeypatch):
    from crawler import gutenberg

    asked = []

    class _Body:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"ok"

    monkeypatch.setattr(
        gutenberg.urllib.request, "urlopen", lambda r, timeout: asked.append(r.full_url) or _Body()
    )
    assert gutenberg.download("http://x.dk/Photos/land photos/ø.jpg?a=1%20b") == b"ok"
    assert asked == ["http://x.dk/Photos/land%20photos/%C3%B8.jpg?a=1%20b"]
