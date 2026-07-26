"""Package name + version rule matching for allow / block lists.

Supported version rules (column B style):
  * or empty     … any version
  1.2.3          … exact
  1.* / 1.*.*    … major 1 (any minor/patch)
  1.2.*          … major.minor fixed
  >=1.0          … comparison operators (>= > <= < == !=)
  >=1.0,<2       … comma-separated AND of comparisons

Against a project's declared requirement:
  httpx==0.27.2  … exact pin is checked against the rule
  httpx>=0.27    … open range → name match only (noted)
  httpx          … no pin → name match only

Version numbers are whatever the package publisher uploaded to PyPI, so some
notations (rc / post / dev / local / epoch) cannot be ordered by the simple
numeric comparison used here. Those are reported instead of silently guessed —
see `validate_rule` and `version_notation_note`.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass

from uvdrop.i18n import t


_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_VER_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?")
_CMP_RE = re.compile(r"^(==|!=|>=|<=|>|<)\s*(.+)$")
_PLAIN_NUM_RE = re.compile(r"^\d+(?:\.\d+)*$")
_WILDCARD_RE = re.compile(r"^(?:\*|\d+)(?:\.(?:\*|\d+))*$")
_HEADER_NAMES = {
    "package",
    "packages",
    "name",
    "名前",
    "パッケージ",
    "パッケージ名",
}


@dataclass(frozen=True)
class PackageRule:
    name: str
    version: str = "*"

    def normalized(self) -> PackageRule:
        name = (self.name or "").strip().lower().replace("_", "-")
        ver = (self.version or "").strip() or "*"
        return PackageRule(name=name, version=ver)


@dataclass(frozen=True)
class DeclaredDep:
    """A dependency taken from pyproject.toml."""

    name: str
    raw: str
    version: str | None  # exact pin if == / ===, else None
    has_constraint: bool


def parse_declared_dep(req: str) -> DeclaredDep | None:
    req = req.strip()
    if not req or req.startswith("-"):
        return None
    m = _NAME_RE.match(req)
    if not m:
        return None
    name = m.group(1).lower().replace("_", "-")
    rest = req[m.end() :].strip()
    # strip extras: name[extra]; python_version ...
    if rest.startswith("["):
        close = rest.find("]")
        rest = rest[close + 1 :].strip() if close >= 0 else ""
    if rest.startswith(";"):
        rest = ""
    has_constraint = bool(rest)
    exact: str | None = None
    for op in ("===", "=="):
        if rest.startswith(op):
            exact = rest[len(op) :].strip().split(",")[0].strip().split(";")[0].strip()
            break
    return DeclaredDep(name=name, raw=req, version=exact, has_constraint=has_constraint)


def _parse_tuple(ver: str) -> tuple[int, ...] | None:
    m = _VER_RE.match(ver.strip())
    if not m:
        return None
    parts = [int(p) for p in m.groups() if p is not None]
    return tuple(parts) if parts else None


def _pad(a: tuple[int, ...], n: int) -> tuple[int, ...]:
    return a + (0,) * max(0, n - len(a))


def _cmp(op: str, left: tuple[int, ...], right: tuple[int, ...]) -> bool:
    n = max(len(left), len(right))
    l, r = _pad(left, n), _pad(right, n)
    if op == "==":
        return l == r
    if op == "!=":
        return l != r
    if op == ">=":
        return l >= r
    if op == "<=":
        return l <= r
    if op == ">":
        return l > r
    if op == "<":
        return l < r
    return False


def version_matches(rule: str, version: str | None) -> bool:
    """Does `version` satisfy `rule`? None version only matches * / empty."""
    rule = (rule or "").strip() or "*"
    if rule in {"*", ""}:
        return True
    if version is None:
        return False

    ver_t = _parse_tuple(version)
    if ver_t is None:
        return False

    # wildcard form: 1.* / 1.*.* / 1.2.*
    if "*" in rule and not any(op in rule for op in (">=", "<=", "!=", "==", ">", "<")):
        parts = rule.split(".")
        for i, part in enumerate(parts):
            if part == "*":
                continue
            if not part.isdigit():
                return False
            if i >= len(ver_t) or ver_t[i] != int(part):
                return False
        return True

    # exact digits without operators
    if re.fullmatch(r"\d+(?:\.\d+)*", rule):
        rt = _parse_tuple(rule)
        if rt is None:
            return False
        n = max(len(rt), len(ver_t))
        return _pad(rt, n) == _pad(ver_t, n)

    # comparison clauses joined by comma (AND)
    for clause in rule.split(","):
        clause = clause.strip()
        if not clause:
            continue
        m = _CMP_RE.match(clause)
        if not m:
            return False
        op, rhs = m.group(1), m.group(2).strip()
        rhs_t = _parse_tuple(rhs)
        if rhs_t is None:
            return False
        if not _cmp(op, ver_t, rhs_t):
            return False
    return True


def name_only_ok(rule: str) -> bool:
    """True when the rule allows any declared/open version (name match is enough)."""
    rule = (rule or "").strip() or "*"
    return rule in {"*", ""}


# --- rule validation / explanation ------------------------------------------

def version_rule_guide() -> str:
    """Full multilingual guide for writing version rules."""
    return t("ver.guide")


# Backwards-compatible module attribute (evaluated in the active language).
def __getattr__(name: str) -> str:
    if name == "VERSION_RULE_GUIDE":
        return t("ver.guide")
    raise AttributeError(name)


@dataclass(frozen=True)
class RuleCheck:
    """Result of inspecting a version rule typed into the table."""

    ok: bool  # usable as-is
    message: str = ""  # why it is unusable, or what to watch out for
    exact: bool = True  # False when uvdrop cannot compare precisely

    @property
    def has_note(self) -> bool:
        return bool(self.message)


_PRE_POST_DEV_RE = re.compile(
    r"(?:^|[\d.\-_])(?:a|b|c|rc|alpha|beta|pre|preview|post|rev|r|dev)\d*$",
    re.IGNORECASE,
)


def version_notation_note(version: str | None) -> str | None:
    """Explain why a PyPI version string cannot be compared numerically."""
    v = (version or "").strip()
    if not v:
        return None
    if "!" in v:
        return t("ver.note.epoch", v=v)
    if "+" in v:
        return t("ver.note.local", v=v)
    if _PLAIN_NUM_RE.match(v):
        return None
    if v.lower().startswith("v") and _PLAIN_NUM_RE.match(v[1:]):
        return t("ver.note.leading_v", v=v)
    if _PRE_POST_DEV_RE.search(v):
        return t("ver.note.pre_post_dev", v=v)
    return t("ver.note.non_numeric", v=v)


def validate_rule(rule: str) -> RuleCheck:
    """Check a version rule cell. Empty / * is always fine."""
    r = (rule or "").strip()
    if not r or r == "*":
        return RuleCheck(True)

    if "~=" in r:
        return RuleCheck(False, t("ver.val.tilde"))
    if "===" in r:
        return RuleCheck(False, t("ver.val.triple_eq"))
    if r.lower().startswith("v") and _PLAIN_NUM_RE.match(r[1:]):
        return RuleCheck(False, t("ver.val.leading_v"))

    has_op = any(op in r for op in (">=", "<=", "!=", "==", ">", "<"))
    if "*" in r and has_op:
        return RuleCheck(False, t("ver.val.op_wildcard"))

    if "*" in r:
        if not _WILDCARD_RE.match(r):
            return RuleCheck(False, t("ver.val.bad_wildcard"))
        return RuleCheck(True)

    if _PLAIN_NUM_RE.match(r):
        return RuleCheck(True)

    if not has_op:
        note = version_notation_note(r)
        return RuleCheck(False, note or t("ver.val.need_numeric"))

    for clause in r.split(","):
        clause = clause.strip()
        if not clause:
            continue
        m = _CMP_RE.match(clause)
        if not m:
            return RuleCheck(False, t("ver.val.clause_unreadable", clause=clause))
        rhs = m.group(2).strip()
        if not _PLAIN_NUM_RE.match(rhs):
            note = version_notation_note(rhs)
            return RuleCheck(
                False,
                note or t("ver.val.clause_num_unreadable", clause=clause),
            )
    return RuleCheck(True)


def describe_rule(rule: str) -> str:
    """One-line plain-Japanese reading of a version rule."""
    r = (rule or "").strip()
    if not r or r == "*":
        return t("ver.desc.any")
    check = validate_rule(r)
    if not check.ok:
        return check.message
    if "*" in r:
        fixed = [p for p in r.split(".") if p != "*"]
        if not fixed:
            return t("ver.desc.any")
        return t("ver.desc.prefix", prefix=".".join(fixed))
    if _PLAIN_NUM_RE.match(r):
        return t("ver.desc.exact", r=r)
    parts = [c.strip() for c in r.split(",") if c.strip()]
    clauses = t("ver.desc.and").join(t("ver.desc.satisfy", p=p) for p in parts)
    return t("ver.desc.compare", clauses=clauses)


def rule_allows(rule: PackageRule, dep: DeclaredDep) -> tuple[bool, str]:
    """Return (ok, note). note is empty when nothing special to say."""
    r = rule.normalized()
    if r.name != dep.name:
        return False, ""
    if name_only_ok(r.version):
        return True, ""
    if dep.version is not None:
        if version_matches(r.version, dep.version):
            return True, ""
        return False, t("ver.allow.mismatch", name=dep.name, ver=dep.version, rule=r.version)
    # open / missing pin — allow by name, but note
    return True, t("ver.allow.open", name=dep.name, rule=r.version)


def match_uncertainty(rule: PackageRule, dep: DeclaredDep) -> str | None:
    """Note when uvdrop cannot judge this rule / version pair precisely.

    Returns None when the comparison is exact (or when only the name matters).
    """
    r = rule.normalized()
    if r.name != dep.name or name_only_ok(r.version):
        return None
    check = validate_rule(r.version)
    if not check.ok:
        return t("ver.uncertain.rule_bad", name=dep.name, rule=r.version, msg=check.message)
    if dep.version is None:
        return None
    note = version_notation_note(dep.version)
    if note:
        return t("ver.uncertain.approx", name=dep.name, note=note, rule=r.version)
    return None


def rule_blocks(rule: PackageRule, dep: DeclaredDep) -> bool:
    """NG list: name hit, and version rule matches if we have an exact pin."""
    r = rule.normalized()
    if r.name != dep.name:
        return False
    if name_only_ok(r.version):
        return True
    if dep.version is None:
        # Open pin still treated as blocked by name for safety
        return True
    return version_matches(r.version, dep.version)


def rules_from_legacy_text(text: str) -> list[PackageRule]:
    """Migrate comma-separated names into name-only rules."""
    parts = re.split(r"[,;\s]+", (text or "").strip())
    out: list[PackageRule] = []
    seen: set[str] = set()
    for p in parts:
        name = p.strip().lower().replace("_", "-")
        if not name:
            continue
        m = _NAME_RE.match(name)
        if not m:
            continue
        name = m.group(1).replace("_", "-")
        if name in seen:
            continue
        seen.add(name)
        out.append(PackageRule(name=name, version="*"))
    return out


def rules_from_dicts(items: list) -> list[PackageRule]:
    out: list[PackageRule] = []
    seen: set[str] = set()
    for item in items or []:
        if isinstance(item, str):
            rule = PackageRule(name=item, version="*").normalized()
        elif isinstance(item, dict):
            rule = PackageRule(
                name=str(item.get("name") or ""),
                version=str(item.get("version") or "*"),
            ).normalized()
        else:
            continue
        if not rule.name or rule.name in _HEADER_NAMES or rule.name in seen:
            continue
        seen.add(rule.name)
        out.append(rule)
    return out


def rules_to_dicts(rules: list[PackageRule]) -> list[dict[str, str]]:
    return [{"name": r.name, "version": r.version or "*"} for r in rules if r.name]


def _split_cells(line: str) -> list[str]:
    if "\t" in line:
        cells = line.split("\t")
    else:
        try:
            cells = next(csv.reader([line]))
        except StopIteration:
            cells = [line]
        # An unquoted comma inside a version rule (">=1.0,<2") must not become a
        # column, so fall back to whitespace when the first cell is not a name.
        first = cells[0].strip() if cells else ""
        if len(cells) == 1 or first != first.split(" ")[0]:
            cells = line.split(None, 1)
    return [c.strip().strip('"').strip() for c in cells]


def parse_pasted_table(text: str) -> list[tuple[str, str]]:
    """Parse a spreadsheet clipboard block into (name, version) cell pairs.

    Excel copies tab-separated rows; CSV text and plain "name version" also work.
    Header rows and blank lines are dropped, values are left as typed so the
    grid can show exactly what was pasted.
    """
    rows: list[tuple[str, str]] = []
    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw.strip():
            continue
        cells = _split_cells(raw)
        name = cells[0] if cells else ""
        version = cells[1] if len(cells) > 1 else ""
        if not name:
            continue
        if name.strip().lower() in _HEADER_NAMES:
            continue
        rows.append((name, version))
    return rows
