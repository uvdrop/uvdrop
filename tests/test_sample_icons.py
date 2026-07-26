"""Sample theme PNG rendering."""

from __future__ import annotations

from uvdrop.sample_icons import THEMES, render_theme_png


def test_eight_themes_are_defined() -> None:
    assert len(THEMES) == 8
    assert len({th.id for th in THEMES}) == 8


def test_each_theme_renders_png() -> None:
    for theme in THEMES:
        data = render_theme_png(theme.id, "#2f7d62", size=64)
        assert data.startswith(b"\x89PNG")
        assert len(data) > 100


def test_theme_scales_with_size() -> None:
    small = render_theme_png("rocket", "#3b6ea5", size=32)
    large = render_theme_png("rocket", "#3b6ea5", size=128)
    assert small.startswith(b"\x89PNG")
    assert large.startswith(b"\x89PNG")
    assert len(large) > len(small)


def test_two_tone_changes_rendered_image() -> None:
    white_glyph = render_theme_png("bolt", "#3b6ea5", "#ffffff", size=64)
    amber_glyph = render_theme_png("bolt", "#3b6ea5", "#ffcc33", size=64)
    assert white_glyph != amber_glyph
