"""Resolve the full dependency set with uv before any install.

Uses `uv lock --no-build` (no packages are installed, and no package build
backend is executed just to read metadata) and reads `uv.lock`.
If locking fails (offline, sdist that needs building, bad metadata, …),
callers fall back to the declared top-level list and surface that as an
unresolved warning. When the allow list is in *block* mode, callers refuse
to launch rather than install an unverified transitive tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from uvdrop.tomlcompat import loads as toml_loads
from uvdrop.uv_tool import run_uv


@dataclass(frozen=True)
class ResolvedPackage:
    name: str
    version: str

    @property
    def label(self) -> str:
        return f"{self.name}=={self.version}" if self.version else self.name


def parse_uv_lock(text: str) -> list[ResolvedPackage]:
    """Parse package name/version pairs from a uv.lock document."""
    data = toml_loads(text)
    out: list[ResolvedPackage] = []
    seen: set[str] = set()
    for item in data.get("package") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower().replace("_", "-")
        version = str(item.get("version") or "").strip()
        if not name or name in seen:
            continue
        # Skip the project itself when marked as such
        if item.get("source") == {"editable": "."} or item.get("source") == {"virtual": "."}:
            continue
        source = item.get("source")
        if isinstance(source, dict) and (
            source.get("editable") in {".", "./"} or source.get("virtual") in {".", "./"}
        ):
            continue
        seen.add(name)
        out.append(ResolvedPackage(name=name, version=version))
    out.sort(key=lambda p: p.name)
    return out


def lock_and_list(
    project_dir: Path,
    *,
    venv_dir: Path | None = None,
    no_build: bool = True,
) -> list[ResolvedPackage]:
    """Run `uv lock` and return every third-party package that would be installed.

    This runs *before* the user has approved the app, so by default it passes
    ``--no-build``: uv resolves from cached / pre-built wheel metadata and never
    executes a package's build backend (which would be arbitrary code) just to
    read metadata. Packages that would require building fall back to the
    declared-only check, which callers surface to the user.

    Raises RuntimeError when uv cannot produce a lock file.
    """
    env: dict[str, str] = {}
    if venv_dir is not None:
        env["UV_PROJECT_ENVIRONMENT"] = str(venv_dir)
    args = ["lock", "--directory", str(project_dir)]
    if no_build:
        args.append("--no-build")
    proc = run_uv(args, env=env or None, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"uv lock failed ({proc.returncode}): {detail}")

    lock_path = project_dir / "uv.lock"
    if not lock_path.is_file():
        raise RuntimeError("uv lock succeeded but uv.lock was not created")
    return parse_uv_lock(lock_path.read_text(encoding="utf-8"))


def try_resolve_packages(
    project_dir: Path,
    *,
    venv_dir: Path | None = None,
    no_build: bool = True,
) -> tuple[list[ResolvedPackage] | None, str | None]:
    """Best-effort resolve. Returns (packages, error_note).

    Uses ``--no-build`` by default so no build backend runs before the user
    confirms the launch.
    """
    try:
        return lock_and_list(project_dir, venv_dir=venv_dir, no_build=no_build), None
    except Exception as e:  # noqa: BLE001 — surfaced to the user as a note
        return None, str(e)
