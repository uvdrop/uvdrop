"""Local / remote policy: package allow/block lists + Python versions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from uvdrop.i18n import t
from uvdrop.package_spec import (
    DeclaredDep,
    PackageRule,
    match_uncertainty,
    parse_declared_dep,
    rule_allows,
    rule_blocks,
    rules_from_dicts,
    validate_rule,
)
from uvdrop.paths import ensure_layout, policies_dir, project_root
from uvdrop.tomlcompat import loads as toml_loads


@dataclass
class PolicyHit:
    kind: str  # package | python | block
    message: str
    blocking: bool


@dataclass
class PolicyReport:
    hits: list[PolicyHit] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # display labels
    unlisted: list[str] = field(default_factory=list)  # names outside allowlist
    unresolved: list[str] = field(default_factory=list)  # rules/versions we cannot judge
    allowlist_active: bool = False
    resolved_tree: bool = False  # True when dependencies came from uv.lock

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
    """Resolve an active policy file. Examples (*.example.json) are never used."""
    ensure_layout()
    candidates = [
        policies_dir() / name,
        project_root() / "policies" / name,
    ]
    for p in candidates:
        if p.is_file() and not p.name.endswith(".example.json"):
            return p
    return None


def _deps_from_pyproject(pyproject: Path) -> list[DeclaredDep]:
    data = toml_loads(pyproject.read_text(encoding="utf-8"))
    items: list[str] = []
    project = data.get("project") or {}
    for item in project.get("dependencies") or []:
        items.append(str(item))
    optional = project.get("optional-dependencies") or {}
    for group in optional.values():
        for item in group:
            items.append(str(item))
    for group in (data.get("dependency-groups") or {}).values():
        if isinstance(group, list):
            for item in group:
                if isinstance(item, str):
                    items.append(item)
    out: list[DeclaredDep] = []
    seen: set[str] = set()
    for raw in items:
        dep = parse_declared_dep(raw)
        if dep is None or dep.name in seen:
            continue
        seen.add(dep.name)
        out.append(dep)
    return out


def _dep_label(dep: DeclaredDep) -> str:
    if dep.version:
        return f"{dep.name}=={dep.version}"
    if dep.has_constraint:
        # keep short raw after name
        return dep.raw.strip()
    return dep.name


def _rules_from_file(path: Path) -> tuple[list[PackageRule], str]:
    data = _load_json(path)
    mode = str(data.get("mode") or "warn").lower()
    pkgs = data.get("packages") or []
    # New shape: list of {name, version}; old shape: list of strings
    return rules_from_dicts(pkgs), mode


def _merged_allow_rules() -> tuple[list[PackageRule], str] | None:
    from uvdrop.settings import load_settings

    local = resolve_policy_file("allowlist.json")
    file_cache = policies_dir() / "allowlist.from-file.json"
    # legacy cache name
    xlsx_cache = policies_dir() / "allowlist.from-xlsx.json"

    by_name: dict[str, PackageRule] = {}
    mode = "warn"
    found = False

    for path in (local, file_cache if file_cache.is_file() else None, xlsx_cache if xlsx_cache.is_file() else None):
        if path is None or not path.is_file():
            continue
        try:
            rules, file_mode = _rules_from_file(path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not rules:
            continue
        found = True
        mode = file_mode or mode
        for rule in rules:
            by_name[rule.name] = rule

    s = load_settings()
    if s.allowlist.enabled:
        found = True
        mode = str(s.allowlist.mode or mode).lower()
        for rule in s.allowlist.packages:
            n = rule.normalized()
            if n.name:
                by_name[n.name] = n

    if not found:
        return None
    return list(by_name.values()), mode


def _block_rules() -> list[PackageRule]:
    from uvdrop.settings import load_settings

    s = load_settings()
    if not s.blocklist.enabled:
        return []
    return [r.normalized() for r in s.blocklist.packages if r.normalized().name]


@dataclass
class AllowlistOutcome:
    hits: list[PolicyHit] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    unlisted: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    active: bool = False
    resolved_tree: bool = False  # True when deps came from uv.lock
    mode: str = "warn"  # allowlist mode: warn | block


def check_allowlist(
    pyproject: Path,
    *,
    deps: list[DeclaredDep] | None = None,
    resolved_tree: bool = False,
) -> AllowlistOutcome:
    """Compare dependencies against allow + block lists.

    When `deps` is omitted, only the top-level declarations in pyproject.toml
    are used. Callers that already ran `uv lock` should pass the full resolved
    set so transitive packages are checked too.
    """
    if deps is None:
        deps = _deps_from_pyproject(pyproject)
        resolved_tree = False
    labels = [_dep_label(d) for d in deps]
    try:
        from uvdrop.xlsx_policy import sync_file_allowlist

        sync_file_allowlist(force=False)
    except Exception as e:  # noqa: BLE001
        return AllowlistOutcome(
            hits=[PolicyHit("package", t("pol.file_fetch_fail", e=e), False)],
            dependencies=labels,
            resolved_tree=resolved_tree,
        )

    hits: list[PolicyHit] = []
    notes: list[str] = []
    unresolved: list[str] = []

    if resolved_tree:
        notes.append(t("pol.resolved_note", n=len(deps)))
    else:
        notes.append(t("pol.declared_note"))

    # NG list always wins
    blocked_names: set[str] = set()
    for dep in deps:
        for rule in _block_rules():
            note = match_uncertainty(rule, dep)
            if note:
                entry = t("pol.unresolved_ng", note=note)
                if entry not in unresolved:
                    unresolved.append(entry)
            if rule_blocks(rule, dep):
                if rule.version not in {"*", ""}:
                    msg = t("pol.block_hit_rule", name=dep.name, rule=rule.version)
                else:
                    msg = t("pol.block_hit", name=dep.name)
                hits.append(PolicyHit("block", msg, True))
                blocked_names.add(dep.name)
                break

    merged = _merged_allow_rules()
    if merged is None:
        if not hits:
            notes.append(t("pol.no_allowlist_note"))
        return AllowlistOutcome(
            hits=hits,
            notes=notes,
            dependencies=labels,
            unlisted=[d.name for d in deps if d.name not in blocked_names],
            unresolved=unresolved,
            active=bool(hits),
            resolved_tree=resolved_tree,
        )

    allowed_rules, mode = merged
    by_name = {r.name: r for r in allowed_rules}
    blocking = mode == "block"
    unlisted: list[str] = []
    notes.append(t("pol.allow_count_note", n=len(allowed_rules), mode=mode))

    for rule in allowed_rules:
        check = validate_rule(rule.version)
        if not check.ok:
            unresolved.append(
                t(
                    "pol.unresolved_allow_rule",
                    name=rule.name,
                    rule=rule.version,
                    msg=check.message,
                )
            )

    for dep in deps:
        if dep.name in blocked_names:
            continue
        rule = by_name.get(dep.name)
        if rule is None:
            unlisted.append(dep.name)
            hits.append(PolicyHit("package", t("pol.not_listed", name=dep.name), blocking))
            continue
        note = match_uncertainty(rule, dep)
        if note:
            entry = t("pol.unresolved_allow", note=note)
            if entry not in unresolved:
                unresolved.append(entry)
        ok, allow_note = rule_allows(rule, dep)
        if not ok:
            unlisted.append(dep.name)
            hits.append(
                PolicyHit("package", allow_note or t("pol.version_out", name=dep.name), blocking)
            )
        elif allow_note:
            notes.append(allow_note)

    if deps and not unlisted and not blocked_names:
        notes.append(t("pol.all_allowed"))

    return AllowlistOutcome(
        hits=hits,
        notes=notes,
        dependencies=labels,
        unlisted=unlisted,
        unresolved=unresolved,
        active=True,
        resolved_tree=resolved_tree,
        mode=mode,
    )


def _python_major_minor(requires: str | None, pinned: str | None) -> str | None:
    if pinned:
        m = re.search(r"(\d+\.\d+)", pinned)
        return m.group(1) if m else pinned
    if not requires:
        return None
    m = re.search(r"(\d+\.\d+)", requires)
    return m.group(1) if m else None


def check_python_versions(requires_python: str | None, pinned: str | None = None) -> list[PolicyHit]:
    from uvdrop.python_support import check_python_support, merge_eol_map, warn_days_from_policy

    path = resolve_policy_file("python-versions.json")
    data: dict = {}
    if path is not None:
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError) as e:
            return [PolicyHit("python", f"python-versions read error: {e}", True)]

    hits: list[PolicyHit] = []
    ver = _python_major_minor(requires_python, pinned)

    # Allow-list (optional when file missing / empty allowed)
    allowed = [str(x) for x in (data.get("allowed") or [])]
    if allowed and ver:
        mode = (data.get("mode") or "warn").lower()
        blocking = mode == "block"
        ok = any(ver == a or ver.startswith(a + ".") or a.startswith(ver) for a in allowed)
        if not ok:
            hits.append(
                PolicyHit(
                    "python",
                    f"Python {ver} not in allowed list {allowed}",
                    blocking,
                )
            )

    # Support window (EOL / within warn_days) — warn by default, never blocks unless eol_mode=block
    if ver:
        eol_raw = data.get("eol") if isinstance(data.get("eol"), dict) else None
        eol_map = merge_eol_map(eol_raw)
        warn_days = warn_days_from_policy(data)
        eol_mode = str(data.get("eol_mode") or "warn").lower()
        eol_blocking = eol_mode == "block"
        for hit in check_python_support(ver, eol_map=eol_map, warn_days=warn_days):
            # nearing_eol never blocks; eol may block when eol_mode=block
            blocking = bool(eol_blocking and hit.kind == "eol")
            hits.append(PolicyHit("python_support", hit.message, blocking))

    return hits


def evaluate_policies(
    pyproject: Path,
    requires_python: str | None,
    *,
    project_dir: Path | None = None,
    venv_dir: Path | None = None,
    resolve: bool = True,
) -> PolicyReport:
    """Run Python-version + package policies.

    When `resolve` is True (default), `uv lock` is attempted first so the
    allow/block lists cover the full install set, not just top-level names.
    """
    hits: list[PolicyHit] = []
    notes: list[str] = []
    hits.extend(check_python_versions(requires_python))

    resolved_deps: list[DeclaredDep] | None = None
    unresolved_extra: list[str] = []
    resolve_attempted = resolve
    if resolve:
        from uvdrop.resolve_deps import try_resolve_packages

        packages, err = try_resolve_packages(
            project_dir or pyproject.parent,
            venv_dir=venv_dir,
        )
        if packages is not None:
            resolved_deps = [
                DeclaredDep(
                    name=p.name,
                    raw=p.label,
                    version=p.version or None,
                    has_constraint=bool(p.version),
                )
                for p in packages
            ]
        elif err:
            unresolved_extra.append(t("pol.resolve_failed", err=err))

    outcome = check_allowlist(
        pyproject,
        deps=resolved_deps,
        resolved_tree=resolved_deps is not None,
    )
    hits.extend(outcome.hits)
    notes.extend(outcome.notes)
    unresolved = list(outcome.unresolved)
    unresolved.extend(unresolved_extra)

    # Conservative stance: when the allow list blocks anything not listed, we
    # must see the *full* install set. If resolution was attempted but failed,
    # transitive packages are unknown — refuse instead of installing blind.
    if (
        resolve_attempted
        and resolved_deps is None
        and outcome.active
        and outcome.mode == "block"
    ):
        hits.append(PolicyHit("block", t("pol.block_needs_resolve"), True))

    return PolicyReport(
        hits=hits,
        notes=notes,
        dependencies=outcome.dependencies,
        unlisted=outcome.unlisted,
        unresolved=unresolved,
        allowlist_active=outcome.active,
        resolved_tree=outcome.resolved_tree,
    )


def needs_launch_confirm(policy: PolicyReport) -> bool:
    """Whether the GUI must show the pre-run confirmation dialog.

    Safe defaults:
      - confirm_before_run=True → always confirm
      - allowlist inactive + no_allowlist=confirm → confirm
      - any warning / unresolved notation → confirm
      - otherwise (clean allowlist, confirm_before_run off) → skip
    """
    from uvdrop.settings import load_settings

    guard = load_settings().guard
    if guard.confirm_before_run:
        return True
    if not policy.allowlist_active and guard.no_allowlist == "confirm":
        return True
    if policy.warnings or policy.unresolved:
        return True
    return False
