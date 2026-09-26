# AGENTS.md

For any agent (Claude Code, Codex, Cursor) or person working in this repo.
`CLAUDE.md` is only `@AGENTS.md`, so this is the one source.

## Project

**Memory Lane** extracts location-based memories from video transcripts and
makes them queryable by geographic proximity. A story opens only once you stand
on its spot, and the app plans a daily walk past a few.

Pipeline: `Content URLs → Transcripts → LLM Extraction (with coords) → Query API → Expo app`

## Before making changes

Read what the change touches, not everything:

- [docs/architecture.md](docs/architecture.md): how the parts talk, who writes which table, security, deployment
- [docs/repository-map.md](docs/repository-map.md): where every file lives, and what it is for
- [docs/10-decisions.md](docs/10-decisions.md): **why the code is shaped this way.** Read the relevant entry before "fixing" something odd
- [docs/coding-standards.md](docs/coding-standards.md), with real examples in [docs/examples/](docs/examples/)
- The app: [mobile/UI.md](mobile/UI.md) (tokens, load-bearing rules) and [docs/08-ux-flows.md](docs/08-ux-flows.md) (what the user does)
- The API: [docs/06-api.md](docs/06-api.md). Tests: [docs/07-testing.md](docs/07-testing.md). Setup, env, tables: [docs/01-setup.md](docs/01-setup.md)

## Architecture constraints

- **Memories are gated by standing there.** Every memory-shaped response goes through `api/gate.py`. See [The gate](docs/10-decisions.md#the-gate)
- **The device UUID is the only credential.** Self-issued, sent in the body, and never a session token. See [Identity](docs/architecture.md#identity)
- **Google and Apple sign-in only.** See [Google and Apple only](docs/10-decisions.md#google-and-apple-only)
- **The summary is the product.** Measure a prompt change before and after it ships. See [Memory quality](docs/04-extract.md#memory-quality)
- Two writers to one database: the pipeline and the API. See [Data ownership](docs/architecture.md#data-ownership)

## Forbidden actions

- **Never run `python -m pipeline.extract` casually.** There is no `--limit`: it bills
  every pending video. To spend cents, use `python -m pipeline.enqueue --video <id>`.
- Never serve a summary without the gate. A new route that emits one gates itself, as `api/card.py` does.
- Never match or link accounts on email.
- Never issue a session token, and never add a password sign-in.
- Never hand-format or hand-align. `pyproject.toml` decides.
- Never let a test touch the network or spend credits (`tests/fakes.py`, the `live`/`credits` markers).
- Never delete a decision that changed. Mark it `Superseded` in `docs/10-decisions.md`.

## Development rules

### Run the gate

Two things verify this project and they answer different questions. The gate
says the rules are right; `./e2e/run.sh` says the product works, by driving the
real app on a simulator. The gate is the one you must not leave red.

One trap worth knowing: `./loop/verify.sh | tail` reports `tail`'s exit status,
not the gate's. Check `$?` on the gate itself, or a red gate reads as green.

```bash
./loop/verify.sh     # 0 GREEN | 1 RED (fix it) | 2 INFRA (needs a human)
```

It runs compileall, ruff check + format --check, pytest, and the app's
typecheck. If it reports RED because of formatting:

```bash
venv/bin/python -m ruff format .
```

Style is not a matter of taste here - `pyproject.toml` decides and the gate
enforces. Don't hand-align anything.

### Then log the friction

Every session, before the last commit: add to `TODO.md` § **Friction** anything
that cost this session real time or nearly shipped something wrong. The aim is
clean code, speed, understandability, and a repo an agent can work in without
tripping. Be strict:

- **In:** it will happen again to the next person or agent, and there is a
  concrete fix. A stale doc, a slow loop, a trap in the tooling, code that took
  two readings, a fake that lies.
- **Out:** one-offs, your own slips, anything already logged (sharpen that
  entry instead), and a problem you fixed in the same session.
- **Shape:** one entry each. What happened, dated, what it cost, and the fix
  in one line. No entry beats a vague one.

If nothing qualifies, add nothing.

## Quick start

```bash
docker compose up -d                                   # database, Redis, API
python3 -m venv venv && source venv/bin/activate       # 3.12, not 3.14
pip install -r requirements.txt -r requirements-dev.txt
# Required: ANTHROPIC_API_KEY. Every other knob: docs/01-setup.md, read once in pipeline/config.py

python -m pipeline.ingest && python -m pipeline.transcripts   # free
python -m pipeline.enqueue --video <content_id>               # extract one video (bills cents)
python -m pipeline.worker --burst                             # run the queues, exit when empty

python -m pipeline.seed_dev          # memories you can walk to; --clear removes them
python -m pipeline.seed_dev --dense 300 --seed 1   # plus a full map for the route to choose from
python -m pipeline.seed_dev --routes bimodal   # one route scenario alone, all in Copenhagen: sparse, dense, bimodal, linear, one-layer, stack-heavy, lakes

uvicorn api.main:app --reload        # API; /docs is Swagger
cd mobile && npx expo start --ios    # the app (mobile/UI.md has the recipe)
```

## Commit checklist

- [ ] `./loop/verify.sh; echo $?` prints `0`
- [ ] Friction logged in `TODO.md`, or nothing qualified
- [ ] If a decision changed: `docs/10-decisions.md` is updated (the old one marked `Superseded`), and so is any doc that restated it
- [ ] New files are in `docs/repository-map.md`; new env knobs are in `pipeline/config.py` and `docs/01-setup.md`
