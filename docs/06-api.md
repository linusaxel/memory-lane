# API

FastAPI over PostGIS. `GET /docs` on a running server is the Swagger page and
the authority on shapes (`api/models.py`); this is the map. Where the code lives
is in [repository-map.md](repository-map.md#api); why it is gated is in
[architecture.md](architecture.md#security).

- `GET /v1/memories/nearby?lat=X&lng=Y&radius_km=10&tags=food,travel&min_confidence=medium` - Find memories near location (tags and confidence optional)
  - Gated memories always come back locked here: no summary, media or links, but
    tags, `source_name`, `year` and `summary_words` (the app's peek, F29).
    This endpoint never unlocks. See [Proximity unlock](architecture.md#proximity-unlock).
- `GET /v1/memories/search?q=coffee&lat=X&lng=Y&radius_km=50` - Full-text search across summaries and place names (location optional)
- `GET /v1/memories/{id}?at_lat=X&at_lng=Y` - Get single memory, gated
- `POST /v1/memories/{id}/unlock` `{device, lat, lng}` - **the unlock.** Same gate,
  and the only route that records one. POST because it creates something.
  403 unless the memory is a stop of this account's walk today
- `GET /v1/unlocks?device=UUID` - that device's collection, always unlocked
- `GET /v1/routes/preview?device=UUID&lat=X&lng=Y&budget_meters=4000&loop=true&tag=food` - the walk
  of that length from there would be: up to five stops. Stores nothing.
  `budget_meters` is 1000–10000; `loop` defaults to `ROUTE_LOOP`, `tag` (one of
  `pipeline/tags.py`) keeps only stops carrying it; `again` is "Show me
  another" (F32), another walk as good; `include=<memory_id>` is "Walk here",
  a memory every walk passes (the theme does not filter it). 422 with
  `detail: {reason: "not_a_stop"}` when it could not be a stop, or
  `{reason: "too_far", min_budget_meters}` when the streets there are longer
  than this walk. `end_lat` and `end_lng`, together, are where a one-way walk
  finishes (it makes the walk one-way, and is stored nowhere); the same
  `too_far` when this walk cannot reach it
- `POST /v1/routes/today` `{device, lat, lng, budget_meters, loop?, tag?, again?, include?, end?}` - accept it. The
  same solve, stored; one in progress per device, and a second accept gets
  that walk back until it is ended. The only stop id the client ever sends is `include`, vetted
- `POST /v1/routes/today/end` `{device}` - end today's walk, finished or not;
  204, and 204 again with nothing to end. The walk stays in `walked`, its
  unearned stops lock again, and another can be accepted
- `GET /v1/routes/today?device=UUID` - today's walk in progress, or 404. Only reads
- `GET /v1/routes/walked?device=UUID` - every walk the account accepted,
  newest first: earned stops open, `earned` of `size`, `completed_at`
- `GET /v1/routes/{id}` - an authored walk: its stops in order, locked like
  today's. 404 while it is a draft. Nothing writes these yet but SQL
- `POST /v1/memories` `{device, lat, lng, place_name, summary, tags, ...}` -
  **file your own memory.** One coordinate: it is both where you are and where
  the memory goes. Lands in the `stranger` layer, gated like everything else,
  and records the unlock for the person who filed it
- `POST /v1/media` (multipart: `device`, `file`, optional `duration_seconds`) -
  a photo or a recording, held until a submission claims it. `api/media.py`
  decides what a file may be; see [Uploads](architecture.md#uploads)
- `PUT /v1/memories/{id}` / `DELETE /v1/memories/{id}` `{device, ...}` - change
  or take down something you filed. Ownership is the only check; the delete is
  real, not the report path's hidden flag
- `GET /v1/me/memories?device=UUID` - everything this account filed, newest
  first, hidden and sealed ones included
- `POST /v1/memories/{id}/heart` `{device}` - one heart per device, and it does
  not come back off. No position check
- `POST /v1/memories/{id}/note` `{device, body}` / `GET /v1/memories/{id}/notes?device=UUID`
  - one note per device, 280 characters, rewritten by posting again. Both are
  403 without an unlock; the POST returns the list. `note_count` travels on
  every memory, locked too
- `DELETE /v1/memories/{id}/notes/{note_id}?device=UUID` - hide a note: your
  own, or anyone's on a memory you filed
- `POST /v1/memories/{id}/report` `{device, reason}` - REPORT_THRESHOLD distinct
  devices and the memory stops being served by every endpoint
- `GET /v1/me?device=UUID` / `PUT /v1/me` `{device, display_name}` - the name a
  submission is signed with, plus which sign-ins are attached. The GET creates
  nothing
- `POST /v1/auth/google` / `POST /v1/auth/apple` `{device, id_token,
  display_name?}` - verify a provider ID token and bind this device to that
  account. `display_name` is for Apple, which gives the name to the client once
  and never again
- `POST /v1/auth/signout` `{device}` - unlink the device. Deletes nothing, and
  there is no token to revoke
- `GET /v1/places/nearby?lat=X&lng=Y&radius_km=10` - Get places with memory counts
- `GET /v1/stats` - Database statistics
- `GET /v1/memories/{id}/card` - the server-rendered share card. Gates itself
  (`api/card.py`)
- `GET /embed`, `/embed.js` - the embeddable map. Off when `ENABLE_EMBED=0`
- `GET /privacy` - the policy both app stores link to
- `GET /` - the health shape Railway probes
- `GET /docs` - Swagger UI
