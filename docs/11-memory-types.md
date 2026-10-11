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

`memories.layer` is a `VARCHAR(20)` closed by a `CHECK` constraint to two
values (`db/schema.sql`, `memories.layer`):

> *"Which content layer this belongs to: historical is what the pipeline
> extracted, stranger what a person filed. They render differently and
> must never appear at equal weight in one feed."*

- **`historical`** — everything the pipeline extracted from a video or
  archival transcript. `pipeline/extract.py`'s `layer_for()` (lines 401–404)
  hardcodes this for every row the pipeline writes, with a comment that says
  exactly why: *"Everything the pipeline ingests is public, permanent
  content."* No author (`user_id` is null), and its `content_id` links back
  to the video or document it came from.
- **`stranger`** — everything filed from a phone via `POST /v1/memories`.
  `SUBMISSION_INSERT` in `api/queries.py` hardcodes the literal `'stranger'`;
  there is no code path that lets a client choose a different layer for its
  own submission. Always has an author, never a `content_id`, and is always
  gated (see below) because it was filed by someone standing exactly there.
- **`friend`** was a reserved third value with no writer. Migration 044
  dropped it (docs/10, *The schema keeps only what is read*).

Layer is not chosen by a filter or a segmented control. F4
(`docs/08-ux-flows.md`) explains why: every layer is drawn at once, as the
same pin, and the sheet says which kind a memory is. See "One pin" below.

## Tags: a topical vocabulary, orthogonal to layer

Eighteen words, in `pipeline/tags.py:7-26`, ordered by how often the real
corpus actually uses them: `personal, travel, business, nightlife, culture,
adventure, comedy, food, drink, nature, music, art, history, sport, romance,
family, work, strange`. `clean()` (`pipeline/tags.py:29-40`) lowercases,
dedups, and silently drops anything outside this closed list — *"one tag
vocabulary, not two"* (`docs/10-decisions.md#one-tag-vocabulary-not-two`).

That list is the extractor's. A submission's tags are open: the #words its
author wrote in the description (`from_text` in `pipeline/tags.py`), since
2026-09-26 (`docs/10-decisions.md#tags-come-from-the-text-and-a-walk-has-no-theme`).

Tags say nothing about layer or confidence, and they never reach the map:
`Memory.tags` shows only as the locked peek's first word, and a submission's
#words highlighted in its own text. (Pins carried a
dominant-tag glyph from 2026-09-22 to 2026-09-23; it went with the one-pin
simplification below.)

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

## One pin

Every coordinate draws the same pin, and it lights up — larger, in `seal`, over
a halo — only when it can be opened from where you stand. Layer, tag,
confidence, earned-or-not and near-or-far are not on the pin. `mobile/UI.md`'s
"One pin" section has the geometry.

It was briefly a two-axis language (an ink state per `Reach`, a shape per
layer, a ranked corner slot for a padlock or a tag glyph) and that was cut on
2026-09-23 for being a legend to learn before the map made sense. The lit pin
still does not lean on colour alone (WCAG 1.4.1): it is bigger and haloed as
well, and every marker's `title` states its full reach state in words for
VoiceOver.

`seal` (a warm ochre since 2026-09-23, a stamp red before it) means *openable
now, and nothing else, ever* — the route line, a badge, a padlock, none of them
may use it. The walk has its own colour, `route`.

## Guardrail appendix: things already tried and reverted for pins

Before adding anything to a pin, first re-read "One pin" above — the answer is
probably the sheet. Then check this list —
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
  two elements that genuinely hover over the map ("Turn on location", the location
  primer); a pin is not one of those, and never gets a shadow of its own.
- **Tailwind's zinc ramp** — the app's palette (`mobile/src/theme.ts`)
  exists specifically so nothing in the app, pins included, reads as a
  generated default. The type is now the system's own, SF Pro Rounded, chosen
  to sit with the map (`docs/10-decisions.md`, "One font, the map's").

And a related restraint that isn't visual, **reopened 2026-09-22** (see
`docs/10-decisions.md`, "A streak and a proximity notification, after all"): this product used to have
no notifications, no streaks and no gamification chrome anywhere
(`docs/08-ux-flows.md`'s "deliberately absent" list under F1). Both have shipped (the streak removed again 2026-10-11, docs/10 *No streak*): a streak counter (F27, no
notification of its own) and a geofenced proximity notification (F28) that is
the one narrow exception F1's list now names — local, opt-in, off by default,
scoped to memories that are locked and unlockable by walking there. This
restraint no longer holds as a blanket rule — a route, a badge, a count still
render silently where nothing was decided to push, but this one proximity
nudge is now allowed to.
