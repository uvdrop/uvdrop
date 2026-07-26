"""Resolve pyproject.toml and entrypoint inside an app tree."""

from __future__ import annotations

import shlex
from pathlib import Path

from uvdrop.i18n import t
from uvdrop.manifest import load_app_manifest
from uvdrop.tomlcompat import TOMLDecodeError, loads as toml_loads


PREFERRED_SUBDIRS = ("app", "backend", "src", "packages", "python", "server")

ENTRY_FILENAMES = ("main.py", "app.py", "run.py", "src/main.py", "src/app.py", "__main__.py")

PYTHON_TOKENS = {"python", "python.exe", "python3", "py", "uv", "run"}


def find_pyproject(root: Path) -> Path | None:
    root = root.resolve()
    data = load_app_manifest(root)
    rel = (data.get("packagesProject") or data.get("project") or "").strip()
    if rel:
        cand = (root / rel).resolve()
        if cand.name == "pyproject.toml" and cand.is_file():
            return cand
        if (cand / "pyproject.toml").is_file():
            return cand / "pyproject.toml"

    direct = root / "pyproject.toml"
    if direct.is_file():
        return direct

    # Legacy layout still supported, not advertised in UI
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


def _manifest_entry(root: Path) -> list[str] | None:
    data = load_app_manifest(root)
    entry = data.get("entry") or data.get("appEntry") or {}
    if isinstance(entry, str) and entry.strip():
        return (
            ["-m", entry.strip()]
            if "." in entry and "/" not in entry and "\\" not in entry
            else [entry]
        )
    if isinstance(entry, dict):
        if entry.get("module"):
            return ["-m", str(entry["module"])]
        for key in ("script", "file"):
            if entry.get(key):
                p = Path(str(entry[key]))
                if not p.is_absolute():
                    p = root / p
                return [str(p)]
    return None


def _script_entry(project_dir: Path) -> list[str] | None:
    pp = project_dir / "pyproject.toml"
    if not pp.is_file():
        return None
    try:
        pdata = toml_loads(pp.read_text(encoding="utf-8"))
    except (OSError, TOMLDecodeError):
        return None
    scripts = (pdata.get("project") or {}).get("scripts") or {}
    if not scripts:
        return None
    mod = str(next(iter(scripts.values()))).split(":", 1)[0]
    return ["-m", mod] if mod else None


def entry_candidates(root: Path, project_dir: Path) -> list[list[str]]:
    """Every plausible argv after `python`, best guess first."""
    found: list[list[str]] = []

    def add(argv: list[str] | None) -> None:
        if argv and argv not in found:
            found.append(argv)

    add(_manifest_entry(root))
    for rel in ENTRY_FILENAMES:
        for base in (project_dir, root):
            cand = base / rel
            if cand.is_file():
                add([str(cand)])
    add(_script_entry(project_dir))
    return found


def resolve_entry(root: Path, project_dir: Path) -> list[str]:
    """Return argv after `python` for `uv run --directory … python …`."""
    found = entry_candidates(root, project_dir)
    if found:
        return found[0]
    raise FileNotFoundError(t("project.no_entry", root=root))


def format_entry(argv: list[str], project_dir: Path, root: Path | None = None) -> str:
    """Render argv as an editable command string with short, relative paths."""
    bases = [project_dir] + ([root] if root and root != project_dir else [])
    parts: list[str] = []
    for token in argv:
        text = token
        p = Path(token)
        if p.is_absolute():
            for base in bases:
                try:
                    text = p.relative_to(base).as_posix()
                    break
                except ValueError:
                    continue
        parts.append(f'"{text}"' if " " in text else text)
    return " ".join(parts)


def parse_entry(command: str, project_dir: Path, root: Path | None = None) -> list[str]:
    """Turn a user-typed command back into argv after `python`.

    A leading `python` / `uv run python` is accepted and dropped. Relative paths
    stay relative because uv runs with the project directory as cwd; only files
    that live outside it are expanded.
    """
    tokens = shlex.split(command.replace("\\", "/"), posix=True)
    while tokens and tokens[0].lower().removesuffix(".exe") in PYTHON_TOKENS:
        tokens.pop(0)
    if not tokens:
        raise ValueError(t("project.empty_command"))

    out: list[str] = []
    for token in tokens:
        p = Path(token)
        if not p.is_absolute() and not token.startswith("-"):
            if (project_dir / token).is_file():
                out.append(token)
                continue
            if root is not None and (root / token).is_file():
                out.append(str((root / token).resolve()))
                continue
        out.append(token)
    return out


def requires_python(project_dir: Path) -> str | None:
    pp = project_dir / "pyproject.toml"
    if not pp.is_file():
        return None
    try:
        data = toml_loads(pp.read_text(encoding="utf-8"))
        return (data.get("project") or {}).get("requires-python")
    except (OSError, TOMLDecodeError):
        return None
