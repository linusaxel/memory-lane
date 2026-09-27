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
        "unnamed someone": 0,
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


def test_someone_is_caught():
    """Verbatim from the Copenhagen video, where the rider is named in the transcript."""
    real = "Working as a ski guide, someone met 'maleren' and his friends in Sölden."
    assert counts(real)["unnamed someone"] == 1


def test_length_is_counted_in_words_not_characters():
    """A 71-word summary of a conversation, not a 400-character one - the limit
    is about how much there is to read standing up, not about storage."""
    assert counts(" ".join(["word"] * 71))["over 70 words"] == 1
    assert counts(" ".join(["word"] * 70))["over 70 words"] == 0


def test_a_clean_corpus_reports_all_zeroes():
    assert set(counts(GOOD, GOOD).values()) == {0}


def test_a_memory_nobody_could_stand_on_is_dropped():
    """The spot test, answered: an empty why_here or a city-wide pin goes."""
    from pipeline.extract import filter_low_confidence

    ok = {"confidence": "medium", "location_precision": "street", "why_here": "it sank"}
    kept = filter_low_confidence(
        [
            ok,
            {**ok, "why_here": " "},
            {**ok, "location_precision": "city"},
            {**ok, "confidence": "low"},
        ]
    )
    assert kept == [ok]


# -- the prompt itself, since the corpus cannot be re-extracted for free ------


def test_the_prompt_carries_the_corpus_failures_as_examples():
    """Examples outperform rules, and these are taken from real output rather
    than invented - the Joe List one is the case that proves "the speaker" had
    a name available the whole time."""
    from pipeline.extract import SYSTEM_PROMPT

    assert "<examples>" in SYSTEM_PROMPT
    assert "Joe List" in SYSTEM_PROMPT, "the worked case for the anonymous label"
    assert "Falls View Casino" in SYSTEM_PROMPT, "the worked case for a tour date"


def test_the_prompt_permits_returning_nothing():
    """Explicit permission to decline reduces invention, and an invented memory
    is indistinguishable from a real one once somebody has walked to it."""
    from pipeline.extract import SYSTEM_PROMPT

    assert "<uncertainty>" in SYSTEM_PROMPT
    assert "An empty list is a correct and common answer" in SYSTEM_PROMPT


def test_the_source_context_names_the_show_and_the_episode():
    from pipeline.extract import source_context

    context = source_context("Tuesdays with Stories", "Ottomans Piglet #666 w/ Mark Normand")
    assert "Tuesdays with Stories" in context
    assert "Mark Normand" in context, "the episode title is usually where the names are"
    assert 'never "the speaker"' in context


def test_no_source_means_no_context_rather_than_an_empty_claim():
    """Better to say nothing than to tell the model the show is called None."""
    from pipeline.extract import source_context

    assert source_context(None, "an episode") == ""
