-- F31's history: whichever device turns up first walked the south end three
-- days ago (5 of 5) and gave up two days ago (2 of 5; the two it had already
-- earned). A device turns up on Accept, so the preview before it is planned
-- without this history.
CREATE FUNCTION past_walks() RETURNS trigger AS $$
DECLARE
  walked int[] := ARRAY(SELECT m.id FROM unnest(ARRAY['Sortedams Sø 4', 'Peblinge Sø 5',
      'Sankt Jørgens Sø 6', 'Sankt Jørgens Sø 7', 'Sankt Jørgens Sø 8']) WITH ORDINALITY n(name, i)
    JOIN places p ON p.name = n.name || ', dev seed' JOIN memories m ON m.place_id = p.id ORDER BY n.i);
  abandoned int[] := ARRAY(SELECT m.id FROM unnest(ARRAY['Peblinge Sø 5', 'Sortedams Sø 4',
      'Sortedams Sø 3', 'Sortedams Sø 2', 'Sortedams Sø 1']) WITH ORDINALITY n(name, i)
    JOIN places p ON p.name = n.name || ', dev seed' JOIN memories m ON m.place_id = p.id ORDER BY n.i);
BEGIN
  INSERT INTO unlocks (device_id, memory_id, unlocked_at)
    SELECT NEW.id, unnest(walked), now() - interval '3 days';
  INSERT INTO daily_routes (device_id, route_date, memory_ids, completed_at) VALUES
    (NEW.id, (now() - interval '3 days')::date, walked, now() - interval '3 days'),
    (NEW.id, (now() - interval '2 days')::date, abandoned, NULL);
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER past_walks AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION past_walks();
