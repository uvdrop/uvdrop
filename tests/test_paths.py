"""Minimal tests for path/policy helpers (no uv required)."""

from __future__ import annotations

from pathlib import Path

from uvdrop.paths import slugify
from uvdrop.project import find_pyproject


def test_slugify() -> None:
    assert slugify("Hello World") == "hello_world"
    assert slugify("  Foo/Bar  ") == "foo_bar"


def test_find_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    assert find_pyproject(tmp_path) == tmp_path / "pyproject.toml"


def test_find_pyproject_nested(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    assert find_pyproject(tmp_path) == app / "pyproject.toml"
