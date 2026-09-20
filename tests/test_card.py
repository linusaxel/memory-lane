"""The card must always carry its credit, and must never carry raw HTML.

Rendering server-side is the whole point: a client that builds the card from
JSON can drop the attribution, and this corpus is someone else's archive. So
the credit line is asserted to be un-droppable, including when every field it
prefers is NULL.

The escaping tests are not theatre. summary and place name are model output
stored verbatim, and they are interpolated into a document - that is an
injection boundary whatever wrote the text.
"""

import datetime
import re

import pytest

from api.card import credit_line, format_happened, render_card


class Row:
    """Stand-in for the SQLAlchemy row; only attribute access is used."""

    def __init__(self, **kw):
        defaults = dict(
            id=1,
            summary="They argued about pastrami for twenty minutes.",
            layer="historical",
            happened_at=None,
            happened_precision=None,
            attribution=None,
            source_url=None,
            contrast_note=None,
            timestamp_start=12.0,
            place_name="Katz's Delicatessen",
            precision_meters=50,
            source_name=None,
            user_id=None,
            author_name=None,
            photo_path=None,
            content_title="Tuesdays with Stories #500",
            content_url="https://www.youtube.com/watch?v=abc",
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


# -- the credit is the point --------------------------------------------------


def test_attribution_wins_when_present():
    assert credit_line(Row(attribution="Københavns Stadsarkiv")) == "Københavns Stadsarkiv"


def test_falls_back_through_title_then_url():
    assert credit_line(Row(content_title="A video")) == "A video"
    assert credit_line(Row(content_title=None)) == "https://www.youtube.com/watch?v=abc"


def test_credit_is_never_empty():
    """Every source field null is the case that must still not ship uncredited."""
    bare = Row(attribution=None, content_title=None, content_url=None)
    assert credit_line(bare) == "Source unknown"
    assert "Source unknown" in render_card(bare)


def test_credit_survives_into_the_markup():
    html = render_card(Row(attribution="Stadsarkiv", source_url="https://example.org/x"))
    assert "Stadsarkiv" in html
    assert 'href="https://example.org/x"' in html


# -- injection ----------------------------------------------------------------


@pytest.mark.parametrize(
    "field", ["summary", "place_name", "attribution", "contrast_note", "content_title"]
)
def test_model_text_cannot_inject_markup(field):
    html = render_card(Row(**{field: "<script>alert(1)</script>"}))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_a_hostile_source_url_cannot_break_out_of_the_attribute():
    html = render_card(Row(source_url='https://x/" onmouseover="steal()'))
    assert 'onmouseover="steal()"' not in html
    assert "&quot;" in html


# -- dates say only what the precision supports -------------------------------


@pytest.mark.parametrize(
    "precision,expected",
    [
        ("decade", "1890s"),
        ("year", "1893"),
        ("month", "March 1893"),
        ("day", "4 March 1893"),
        (None, "1893"),
    ],
)
def test_precision_bounds_what_the_date_claims(precision, expected):
    assert format_happened(datetime.date(1893, 3, 4), precision) == expected


def test_no_date_renders_no_date_line():
    assert format_happened(None, "year") is None
    assert 'class="when"' not in render_card(Row())


# -- the shell ----------------------------------------------------------------


def test_card_is_self_contained_and_scheme_aware():
    """No asset pipeline behind this: it renders inside an iframe, a WebView and
    a link preview. One stylesheet is allowed and only for the two faces, which
    is why the CSS keeps stacks that stand on their own - a preview bot fetches
    no fonts at all. Everything else still has to be inline."""
    html = render_card(Row())
    assert "prefers-color-scheme:dark" in html
    assert "<script" not in html, "nothing here should need scripting"
    links = re.findall(r"<link[^>]*>", html)
    assert len(links) == 1, f"one stylesheet, got {len(links)}: {links}"
    assert 'href="https://fonts.googleapis.com/' in links[0], links[0]
    assert 'name="viewport"' in html


# -- linking the source ------------------------------------------------------


def test_timestamp_zero_is_a_real_offset_not_a_missing_value():
    """0.0 is the start of the video. A truthiness check dropped it."""
    html = render_card(Row(timestamp_start=0.0))
    assert 't=0"' in html


def test_only_youtube_gets_a_time_offset():
    """?t= on an arbitrary host is a guess about someone else's URL scheme."""
    html = render_card(Row(content_url="https://archive.example/doc/12", timestamp_start=99.0))
    assert "t=99" not in html
    assert "https://archive.example/doc/12" in html


def test_an_archival_source_url_is_linked_untouched():
    html = render_card(Row(source_url="https://stadsarkiv.dk/item/9", timestamp_start=42.0))
    assert 'href="https://stadsarkiv.dk/item/9"' in html


def test_the_publisher_outranks_the_episode_title():
    """A card that leaves the screen is read by people who know neither, and
    "Tuesdays with Stories" says who is talking where an episode title does not."""
    row = Row(source_name="Tuesdays with Stories", content_title="Ep 512 - A Sauna Too Far")
    assert credit_line(row) == "Tuesdays with Stories — Ep 512 - A Sauna Too Far"


def test_the_publisher_alone_is_enough():
    assert credit_line(Row(source_name="Tuesdays with Stories", content_title=None)) == (
        "Tuesdays with Stories"
    )


def test_an_archive_attribution_still_outranks_the_publisher():
    row = Row(attribution="Museum of Copenhagen", source_name="Tuesdays with Stories")
    assert credit_line(row) == "Museum of Copenhagen"


def test_a_row_with_no_publisher_falls_through_as_before():
    assert credit_line(Row(source_name=None, content_title="Ep 3")) == "Ep 3"


# -- memories people filed themselves -----------------------------------------


def test_a_submission_is_credited_to_whoever_filed_it():
    """No content row at all, so the fallback chain runs off the end of
    everything it used to rely on. The signature is the credit."""
    row = Row(user_id="9f0c", author_name="Lise", content_title=None, content_url=None)
    assert credit_line(row) == "Lise"
    assert "Lise" in render_card(row)


def test_an_unnamed_submitter_is_anonymous_not_unknown():
    """ "Source unknown" is what we say when nobody knows. Somebody knows here -
    they just did not put their name to it."""
    row = Row(user_id="9f0c", author_name=None, content_title=None, content_url=None)
    assert credit_line(row) == "Anonymous"


def test_an_archive_attribution_still_outranks_the_person():
    row = Row(attribution="Museum of Copenhagen", user_id="9f0c", author_name="Lise")
    assert credit_line(row) == "Museum of Copenhagen"


def test_a_photo_is_part_of_the_card():
    """A submitted memory usually is the photograph, and the card is the thing
    that gets pasted into a chat."""
    html = render_card(Row(user_id="9f0c", photo_path="abc123.jpg"))
    assert 'src="/media/abc123.jpg"' in html
    assert 'class="photo"' in html


def test_no_photo_renders_no_image():
    assert "<img" not in render_card(Row())
