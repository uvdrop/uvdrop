"""Locate and invoke uv."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from uvdrop.i18n import t
from uvdrop.paths import bundled_uv
from uvdrop.settings import load_settings, proxy_environ


class UvNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class UvInfo:
    path: Path
    source: str  # bundled | path
    version: str


def resolve_uv() -> Path:
    return resolve_uv_info().path


def resolve_uv_info() -> UvInfo:
    bundled = bundled_uv()
    if bundled:
        return UvInfo(path=bundled, source="bundled", version=_uv_version(bundled))
    which = shutil.which("uv") or shutil.which("uv.exe")
    if which:
        p = Path(which)
        return UvInfo(path=p, source="path", version=_uv_version(p))
    raise UvNotFoundError(t("uv.not_found"))


def _uv_version(uv: Path) -> str:
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        proc = subprocess.run(
            [str(uv), "--version"],
            check=False,
            text=True,
            capture_output=True,
            timeout=15,
            creationflags=flags,
        )
        line = (proc.stdout or proc.stderr or "").strip().splitlines()
        return line[0] if line else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _base_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    full = os.environ.copy()
    full.update(proxy_environ(load_settings()))
    if extra:
        full.update(extra)
    return full


def run_uv(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    uv = resolve_uv()
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.run(
        [str(uv), *args],
        cwd=str(cwd) if cwd else None,
        env=_base_env(env),
        check=check,
        text=True,
        capture_output=True,
        creationflags=flags,
    )


def probe_python_version(python_exe: Path) -> str | None:
    """Return e.g. ``3.12.10`` for an interpreter, or None on failure."""
    if not python_exe.is_file():
        return None
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    try:
        proc = subprocess.run(
            [str(python_exe), "-c", "import sys; print(sys.version.split()[0])"],
            check=False,
            text=True,
            capture_output=True,
            timeout=20,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    line = (proc.stdout or "").strip().splitlines()
    return line[0] if line else None


def find_project_python(
    project_dir: Path,
    *,
    venv_dir: Path | None = None,
) -> tuple[str | None, str | None]:
    """Best-effort Python path and version for UI display.

    Prefers an existing project venv, otherwise ``uv python find``.
    Returns ``(path, version)``; either may be None.
    """
    if venv_dir is not None:
        candidates = [
            venv_dir / "Scripts" / "python.exe",
            venv_dir / "bin" / "python",
            venv_dir / "bin" / "python3",
        ]
        for exe in candidates:
            ver = probe_python_version(exe)
            if ver:
                return str(exe), ver

    proc = run_uv(
        ["python", "find", "--directory", str(project_dir)],
        cwd=project_dir,
        check=False,
    )
    if proc.returncode == 0:
        path = (proc.stdout or "").strip().splitlines()
        if path:
            exe = Path(path[0].strip())
            return str(exe), probe_python_version(exe)
    return None, None


def sync_project(project_dir: Path, venv_dir: Path, *, python: str | None = None) -> None:
    env = {"UV_PROJECT_ENVIRONMENT": str(venv_dir)}
    args = ["sync", "--directory", str(project_dir)]
    if python:
        args.extend(["--python", python])
    proc = run_uv(args, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"uv sync failed ({proc.returncode}):\n{proc.stderr or proc.stdout}"
        )


def run_detached(
    project_dir: Path,
    venv_dir: Path,
    python_args: list[str],
    *,
    waitable: bool = False,
    show_console: bool | None = None,
) -> subprocess.Popen[bytes]:
    """Start app via uv run.

    waitable=True keeps a handle suitable for proc.wait() (temp-run cleanup).
    waitable=False fully detaches on Windows (kept apps).

    show_console=None reads settings.guard.show_console.
    False (default): hide the black console window.
    True: open a new console so stdout/stderr are visible for debugging.
    """
    if show_console is None:
        show_console = bool(load_settings().guard.show_console)

    uv = resolve_uv()
    env = _base_env({"UV_PROJECT_ENVIRONMENT": str(venv_dir)})
    creationflags = 0
    if os.name == "nt":
        if show_console:
            # Dedicated console so print() / logs are visible
            creationflags = (
                subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            )
        elif waitable:
            creationflags = (
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            )
        else:
            creationflags = (
                subprocess.CREATE_NO_WINDOW
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            )
    cmd = [str(uv), "run", "--directory", str(project_dir), "python", *python_args]
    return subprocess.Popen(
        cmd,
        cwd=str(project_dir),
        env=env,
        creationflags=creationflags,
        close_fds=not waitable and not show_console,
    )
