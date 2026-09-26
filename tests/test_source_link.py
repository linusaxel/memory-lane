"""What the API says about a source, and how far into it.

The rules were only ever asserted against the rendered card (tests/test_card.py).
The API emitted its own copy of them, which had already drifted: it ignored
`source_url` entirely, and used truthiness where the card used `is not None`.
Both callers read `api.gate.source_link` now, so these assert the half that had
nothing.

An offset is seconds into a recording. When there is no recording there is no
offset, and the app must not be handed a zero it would render as "Watch at
0:00" against a document.
"""

from api.gate import row_to_memory, source_link


class Row:
    """Only attribute access is used, as in tests/test_card.py."""

    def __init__(self, **kw):
        defaults = dict(
            id=1,
            summary="They argued about pastrami for twenty minutes.",
            content_id=7,
            content_title="NYC Food Tour",
            content_url="https://youtube.com/watch?v=abc123",
            source_url=None,
            timestamp_start=12.0,
            place_id=3,
            place_name="Katz's Delicatessen",
            precision_meters=50,
            lat=40.7223,
            lng=-73.9874,
            tags=[],
            extraction_confidence="high",
            layer="historical",
            happened_at=None,
            user_id=None,
            author_name=None,
            source_name=None,
            source_channel_url=None,
            source_icon_url=None,
            coordinate_is_unique=False,
            media=[],
            contrast_score=None,
            contrast_note=None,
            attribution=None,
            anniversary=False,
        )
        self.__dict__.update({**defaults, **kw})


def test_a_youtube_video_keeps_its_offset():
    href, offset = source_link(Row(timestamp_start=847.5))
    assert href == "https://youtube.com/watch?v=abc123&t=847"
    assert offset == 847.5


def test_second_zero_is_an_offset_not_a_missing_value():
    """The truthiness bug the card fixed and the API never did."""
    href, offset = source_link(Row(timestamp_start=0.0))
    assert href.endswith("t=0")
    assert offset == 0.0


def test_a_non_video_source_has_no_offset_to_report():
    """An archival host is not known to honour ?t=, so there is no moment to
    name - and naming one anyway is what put "Watch at 0:00" on a document."""
    href, offset = source_link(
        Row(content_url="https://archive.example/doc/12", timestamp_start=99.0)
    )
    assert href == "https://archive.example/doc/12"
    assert offset is None


def test_an_archival_source_url_wins_and_carries_no_offset():
    """The behaviour api/card.py had and api/gate.py did not."""
    href, offset = source_link(Row(source_url="https://stadsarkiv.dk/item/9", timestamp_start=42.0))
    assert href == "https://stadsarkiv.dk/item/9"
    assert offset is None


def test_a_missing_offset_survives_to_the_response():
    """End to end through the model, because ContentRef.timestamp_start was
    required and that is what forced the fabricated zero in the first place."""
    memory = row_to_memory(Row(content_url="https://archive.example/doc/12", timestamp_start=None))
    assert memory.content is not None
    assert memory.content.timestamp_start is None
    assert memory.content.url == "https://archive.example/doc/12"


def test_a_video_offset_survives_to_the_response():
    memory = row_to_memory(Row(timestamp_start=847.5))
    assert memory.content.timestamp_start == 847.5
    assert memory.content.url == "https://youtube.com/watch?v=abc123&t=847"
