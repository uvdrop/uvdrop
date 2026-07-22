"""Remove app workspace / venv / dotenv / registry entry."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from uvdrop.paths import dotenv_dir, envs_dir
from uvdrop.registry import load_registry, remove


def cleanup_app(key: str, *, remove_registry: bool = True) -> None:
    apps = load_registry()
    rec = apps.get(key)
    workspace = Path(rec.workspace) if rec else None
    if workspace and workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    venv = envs_dir() / key
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)
    dotenv = dotenv_dir() / key
    if dotenv.exists():
        shutil.rmtree(dotenv, ignore_errors=True)
    if remove_registry:
        remove(key)


def schedule_cleanup_after(proc, key: str) -> None:
    """Wait for process exit in a daemon thread, then delete temp artifacts."""
    import threading

    def _wait() -> None:
        try:
            proc.wait()
        except Exception:  # noqa: BLE001
            pass
        # brief settle for file locks on Windows
        time.sleep(1.0)
        cleanup_app(key, remove_registry=True)

    threading.Thread(target=_wait, daemon=True, name=f"uvdrop-cleanup-{key}").start()


def gc_stale_temp_apps() -> list[str]:
    """Remove registry temp apps whose workspace is missing or marked temp on startup."""
    removed: list[str] = []
    for key, rec in list(load_registry().items()):
        if rec.mode != "temp":
            continue
        # Temp entries should not survive a restart — clean them up.
        cleanup_app(key, remove_registry=True)
        removed.append(key)
    return removed
