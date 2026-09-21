-- The gate's own question was the slowest thing in the read path.
--
-- COORDINATE_IS_UNIQUE asks, for a place, whether any other place shares its
-- snapped grid cell - that is what decides whether a memory is gated at all.
-- It compares ST_SnapToGrid(...) on both sides, so nothing could serve it and
-- Postgres scanned every place in the table, once per row returned.
--
-- Measured on 50,000 memories across 20,000 places, /v1/memories/nearby at a
-- 10km radius:
--
--     Seq Scan on places p2 ... rows=1 loops=20
--       Rows Removed by Filter: 19999
--
--   before   338 ms   (305 ms of it in that subplan)
--   after     14 ms
--
-- and /v1/places/nearby went 265 ms -> 9 ms. It is the hot path: the app
-- refires it on every pan, debounced at 400ms.
--
-- The index has to match the expression exactly, including the argument form -
-- ST_SnapToGrid(geom, size) and ST_SnapToGrid(geom, 0, 0, size, size) are the
-- same answer and different expressions, and only the one that matches the
-- query text is used. api/queries.py is where that text lives.

CREATE INDEX IF NOT EXISTS idx_places_grid
    ON places (ST_SnapToGrid(coordinates::geometry, 0.0001));
