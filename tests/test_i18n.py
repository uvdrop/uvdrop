"""i18n helpers."""

from __future__ import annotations

import re

import pytest

from uvdrop.i18n import _STRINGS, SUPPORTED, detect_os_language, set_language, t

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def test_t_switches_language() -> None:
    set_language("en")
    assert "folder" in t("app.open_folder").lower() or "Open" in t("app.open_folder")
    set_language("zh")
    assert "打开" in t("app.open_folder") or "ZIP" in t("app.open_zip")
    set_language("ja")
    assert "フォルダ" in t("app.open_folder")


def test_detect_os_language_returns_supported() -> None:
    assert detect_os_language() in {"ja", "en", "zh"}


def test_every_key_has_all_languages() -> None:
    """Safety-critical UI must never fall back to another language silently."""
    langs = set(SUPPORTED)
    missing: list[str] = []
    for key, entry in _STRINGS.items():
        for lang in langs:
            if not entry.get(lang, "").strip():
                missing.append(f"{key}:{lang}")
    assert not missing, f"missing/empty translations: {missing}"


def _placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(text))


def test_placeholders_match_across_languages() -> None:
    """`t(key, **kwargs)` must accept the same fields in every language."""
    mismatched: list[str] = []
    for key, entry in _STRINGS.items():
        ja_fields = _placeholders(entry.get("ja", ""))
        for lang in ("en", "zh"):
            if _placeholders(entry.get(lang, "")) != ja_fields:
                mismatched.append(f"{key}:{lang}")
    assert not mismatched, f"placeholder mismatch: {mismatched}"


@pytest.mark.parametrize("lang", ["ja", "en", "zh"])
def test_unknown_key_returns_key(lang: str) -> None:
    set_language(lang)
    assert t("does.not.exist") == "does.not.exist"
    set_language("ja")


def test_t_accepts_key_as_format_kwarg() -> None:
    """Regression: format field named `key` must not collide with t()'s first arg."""
    set_language("ja")
    text = t("delete.confirm", key="demo-app")
    assert "demo-app" in text
    assert "delete.confirm" not in text
    done = t("delete.done", key="demo-app")
    assert "demo-app" in done
    set_language("ja")
