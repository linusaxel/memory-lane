# Coding standards

The rules that are not a matter of taste. Each one links to where it is
enforced or argued, rather than restating it. For worked cases, see
[examples/](examples/).

## Python

- **Style is [`pyproject.toml`](../pyproject.toml)'s, and the gate enforces it.** Never hand-align.
  Red on formatting means `venv/bin/python -m ruff format .`, or for the app
  `(cd mobile && npm run format)` (`mobile/.prettierrc`).
- **`except (A, B):` stays exploded.** See [why](10-decisions.md#except-a-b-stays-exploded).
- **Every SQL string lives in [`api/queries.py`](../api/queries.py).** [`tests/test_api_sql.py`](../tests/test_api_sql.py)
  EXPLAINs every `*_QUERY` constant against the real schema, so a query outside that file is a query nobody checks.
  See [good-sql-test](examples/good-sql-test.md).
- **Every env knob is read once, in [`pipeline/config.py`](../pipeline/config.py).** Add new settings there, not as an `os.getenv` at the call site.
- **One tag vocabulary: [`pipeline/tags.py`](../pipeline/tags.py).** Both write paths filter through `clean`.
  See [why](10-decisions.md#one-tag-vocabulary-not-two).

## The gate

- **Every memory-shaped response goes through [`api/gate.py`](../api/gate.py)** (`row_to_memory`). See
  [good-endpoint](examples/good-endpoint.md) and [the gate](10-decisions.md#the-gate).
- **Anything else that emits a summary gates itself.** [`api/card.py`](../api/card.py) renders HTML, cannot use
  `row_to_memory`, and calls `is_locked` itself. A new route like it is a hole until it does the same.

## Routes

- **How a walk is ranked is the docstring of [`api/route_solver.py`](../api/route_solver.py).** Change the ranking, change that docstring.

## Comments

- **A comment has to be load-bearing.** Reasoning goes in [10-decisions.md](10-decisions.md), and the code keeps
  a pointer: `# see docs/10-decisions.md#the-gate`. `tests/test_harness.py` fails if that anchor stops existing.

## Tests

- **No network, no credits.** An autouse fixture in [`tests/conftest.py`](../tests/conftest.py) refuses non-local sockets
  unless a test is marked `live`. Anthropic is [`tests/fakes.py`](../tests/fakes.py)'s `FakeAnthropic`. For the markers,
  see [07-testing.md](07-testing.md#markers). See [good-flow-test](examples/good-flow-test.md).

## The app

- **[`mobile/UI.md`](../mobile/UI.md) before touching `mobile/`.** Tokens, the spacing/radius/shadow scale, and the rules that are load-bearing.
