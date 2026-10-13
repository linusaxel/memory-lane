-- The round-5 lockets (Gold XI-XVI) join the rotation, and every memory draws
-- again so they show up (docs/10-decisions.md#each-locket-opens-as-itself).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/055_six_lockets.sql

INSERT INTO lockets (id, name, level) VALUES
    ('quatre-couleur', 'Quatre-couleur garland', 21),
    ('rose-egg', 'Rose-gold egg', 23),
    ('dragonfly', 'Green-gold dragonfly', 25),
    ('white-gold-frost', 'White-gold frost', 27),
    ('etruscan-bulla', 'Etruscan bulla', 29),
    ('mokume-river', 'Mokume-gane river', 31)
ON CONFLICT (id) DO NOTHING;

UPDATE memories SET locket = random_locket();
