"""Kept / temporary app registry."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field, fields
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
    run_count: int = 0
    entry_command: str = ""
    icon_path: str = ""


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
    known = {f.name for f in fields(AppRecord)}
    out: dict[str, AppRecord] = {}
    for item in apps:
        if not isinstance(item, dict):
            continue
        try:
            rec = AppRecord(**{k: v for k, v in item.items() if k in known})
            out[rec.key] = rec
        except TypeError:
            continue
    return out


def set_icon(key: str, icon_path: str) -> None:
    apps = load_registry()
    if key in apps:
        apps[key].icon_path = icon_path
        save_registry(apps)


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
    from uvdrop.usage import drop_app

    apps = load_registry()
    if key in apps:
        del apps[key]
        save_registry(apps)
    drop_app(key)


def touch_run(key: str) -> None:
    from uvdrop.usage import record_run

    apps = load_registry()
    if key in apps:
        apps[key].last_run_at = time.time()
        apps[key].run_count = int(apps[key].run_count or 0) + 1
        save_registry(apps)
    record_run(key)
