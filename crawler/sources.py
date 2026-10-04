"""Text sources: a thing that fetches records, and the list of them.

A new source is one file with a class that fits `Source`, plus one line in
SOURCES. Sources only fetch; pipeline.ingest.ingest_records only writes.
YouTube is not one of these: it lists videos now and fetches transcripts later.
See docs/10-decisions.md#sources-are-a-protocol-and-a-registry.
"""

from collections.abc import Iterable
from typing import Protocol, TypedDict


class Record(TypedDict, total=False):
    source_url: str  # required: becomes content.url, so re-ingesting is a no-op
    text: str  # required
    title: str
    language: str
    lat: float  # the source's own point, if it has one; only --bbox reads it
    lng: float


class Source(Protocol):
    name: str  # the --source key
    source_name: str  # the credit on a card
    source_type: str  # content.source_type

    def fetch(self, query: str, limit: int) -> Iterable[Record]: ...


from crawler.filming import Filming  # noqa: E402  (they need Record defined first)
from crawler.gutenberg import Gutenberg  # noqa: E402
from crawler.historisk_atlas import HistoriskAtlas  # noqa: E402
from crawler.kb_aviser import KbAviser  # noqa: E402
from crawler.plaques import Plaques  # noqa: E402
from crawler.rss import Podcast, Press  # noqa: E402
from crawler.runeberg import Runeberg  # noqa: E402
from crawler.wikipedia import Wikipedia  # noqa: E402

SOURCES: dict[str, Source] = {
    s.name: s
    for s in (
        KbAviser(),
        HistoriskAtlas(),
        Gutenberg(),
        Runeberg(),
        Plaques(),
        Wikipedia(),
        Filming(),
        Press(),
        Podcast(),
    )
}
