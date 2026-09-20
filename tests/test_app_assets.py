"""App icon constraints.

Apple rejects an app icon that carries an alpha channel, and it is an easy
thing to reintroduce by exporting from a design tool. Parsing the PNG header
directly avoids a Pillow dependency for a 26-byte check.
"""

import pathlib
import struct

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "mobile" / "assets"

pytestmark = pytest.mark.skipif(not ASSETS.exists(), reason="mobile app not scaffolded yet")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# PNG colour types that carry alpha directly.
COLOR_TYPES_WITH_ALPHA = {4, 6}


def png_info(path: pathlib.Path):
    """(width, height, has_alpha) from the IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE, f"{path.name} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    # A palette image can still be transparent via a tRNS chunk.
    has_alpha = color_type in COLOR_TYPES_WITH_ALPHA or b"tRNS" in data[:2048]
    return width, height, has_alpha


def test_ios_icon_has_no_alpha_channel():
    """The App Store rejects icons with transparency outright."""
    _, _, has_alpha = png_info(ASSETS / "icon.png")
    assert not has_alpha, "icon.png has an alpha channel - App Store will reject it"


def test_ios_icon_is_1024_square():
    width, height, _ = png_info(ASSETS / "icon.png")
    assert (width, height) == (1024, 1024)


def test_adaptive_icon_foreground_exists():
    """Android's adaptive icon foreground SHOULD be transparent - it is composited
    over the background layer, so no alpha assertion here."""
    width, height, _ = png_info(ASSETS / "android-icon-foreground.png")
    assert width == height >= 432, "adaptive icon foreground should be a large square"
