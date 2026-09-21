"""Search is a stored vector now, which buys an index and costs a trigger.

The scan it replaced was the documented reason search could not be indexed:
to_tsvector(m.summary || ' ' || p.name) spans two tables, and no expression
index can cover that. The tempting fix - an OR of two single-table predicates -
indexes cleanly and quietly stops matching queries whose words straddle the two
fields, which tests/test_api_search.py pins deliberately.

So the concatenation is materialised. That is only correct while both triggers
keep it true, and a stale search vector is invisible: the row is still there,
still readable, and simply stops answering to its own name. Hence this file.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def _place(session, name):
    return session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :q, ST_MakePoint(12.5655, 55.6759)::geography, 50) RETURNING id"
        ),
        {"n": name, "q": f"q:{name}"},
    ).scalar()


def _memory(session, place_id, summary):
    return session.execute(
        text(
            "INSERT INTO memories (place_id, summary, extraction_confidence) "
            "VALUES (:p, :s, 'high') RETURNING id"
        ),
        {"p": place_id, "s": summary},
    ).scalar()


def _matches(session, query):
    return (
        session.execute(
            text(
                "SELECT m.id FROM memories m "
                "WHERE m.search_vector @@ plainto_tsquery('english', :q)"
            ),
            {"q": query},
        )
        .scalars()
        .all()
    )


def test_a_new_memory_is_searchable_without_anybody_refreshing_it(db_session):
    place = _place(db_session, "The Comedy Cellar")
    memory = _memory(db_session, place, "a heckler got the better of him")

    assert _matches(db_session, "heckler") == [memory]
    # The half that only a stored vector can do: the place name is in there too.
    assert _matches(db_session, "cellar") == [memory]
    # And the straddling query, which an OR of two predicates would miss.
    assert _matches(db_session, "cellar heckler") == [memory]


def test_editing_a_summary_updates_what_it_answers_to(db_session):
    place = _place(db_session, "Vega")
    memory = _memory(db_session, place, "the amp died mid-set")
    assert _matches(db_session, "amp") == [memory]

    db_session.execute(
        text("UPDATE memories SET summary = :s WHERE id = :id"),
        {"s": "the drummer never showed up", "id": memory},
    )
    assert _matches(db_session, "amp") == []
    assert _matches(db_session, "drummer") == [memory]


def test_renaming_a_place_updates_every_memory_filed_there(db_session):
    """The trigger that is easy to forget. pipeline/dedup.py renames places,
    and without this half a renamed place answers to its old name for ever."""
    place = _place(db_session, "Comedy Cellar")
    one = _memory(db_session, place, "first night")
    two = _memory(db_session, place, "second night")
    assert sorted(_matches(db_session, "cellar")) == sorted([one, two])

    db_session.execute(
        text("UPDATE places SET name = :n WHERE id = :id"),
        {"n": "The Stand", "id": place},
    )

    assert _matches(db_session, "cellar") == []
    assert sorted(_matches(db_session, "stand")) == sorted([one, two])
    # The summaries are untouched, so they still answer to themselves.
    assert _matches(db_session, "first") == [one]


def test_moving_a_memory_to_another_place_follows_it(db_session):
    here = _place(db_session, "Vega")
    there = _place(db_session, "Loppen")
    memory = _memory(db_session, here, "the amp died mid-set")
    assert _matches(db_session, "vega") == [memory]

    db_session.execute(
        text("UPDATE memories SET place_id = :p WHERE id = :id"),
        {"p": there, "id": memory},
    )

    assert _matches(db_session, "vega") == []
    assert _matches(db_session, "loppen") == [memory]


def test_the_index_can_actually_serve_the_search(db_session):
    """The whole point of the change. On a table this small Postgres will
    rightly prefer a sequential scan, so it is asked to cost the alternative -
    if the index could not serve the predicate there would be no alternative
    to cost."""
    place = _place(db_session, "Vega")
    _memory(db_session, place, "the amp died mid-set")

    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        row[0]
        for row in db_session.execute(
            text(
                "EXPLAIN SELECT m.id FROM memories m "
                "WHERE m.search_vector @@ plainto_tsquery('english', 'amp')"
            )
        )
    )

    assert "idx_memories_search" in plan, f"search is not using its index:\n{plan}"
