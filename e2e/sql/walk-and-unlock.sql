-- F15's reread taps a linked name and gets its Wikipedia preview in the card.
-- Each seed stop's WORDS (e2e/travel.py) is the link, so stop 1 has one.
UPDATE memories m
  SET links = jsonb_build_array(jsonb_build_object(
    'text', w, 'url', 'https://en.wikipedia.org/wiki/Copenhagen'))
  FROM (VALUES ('filed this one myself'), ('Lygteå'), ('swam to the other side'),
               ('jukebox on shuffle'), ('mortared it in')) v(w)
  WHERE m.summary LIKE '%' || w || '%';
-- F35: the account renamed "Paid" is given a month, with no store.
CREATE FUNCTION subscriber() RETURNS trigger AS $$ BEGIN
  INSERT INTO subscriptions (user_id, expires_at) VALUES (NEW.id, now() + interval '30 days')
    ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER subscriber AFTER UPDATE OF display_name ON users
  FOR EACH ROW WHEN (NEW.display_name = 'Paid') EXECUTE FUNCTION subscriber();
