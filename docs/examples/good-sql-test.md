# A good SQL test: EXPLAIN every query

Look at [`tests/test_api_sql.py`](../../tests/test_api_sql.py).

- `QUERIES` collects every `*_QUERY` constant from [`api/queries.py`](../../api/queries.py) by name.
- `test_query_is_valid_sql` runs `EXPLAIN` on each one against the real schema, binding only the
  `PARAMS` its text mentions.
- `test_every_query_constant_is_collected` fails if a rename hides queries from the collection.
- `test_the_gates_uniqueness_question_can_use_an_index` goes one step further. It reads the plan
  and asserts that `idx_places_grid` is in it.

## Why copy it

- **A new query is tested for free.** Name it `SOMETHING_QUERY` in `api/queries.py` and it is
  collected. Nobody has to remember to write a test for it.
- **EXPLAIN plans without returning rows**, so it runs against the empty test database in
  milliseconds. The API tests use a `TestClient`, and without this file a typo in a query would reach production untouched.
- **Assert the plan, not the index.** The gate's index only helps if the planner's expression matches it
  exactly. Checking that the index exists would pass while every nearby read scans `places`.
  See [why it matters](../10-decisions.md#the-gates-uniqueness-question-is-indexed-and-it-is-the-hot-path).

## The trap it avoids

SQL assembled inline in a handler. It is invisible to this test, and after enough copy-paste the
fourteen-column SELECT drifts between endpoints. That is what `MEMORY_COLUMNS` replaced.
