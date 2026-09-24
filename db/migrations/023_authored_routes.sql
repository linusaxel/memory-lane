-- A walk somebody authored, as opposed to today's, which the solver picks per
-- device. Long-lived, ordered and edited, so it earns the join table that
-- daily_routes refused for five ints (013). Only published ones are served.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/023_authored_routes.sql

CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    is_loop BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS route_stops (
    route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    PRIMARY KEY (route_id, position),
    UNIQUE (route_id, memory_id)
);
