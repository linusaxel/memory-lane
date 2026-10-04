-- F27's streak needs a walk stop unlocked each of the six days before, by a
-- device id the app has not minted yet, so today's walk makes seven (G5's
-- first milestone). So whichever device turns up first is given a one-stop
-- walk on each of those days and its unlock, of a memory at 0,0: never a
-- route candidate, never on screen, and no stop's date moves.
WITH p AS (INSERT INTO places (name, place_query, coordinates)
           VALUES ('Yesterday', 'e2e yesterday', ST_MakePoint(0, 0)::geography) RETURNING id)
INSERT INTO memories (place_id, content_id, summary)
  SELECT p.id, (SELECT id FROM content LIMIT 1), 'Unlocked ' || n || ' days ago.'
  FROM p, generate_series(1, 6) n;
CREATE FUNCTION yesterday() RETURNS trigger AS $$ BEGIN
  WITH past AS (
    SELECT m.id, row_number() OVER (ORDER BY m.id) AS n FROM memories m
    JOIN places p ON p.id = m.place_id WHERE p.place_query = 'e2e yesterday'
  ), u AS (
    INSERT INTO unlocks (device_id, memory_id, unlocked_at)
      SELECT NEW.id, id, now() - n * interval '1 day' FROM past
  )
  INSERT INTO daily_routes (device_id, route_date, memory_ids)
    SELECT NEW.id, (now() - n * interval '1 day')::date, ARRAY[id] FROM past;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER yesterday AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION yesterday();
-- F15's reread taps a linked name and gets its Wikipedia preview in the card.
-- Each seed stop's WORDS (e2e/travel.py) is the link, so stop 1 has one.
UPDATE memories m
  SET links = jsonb_build_array(jsonb_build_object(
    'text', w, 'url', 'https://en.wikipedia.org/wiki/Copenhagen'))
  FROM (VALUES ('filed this one myself'), ('Lygteå'), ('swam to the other side'),
               ('jukebox on shuffle'), ('mortared it in')) v(w)
  WHERE m.summary LIKE '%' || w || '%';
