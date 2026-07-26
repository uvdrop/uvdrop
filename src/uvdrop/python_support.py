"""Python runtime support window (EOL / nearing-EOL warnings).

Separate from the allow-list in ``python-versions.json``: a version can be
allowed by policy and still warn that upstream support ends soon.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping


# Upstream CPython end-of-support (approx. October of year+5 from release).
# Override / extend via ``python-versions.json`` → ``eol`` map.
DEFAULT_EOL: dict[str, str] = {
    "3.8": "2024-10-07",
    "3.9": "2025-10-31",
    "3.10": "2026-10-31",
    "3.11": "2027-10-31",
    "3.12": "2028-10-31",
    "3.13": "2029-10-31",
    "3.14": "2030-10-31",
}

DEFAULT_WARN_DAYS = 365


@dataclass(frozen=True)
class PythonSupportHit:
    """One support-window finding for a Python X.Y version."""

    version: str  # e.g. "3.10"
    kind: str  # "eol" | "nearing_eol" | "unknown_eol"
    eol_date: date | None
    days_remaining: int | None
    message: str


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def merge_eol_map(overrides: Mapping[str, object] | None = None) -> dict[str, date]:
    """Built-in schedule, overridden by policy ``eol`` entries."""
    out: dict[str, date] = {}
    for ver, raw in DEFAULT_EOL.items():
        d = parse_iso_date(raw)
        if d:
            out[ver] = d
    if overrides:
        for ver, raw in overrides.items():
            key = str(ver).strip()
            d = parse_iso_date(str(raw) if raw is not None else None)
            if key and d:
                out[key] = d
    return out


def check_python_support(
    version: str | None,
    *,
    eol_map: Mapping[str, date] | None = None,
    warn_days: int = DEFAULT_WARN_DAYS,
    today: date | None = None,
) -> list[PythonSupportHit]:
    """Return support warnings for ``version`` (``X.Y``).

    - Already past EOL → ``eol``
    - Within ``warn_days`` of EOL → ``nearing_eol``
    - Unknown version with no schedule → empty (no noise)
    """
    if not version:
        return []
    ver = version.strip()
    if not ver:
        return []
    # Normalize 3.10.5 → 3.10 for schedule lookup
    parts = ver.split(".")
    major_minor = ".".join(parts[:2]) if len(parts) >= 2 else ver

    schedule = dict(eol_map) if eol_map is not None else merge_eol_map()
    eol = schedule.get(major_minor)
    if eol is None:
        return []

    now = today or date.today()
    remaining = (eol - now).days
    if remaining < 0:
        return [
            PythonSupportHit(
                version=major_minor,
                kind="eol",
                eol_date=eol,
                days_remaining=remaining,
                message=(
                    f"Python {major_minor} reached end of support on {eol.isoformat()} "
                    f"({abs(remaining)} days ago). Prefer a supported release."
                ),
            )
        ]
    if remaining <= max(0, int(warn_days)):
        return [
            PythonSupportHit(
                version=major_minor,
                kind="nearing_eol",
                eol_date=eol,
                days_remaining=remaining,
                message=(
                    f"Python {major_minor} reaches end of support on {eol.isoformat()} "
                    f"({remaining} days left; warn window {warn_days} days)."
                ),
            )
        ]
    return []


def warn_days_from_policy(data: Mapping[str, object] | None) -> int:
    if not data:
        return DEFAULT_WARN_DAYS
    raw = data.get("eol_warn_days", data.get("support_warn_days", DEFAULT_WARN_DAYS))
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_WARN_DAYS
