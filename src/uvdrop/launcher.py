"""Prepare workspace and launch via uv."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from uvdrop.app_env import ensure_dotenv
from uvdrop.cleanup import schedule_cleanup_after
from uvdrop.i18n import t
from uvdrop.paths import apps_dir, envs_dir, ensure_layout, slugify
from uvdrop.policy import PolicyReport, evaluate_policies
from uvdrop.project import (
    entry_candidates,
    find_pyproject,
    format_entry,
    parse_entry,
    requires_python,
)
from uvdrop.registry import AppRecord, load_registry, remove, touch_run, upsert
from uvdrop.uv_tool import run_detached, sync_project


@dataclass
class PreparedLaunch:
    app_key: str
    workspace: Path
    project_dir: Path
    pyproject: Path
    source: Path
    source_kind: str
    policy: PolicyReport
    venv_dir: Path
    converted_from: Path | None = None
    conversion_skipped: list[str] = field(default_factory=list)
    entry_command: str = ""
    entry_options: list[str] = field(default_factory=list)


@dataclass
class LaunchResult:
    app_key: str
    workspace: Path
    project_dir: Path
    policy: PolicyReport
    pid: int | None = None
    mode: str = "keep"
    venv_dir: Path | None = None


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
        _safe_extractall(zf, dest)
    children = [p for p in dest.iterdir() if not p.name.startswith(".")]
    if len(children) == 1 and children[0].is_dir():
        inner = children[0]
        tmp = dest.parent / f".{dest.name}_flatten"
        if tmp.exists():
            shutil.rmtree(tmp)
        inner.rename(tmp)
        shutil.rmtree(dest)
        tmp.rename(dest)


def _safe_extractall(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract ZIP members, rejecting path traversal (Zip Slip)."""
    dest = dest.resolve()
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if not name or name.endswith("/"):
            # Directory entries are created as needed by file members
            target = (dest / name).resolve()
            if dest != target and dest not in target.parents:
                raise ValueError(t("launch.zip_bad_path", name=info.filename))
            target.mkdir(parents=True, exist_ok=True)
            continue
        if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/":
            # Fast reject for obvious traversal; still verify with resolve()
            pass
        target = (dest / name).resolve()
        if dest != target and dest not in target.parents:
            raise ValueError(t("launch.zip_bad_path", name=info.filename))
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)


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


def _resolve_or_convert_project(workspace: Path) -> tuple[Path, Path | None, list[str]]:
    """Return (pyproject, converted_from, skipped_lines)."""
    pyproject = find_pyproject(workspace)
    if pyproject:
        return pyproject, None, []

    from uvdrop.requirements_convert import convert_to_pyproject, find_requirements
    from uvdrop.settings import load_settings

    if not load_settings().guard.allow_requirements_txt:
        raise FileNotFoundError(f"pyproject.toml not found under {workspace}")

    requirements = find_requirements(workspace)
    if not requirements:
        raise FileNotFoundError(t("launch.no_project", workspace=workspace))
    result = convert_to_pyproject(requirements)
    return result.pyproject, requirements, result.skipped


def prepare_launch(
    source: Path,
    *,
    app_key: str | None = None,
    preferred_command: str | None = None,
) -> PreparedLaunch:
    """Copy/extract + policy check (before venv sync).

    ``preferred_command`` (e.g. from a shared catalog) is pre-selected in the
    confirm dialog; launch guards still run unchanged.
    """
    key, workspace, kind = prepare_workspace(source, app_key=app_key)
    pyproject, converted_from, skipped = _resolve_or_convert_project(workspace)
    project_dir = pyproject.parent
    req = requires_python(project_dir)
    venv_dir = envs_dir() / key
    policy = evaluate_policies(
        pyproject, req, project_dir=project_dir, venv_dir=venv_dir
    )
    options = _entry_options(workspace, project_dir)
    preferred = (preferred_command or "").strip()
    if preferred and preferred not in options:
        options = [preferred, *options]
    entry = preferred or (options[0] if options else "")
    return PreparedLaunch(
        app_key=key,
        workspace=workspace,
        project_dir=project_dir,
        pyproject=pyproject,
        source=source.resolve(),
        source_kind=kind,
        policy=policy,
        venv_dir=venv_dir,
        converted_from=converted_from,
        conversion_skipped=skipped,
        entry_command=entry,
        entry_options=options,
    )


