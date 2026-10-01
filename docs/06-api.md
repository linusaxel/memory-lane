# API

FastAPI over PostGIS. `GET /docs` on a running server is the Swagger page and
the authority on shapes (`api/models.py`); this is the map. Where the code lives
is in [repository-map.md](repository-map.md#api); why it is gated is in
[architecture.md](architecture.md#security).

- `GET /v1/memories/nearby?lat=X&lng=Y&radius_km=10&tags=food,travel&min_confidence=medium&device=UUID` - Find memories near location (tags, confidence and device optional; a device leaves out whoever it blocked)
  - Gated memories always come back locked here: no summary, quote, media or links, but
    tags, `source_name` and `year` (the app's peek, F29).
    This endpoint never unlocks. See [Proximity unlock](architecture.md#proximity-unlock).
- `GET /v1/memories/search?q=coffee&lat=X&lng=Y&radius_km=50` - Full-text search across summaries and place names (location optional)
- `GET /v1/memories/{id}?at_lat=X&at_lng=Y` - Get single memory, gated
  - Open, it carries `links`: names in the summary, exactly as written, with their
    Wikipedia article (`pipeline/links.py`). Locked, `links` is empty
  - Open, it also carries `quote` and `quote_by` (a line copied from the source,
    or null), `happened_at` with `happened_precision`, and `contrast_note`
- `POST /v1/memories/{id}/unlock` `{device, lat?, lng?}` - **the unlock.** Same gate,
  and the only route that records one. POST because it creates something.
  One of today's three free unlocks opens it from anywhere, position or not.
  After those, standing on it costs 1,000 steps (nothing for a subscriber),
  and away from it answers the locked memory and its distance. Opening one
  this account already has costs nothing. 403 `{reason: "no_steps", steps,
  price}` standing there with nothing to spend (docs/10, "Three free a day, then steps where you stand")
- `GET /v1/unlocks?device=UUID` - that device's collection, always unlocked
- `GET /v1/routes/preview?device=UUID&lat=X&lng=Y&budget_meters=4000&loop=true` - the walk
  of that length from there would be: about one stop a km. Stores nothing.
  `budget_meters` is 1000–10000; `loop` defaults to `ROUTE_LOOP`; `again` is "Show me
  another" (F32), another walk as good; `include=<memory_id>` is "Walk here",
  a memory every walk passes. 422 with
  `detail: {reason: "not_a_stop"}` when it could not be a stop, or
  `{reason: "too_far", min_budget_meters}` when the streets there are longer
  than this walk. `end_lat` and `end_lng`, together, are where a one-way walk
  finishes (it makes the walk one-way, and is stored nowhere); the same
  `too_far` when this walk cannot reach it
- `POST /v1/routes/today` `{device, lat, lng, budget_meters, loop?, again?, include?, end?}` - accept it. The
  same solve, stored; one in progress per device, and a second accept gets
  that walk back until it is ended. The only stop id the client ever sends is `include`, vetted
- `POST /v1/routes/today/end` `{device}` - end today's walk, finished or not;
  204, and 204 again with nothing to end. A walk that opened something stays
  in `walked`; one that opened nothing is deleted. Its unearned stops lock
  again, and another can be accepted if it opened nothing or the account is
  subscribed
- `GET /v1/routes/today?device=UUID` - today's walk in progress, or 404. Only reads
- `GET /v1/routes/walked?device=UUID` - every walk the account took that
  opened something, newest first: earned stops open, `earned` of `size`, `completed_at`
- `GET /v1/routes/{id}` - an authored walk: its stops in order, locked like
  today's. 404 while it is a draft. Nothing writes these yet but SQL
- `POST /v1/memories` `{device, lat, lng, place_name, summary, ...}` -
  **file your own memory.** Its tags are the #words in `summary`
  (`pipeline/tags.py`, `from_text`); a `tags` field is ignored. One coordinate: it is both where you are and where
  the memory goes. Lands in the `stranger` layer, gated like everything else,
  and records the unlock for the person who filed it
- `POST /v1/media` (multipart: `device`, `file`, optional `duration_seconds`) -
  a photo or a recording, held until a submission claims it. `api/media.py`
  decides what a file may be; see [Uploads](architecture.md#uploads)
- `PUT /v1/memories/{id}` / `DELETE /v1/memories/{id}` `{device, ...}` - change
  or take down something you filed. Ownership is the only check; the delete is
  real, not the report path's hidden flag
- `GET /v1/me/memories?device=UUID` - everything this account filed, newest
  first, hidden ones included
- `POST /v1/memories/{id}/heart` `{device}` - one heart per device, and it does
  not come back off. No position check. Your own memory is a 403
- `POST /v1/memories/{id}/note` `{device, body}` / `GET /v1/memories/{id}/notes?device=UUID`
  - one note per device, 280 characters, rewritten by posting again. Both are
  403 without an unlock; the POST returns the list. `note_count` travels on
  every memory, locked too
- `DELETE /v1/memories/{id}/notes/{note_id}?device=UUID` - hide a note: your
  own, or anyone's on a memory you filed
- `POST /v1/memories/{id}/report` `{device, reason}` - REPORT_THRESHOLD distinct
  signed-in accounts and the memory stops being served by every endpoint. A
  device with no Google or Apple sign-in is recorded and not counted.
  `python -m api.moderate` lists what is hidden and reinstates it
- `POST /v1/users/{id}/block` `{device}` - that person's memories and notes are
  gone for every device on this account: nearby (pass `device`), unlock, the
  collection, notes and today's walk. 404 for nobody. No unblock
- A memory, an edit, a note and a display name are screened by local rules
  before they are stored (`api/moderation.py`): 422 `{"reason": "refused"}`
  for a blocked word, an email, a phone number or a link
- `GET /v1/me?device=UUID` / `PUT /v1/me` `{device, display_name}` - the name a
  submission is signed with, which sign-ins are attached, `subscribed` /
  `subscribed_until`, and what unlocks spend: `free_per_day`, `free_unlocks`,
  `steps`, `steps_per_unlock`, and `steps_counted_until`, where the next count
  starts.
  The GET creates nothing
- `POST /v1/me/steps` `{device, since, steps}` - credit the steps the phone
  counted from `since`, which must be `steps_counted_until`, and move it to
  now. A stale `since` credits nothing; either way it returns the `Profile`.
  At most three steps a second over the window
- `POST /v1/auth/google` / `POST /v1/auth/apple` `{device, id_token,
  display_name?, link_token?}` - verify a provider ID token and bind this device
  to that account. `display_name` is for Apple, which gives the name to the
  client once and never again. Adding a new sign-in to an account that already
  has one needs `link_token`, a fresh token from a sign-in already on it; 403
  without it. Every token's `nonce`, `link_token`'s too, must be the SHA-256
  hex of `device`, or 401: a copied token signs in only the phone it was minted for
- `DELETE /v1/me?device=UUID` - delete the account and everything it made:
  memories, media, sign-ins, the subscription row, and every device on it with
  their unlocks, hearts, notes and walks. 204
- `POST /v1/auth/signout` `{device}` - unlink the device. Deletes nothing, and
  there is no token to revoke
- `POST /v1/me/subscription` `{device}` - read this account's subscription
  back from RevenueCat now and return the `Profile` (`subscribed`,
  `subscribed_until`). The app calls it after a purchase or a restore. 503
  without `REVENUECAT_API_KEY`
- `POST /v1/billing/revenuecat` - RevenueCat's webhook, `Authorization: Bearer
  <REVENUECAT_WEBHOOK_SECRET>`. 401 on a wrong secret, 503 without one. Any
  event re-reads that subscriber; an unknown `app_user_id` is 200 and ignored
- `GET /v1/places/nearby?lat=X&lng=Y&radius_km=10` - Get places with memory counts
- `GET /v1/stats` - Database statistics
- `GET /v1/memories/{id}/card` - the server-rendered share card. Gates itself
  (`api/card.py`)
- `GET /embed`, `/embed.js` - the embeddable map. Off when `ENABLE_EMBED=0`
- `GET /privacy` - the policy both app stores link to
- `GET /` - the health shape Railway probes
- `GET /docs` - Swagger UI. Not on Railway
