"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from uvdrop.i18n import set_language


@pytest.fixture(autouse=True)
def _reset_language() -> None:
    """Keep tests isolated: the active UI language is global state.

    Default to Japanese (the project default) before each test so a test that
    switches language cannot leak that choice into unrelated tests.
    """
    set_language("ja")