def _entry_options(workspace: Path, project_dir: Path) -> list[str]:
    """Editable command strings the user can pick from before launching."""
    return [
        format_entry(argv, project_dir, workspace)
        for argv in entry_candidates(workspace, project_dir)
    ]


def execute_launch(
    prep: PreparedLaunch,
    *,
    keep: bool = True,
    sync: bool = True,
    run: bool = True,
    entry_command: str | None = None,
    show_console: bool | None = None,
) -> LaunchResult:
    if prep.policy.blocking:
        raise RuntimeError("Policy blocked launch:\n" + "\n".join(prep.policy.errors))

    command = (entry_command if entry_command is not None else prep.entry_command).strip()
    if run and not command:
        raise FileNotFoundError(t("err.no_command"))

    ensure_dotenv(prep.app_key, prep.workspace)
    if sync:
        sync_project(prep.project_dir, prep.venv_dir)

    mode = "keep" if keep else "temp"

    def record() -> AppRecord:
        previous = load_registry().get(prep.app_key)
        rec = AppRecord(
            key=prep.app_key,
            name=prep.workspace.name,
            source_kind=prep.source_kind,
            source_path=str(prep.source),
            workspace=str(prep.workspace),
            mode=mode,
            entry_command=command,
            icon_path=previous.icon_path if previous else "",
        )
        if previous is not None:
            rec.created_at = previous.created_at
            rec.last_run_at = previous.last_run_at
            rec.run_count = previous.run_count
        return rec

    pid = None
    if run:
        entry = parse_entry(command, prep.project_dir, prep.workspace)
        proc = run_detached(
            prep.project_dir,
            prep.venv_dir,
            entry,
            waitable=not keep,
            show_console=show_console,
        )
        pid = proc.pid
        upsert(record())
        if not keep:
            schedule_cleanup_after(proc, prep.app_key)
        else:
            touch_run(prep.app_key)
    elif keep:
        upsert(record())
    else:
        remove(prep.app_key)

    return LaunchResult(
        app_key=prep.app_key,
        workspace=prep.workspace,
        project_dir=prep.project_dir,
        policy=prep.policy,
        pid=pid,
        mode=mode,
        venv_dir=prep.venv_dir,
    )


def launch_source(
    source: Path,
    *,
    keep: bool = True,
    app_key: str | None = None,
    sync: bool = True,
    run: bool = True,
) -> LaunchResult:
    prep = prepare_launch(source, app_key=app_key)
    return execute_launch(prep, keep=keep, sync=sync, run=run)


def prepare_relaunch(key: str) -> PreparedLaunch:
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
    venv_dir = envs_dir() / key
    policy = evaluate_policies(
        pyproject, req, project_dir=project_dir, venv_dir=venv_dir
    )
    options = _entry_options(workspace, project_dir)
    if rec.entry_command and rec.entry_command not in options:
        options.insert(0, rec.entry_command)
    return PreparedLaunch(
        app_key=key,
        workspace=workspace,
        project_dir=project_dir,
        pyproject=pyproject,
        source=Path(rec.source_path) if rec.source_path else workspace,
        source_kind=rec.source_kind,
        policy=policy,
        venv_dir=venv_dir,
        entry_command=rec.entry_command or (options[0] if options else ""),
        entry_options=options,
    )


def relaunch_kept(key: str, *, sync: bool = True) -> LaunchResult:
    prep = prepare_relaunch(key)
    return execute_launch(prep, keep=True, sync=sync, run=True)
