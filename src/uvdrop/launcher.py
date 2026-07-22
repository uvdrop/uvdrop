"""Prepare workspace and launch via uv."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from uvdrop.app_env import ensure_dotenv
from uvdrop.cleanup import schedule_cleanup_after
from uvdrop.paths import apps_dir, envs_dir, ensure_layout, slugify
from uvdrop.policy import PolicyReport, evaluate_policies
from uvdrop.project import find_pyproject, requires_python, resolve_entry
from uvdrop.registry import AppRecord, remove, touch_run, upsert
from uvdrop.uv_tool import run_detached, sync_project


@dataclass
class LaunchResult:
    app_key: str
    workspace: Path
    project_dir: Path
    policy: PolicyReport
    pid: int | None = None
    mode: str = "keep"


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git", ".mypy_cache", ".ruff_cache"),
    )


def _extract_zip(zip_path: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    children = [p for p in dest.iterdir() if p.name not in (".noraops-artifact-ok",)]
    if len(children) == 1 and children[0].is_dir():
        inner = children[0]
        tmp = dest.parent / f".{dest.name}_flatten"
        if tmp.exists():
            shutil.rmtree(tmp)
        inner.rename(tmp)
        shutil.rmtree(dest)
        tmp.rename(dest)


def prepare_workspace(source: Path, *, app_key: str | None = None) -> tuple[str, Path, str]:
    """Return (key, workspace, source_kind)."""
    ensure_layout()
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    if source.is_file() and source.suffix.lower() == ".zip":
        key = app_key or slugify(source.stem)
        workspace = apps_dir() / key
        _extract_zip(source, workspace)
        return key, workspace, "zip"

    if source.is_dir():
        key = app_key or slugify(source.name)
        workspace = apps_dir() / key
        _copy_tree(source, workspace)
        return key, workspace, "folder"

    raise ValueError(f"Unsupported source: {source}")


def launch_source(
    source: Path,
    *,
    keep: bool = True,
    app_key: str | None = None,
    sync: bool = True,
    run: bool = True,
) -> LaunchResult:
    key, workspace, kind = prepare_workspace(source, app_key=app_key)
    pyproject = find_pyproject(workspace)
    if not pyproject:
        raise FileNotFoundError(f"pyproject.toml not found under {workspace}")
    project_dir = pyproject.parent
    req = requires_python(project_dir)
    policy = evaluate_policies(pyproject, req)
    if policy.blocking:
        raise RuntimeError("Policy blocked launch:\n" + "\n".join(policy.errors))

    ensure_dotenv(key, workspace)
    venv_dir = envs_dir() / key
    if sync:
        sync_project(project_dir, venv_dir)

    mode = "keep" if keep else "temp"
    pid = None
    if run:
        entry = resolve_entry(workspace, project_dir)
        proc = run_detached(project_dir, venv_dir, entry, waitable=not keep)
        pid = proc.pid
        if not keep:
            # Register briefly so UI can show it, then schedule wipe after exit.
            upsert(
                AppRecord(
                    key=key,
                    name=workspace.name,
                    source_kind=kind,
                    source_path=str(source.resolve()),
                    workspace=str(workspace),
                    mode=mode,
                )
            )
            schedule_cleanup_after(proc, key)
        else:
            upsert(
                AppRecord(
                    key=key,
                    name=workspace.name,
                    source_kind=kind,
                    source_path=str(source.resolve()),
                    workspace=str(workspace),
                    mode=mode,
                )
            )
            touch_run(key)
    elif keep:
        upsert(
            AppRecord(
                key=key,
                name=workspace.name,
                source_kind=kind,
                source_path=str(source.resolve()),
                workspace=str(workspace),
                mode=mode,
            )
        )
    else:
        remove(key)

    return LaunchResult(
        app_key=key,
        workspace=workspace,
        project_dir=project_dir,
        policy=policy,
        pid=pid,
        mode=mode,
    )


def relaunch_kept(key: str, *, sync: bool = True) -> LaunchResult:
    from uvdrop.registry import load_registry

    apps = load_registry()
    if key not in apps:
        raise KeyError(key)
    rec = apps[key]
    workspace = Path(rec.workspace)
    if not workspace.is_dir():
        raise FileNotFoundError(workspace)
    pyproject = find_pyproject(workspace)
    if not pyproject:
        raise FileNotFoundError(f"pyproject.toml not found under {workspace}")
    project_dir = pyproject.parent
    req = requires_python(project_dir)
    policy = evaluate_policies(pyproject, req)
    if policy.blocking:
        raise RuntimeError("Policy blocked launch:\n" + "\n".join(policy.errors))
    ensure_dotenv(key, workspace)
    venv_dir = envs_dir() / key
    if sync:
        sync_project(project_dir, venv_dir)
    entry = resolve_entry(workspace, project_dir)
    proc = run_detached(project_dir, venv_dir, entry, waitable=False)
    touch_run(key)
    return LaunchResult(
        app_key=key,
        workspace=workspace,
        project_dir=project_dir,
        policy=policy,
        pid=proc.pid,
        mode=rec.mode,
    )
