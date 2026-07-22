"""Kept / temporary app registry."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from uvdrop.paths import ensure_layout, registry_path


Mode = Literal["keep", "temp"]


@dataclass
class AppRecord:
    key: str
    name: str
    source_kind: str  # folder | zip
    source_path: str
    workspace: str
    mode: Mode = "keep"
    created_at: float = field(default_factory=time.time)
    last_run_at: float | None = None


def load_registry() -> dict[str, AppRecord]:
    ensure_layout()
    path = registry_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    apps = raw.get("apps") if isinstance(raw, dict) else None
    if not isinstance(apps, list):
        return {}
    out: dict[str, AppRecord] = {}
    for item in apps:
        try:
            rec = AppRecord(**item)
            out[rec.key] = rec
        except TypeError:
            continue
    return out


def save_registry(apps: dict[str, AppRecord]) -> None:
    ensure_layout()
    payload = {
        "version": 1,
        "apps": [asdict(a) for a in sorted(apps.values(), key=lambda x: x.name.lower())],
    }
    registry_path().write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def upsert(record: AppRecord) -> None:
    apps = load_registry()
    apps[record.key] = record
    save_registry(apps)


def remove(key: str) -> None:
    apps = load_registry()
    if key in apps:
        del apps[key]
        save_registry(apps)


def touch_run(key: str) -> None:
    apps = load_registry()
    if key in apps:
        apps[key].last_run_at = time.time()
        save_registry(apps)
