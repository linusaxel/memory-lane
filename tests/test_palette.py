"""The palette, held to two promises.

There is no build step between `mobile/src/theme.ts` and `api/card.py`, and
there should not be one for eleven hex values copied once. What there should be
is something that notices when the copy drifts, and something that notices when
a colour stops being readable. Both are cheaper as a test than as a convention.

The contrast numbers are the reason this file exists at all. `inkFaint` shipped
at 3.4:1 on paper for months - under AA, and it carries the 9-11px label voice.
It passed in the dark, which is exactly why nobody caught it: a light-mode-only
failure is invisible to anyone reviewing an app they use outdoors at night.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "mobile" / "src" / "theme.ts"
CARD = ROOT / "api" / "card.py"

# WCAG 2 AA for body text. Everything below is text on a ground.
AA = 4.5


def palette() -> dict[str, tuple[str, str]]:
    """`name: (light, dark)` straight out of theme.ts.

    A regex rather than codegen: theme.ts is the one file that owns these, the
    shape is `dual('#light', '#dark')`, and a parser would be more machinery
    than the thing it parses.
    """
    found = re.findall(
        r"^\s*(\w+): dual\('(#[0-9A-Fa-f]{6})', '(#[0-9A-Fa-f]{6})'\),",
        THEME.read_text(),
        re.M,
    )
    assert found, "theme.ts stopped matching - has dual() changed shape?"
    return {name: (light, dark) for name, light, dark in found}


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_the_regex_still_finds_the_whole_palette():
    """If theme.ts is restructured this file goes quiet rather than wrong, so
    the count is asserted before anything is measured against it."""
    assert set(palette()) >= {
        "paper",
        "paperRaised",
        "ink",
        "inkSoft",
        "inkFaint",
        "rule",
        "seal",
        "sealSoft",
        "sealDeep",
        "faded",
        "route",
    }


# Every pair is a real one: the token on the left is set as text, or as a mark
# that carries meaning, on the ground to its right. mobile/UI.md lists them.
TEXT_ON_GROUND = [
    ("ink", "paper"),
    ("ink", "paperRaised"),
    ("inkSoft", "paper"),
    ("inkFaint", "paper"),
    ("inkFaint", "paperRaised"),
    ("faded", "paper"),
    ("paper", "seal"),
    ("paper", "faded"),
    ("paper", "route"),
    ("sealDeep", "paper"),
    ("sealDeep", "sealSoft"),
]


@pytest.mark.parametrize("fg,bg", TEXT_ON_GROUND)
@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
def test_every_text_pair_is_readable_in_both_themes(fg, bg, theme):
    colours = palette()
    ratio = contrast(colours[fg][theme], colours[bg][theme])
    assert ratio >= AA, f"{fg} on {bg} is {ratio:.2f}:1, under {AA}:1"


# api/card.py hand-copies these. The card deliberately maps --muted to `faded`
# and not to `inkFaint`: it sets 12px in that colour, and inkFaint only just
# clears AA at all. docs/09-visual-design.md part 6 argues it.
CARD_VARIABLES = {
    "bg": "paper",
    "fg": "ink",
    "muted": "faded",
    "rule": "rule",
    "accent": "seal",
}


def card_variables() -> tuple[dict[str, str], dict[str, str]]:
    """The card's two `:root` blocks, light first."""
    blocks = re.findall(r":root\{([^}]*)\}", CARD.read_text())
    assert len(blocks) == 2, f"expected a light and a dark :root, found {len(blocks)}"
    return tuple(dict(re.findall(r"--(\w+):\s*(#[0-9A-Fa-f]{6})", block)) for block in blocks)


@pytest.mark.parametrize("variable,token", CARD_VARIABLES.items())
@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
def test_the_card_uses_the_apps_palette(variable, token, theme):
    """The one thing about this product that travels should not look like a
    different product. Nothing enforces that but this."""
    assert card_variables()[theme][variable] == palette()[token][theme].lower()
