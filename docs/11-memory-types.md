# Memory types: what a memory is, what it isn't, and how it renders

This is the vocabulary a memory is described in today, written down in one
place because it was previously scattered across `pipeline/tags.py`,
`api/write.py`, `db/schema.sql`, `mobile/UI.md` and a handful of code
comments — and because F25 (`docs/08-ux-flows.md`) is the first flow that has
to reason about the *mix* of layers and tags nearby, not just render one at a
time. It describes the vocabulary as it exists, not as it might grow; where
something is a placeholder rather than a feature, that is said plainly.

## What a memory is

A memory is one experience, tied to one coordinate, that came from exactly one
of two places: something a video or archival transcript said happened there
(`content_id` set), or something a person typed while standing there
(`user_id` set) — never both, and never neither. `memories.content_id` and
`memories.user_id` are separate nullable foreign keys, not a discriminated
union with its own column, because the two things a memory can come from are
also the two things that decide almost everything else about it: whether it
has an author, whether it can link to a source, and which of the layers below
it belongs to.

## What a memory isn't

- **Not a place.** `places` is the coordinate row — a name, a point, how
  precise that point is. One place can hold several memories (`stack` in
  `pipeline/seed_dev.py` is three memories on one place on purpose), and a
  submission mints itself a brand-new place rather than reusing one, so
  "place" and "memory" have never been interchangeable here.
- **Not a review or a rating.** There is no star, no thumbs, nothing scored by
  a reader. `contrast_score` looks like a rating and is not one — it is set
  once, at extraction, by the model judging its own summary against what a
  passer-by is probably looking at, and it exists to order a feed, not to
  represent anyone's opinion.
- **Not a check-in.** Filing a memory (F5) happens to record an unlock for
  its author, because standing there to write it already earned the walk —
  but nothing here tracks visits, streaks, or how often a place is checked
  into. See "no notifications" and "no gamification" below.

## Layer: what kind of memory this is

`memories.layer` is a `VARCHAR(20)` closed by a `CHECK` constraint to three
values (`db/schema.sql:96-102`):

> *"Which of the three content layers this belongs to. The layers render
> differently and must never appear at equal weight in one feed: friend
> memories are intimate and ephemeral, historical cards public and
> permanent."*

- **`historical`** — everything the pipeline extracted from a video or
  archival transcript. `pipeline/extract.py`'s `layer_for()` (lines 401–404)
  hardcodes this for every row the pipeline writes, with a comment that says
  exactly why: *"Everything the pipeline ingests is public, permanent
  content."* No author (`user_id` is null), and its `content_id` links back
  to the video or document it came from. Renders as a **round** pin.
- **`stranger`** — everything filed from a phone via `POST /v1/memories`.
  `SUBMISSION_INSERT` in `api/queries.py` hardcodes the literal `'stranger'`;
  there is no code path that lets a client choose a different layer for its
  own submission. Always has an author, never a `content_id`, and is always
  gated (see below) because it was filed by someone standing exactly there.
  Renders as a **square card with a folded corner**.
- **`friend`** — reserved in the schema and nowhere else. No pipeline path
  writes it, no submission path writes it, and no migration has ever
  inserted a row with it. It exists as a designed-but-unbuilt third tier —
  "intimate and ephemeral" content from people you actually know, as opposed
  to a stranger's public post — and until it has a writer, `layerOf()`
  (`mobile/src/cluster.ts:98-101`) falls a `friend` memory back to rendering
  round, the same as `historical`.

Layer is not chosen by a filter or a segmented control. F4
(`docs/08-ux-flows.md`) explains why: the one accent color already means
*openable*, so there was nothing left to spend on layer, and the answer
became shape instead — drawn all at once, told apart by the pin. See
"The pin's two-axis language" below.

## Tags: a topical vocabulary, orthogonal to layer

Eighteen words, in `pipeline/tags.py:7-26`, ordered by how often the real
corpus actually uses them: `personal, travel, business, nightlife, culture,
adventure, comedy, food, drink, nature, music, art, history, sport, romance,
family, work, strange`. `clean()` (`pipeline/tags.py:29-40`) lowercases,
dedups, and silently drops anything outside this closed list — *"one tag
vocabulary, not two"* (`docs/10-decisions.md#one-tag-vocabulary-not-two`).

A submission's chip picker offers a narrower ten-word subset,
`SUBMISSION_TAGS` in `api/write.py:52-65` — chosen for somebody filing their
own memory rather than for a podcast transcript — but the server still
accepts any of the full eighteen from a client that sends one directly; the
chips are a UI convenience, not a second, stricter vocabulary.

Tags say nothing about layer or confidence. A `historical` memory and a
`stranger` memory can carry the same tag, and until this revamp, no tag ever
reached the map: `Memory.tags` was rendered only inside the detail sheet.
Pins now surface the *dominant* tag — the first memory's first tag — as a
small glyph in the corner slot that isn't already busy with a count, a
padlock, or a route number (`mobile/src/tagGlyph.tsx`,
`mobile/src/MemoryMarker.tsx`). Only a handful of tags have real art yet —
`food`, `drink`, `nightlife`, `music`, `nature`, `family`, `history`,
`personal` — chosen because they're what the dev-seed corpus actually
contains; everything else renders no glyph at all until it earns one. This is
a stated ceiling, not an oversight: adding a tag's glyph is a single `case` in
`tagGlyph.tsx` whenever a real need for it shows up on the map, not something
worth guessing at for all eighteen up front.

