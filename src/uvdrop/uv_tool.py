"""Locate and invoke uv."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from uvdrop.paths import bundled_uv


class UvNotFoundError(RuntimeError):
    pass


def resolve_uv() -> Path:
    bundled = bundled_uv()
    if bundled:
        return bundled
    which = shutil.which("uv") or shutil.which("uv.exe")
    if which:
        return Path(which)
    raise UvNotFoundError(
        "uv.exe not found. Place it under resources/tools/windows-x64/uv.exe "
        "or add uv to PATH."
    )


def run_uv(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    uv = resolve_uv()
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [str(uv), *args],
        cwd=str(cwd) if cwd else None,
        env=full_env,
        check=check,
        text=True,
        capture_output=True,
    )


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
) -> subprocess.Popen[bytes]:
    """Start app via uv run.

    waitable=True keeps a handle suitable for proc.wait() (temp-run cleanup).
    waitable=False fully detaches on Windows (kept apps).
    """
    uv = resolve_uv()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(venv_dir)
    creationflags = 0
    if os.name == "nt":
        if waitable:
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
            )
    cmd = [str(uv), "run", "--directory", str(project_dir), "python", *python_args]
    return subprocess.Popen(
        cmd,
        cwd=str(project_dir),
        env=env,
        creationflags=creationflags,
        close_fds=not waitable,
    )
