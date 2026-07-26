"""ZIP slip protection, uv.lock parsing, and confirm-gate helpers."""

from __future__ import annotations

import io
import types
import zipfile
from pathlib import Path

import pytest

from uvdrop.launcher import _safe_extractall
from uvdrop.package_spec import PackageRule
from uvdrop.policy import PolicyReport, evaluate_policies, needs_launch_confirm
from uvdrop.resolve_deps import parse_uv_lock
from uvdrop.settings import Settings, save_settings


def test_parse_uv_lock_lists_third_party_only() -> None:
    text = """\
version = 1
revision = 1

[[package]]
name = "demo-app"
version = "0.1.0"
source = { virtual = "." }

[[package]]
name = "httpx"
version = "0.27.2"

[[package]]
name = "httpcore"
version = "1.0.5"

[[package]]
name = "idna"
version = "3.7"
"""
    pkgs = parse_uv_lock(text)
    names = [p.name for p in pkgs]
    assert names == ["httpcore", "httpx", "idna"]
    assert pkgs[1].label == "httpx==0.27.2"


def test_zip_slip_is_rejected(tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "nope")
        zf.writestr("ok/hello.txt", "yes")
    buf.seek(0)
    with zipfile.ZipFile(buf, "r") as zf:
        # message is localized, but the offending filename is always included
        with pytest.raises(ValueError, match="evil"):
            _safe_extractall(zf, dest)
    assert not (tmp_path / "evil.txt").exists()


def test_safe_zip_extracts_normally(tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("pkg/main.py", "print(1)\n")
    buf.seek(0)
    with zipfile.ZipFile(buf, "r") as zf:
        _safe_extractall(zf, dest)
    assert (dest / "pkg" / "main.py").is_file()


def test_needs_launch_confirm_respects_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout

    ensure_layout()
    clean = PolicyReport(allowlist_active=True, resolved_tree=True)

    s = Settings()
    s.guard.confirm_before_run = True
    s.guard.no_allowlist = "allow"
    save_settings(s)
    assert needs_launch_confirm(clean) is True

    s.guard.confirm_before_run = False
    save_settings(s)
    assert needs_launch_confirm(clean) is False

    inactive = PolicyReport(allowlist_active=False, resolved_tree=True)
    s.guard.no_allowlist = "confirm"
    save_settings(s)
    assert needs_launch_confirm(inactive) is True

    s.guard.no_allowlist = "allow"
    save_settings(s)
    assert needs_launch_confirm(inactive) is False

    warned = PolicyReport(allowlist_active=True, hits=[])
    # fabricate a non-blocking hit via notes/unresolved
    warned.unresolved.append("something odd")
    assert needs_launch_confirm(warned) is True


def test_lock_and_list_passes_no_build(monkeypatch, tmp_path) -> None:
    """Pre-confirmation resolution must never execute a build backend."""
    import uvdrop.resolve_deps as rd

    captured: dict[str, list[str]] = {}

    def fake_run_uv(args, *, env=None, check=True):
        captured["args"] = args
        (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(rd, "run_uv", fake_run_uv)
    rd.lock_and_list(tmp_path)
    assert "--no-build" in captured["args"]


def _write_pyproject(tmp_path: Path, deps: list[str]) -> Path:
    dep_list = ", ".join(f'"{d}"' for d in deps)
    py = tmp_path / "pyproject.toml"
    py.write_text(
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.0"\n'
        f"dependencies = [{dep_list}]\n",
        encoding="utf-8",
    )
    return py


def test_block_mode_refuses_when_tree_unresolved(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout

    ensure_layout()

    s = Settings()
    s.allowlist.enabled = True
    s.allowlist.mode = "block"
    # The one declared package IS allowed, so any block must come from the
    # "could not verify the full tree" rule, not from a per-package miss.
    s.allowlist.packages = [PackageRule(name="requests", version="*")]
    save_settings(s)

    py = _write_pyproject(tmp_path, ["requests"])

    # Simulate: full resolution failed (offline / sdist needs building).
    # evaluate_policies imports this lazily from resolve_deps at call time.
    import uvdrop.resolve_deps as rd

    monkeypatch.setattr(rd, "try_resolve_packages", lambda *a, **k: (None, "offline"))

    report = evaluate_policies(py, ">=3.11", project_dir=tmp_path, resolve=True)
    assert report.blocking is True
    assert not report.resolved_tree

    from uvdrop.i18n import t

    assert t("pol.block_needs_resolve") in report.errors


def test_block_mode_ok_when_resolved(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from uvdrop.paths import ensure_layout

    ensure_layout()

    s = Settings()
    s.allowlist.enabled = True
    s.allowlist.mode = "block"
    s.allowlist.packages = [PackageRule(name="requests", version="*")]
    save_settings(s)

    py = _write_pyproject(tmp_path, ["requests"])

    from uvdrop.resolve_deps import ResolvedPackage
    import uvdrop.resolve_deps as rd

    monkeypatch.setattr(
        rd,
        "try_resolve_packages",
        lambda *a, **k: ([ResolvedPackage(name="requests", version="2.32.0")], None),
    )

    report = evaluate_policies(py, ">=3.11", project_dir=tmp_path, resolve=True)
    assert report.resolved_tree is True
    assert report.blocking is False
