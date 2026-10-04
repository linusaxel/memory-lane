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
        "over 180 words": 0,
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
    """A 181-word summary of a conversation, not a 1000-character one - the
    limit is about how much there is to read standing up, not about storage."""
    assert counts(" ".join(["word"] * 181))["over 180 words"] == 1
    assert counts(" ".join(["word"] * 180))["over 180 words"] == 0


def test_a_clean_corpus_reports_all_zeroes():
    assert set(counts(GOOD, GOOD).values()) == {0}


def test_a_memory_nobody_could_stand_on_is_dropped():
    """The spot test, answered: a fail or a city-wide pin goes."""
    from pipeline.extract import filter_low_confidence

    ok = {"confidence": "medium", "location_precision": "street", "spot_test": "pass"}
    kept = filter_low_confidence(
        [
            ok,
            {**ok, "spot_test": "fail"},
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


def test_a_place_the_chunk_never_names_is_dropped():
    """The quote gate. Captions split and punctuate a name differently from how
    the model copies it, so the match ignores both - but not the words."""
    from pipeline.extract import grounded

    chunk = "[01:33] Og øh ringkafen her,\n[01:36] den er fra 30'erne."
    said = {"place_words": "Ringkafen her, den er fra 30'erne"}
    invented = {"place_words": "Levinho après-ski bar"}
    assert grounded([said, invented, {"place_words": ""}], chunk) == [said]


def test_a_quote_the_chunk_never_says_is_dropped_and_the_memory_kept():
    from pipeline.extract import grounded

    chunk = "[01:33] Og øh ringkafen her,\n[01:36] den er fra 30'erne. Den sank bare!"
    said = {"place_words": "ringkafen her", "quote": "Den sank, bare!", "quote_by": "Mads"}
    invented = {"place_words": "ringkafen her", "quote": "Den druknede", "quote_by": "Mads"}
    kept = grounded([said, invented], chunk)

    assert [m["quote"] for m in kept] == ["Den sank, bare!", None]
    assert kept[1]["quote_by"] is None


def test_the_brief_reaches_every_chunk():
    from pipeline.extract import source_context

    brief = "Trip Nørrebro: a yearly crawl through Nørrebro's bars."
    context = source_context("Københavnerliv", None, brief)
    assert "<video_brief>" in context and brief in context
    assert "not a source of memories" in context
    assert source_context("Københavnerliv", None) == source_context("Københavnerliv", None, "")


def _verdict(**yes):
    base = dict.fromkeys(
        (
            "only_here",
            "breach",
            "consequence",
            "visible_now",
            "so_what",
            "stands_alone",
            "glad_to_know",
        ),
        False,
    )
    return {**base, **yes}


def test_the_tellability_bar():
    """The model answers yes/no; code holds the bar. The place must be the point,
    a stranger must follow it and be glad to know it, and two of the other four
    must hold - an origin story like Nørrebroparken has consequence and a point,
    but breaks no script."""
    from pipeline.extract import tellable

    must = {"only_here": True, "stands_alone": True, "glad_to_know": True}
    assert tellable(_verdict(**must, consequence=True, so_what=True))
    # 7220: true, on its spot, and a bare name and date nobody is glad to know.
    assert not tellable(_verdict(only_here=True, stands_alone=True, breach=True, visible_now=True))
    assert not tellable(_verdict(**must, breach=True))
    assert not tellable(
        _verdict(stands_alone=True, breach=True, consequence=True, visible_now=True, so_what=True)
    )
    assert not tellable(
        _verdict(only_here=True, breach=True, consequence=True, visible_now=True, so_what=True)
    )


def test_an_unreadable_judge_keeps_everything():
    """It only filters: a broken judge must not empty a video."""
    from pipeline.extract import worth_telling

    class _Session:
        def execute(self, *a, **k):
            return type("R", (), {"scalar": lambda self: "not json"})()

    memories = [{"venue": "Ringkaféen", "summary": "It sank."}]
    assert worth_telling(_Session(), None, 1, memories) == memories


def test_the_judge_drops_what_fails_and_keeps_what_it_skipped():
    import json

    from pipeline.extract import worth_telling

    reply = json.dumps(
        {
            "verdicts": [
                {"index": 0, "note": "sank", **_verdict(**dict.fromkeys(_verdict(), True))},
                {"index": 1, "note": "routine", **_verdict(stands_alone=True)},
            ]
        }
    )

    class _Session:
        def execute(self, *a, **k):
            return type("R", (), {"scalar": lambda self: reply})()

    memories = [{"venue": "Ringkaféen"}, {"venue": "Maskot"}, {"venue": "not judged"}]
    assert [m["venue"] for m in worth_telling(_Session(), None, 1, memories)] == [
        "Ringkaféen",
        "not judged",
    ]


def _replying(reply):
    class _Session:
        def execute(self, *a, **k):
            return type("R", (), {"scalar": lambda self: reply})()

    return _Session()


def test_one_venue_named_three_ways_in_a_video_becomes_one_name():
    """Content 535: Jørgen Leth's barber came out as three places."""
    import json

    from pipeline.extract import one_name_per_venue

    names = [
        "Barbershop on Vognmagergade",
        "Herrefrisør på Vognmagergade",
        "Jørgen Let's barbershop, Vognmagergade",
        "Under Hylden",
    ]
    memories = [{"venue": v, "locality": "Copenhagen", "summary": "..."} for v in names]
    memories.append({"venue": "herrefrisør på vognmagergade", "locality": "copenhagen"})
    reply = json.dumps({"same": [{"index": 1, "as": 0}, {"index": 2, "as": 0}]})
    out = one_name_per_venue(_replying(reply), None, 1, memories)
    assert [m["venue"] for m in out] == [names[0]] * 3 + ["Under Hylden", names[0]]


def test_an_unreadable_venue_reply_changes_nothing():
    from pipeline.extract import one_name_per_venue

    memories = [{"venue": "Maskot"}, {"venue": "Mexibar"}]
    assert one_name_per_venue(_replying("not json"), None, 1, memories) == memories
