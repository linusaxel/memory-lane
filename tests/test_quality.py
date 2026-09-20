"""The summary checks catch what they claim to.

The report in pipeline/quality.py is the only measurement standing between "the
output feels bad" and a prompt change, so its regexes get held to the actual
sentences they were written from - two real ones from the corpus, and the shape
the new prompt asks for.
"""

from pipeline.quality import report

# Verbatim from the live corpus, which is why they read like that.
ANONYMOUS_REAL = "The speaker drove the massive rental van through Florida swampland to Cape Canal."
PROMO_REAL = (
    "The speaker is performing at Falls View Casino in Niagara on the 14th, making a joke "
    "about Marilyn Monroe."
)
META_REAL = "He describes it as basically a fake town created just to house a casino."

# What the prompt now asks for: named, past tense, about the event.
GOOD = (
    "Mark did three sold-out nights at this 1909 theatre, joking that the marquee had "
    "survived prohibition, the depression, and now his act."
)


def counts(*summaries):
    return {name: n for name, n, _ in report(list(summaries))}


def test_the_good_shape_trips_nothing():
    assert counts(GOOD) == {
        "anonymous subject": 0,
        "talks about talking": 0,
        "not past tense": 0,
        "over 70 words": 0,
    }


def test_the_label_instead_of_a_name_is_caught():
    assert counts(ANONYMOUS_REAL)["anonymous subject"] == 1


def test_an_upcoming_show_is_caught():
    """The 6% that are not memories at all - a tour date names a real venue and
    reads like an event, and is worthless to somebody standing there."""
    assert counts(PROMO_REAL)["not past tense"] == 1


def test_reporting_the_recording_is_caught():
    assert counts(META_REAL)["talks about talking"] == 1


def test_length_is_counted_in_words_not_characters():
    """A 71-word summary of a conversation, not a 400-character one - the limit
    is about how much there is to read standing up, not about storage."""
    assert counts(" ".join(["word"] * 71))["over 70 words"] == 1
    assert counts(" ".join(["word"] * 70))["over 70 words"] == 0


def test_a_clean_corpus_reports_all_zeroes():
    assert set(counts(GOOD, GOOD).values()) == {0}
