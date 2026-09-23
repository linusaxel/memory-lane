"""Semantic place dedup: what the name rules do, and the case that defeats them.

Ground truth is live data:

    [108] Gotham Comedy Club New York City           6 memories  40.75890, -73.98510
    [211] Gotham Comedy Club Chelsea New York City   1 memory    40.74310, -73.99670

One venue, two pins, 1.8km apart - so coordinates cannot be the deciding signal.

Most of these pass `common` in explicitly rather than deriving it from a corpus.
The matching rule and the frequency estimator are separate things and fail for
separate reasons; deriving `common` from a seven-item fixture tests neither,
because the threshold lands somewhere real corpora never put it.
"""

from pipeline.dedup import city_level, common_tokens, distinctive, propose, same_place, tokens

# What the estimator actually produces for these rows against the live 194-place
# corpus: city and state words, nothing that names a venue.
US_PLACES = frozenset({"new", "york", "city", "ontario", "canada", "ottawa"})


def test_venue_words_and_glue_are_not_part_of_a_name():
    assert tokens("Gotham Comedy Club New York City") == {"gotham", "new", "york", "city"}


def test_an_apostrophe_does_not_split_a_name():
    assert tokens("Caroline's") == tokens("Carolines") == {"carolines"}


def test_the_two_gotham_rows_are_one_venue():
    """The case this module exists for. 1.8km apart, so distance cannot be strict."""
    common = frozenset({"new", "york", "city"})
    assert same_place(
        "Gotham Comedy Club New York City",
        "Gotham Comedy Club Chelsea New York City",
        common,
        (40.75890, -73.98510),
        (40.74310, -73.99670),
    )


def test_the_same_name_in_another_city_is_another_venue():
    """Names alone would merge these; the distance bound is what stops it."""
    assert not same_place(
        "Gotham Comedy Club New York City",
        "Gotham Comedy Club London",
        frozenset({"new", "york", "city"}),
        (40.7589, -73.9851),
        (51.5072, -0.1276),
    )


def test_two_unrelated_venues_do_not_merge():
    assert not same_place(
        "Gotham Comedy Club New York City",
        "Katz's Delicatessen New York City",
        frozenset({"new", "york", "city"}),
        (40.7589, -73.9851),
        (40.7223, -73.9874),
    )


def test_a_city_is_never_absorbed_into_a_venue_inside_it():
    """'Ottawa Ontario Canada' is a subset of every venue in Ottawa, and appears
    too rarely for frequency to flag it. Being contained by several other rows is
    what marks an area: things are *in* it.
    """
    corpus = [
        "Ottawa Ontario Canada",
        "Absolute Comedy Club Ottawa Ontario Canada",
        "Southam Hall National Arts Center Ottawa Ontario Canada",
        "Gotham Comedy Club New York City",
    ]
    common = frozenset({"ontario", "canada"})
    assert city_level("Ottawa Ontario Canada", corpus, common)
    assert not city_level("Gotham Comedy Club New York City", corpus, common)


def test_a_bare_area_contributes_nothing_distinctive():
    assert distinctive("New York City", US_PLACES) == set()


def test_a_row_is_never_both_kept_and_dropped():
    """A<-B<-C chains would repoint memories onto a row that is itself going."""
    queries = [
        "Gotham Comedy Club New York City",
        "Gotham Comedy Club Chelsea New York City",
        "Gotham Comedy Club Chelsea Manhattan New York City",
    ]
    places = [
        {"id": i, "place_query": q, "coords": (40.75, -73.98), "memories": 1}
        for i, q in enumerate(queries, start=1)
    ]
    merges = propose(places)
    kept = {k["id"] for k, _ in merges}
    dropped = {ln["id"] for _, ln in merges}
    assert not kept & dropped


def test_a_frequent_venue_is_misread_as_a_location():
    """The failure that stops this shipping unattended.

    The estimator calls a token 'common' when it recurs, on the theory that
    locations recur and names do not. In a comedy-podcast corpus the Comedy
    Store recurs constantly, so 'store' is classified as a location and stripped
    - leaving 'sunset boulevard', which the Andaz hotel on the same street also
    has. The two then look like one venue.

    Asserting the wrong answer on purpose. W4-02 shipped the real fix as an
    exact match on venue+locality at insert time (pipeline/extract.py's
    save_memories), not a rewrite of this heuristic - dedup.py is retained
    only to serve places written before that migration, so this input is
    expected to produce this wrong answer permanently. See TODO.md 1.2.
    """
    store_is_common = frozenset({"store", "west", "hollywood"})
    assert same_place(
        "Andaz West Hollywood Sunset Boulevard",
        "Comedy Store Sunset Boulevard West Hollywood",
        store_is_common,
        (34.0900, -118.3850),
        (34.0905, -118.3855),
    ), "dedup.py is unchanged by W4-02 by design - see this test's docstring"


def test_the_estimator_calls_recurring_tokens_common():
    corpus = ["Comedy Store Los Angeles"] * 5 + ["Gotham Comedy Club New York City"]
    common = common_tokens(corpus)
    assert "store" in common
    assert "gotham" not in common
