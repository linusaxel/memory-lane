# UX flows

What a person actually does, start to finish. One flow per section.

This file is the target, not a description of the code — where a flow is marked
**Proposed**, the app does not do it yet and the flow is the spec to build
toward. Implemented flows describe exactly what ships today; if you change
behaviour, change the flow in the same commit.

Visual conventions, tokens and the store-review constraints are in
[`mobile/UI.md`](../mobile/UI.md).

## Format

Each flow states: who, the trigger, the numbered path, what can go wrong, and
how you know it worked. Keep them concrete enough to test against.

---

## F1 · Discover memories near me — **Implemented**

**Who:** someone who opened the app for the first time, standing somewhere.

1. App launches, map appears already centred on `FALLBACK_REGION` (Manhattan).
2. It immediately asks for foreground location.
   - **Granted** → animates to the person's position over 600ms, fetches.
   - **Denied** → stays on Manhattan and fetches there. Never a blank map.
3. Pins drop for every memory with coordinates in the viewport radius.
4. Banner reads "N memories here".
5. Panning or zooming refetches, debounced 400ms, radius derived from the
   viewport and clamped to 0.1–100km.

**Failure:** if the request *rejects*, the banner becomes "Could not reach
Memory Lane" and the map stays interactive with the last good pins.

But if the request *hangs* — wrong host, dropped network — nothing rejects.
`fetchNearby` takes an `AbortSignal` and `App.tsx` never passes one, so there is
no timeout: the banner sits on "0 memories here" with a spinner forever, which
reads as "this area is empty" rather than "this is broken". Observed live, not
theoretical. Fixing it means passing a signal with a deadline, and is the same
work as **0.4 Design the empty state** in `TODO.md` — genuinely empty and
unreachable must not look identical.

**Done when:** a pin appears within ~1s of the map settling, and the count
matches the pins drawn.

## F2 · Read one memory and go to its source — **Implemented**

**Who:** someone who sees a pin near a place they know.

1. Tap a pin → sheet slides up.
2. Place name, distance, confidence.
3. The summary is the point of the screen — a story about what happened there.
4. Tags; the source video title.
5. "Watch at 12:04" → opens YouTube at that exact second.
6. Close, or Android back → returns to the map, viewport unchanged.

**Failure:** no YouTube app and no browser → `Linking.openURL` rejects. Not
currently handled.

**Done when:** the video opens at the right second and returning preserves the
map position.

---

## Proposed

Not built. Each needs a decision before it can be specified properly — see
*Open questions* at the bottom, and `TODO.md` for the phase each belongs to.

### F3 · Arrive somewhere and find its history — **Proposed** (Phase 1)

The core of the product brief: stand in a Copenhagen street, learn what
happened there. Blocked on choosing the historical source, and on deciding
whether it is a separate map layer, a filter, or a second pin style.

### F4 · Switch between historical, friend and stranger layers — **Proposed** (Phases 1, 3, 4)

Once memories carry a `layer`, the map needs a way to choose. Unanswered: is
this a segmented control, a filter sheet, or layers stacked at once with
different pin colours? At a dense location this decides whether the map is
readable.

### F5 · Contribute a memory — **Proposed** (Phases 3, 4)

Nothing in the app writes today; the API is read-only. Needs auth, moderation
and an abuse story before the UI matters.

### F6 · Many memories at one point — **Proposed**

Already reachable: one place can hold six memories (Gotham Comedy Club does),
and near-duplicate places still produce separate pins at nearly the same spot.
Today the sheet shows one memory and overlapping pins are hard to tap. Needs
clustering, or a place-level sheet listing its memories.

---

## Open questions

Answer these and the proposed flows can be written properly.

1. **Layers: filter or stack?** One at a time, or several with distinct pin
   styles?
2. **What does a person see with zero memories nearby?** The realistic
   Copenhagen case before the historical corpus lands. Empty map, a nudge to
   zoom out, or auto-widen the radius?
3. **Is contribution in v1 at all**, or is v1 read-only?
4. **Does a pin represent a place or a memory?** Today it is a memory, so one
   place with six memories is six overlapping pins. Place-level pins would fix
   F6 but change what tapping means.
