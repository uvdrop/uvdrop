"""AppData / resource path helpers."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


APP_NAME = "uvdrop"


def local_app_data() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base)
    return Path.home() / "AppData" / "Local"


def app_root() -> Path:
    return local_app_data() / APP_NAME


def apps_dir() -> Path:
    return app_root() / "apps"


def envs_dir() -> Path:
    return app_root() / "envs"


def dotenv_dir() -> Path:
    return app_root() / "dotenv"


def policies_dir() -> Path:
    return app_root() / "policies"


def launchers_dir() -> Path:
    return app_root() / "launchers"


def registry_path() -> Path:
    return app_root() / "apps.json"


def usage_path() -> Path:
    return app_root() / "usage.json"


def ensure_layout() -> None:
    for d in (apps_dir(), envs_dir(), dotenv_dir(), policies_dir(), launchers_dir()):
        d.mkdir(parents=True, exist_ok=True)
    _seed_policy_examples()


# Stock packages from policies/allowlist.example.json — used to detect untouched seeds.
_STOCK_ALLOWLIST_PACKAGES = frozenset({"requests", "httpx", "pydantic", "rich", "typer"})


def _seed_policy_examples() -> None:
    """Copy example policies into AppData as examples only (not auto-enforced)."""
    examples = project_root() / "policies"
    if not examples.is_dir():
        return
    # allowlist: never auto-activate. python-versions: still seed as active default.
    mapping = {
        "allowlist.example.json": "allowlist.example.json",
        "python-versions.example.json": "python-versions.json",
    }
    for src_name, dest_name in mapping.items():
        src = examples / src_name
        dest = policies_dir() / dest_name
        if src.is_file() and not dest.is_file():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    _retire_stock_allowlist_seed()


def _retire_stock_allowlist_seed() -> None:
    """Disable first-run allowlist.json that was copied from the example (pre-0.3.6).

    That seed silently allowed httpx/requests/… so manual allowlist tests looked broken.
    """
    import json

    active = policies_dir() / "allowlist.json"
    if not active.is_file():
        return
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    pkgs = {str(x).lower().replace("_", "-") for x in (data.get("packages") or [])}
    notes = str(data.get("notes") or "")
    stock = pkgs == set(_STOCK_ALLOWLIST_PACKAGES) or "Copy to %LOCALAPPDATA%" in notes
    if not stock:
        return
    example = policies_dir() / "allowlist.example.json"
    if not example.is_file():
        try:
            active.replace(example)
        except OSError:
            return
    else:
        try:
            active.unlink()
        except OSError:
            return


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._-")
    return s or "app"


def package_root() -> Path:
    """Source package root (…/src/uvdrop)."""
    return Path(__file__).resolve().parent


def project_root() -> Path:
    """Repo root when running from source; otherwise install/bundle root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/uvdrop -> src -> repo
    return package_root().parent.parent


def bundled_uv() -> Path | None:
    root = project_root()
    candidates = [
        root / "tools" / "uv.exe",  # installed (Inno) layout
        root / "resources" / "tools" / "windows-x64" / "uv.exe",
        root / "resources" / "tools" / "uv.exe",
        root / "uv.exe",
    ]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / "uv.exe")
            candidates.insert(0, Path(meipass) / "tools" / "uv.exe")
        # onedir: exe sits next to _internal/; tools/ is sibling of exe
        candidates.insert(0, root / "tools" / "uv.exe")
    for p in candidates:
        if p.is_file():
            return p
    return None
