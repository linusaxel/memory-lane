-- Today's route: a fixed set of nearby, not-yet-earned stops, computed once
-- per device per calendar day and stored so a relaunch sees the same route
-- rather than a fresh roll of the dice.
--
-- The first calendar-day-keyed table in this schema. SPENT_TODAY and
-- FILED_TODAY (api/write.py) are rolling 24h windows computed on the fly, not
-- stored rows - that works for a quota, which only needs "how much lately",
-- but a route has to be *stable* across reopens the same day, which a rolling
-- window cannot give you. This is new state, not a pattern match.
--
-- memory_ids is a Postgres array rather than a child table: it is never more
-- than a handful of ids, the array preserves stop order natively on both the
-- write and the read side (see api/queries.py's ROUTE_QUERY), and a join
-- table for at most five ordered integers is a table for nothing.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/013_daily_routes.sql

CREATE TABLE IF NOT EXISTS daily_routes (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    route_date DATE NOT NULL,
    memory_ids INTEGER[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- One route per device per day. Two phones on one account each get their
    -- own row and so, deliberately, can get different routes - there is no
    -- MY_DEVICES sharing here the way unlocks-exclusion has one, because a
    -- route is anchored on wherever *that* phone was standing at first ask.
    PRIMARY KEY (device_id, route_date)
);
