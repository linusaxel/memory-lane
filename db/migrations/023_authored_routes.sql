-- A walk somebody authored, as opposed to today's, which the solver picks per
-- device. Long-lived, ordered and edited, so it earns the join table that
-- daily_routes refused for five ints (013). Only published ones are served.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/023_authored_routes.sql

-- routes and route_stops were created here; 044_schema_cleanup.sql drops them
-- again.
