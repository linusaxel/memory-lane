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


def test_ios_declares_always_location_only_for_the_proximity_notification(expo):
    """The iOS half of "location is foreground-only" - true until the
    proximity notification (docs/10-decisions.md#a-streak-and-a-proximity-notification-after-all)
    needed background location on purpose.

    Found on the first native build, before that feature existed: `app.json`
    set only the when-in-use string, but expo-location's config plugin injects
    NSLocationAlwaysAndWhenInUseUsageDescription, NSLocationAlwaysUsageDescription
    and NSMotionUsageDescription with its own boilerplate unless each is
    explicitly `false`. The built Info.plist therefore declared always-on
    location and motion for an app that asked for neither, in copy that read
    "Allow MemoryLane to access your location". `false` deletes a key outright;
    see applyPermissions in @expo/config-plugins.

    Now one of those three is a real, specific purpose string - the other two
    stay false: the pre-iOS11 NSLocationAlwaysUsageDescription key is not
    needed for an app that only supports iOS 13+, and there is still no
    motion feature. A declared purpose string is what App Store review reads
    as intent, so this pair - the deprecated key staying false, and the real
    one being specific - is what keeps this honest, same as
    ACCESS_BACKGROUND_LOCATION being an explicit, single line on Android
    rather than a side effect of some other permission.

    Asserted on app.json rather than the generated plist because ios/ is a
    gitignored prebuild artifact and is not there on a fresh clone.
    """
    options = next(
        entry[1]
        for entry in expo["plugins"]
        if isinstance(entry, list) and entry[0] == "expo-location"
    )
    always = options["locationAlwaysAndWhenInUsePermission"]
    assert always is not False
    assert len(always) > 40, "too vague for review"
    assert options["locationAlwaysPermission"] is False
    assert options["motionUsagePermission"] is False
    assert options["locationWhenInUsePermission"].startswith("Memory Lane")
    assert options["isAndroidBackgroundLocationEnabled"] is True
    # expo-location's startGeofencingAsync throws without UIBackgroundModes
    # location; mobile/UI.md rule 2 has how that went unnoticed.
    assert options["isIosBackgroundLocationEnabled"] is True


def test_ios_declares_no_background_mode_but_location(expo):
    """App Review rejects a background mode the app never uses (2.5.4).
    expo-audio declares `audio` unless told not to, and expo-task-manager
    declares `fetch` for any app linking it; a recording only plays on screen,
    and geofencing needs `location` alone. `npx expo config --type introspect`
    shows the result, but only in a copy without `ios/`: it starts from the
    Info.plist already there, so it never shows a mode going away."""
    audio = next(p for p in expo["plugins"] if isinstance(p, list) and p[0] == "expo-audio")
    assert audio[1]["enableBackgroundPlayback"] is False
    assert "./plugins/withoutBackgroundFetch" in expo["plugins"]


# -- Android -----------------------------------------------------------------


def test_background_location_is_requested_only_for_the_proximity_notification(expo):
    """ACCESS_BACKGROUND_LOCATION triggers Play's background-location
    declaration form plus a screencast review - weeks of latency, budgeted for
    in docs/10-decisions.md#a-streak-and-a-proximity-notification-after-all because the proximity
    notification cannot work without it. Explicit in the allowlist rather than
    left as a side effect of the expo-location plugin option above, so the two
    say the same thing."""
    assert "ACCESS_BACKGROUND_LOCATION" in expo["android"]["permissions"]


def test_android_permissions_are_an_explicit_allowlist(expo):
    assert set(expo["android"]["permissions"]) == {
        "ACCESS_COARSE_LOCATION",
        "ACCESS_FINE_LOCATION",
        "ACCESS_BACKGROUND_LOCATION",
        "INTERNET",
    }


# -- both --------------------------------------------------------------------


def test_bundle_ids_match_each_other(expo):
    assert expo["ios"]["bundleIdentifier"] == expo["android"]["package"]


@pytest.mark.xfail(
    strict=True,
    reason="W3-14: bundle id, Maps key and prod URL are still PLACEHOLDER. "
    "strict=True means this test goes RED the moment they are resolved, which "
    "is the point - that is when the naming decision became irreversible and "
    "this test must be updated.",
)
def test_placeholders_are_still_flagged(expo, eas):
    """A tripwire that cannot trip is decoration.

    The previous version ended in `assert isinstance(unresolved, list)`, which
    is true whatever happens. Now it asserts what it means - nothing is left
    unresolved - and xfail(strict) carries the fact that today it is not."""
    unresolved = []
    if "PLACEHOLDER" in expo["ios"]["bundleIdentifier"]:
        unresolved.append("bundleIdentifier")
    if "PLACEHOLDER" in expo["android"]["config"]["googleMaps"]["apiKey"]:
        unresolved.append("googleMaps.apiKey")
    if "PLACEHOLDER" in eas["build"]["production"]["env"]["EXPO_PUBLIC_API_URL"]:
        unresolved.append("EXPO_PUBLIC_API_URL")
    assert unresolved == [], f"still PLACEHOLDER: {', '.join(unresolved)}"


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
