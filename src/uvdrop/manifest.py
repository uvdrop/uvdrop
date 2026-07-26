"""Optional root manifest for entry / project path (legacy nora/ also accepted silently)."""

from __future__ import annotations

import json
from pathlib import Path


def load_app_manifest(root: Path) -> dict:
    """Load optional manifest. Prefer uvdrop.manifest.json; legacy nora/ still works."""
    candidates = [
        root / "uvdrop.manifest.json",
        root / "manifest.json",
        root / "nora" / "manifest.json",  # legacy compatibility only
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return {}
