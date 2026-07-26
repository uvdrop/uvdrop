"""Remove app workspace / venv / dotenv / registry entry."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from uvdrop.paths import dotenv_dir, envs_dir
from uvdrop.registry import load_registry, remove


def _tree_size(path: Path) -> int:
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def hibernate_venv(key: str) -> int:
    """Remove only an app's venv and return the approximate reclaimed bytes.

    The workspace, dotenv, registry record, shortcut, and uv global cache stay.
    A later launch recreates the venv through the normal guarded ``uv sync``.
    """
    venv = envs_dir() / key
    if not venv.exists():
        return 0
    reclaimed = _tree_size(venv)
    shutil.rmtree(venv)
    return reclaimed


def gc_inactive_venvs(inactive_days: int, *, now: float | None = None) -> list[str]:
    """Hibernate kept-app venvs not launched within ``inactive_days``.

    This function does not decide whether automatic GC is enabled. Callers must
    check the opt-in setting before invoking it.
    """
    cutoff = (time.time() if now is None else now) - max(1, int(inactive_days)) * 86400
    hibernated: list[str] = []
    for key, rec in load_registry().items():
        if rec.mode != "keep":
            continue
        last_used = rec.last_run_at or rec.created_at
        if last_used >= cutoff or not (envs_dir() / key).exists():
            continue
        try:
            hibernate_venv(key)
        except OSError:
            # A running app may still hold files on Windows. Retry next startup.
            continue
        hibernated.append(key)
    return hibernated


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
