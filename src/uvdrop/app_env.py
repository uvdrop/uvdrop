"""Per-app .env stored outside the project tree, copied in before run."""

from __future__ import annotations

import shutil
from pathlib import Path

from uvdrop.paths import dotenv_dir, ensure_layout


DEFAULT_ENV = """# uvdrop managed .env — edit freely; not stored inside the app folder by default
"""


def dotenv_store_path(app_key: str) -> Path:
    ensure_layout()
    d = dotenv_dir() / app_key
    d.mkdir(parents=True, exist_ok=True)
    return d / ".env"


def ensure_dotenv(app_key: str, workspace: Path, seed_from: Path | None = None) -> Path:
    """Ensure store .env exists, then copy into workspace root."""
    store = dotenv_store_path(app_key)
    if not store.is_file():
        if seed_from and seed_from.is_file():
            shutil.copy2(seed_from, store)
        else:
            workspace_env = workspace / ".env"
            if workspace_env.is_file():
                shutil.copy2(workspace_env, store)
            else:
                store.write_text(DEFAULT_ENV, encoding="utf-8")
    target = workspace / ".env"
    shutil.copy2(store, target)
    return store


def open_dotenv_in_notepad(app_key: str) -> None:
    import subprocess

    store = dotenv_store_path(app_key)
    if not store.is_file():
        store.write_text(DEFAULT_ENV, encoding="utf-8")
    subprocess.Popen(["notepad.exe", str(store)], shell=False)
