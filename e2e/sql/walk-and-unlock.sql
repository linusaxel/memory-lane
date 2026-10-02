-- F27's streak needs a walk stop unlocked yesterday, by a device id the app has
-- not minted yet. So whichever device turns up first is given a one-stop walk
-- yesterday and its unlock, of a memory at 0,0: never a route candidate, never
-- on screen, and no stop's date moves.
WITH p AS (INSERT INTO places (name, place_query, coordinates)
           VALUES ('Yesterday', 'e2e yesterday', ST_MakePoint(0, 0)::geography) RETURNING id)
INSERT INTO memories (place_id, content_id, summary)
  SELECT p.id, (SELECT id FROM content LIMIT 1), 'Unlocked yesterday.' FROM p;
CREATE FUNCTION yesterday() RETURNS trigger AS $$ BEGIN
  INSERT INTO unlocks (device_id, memory_id, unlocked_at)
    SELECT NEW.id, m.id, now() - interval '1 day' FROM memories m
    JOIN places p ON p.id = m.place_id WHERE p.place_query = 'e2e yesterday';
  INSERT INTO daily_routes (device_id, route_date, memory_ids)
    SELECT NEW.id, (now() - interval '1 day')::date, ARRAY[m.id] FROM memories m
    JOIN places p ON p.id = m.place_id WHERE p.place_query = 'e2e yesterday';
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER yesterday AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION yesterday();
