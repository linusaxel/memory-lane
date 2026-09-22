-- timestamp_end recorded the span two merged mentions covered, and nothing ever
-- read it back: no model, no endpoint, no test, not the card, not the app. It
-- was set on 1 of 231 rows and selected on every memory query.
--
-- The merge still merges. It just stops writing down how wide the merge was.
ALTER TABLE memories DROP COLUMN IF EXISTS timestamp_end;
