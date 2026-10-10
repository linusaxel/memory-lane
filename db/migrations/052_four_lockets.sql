-- The round-4 lockets: celtic knot, moon phase, lover's eye, sweetheart, in
-- rotation with the six (docs/10-decisions.md#each-locket-opens-as-itself).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/052_four_lockets.sql

INSERT INTO lockets (id, name, level) VALUES
    ('celtic-knot', 'Celtic knot', 13),
    ('moon-phase', 'Moon phase', 15),
    ('lovers-eye', 'Lover''s eye', 17),
    ('sweetheart', 'Sweetheart', 19)
ON CONFLICT (id) DO NOTHING;
