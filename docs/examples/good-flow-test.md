# A good flow test: F7, refused then earned

Look at `test_f7_refused_at_300m_then_earned_by_standing_there` in
[`tests/test_flows.py`](../../tests/test_flows.py).

- The `seeded` fixture plants [`pipeline/seed_dev.py`](../../pipeline/seed_dev.py), the same corpus the
  simulator run in `.maestro/` uses.
- `seeded_id` finds a memory by its seeded `place_query`, not by proximity.
- `read_at` is one read, as somebody standing at a position sees it.
- The test itself: read from `START` (locked, no summary, a distance), unlock from there (refused, and
  nothing recorded), then unlock from the spot (open, with the summary).

## Why copy it

- **It asserts the sequence, not the rule.** Each rule already has a test of its own in
  `test_api_unlock.py`. This test proves that refused, walked in and unlocked compose into
  one collection, which is what the app actually does. The module docstring says keep it to whole flows.
- **It is named after its flow id** in [08-ux-flows.md](../08-ux-flows.md). When a Maestro flow goes red, this file has
  already said whether the API moved or the app did.
- **No network, no credits.** The API runs in-process through `api_client` in
  [`tests/conftest.py`](../../tests/conftest.py), whose autouse `_no_network` refuses any non-local socket.
  Anything touching extraction uses `FakeAnthropic` from [`tests/fakes.py`](../../tests/fakes.py).

## The trap it avoids

Looking a seeded memory up by "nearest to here". Several arrangements sit inside the smallest
radius the API accepts, so the test would silently pick whichever sorted first. `seeded_id`'s docstring
explains this.
