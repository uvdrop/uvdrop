"""Shared catalog JSON — source of truth, no folder scanning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uvdrop.catalog import (
    CatalogApp,
    check_app_path,
    load_all_catalogs,
    load_catalog_file,
    parse_catalog_dict,
)
from uvdrop.i18n import set_language
from uvdrop.settings import CatalogRef, Settings, load_settings, save_settings


SAMPLE = {
    "version": 1,
    "catalog": "Team A",
    "apps": [
        {
            "id": "report",
            "name": "Report",
            "summary": "Makes a PDF",
            "path": "apps/report",
            "command": "main.py --quiet",
        },
        {"name": "Bad", "path": ""},
    ],
}


def test_parse_catalog_skips_incomplete_entries() -> None:
    set_language("en")
    result = parse_catalog_dict(SAMPLE, catalog_path=r"C:\share\uvdrop-catalog.json")
    assert len(result.apps) == 1
    assert result.apps[0].name == "Report"
    assert result.apps[0].command == "main.py --quiet"
    assert result.apps[0].app_key_hint == "report"
    assert result.title == "Team A"
    assert result.errors  # incomplete Bad entry


def test_relative_path_resolves_against_catalog_dir(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "report"
    app_dir.mkdir(parents=True)
    (app_dir / "main.py").write_text("print(1)\n", encoding="utf-8")
    cat = tmp_path / "uvdrop-catalog.json"
    cat.write_text(
        json.dumps(
            {
                "catalog": "Local",
                "apps": [{"name": "Report", "path": "apps/report", "command": "main.py"}],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_catalog_file(cat)
    assert len(loaded.apps) == 1
    resolved = check_app_path(loaded.apps[0])
    assert resolved == app_dir.resolve()


def test_missing_path_raises(tmp_path: Path) -> None:
    set_language("en")
    app = CatalogApp(
        name="Gone",
        path="nope",
        catalog_path=str(tmp_path / "catalog.json"),
    )
    with pytest.raises(FileNotFoundError):
        check_app_path(app)


def test_zip_path_is_accepted(tmp_path: Path) -> None:
    z = tmp_path / "app.zip"
    z.write_bytes(b"PK\x03\x04")  # existence only; prepare_launch validates later
    app = CatalogApp(name="Z", path=str(z), catalog_path=str(tmp_path / "c.json"))
    assert check_app_path(app) == z.resolve()


def test_load_all_merges_enabled_catalogs(tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(
        json.dumps({"catalog": "A", "apps": [{"name": "One", "path": "x"}]}),
        encoding="utf-8",
    )
    b.write_text(
        json.dumps({"catalog": "B", "apps": [{"name": "Two", "path": "y"}]}),
        encoding="utf-8",
    )
    merged = load_all_catalogs([str(a), str(b), str(tmp_path / "missing.json")])
    assert [x.name for x in merged.apps] == ["One", "Two"]
    assert merged.errors  # missing file


def test_catalogs_persist_in_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    s = Settings()
    s.catalogs = [
        CatalogRef(path=r"\\srv\share\uvdrop-catalog.json", enabled=True),
        CatalogRef(path="C:/other/catalog.json", enabled=False),
    ]
    save_settings(s)
    loaded = load_settings()
    assert len(loaded.catalogs) == 2
    assert loaded.catalogs[0].path.endswith("uvdrop-catalog.json")
    assert loaded.catalogs[1].enabled is False
