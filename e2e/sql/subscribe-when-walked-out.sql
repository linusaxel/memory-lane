-- An account that already walked today, then pays, with no store. Whichever
-- device turns up first (the flow's rename mints it) gets an ended walk today, so the planner is walked
-- out; the account renamed "Paid" is given a month.
CREATE FUNCTION walked() RETURNS trigger AS $$ BEGIN
  INSERT INTO daily_routes (device_id, route_date, memory_ids, ended_at)
    SELECT NEW.id, (now() AT TIME ZONE 'utc')::date, ARRAY[m.id], now()
    FROM memories m LIMIT 1;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER walked AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION walked();
CREATE FUNCTION subscriber() RETURNS trigger AS $$ BEGIN
  INSERT INTO subscriptions (user_id, expires_at) VALUES (NEW.id, now() + interval '30 days')
    ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER subscriber AFTER UPDATE OF display_name ON users
  FOR EACH ROW WHEN (NEW.display_name = 'Paid') EXECUTE FUNCTION subscriber();
