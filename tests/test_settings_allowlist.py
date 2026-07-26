"""Tests for settings helpers."""

from __future__ import annotations

from uvdrop.package_spec import PackageRule
from uvdrop.paths import app_root
from uvdrop.settings import Settings, load_settings, parse_package_list, save_settings


def test_parse_package_list() -> None:
    assert parse_package_list("requests, httpx; pydantic  rich") == [
        "requests",
        "httpx",
        "pydantic",
        "rich",
    ]
    assert parse_package_list("Requests==2.0, HTTPX") == ["requests", "httpx"]


def test_allowlist_persists(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    s = Settings()
    s.allowlist.enabled = True
    s.allowlist.packages = [PackageRule("requests", "2.*"), PackageRule("httpx", "*")]
    s.allowlist.mode = "block"
    s.blocklist.enabled = True
    s.blocklist.packages = [PackageRule("evil", "*")]
    save_settings(s)
    loaded = load_settings()
    assert loaded.allowlist.enabled is True
    assert [(r.name, r.version) for r in loaded.allowlist.packages] == [
        ("requests", "2.*"),
        ("httpx", "*"),
    ]
    assert loaded.allowlist.mode == "block"
    assert loaded.blocklist.enabled is True
    assert loaded.blocklist.packages[0].name == "evil"
    assert (app_root() / "settings.json").is_file()


def test_legacy_comma_packages_migrate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout

    ensure_layout()
    path = app_root() / "settings.json"
    path.write_text(
        '{"version":1,"allowlist":{"enabled":true,"packages":"requests, httpx","mode":"warn"},'
        '"xlsx":{},"proxy":{},"guard":{}}\n',
        encoding="utf-8",
    )
    loaded = load_settings()
    assert [r.name for r in loaded.allowlist.packages] == ["requests", "httpx"]
