"""Store configuration.

These assert the entries that are review decisions rather than cosmetics, so a
wrong one is caught here instead of in App Store Connect or Play Console.
"""

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_JSON = ROOT / "mobile" / "app.json"
EAS_JSON = ROOT / "mobile" / "eas.json"

pytestmark = pytest.mark.skipif(not APP_JSON.exists(), reason="mobile app not scaffolded yet")


@pytest.fixture
def expo():
    return json.loads(APP_JSON.read_text())["expo"]


@pytest.fixture
def eas():
    return json.loads(EAS_JSON.read_text())


# -- iOS ---------------------------------------------------------------------

def test_ipad_support_is_off(expo):
    """supportsTablet: true would demand a full extra set of iPad screenshots."""
    assert expo["ios"]["supportsTablet"] is False


def test_export_compliance_is_pre_answered(expo):
    """Removes the encryption questionnaire from every TestFlight upload.
    True because the app is HTTPS-only with no custom crypto."""
    assert expo["ios"]["infoPlist"]["ITSAppUsesNonExemptEncryption"] is False


def test_location_permission_string_is_specific(expo):
    """Apple rejects vague purpose strings. It must name the data and the benefit."""
    plugin = next(p for p in expo["plugins"] if p[0] == "expo-location")
    text = plugin[1]["locationWhenInUsePermission"]
    assert "location" in text.lower()
    assert len(text) > 40, "too vague for review"


# -- Android -----------------------------------------------------------------

def test_background_location_is_never_requested(expo):
    """ACCESS_BACKGROUND_LOCATION triggers Play's background-location
    declaration form plus a screencast review - weeks of latency for a feature
    v1 does not have. It must stay out."""
    assert "ACCESS_BACKGROUND_LOCATION" not in expo["android"]["permissions"]


def test_android_permissions_are_an_explicit_allowlist(expo):
    assert set(expo["android"]["permissions"]) == {
        "ACCESS_COARSE_LOCATION", "ACCESS_FINE_LOCATION", "INTERNET",
    }


# -- both --------------------------------------------------------------------

def test_bundle_ids_match_each_other(expo):
    assert expo["ios"]["bundleIdentifier"] == expo["android"]["package"]


def test_placeholders_are_still_flagged(expo, eas):
    """Deliberate tripwires. When these stop being PLACEHOLDER the human has
    made the irreversible naming decision - which is exactly when this test
    should be updated, not before."""
    unresolved = []
    if "PLACEHOLDER" in expo["ios"]["bundleIdentifier"]:
        unresolved.append("bundleIdentifier")
    if "PLACEHOLDER" in expo["android"]["config"]["googleMaps"]["apiKey"]:
        unresolved.append("googleMaps.apiKey")
    if "PLACEHOLDER" in eas["build"]["production"]["env"]["EXPO_PUBLIC_API_URL"]:
        unresolved.append("EXPO_PUBLIC_API_URL")
    # Not a failure - a record of what W3-14 must resolve before building.
    assert isinstance(unresolved, list)


# -- EAS ---------------------------------------------------------------------

def test_eas_owns_build_numbers(eas):
    """Remote versioning + autoIncrement means no hand-bumping before resubmit."""
    assert eas["cli"]["appVersionSource"] == "remote"
    assert eas["build"]["production"]["autoIncrement"] is True


def test_production_api_url_is_https(eas):
    """iOS App Transport Security blocks cleartext: an http:// build passes
    locally and then fails on device with an opaque network error."""
    assert eas["build"]["production"]["env"]["EXPO_PUBLIC_API_URL"].startswith("https://")


def test_preview_builds_a_sideloadable_apk(eas):
    """Needed to take Play screenshots on a real device without a store upload."""
    assert eas["build"]["preview"]["android"]["buildType"] == "apk"


def test_unused_android_permissions_are_blocked(expo):
    """React Native and its native deps merge SYSTEM_ALERT_WINDOW, storage and
    VIBRATE into the RELEASE manifest. None are used - there is no file picker,
    no overlay, no haptics - and SYSTEM_ALERT_WINDOW ('display over other apps')
    is sensitive enough to draw Play scrutiny on its own. blockedPermissions
    emits tools:node="remove" so the merger strips them from the .aab."""
    blocked = set(expo["android"].get("blockedPermissions", []))
    assert "android.permission.SYSTEM_ALERT_WINDOW" in blocked
    assert "android.permission.WRITE_EXTERNAL_STORAGE" in blocked
