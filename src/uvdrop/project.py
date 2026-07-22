"""Resolve pyproject.toml and entrypoint inside an app tree."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path


PREFERRED_SUBDIRS = ("app", "backend", "src", "packages", "python", "server")


def find_pyproject(root: Path) -> Path | None:
    root = root.resolve()
    manifest = root / "nora" / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            rel = (data.get("packagesProject") or "").strip()
            if rel:
                cand = (root / rel).resolve()
                if cand.name == "pyproject.toml" and cand.is_file():
                    return cand
                if (cand / "pyproject.toml").is_file():
                    return cand / "pyproject.toml"
        except (OSError, json.JSONDecodeError):
            pass

    direct = root / "pyproject.toml"
    if direct.is_file():
        return direct

    legacy = root / "nora" / "packages" / "pyproject.toml"
    if legacy.is_file():
        return legacy

    found: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        pp = child / "pyproject.toml"
        if pp.is_file():
            found.append(pp)
    if not found:
        return None
    for pref in PREFERRED_SUBDIRS:
        for pp in found:
            if pp.parent.name.lower() == pref:
                return pp
    return found[0]


def resolve_entry(root: Path, project_dir: Path) -> list[str]:
    """Return argv after `python` for `uv run --directory … python …`."""
    manifest = root / "nora" / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            entry = data.get("entry") or data.get("appEntry") or {}
            if isinstance(entry, str) and entry.strip():
                return ["-m", entry.strip()] if "." in entry and "/" not in entry and "\\" not in entry else [entry]
            if isinstance(entry, dict):
                if entry.get("module"):
                    return ["-m", str(entry["module"])]
                if entry.get("script"):
                    script = Path(str(entry["script"]))
                    if not script.is_absolute():
                        script = root / script
                    return [str(script)]
                if entry.get("file"):
                    f = Path(str(entry["file"]))
                    if not f.is_absolute():
                        f = root / f
                    return [str(f)]
        except (OSError, json.JSONDecodeError):
            pass

    # pyproject scripts: prefer [project.scripts] first key as module hint is hard;
    # fall back to common files.
    for rel in ("main.py", "app.py", "run.py", "src/main.py"):
        cand = project_dir / rel
        if cand.is_file():
            return [str(cand)]
        cand = root / rel
        if cand.is_file():
            return [str(cand)]

    pp = project_dir / "pyproject.toml"
    if pp.is_file():
        try:
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
            scripts = (data.get("project") or {}).get("scripts") or {}
            if scripts:
                # scripts map to "pkg.module:func" — run as module path before colon
                target = next(iter(scripts.values()))
                mod = str(target).split(":", 1)[0]
                if mod:
                    return ["-m", mod]
        except (OSError, tomllib.TOMLDecodeError):
            pass

    raise FileNotFoundError(
        f"No app entry found under {root}. Add nora/manifest.json entry or main.py."
    )


def requires_python(project_dir: Path) -> str | None:
    pp = project_dir / "pyproject.toml"
    if not pp.is_file():
        return None
    try:
        data = tomllib.loads(pp.read_text(encoding="utf-8"))
        return (data.get("project") or {}).get("requires-python")
    except (OSError, tomllib.TOMLDecodeError):
        return None
