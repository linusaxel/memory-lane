#!/usr/bin/env bash
# Lock everything again for the booted simulator's user: their rows in
# `unlocks` (every device on the account) and the app's own copy in
# AsyncStorage, which the map merges in and never drops (src/unlocked.ts).
# Other local state - the device id in the keychain, hearts, seen - stays.
set -euo pipefail
cd "$(dirname "$0")/../.."

BUNDLE=com.PLACEHOLDER.memorylane
xcrun simctl terminate booted "$BUNDLE" 2>/dev/null || true

docker compose exec -T db psql -U memorylane -v ON_ERROR_STOP=1 -tAc "
  WITH me AS (SELECT id, user_id FROM devices ORDER BY last_seen DESC NULLS LAST LIMIT 1)
  DELETE FROM unlocks WHERE device_id IN (
    SELECT d.id FROM devices d, me
    WHERE d.id = me.id OR (me.user_id IS NOT NULL AND d.user_id = me.user_id)
  )" | sed 's/^/db: /'

STORE="$(xcrun simctl get_app_container booted "$BUNDLE" data)/Library/Application Support/$BUNDLE/RCTAsyncLocalStorage_V1"
python3 - "$STORE" <<'EOF'
import hashlib, json, pathlib, sys
store = pathlib.Path(sys.argv[1])
manifest = store / "manifest.json"
if not manifest.exists():
    sys.exit(print("device: nothing stored yet"))
keys = json.loads(manifest.read_text())
gone = [k for k in keys if k.startswith("memorylane.unlocked.")]
for k in gone:
    del keys[k]
    (store / hashlib.md5(k.encode()).hexdigest()).unlink(missing_ok=True)
manifest.write_text(json.dumps(keys))
print(f"device: dropped {len(gone)} keys")
EOF

xcrun simctl launch booted "$BUNDLE" >/dev/null
