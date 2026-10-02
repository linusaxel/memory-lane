-- An account with nothing to spend that then pays, with no store. Every
-- account the app mints has used its welcome unlock (the flow mints it by
-- typing a name, since reading the profile creates nothing), and the one
-- renamed "Paid" is given a month.
CREATE FUNCTION broke() RETURNS trigger AS $$ BEGIN
  NEW.free_used := 1;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER broke BEFORE INSERT ON users FOR EACH ROW EXECUTE FUNCTION broke();
CREATE FUNCTION subscriber() RETURNS trigger AS $$ BEGIN
  INSERT INTO subscriptions (user_id, expires_at) VALUES (NEW.id, now() + interval '30 days')
    ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER subscriber AFTER UPDATE OF display_name ON users
  FOR EACH ROW WHEN (NEW.display_name = 'Paid') EXECUTE FUNCTION subscriber();
