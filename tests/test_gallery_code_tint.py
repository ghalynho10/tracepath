"""The code tint of the gallery (spec 0012, Feature design "The code tint")."""

import re

import pytest

from tracepath.gallery.render import GRAPH_STYLE, PANEL_STYLE, STYLE

#: The four swipe colours of spec 0012 AC-49 to AC-52.
SWIPES = {"right": "#B9E3EE", "partly right": "#F6E27F", "wrong": "#FFC8C2", "declined": "#CBD3DC"}
PAPER = (255, 255, 255)


def _rules(style: str) -> dict[str, str]:
    """Each rule's selector and its body."""
    return {
        selector.strip(): body.strip()
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", style)
    }


def _tint() -> tuple[int, int, int]:
    """The `code` rule's background, laid over the white page."""
    found = re.search(r"background: rgba\((\d+), (\d+), (\d+), ([\d.]+)\)", _rules(STYLE)["code"])
    assert found is not None
    alpha = float(found[4])
    red, green, blue = (
        round(int(found[n]) * alpha + PAPER[n - 1] * (1 - alpha)) for n in (1, 2, 3)
    )
    return red, green, blue


def _hex(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def _luminance(colour: tuple[int, int, int]) -> float:
    """Relative luminance, as WCAG defines it."""
    channels = [c / 255 for c in colour]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def test_code_tint_is_on_the_code_element() -> None:
    """AC-106: the `code` rule has a background, and the word elements carry none."""
    rules = _rules(STYLE)

    assert "background: rgba(" in rules["code"]
    assert all("background" not in body for selector, body in rules.items() if ".w" in selector)


def test_code_tint_is_the_same_in_the_panel() -> None:
    """AC-107: the panel shares the page's `code` rule and adds no code style of its own."""
    for selector in _rules(GRAPH_STYLE + PANEL_STYLE):
        assert "code" not in selector


@pytest.mark.parametrize("swipe", SWIPES.values(), ids=SWIPES.keys())
def test_code_tint_is_no_swipe_colour(swipe: str) -> None:
    """AC-108."""
    assert _tint() != _hex(swipe)
    assert swipe.lower() not in _rules(STYLE)["code"].lower()


def test_code_tint_is_lighter_than_the_declined_swipe() -> None:
    """AC-109."""
    assert _luminance(_tint()) > _luminance(_hex(SWIPES["declined"]))
