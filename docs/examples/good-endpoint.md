# A good endpoint: `GET /v1/memories/{id}`

Look at `get_memory` in [`api/read.py`](../../api/read.py). It is the unlock read, and every
layer is in its own place:

| Layer | Where |
|---|---|
| Shape | `Memory` in [`api/models.py`](../../api/models.py), as the route's `response_model` |
| SQL | `SINGLE_MEMORY_QUERY` in [`api/queries.py`](../../api/queries.py), built from the shared `MEMORY_COLUMNS` / `MEMORY_JOIN` fragments |
| Gate | `viewer_position` and `row_to_memory` in [`api/gate.py`](../../api/gate.py) |
| Validation | `Query(..., ge=-90, le=90)` on the position, so FastAPI refuses nonsense before any SQL runs |

## Why copy it

- **The handler never decides what is readable.** It hands the row and the viewer's position to
  `row_to_memory`, and a locked memory comes back redacted from the same code that serves
  `/nearby`, `/search` and `/places/nearby`. No endpoint can drift into a side door.
- **The SQL is a named constant**, so [`tests/test_api_sql.py`](../../tests/test_api_sql.py) EXPLAINs it
  without anybody remembering to add it.
- **A refusal is a 200 with a distance, not an error.** Once the gate says no, the handler adds
  `distance_meters`, and the app turns that into "a few steps nearer".

## The trap it avoids

Building a `Memory` by hand from the row. It works, it passes a test that only reads unlocked
rows, and it serves every summary to anybody who asks. If a route cannot use `row_to_memory`
(like [`api/card.py`](../../api/card.py), which renders HTML), it must call `is_locked` itself.
See [the gate](../10-decisions.md#the-gate).
