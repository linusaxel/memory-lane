#!/usr/bin/env bash
# Show a new native splash on the booted simulator. iOS keeps a snapshot of
# the launch screen in the app's container, and it outlives a rebuild, a
# reinstall and a reboot; deleting it is the only thing that works.
set -euo pipefail

BUNDLE=com.PLACEHOLDER.memorylane
xcrun simctl terminate booted "$BUNDLE" 2>/dev/null || true
rm -rf "$(xcrun simctl get_app_container booted "$BUNDLE" data)/Library/SplashBoard"
echo "splash snapshot cleared; the next launch draws the bundle's own"
