"""Local / remote policy: package allowlist + Python versions + optional OSV."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from uvdrop.paths import ensure_layout, policies_dir, project_root


@dataclass
class PolicyHit:
    kind: str  # package | python | osv
    message: str
    blocking: bool


@dataclass
class PolicyReport:
    hits: list[PolicyHit] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return any(h.blocking for h in self.hits)

    @property
    def warnings(self) -> list[str]:
        return [h.message for h in self.hits if not h.blocking]

    @property
    def errors(self) -> list[str]:
        return [h.message for h in self.hits if h.blocking]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_policy_file(name: str) -> Path | None:
    ensure_layout()
    candidates = [
        policies_dir() / name,
        project_root() / "policies" / name,
        project_root() / "policies" / name.replace(".json", ".example.json"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _dep_names_from_pyproject(pyproject: Path) -> set[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    names: set[str] = set()
    project = data.get("project") or {}
    for item in project.get("dependencies") or []:
        names.add(_normalize_req(str(item)))
    optional = project.get("optional-dependencies") or {}
    for group in optional.values():
        for item in group:
            names.add(_normalize_req(str(item)))
    for group in (data.get("dependency-groups") or {}).values():
        if isinstance(group, list):
            for item in group:
                if isinstance(item, str):
                    names.add(_normalize_req(item))
    return {n for n in names if n}


def _normalize_req(req: str) -> str:
    req = req.strip()
    if req.startswith("-"):
        return ""
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", req)
    return (m.group(1) if m else req).lower().replace("_", "-")


def _merged_allowlist() -> tuple[set[str], str] | None:
    """Merge local allowlist.json with optional xlsx-derived cache.

    Returns (allowed_packages, mode) or None if no allowlist configured.
    """
    local = resolve_policy_file("allowlist.json")
    xlsx_cache = policies_dir() / "allowlist.from-xlsx.json"

    allowed: set[str] = set()
    mode = "warn"
    found = False

    for path in (local, xlsx_cache if xlsx_cache.is_file() else None):
        if path is None or not path.is_file():
            continue
        # skip example-only if it is the example path under repo and AppData copy exists
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        pkgs = data.get("packages") or []
        if not pkgs and path.name.endswith(".example.json"):
            continue
        found = True
        allowed |= {str(x).lower().replace("_", "-") for x in pkgs}
        mode = str(data.get("mode") or mode).lower()

    if not found:
        return None
    return allowed, mode


def check_allowlist(pyproject: Path) -> list[PolicyHit]:
    try:
        from uvdrop.xlsx_policy import sync_xlsx_allowlist

        sync_xlsx_allowlist(force=False)
    except Exception as e:  # noqa: BLE001 — soft-fail into policy hit
        return [PolicyHit("package", f"xlsx allowlist sync failed: {e}", False)]

    merged = _merged_allowlist()
    if merged is None:
        return []
    allowed, mode = merged
    blocking = mode == "block"
    deps = _dep_names_from_pyproject(pyproject)
    return [
        PolicyHit("package", f"Package not in allowlist: {name}", blocking)
        for name in sorted(deps - allowed)
    ]


def _python_major_minor(requires: str | None, pinned: str | None) -> str | None:
    if pinned:
        m = re.search(r"(\d+\.\d+)", pinned)
        return m.group(1) if m else pinned
    if not requires:
        return None
    m = re.search(r"(\d+\.\d+)", requires)
    return m.group(1) if m else None


def check_python_versions(requires_python: str | None, pinned: str | None = None) -> list[PolicyHit]:
    path = resolve_policy_file("python-versions.json")
    if path is None:
        return []
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError) as e:
        return [PolicyHit("python", f"python-versions read error: {e}", True)]

    allowed = [str(x) for x in (data.get("allowed") or [])]
    mode = (data.get("mode") or "warn").lower()
    blocking = mode == "block"
    ver = _python_major_minor(requires_python, pinned)
    if not ver:
        return []
    ok = any(ver == a or ver.startswith(a + ".") or a.startswith(ver) for a in allowed)
    if ok:
        return []
    return [
        PolicyHit(
            "python",
            f"Python {ver} not in allowed list {allowed}",
            blocking,
        )
    ]


def evaluate_policies(pyproject: Path, requires_python: str | None) -> PolicyReport:
    hits: list[PolicyHit] = []
    hits.extend(check_python_versions(requires_python))
    hits.extend(check_allowlist(pyproject))
    try:
        from uvdrop.osv_check import check_osv

        hits.extend(check_osv(pyproject))
    except Exception as e:  # noqa: BLE001
        hits.append(PolicyHit("osv", f"OSV check error: {e}", False))
    return PolicyReport(hits=hits)
