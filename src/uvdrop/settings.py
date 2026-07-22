"""User settings under AppData (OSV, xlsx URL, etc.)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from uvdrop.paths import app_root, ensure_layout


@dataclass
class OsvSettings:
    enabled: bool = False
    mode: str = "warn"  # warn | block


@dataclass
class XlsxSettings:
    url: str = ""
    enabled: bool = False
    cache_hours: float = 6.0


@dataclass
class Settings:
    osv: OsvSettings = field(default_factory=OsvSettings)
    xlsx: XlsxSettings = field(default_factory=XlsxSettings)

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        osv_raw = data.get("osv") or {}
        xlsx_raw = data.get("xlsx") or {}
        return cls(
            osv=OsvSettings(
                enabled=bool(osv_raw.get("enabled", False)),
                mode=str(osv_raw.get("mode", "warn")),
            ),
            xlsx=XlsxSettings(
                url=str(xlsx_raw.get("url", "")).strip(),
                enabled=bool(xlsx_raw.get("enabled", False)),
                cache_hours=float(xlsx_raw.get("cache_hours", 6.0)),
            ),
        )


def settings_path() -> Path:
    ensure_layout()
    return app_root() / "settings.json"


def load_settings() -> Settings:
    path = settings_path()
    if not path.is_file():
        return Settings()
    try:
        return Settings.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return Settings()


def save_settings(settings: Settings) -> None:
    path = settings_path()
    payload = {
        "version": 1,
        "osv": asdict(settings.osv),
        "xlsx": asdict(settings.xlsx),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_default_settings() -> Settings:
    path = settings_path()
    if not path.is_file():
        s = Settings()
        save_settings(s)
        return s
    return load_settings()
