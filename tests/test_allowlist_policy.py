"""Allowlist merge / seed retirement / version-aware rules."""

from __future__ import annotations

import json

from uvdrop.package_spec import PackageRule
from uvdrop.paths import ensure_layout, policies_dir
from uvdrop.policy import _merged_allow_rules, check_allowlist, evaluate_policies
from uvdrop.settings import Settings, save_settings


def _write_app(root, deps: str) -> None:
    root.mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text(
        f"""
[project]
name = "{root.name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [{deps}]
""",
        encoding="utf-8",
    )


def test_stock_allowlist_seed_is_retired(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    pol = tmp_path / "uvdrop" / "policies"
    pol.mkdir(parents=True)
    stock = {
        "version": 1,
        "mode": "warn",
        "packages": ["requests", "httpx", "pydantic", "rich", "typer"],
        "notes": "Copy to %LOCALAPPDATA%\\uvdrop\\policies\\allowlist.json",
    }
    (pol / "allowlist.json").write_text(json.dumps(stock), encoding="utf-8")

    ensure_layout()
    assert not (policies_dir() / "allowlist.json").is_file()
    assert (policies_dir() / "allowlist.example.json").is_file()
    assert _merged_allow_rules() is None


def test_manual_only_allowlist_flags_other_deps(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ensure_layout()
    s = Settings()
    s.allowlist.enabled = True
    s.allowlist.packages = [PackageRule("requests", "*")]
    s.allowlist.mode = "warn"
    save_settings(s)

    app = tmp_path / "hello-httpx"
    _write_app(app, '"httpx>=0.27"')
    outcome = check_allowlist(app / "pyproject.toml")
    assert outcome.active
    assert outcome.unlisted == ["httpx"]
    assert any("httpx" in h.message for h in outcome.hits)


def test_manual_httpx_allows_sample2(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ensure_layout()
    s = Settings()
    s.allowlist.enabled = True
    s.allowlist.packages = [PackageRule("httpx", "0.*")]
    save_settings(s)

    app = tmp_path / "hello-httpx"
    _write_app(app, '"httpx>=0.27"')
    report = evaluate_policies(app / "pyproject.toml", ">=3.11", resolve=False)
    assert not any(h.kind == "package" for h in report.hits)
    assert report.allowlist_active


def test_blocklist_always_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ensure_layout()
    s = Settings()
    s.blocklist.enabled = True
    s.blocklist.packages = [PackageRule("httpx", "*")]
    save_settings(s)

    app = tmp_path / "hello-httpx"
    _write_app(app, '"httpx>=0.27"')
    report = evaluate_policies(app / "pyproject.toml", ">=3.11", resolve=False)
    assert report.blocking
    assert any(h.kind == "block" for h in report.hits)


def test_report_lists_deps_when_no_allowlist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    ensure_layout()
    app = tmp_path / "plain-app"
    _write_app(app, '"httpx>=0.27", "rich"')
    report = evaluate_policies(app / "pyproject.toml", ">=3.11", resolve=False)
    assert not report.allowlist_active
    assert "httpx>=0.27" in report.dependencies or any("httpx" in d for d in report.dependencies)
    assert not report.blocking