## Confidence: a quality signal, not a type

`high`, `medium`, or `low`, set once at extraction. `low` is filtered out
before it ever reaches the database (`filter_low_confidence()`,
`pipeline/extract.py:387-388`), so in practice only `high` and `medium` exist
in `memories.extraction_confidence`. `GET /v1/memories/nearby`'s
`min_confidence` parameter can raise the bar further at read time. A
submitted (`stranger`) memory is always inserted as `'high'`
(`SUBMISSION_INSERT`), which is a statement about trust in the mechanism —
somebody stood there and wrote it — not an assessment of the prose. Confidence
never affects a pin's color or shape; it only ever decides whether a memory
is shown at all.

## The pin's two-axis language

`mobile/UI.md` states the whole system in one line: *"A pin is a stamp
impression on paper. Two axes compose, and nothing else does: the ink state
is your relationship to the coordinate, the shape is which layer it belongs
to."*

- **Color / ink state** (`Reach`, `mobile/src/reach.ts:15`): `plain →
  stamped → warm → locked → unlockable`, driven entirely by distance and by
  what this device has already earned. `seal` (a warm ochre since
  2026-09-23, a stamp red before it — `mobile/UI.md` has the recolor) is
  reserved to mean *openable now, and nothing else, ever* — a route line, a
  tag glyph, a padlock, none of them may use it.
- **Shape** (`layerOf()`, `mobile/src/cluster.ts:98-101`): round for
  `historical` (and for `friend`, which has no writer yet), a folded-corner
  square for `stranger`. A group whose memories span both layers falls back
  to round rather than claiming the stack for one — the sheet's pager is
  what actually shows the mix.

This is not an accident of taste: redundant color-*and*-shape encoding for a
categorical distinction is the documented accessibility-correct pattern (WCAG
1.4.1 — color must never be the *only* channel), which is also why every
marker's `title` restates its state in words for VoiceOver
(`mobile/src/MemoryMarker.tsx`'s comment on why `title` carries the state).
A revamp of pin rendering should extend this system, not replace it — new
information (a tag, a route position) gets a new *slot*, never a new meaning
for color or shape.

## Guardrail appendix: things already tried and reverted for pins

Before adding a new visual idea to a pin, check this list —
`docs/09-visual-design.md` part 4 rejected each of these for the app as a
whole, and none of the reasons are specific to the parts of the UI they were
first tried on:

- **Neomorphism / soft-UI / skeuomorphic textures** — wrong for an app whose
  main control (the hold-to-unlock ring) earns its tactility by *moving*, not
  by looking pressed.
- **A dark map theme** — a padlock's color-coded state is already a fragile
  signal; amber-on-dark and grey-on-dark sit closer together than they do on
  parchment.
- **Glassmorphism** — tried on the banner and the reach pill, tuned to 82%
  opacity for contrast, then removed outright: *"what was left was a
  translucent white pill: the cost of the dependency without the effect."*
- **`amber-500` (or any generic Tailwind accent) as the unlock color** —
  named explicitly as an AI-slop tell; a custom, dual light/dark `seal` value
  replaced it and is not reused anywhere else in the app for exactly that
  reason. `seal` moved from a stamp red to a warm ochre on 2026-09-23, which
  happens to sit closer to `amber-500` on a color wheel than the red did —
  the rejection was never about hue, it was about a generic, unmeasured,
  single-value Tailwind token standing in for a considered one; `seal`'s two
  hand-tuned, contrast-checked values (`mobile/UI.md`) are still exactly
  that considered choice.
- **Floating white cards with soft shadows everywhere** — kept only for the
  two elements that genuinely hover over the map ("Near me", the location
  primer); a pin is not one of those, and never gets a shadow of its own.
- **Tailwind's zinc ramp / the system sans-serif** — the app's palette
  (`mobile/src/theme.ts`) and type system (Fraunces + IBM Plex Mono) exist
  specifically so nothing in the app, pins included, reads as a generated
  default.

And a related restraint that isn't visual, **reopened 2026-09-22** (see
`TODO.md`'s "Ideas — founder brainstorm" section): this product used to have
no notifications, no streaks and no gamification chrome anywhere
(`docs/08-ux-flows.md`'s "deliberately absent" list under F1, and F23's "no
notification when it opens"). Both have shipped: a streak counter (F27, no
notification of its own) and a geofenced proximity notification (F28) that is
the one narrow exception F1's list now names — local, opt-in, off by default,
scoped to memories that are locked and unlockable by walking there, and
excluding a sealed one (F23) exactly as the map's own walk hint does. This
restraint no longer holds as a blanket rule — a route, a badge, a count still
render silently where nothing was decided to push, but this one proximity
nudge is now allowed to.
