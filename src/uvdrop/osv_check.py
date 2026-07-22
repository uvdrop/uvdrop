"""Optional OSV.dev malicious package checks for PyPI."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from uvdrop.policy import PolicyHit, _dep_names_from_pyproject
from uvdrop.settings import load_settings

OSV_QUERYBATCH = "https://api.osv.dev/v1/querybatch"


def check_osv(pyproject: Path) -> list[PolicyHit]:
    settings = load_settings()
    if not settings.osv.enabled:
        return []

    deps = sorted(_dep_names_from_pyproject(pyproject))
    if not deps:
        return []

    queries = [{"package": {"name": name, "ecosystem": "PyPI"}} for name in deps]
    body = json.dumps({"queries": queries}).encode("utf-8")
    req = urllib.request.Request(
        OSV_QUERYBATCH,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "uvdrop"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return [
            PolicyHit(
                "osv",
                f"OSV check failed (network/parse): {e}",
                blocking=False,
            )
        ]

    blocking = (settings.osv.mode or "warn").lower() == "block"
    hits: list[PolicyHit] = []
    results = data.get("results") or []
    for name, result in zip(deps, results, strict=False):
        vulns = result.get("vulns") or []
        mal = [v for v in vulns if str(v.get("id", "")).startswith("MAL-")]
        # also treat any vuln as signal if only MAL wanted — prefer MAL
        if not mal:
            continue
        ids = ", ".join(str(v.get("id")) for v in mal[:5])
        hits.append(
            PolicyHit(
                "osv",
                f"OSV malicious advisory for {name}: {ids}",
                blocking,
            )
        )
    return hits
