-- A memory that cannot be read until a date, not even by the person who wrote
-- it. Phase 5.2.
--
-- The proximity gate asks "are you here?". This asks "is it time?", and the two
-- are independent: a time-locked memory stays shut on the spot, stays shut in
-- the collection of the device that filed it, and stays shut on its own card.
-- api/gate.py checks it first, before position is considered at all, so there
-- is one place to get it wrong rather than four.
--
-- A DATE and not a timestamp. "Opens on 3 May 2031" is the whole of what a
-- person means, and a time of day would invite a timezone argument nobody
-- needs: the row says a day, and the day is over when the server's date says it
-- is.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/009_time_locked.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS opens_at DATE;
