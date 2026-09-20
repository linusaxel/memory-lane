-- One tag vocabulary instead of two.
--
-- The extractor's prompt listed thirteen tags, the app's submission chips
-- offered eleven, and they overlapped on six. The sharp end: the app offers
-- `sport` and the corpus stores `sports`, and `m.tags && …` is an exact-string
-- array overlap - so that chip matched none of the four memories it is about.
-- Latent only because nothing filters by tag yet.
--
-- pipeline/tags.py is the single list now, and both write paths filter against
-- it. This renames the one stored value that disagreed.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/008_one_tag_vocabulary.sql

UPDATE memories SET tags = array_replace(tags, 'sports', 'sport')
WHERE tags @> ARRAY['sports']::varchar[];
