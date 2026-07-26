"""User settings under AppData (Excel/CSV, proxy, package tables, etc.)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from uvdrop.package_spec import PackageRule, rules_from_dicts, rules_from_legacy_text, rules_to_dicts
from uvdrop.paths import app_root, ensure_layout


@dataclass
class FileListSettings:
    """Remote or local Excel / CSV package list (A=name, B=version)."""

    url: str = ""
    enabled: bool = False
    cache_hours: float = 6.0


# Back-compat alias used by older imports
XlsxSettings = FileListSettings


@dataclass
class ProxySettings:
    enabled: bool = False
    http: str = ""
    https: str = ""
    no_proxy: str = ""


@dataclass
class ManualAllowlistSettings:
    """Editable allow table in Settings (name + version rule)."""

    enabled: bool = False
    packages: list[PackageRule] = field(default_factory=list)
    mode: str = "warn"  # warn | block


@dataclass
class BlocklistSettings:
    """NG packages — any hit is always blocking."""

    enabled: bool = False
    packages: list[PackageRule] = field(default_factory=list)


@dataclass
class GuardSettings:
    """Safety defaults applied before any venv is created."""

    confirm_before_run: bool = True
    no_allowlist: str = "confirm"  # confirm | allow
    allow_requirements_txt: bool = True
    show_console: bool = False  # black console window for stdout/stderr (debug)


@dataclass
class CatalogRef:
    """Local path or HTTP(S) URL to a catalog JSON (source of truth for listed apps)."""

    path: str = ""  # file path or https://...
    enabled: bool = True


@dataclass
class Settings:
    xlsx: FileListSettings = field(default_factory=FileListSettings)
    proxy: ProxySettings = field(default_factory=ProxySettings)
    allowlist: ManualAllowlistSettings = field(default_factory=ManualAllowlistSettings)
    blocklist: BlocklistSettings = field(default_factory=BlocklistSettings)
    guard: GuardSettings = field(default_factory=GuardSettings)
    catalogs: list[CatalogRef] = field(default_factory=list)
    ui_language: str = "auto"  # auto | ja | en | zh

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        xlsx_raw = data.get("xlsx") or data.get("file_list") or {}
        proxy_raw = data.get("proxy") or {}
        al_raw = data.get("allowlist") or {}
        bl_raw = data.get("blocklist") or {}
        guard_raw = data.get("guard") or {}
        catalogs_raw = data.get("catalogs") or []

        pkgs = al_raw.get("packages", [])
        if isinstance(pkgs, str):
            allow_rules = rules_from_legacy_text(pkgs)
        else:
            allow_rules = rules_from_dicts(pkgs or [])

        block_rules = rules_from_dicts(bl_raw.get("packages") or [])

        catalogs: list[CatalogRef] = []
        if isinstance(catalogs_raw, list):
            for item in catalogs_raw:
                if isinstance(item, str):
                    p = item.strip()
                    if p:
                        catalogs.append(CatalogRef(path=p, enabled=True))
                elif isinstance(item, dict):
                    p = str(item.get("path") or "").strip()
                    if p:
                        catalogs.append(
                            CatalogRef(path=p, enabled=bool(item.get("enabled", True)))
                        )

        return cls(
            xlsx=FileListSettings(
                url=str(xlsx_raw.get("url", "")).strip(),
                enabled=bool(xlsx_raw.get("enabled", False)),
                cache_hours=float(xlsx_raw.get("cache_hours", 6.0)),
            ),
            proxy=ProxySettings(
                enabled=bool(proxy_raw.get("enabled", False)),
                http=str(proxy_raw.get("http", "")).strip(),
                https=str(proxy_raw.get("https", "")).strip(),
                no_proxy=str(proxy_raw.get("no_proxy", "")).strip(),
            ),
            allowlist=ManualAllowlistSettings(
                enabled=bool(al_raw.get("enabled", False)),
                packages=allow_rules,
                mode=str(al_raw.get("mode", "warn")),
            ),
            blocklist=BlocklistSettings(
                enabled=bool(bl_raw.get("enabled", False)),
                packages=block_rules,
            ),
            guard=GuardSettings(
                confirm_before_run=bool(guard_raw.get("confirm_before_run", True)),
                no_allowlist=str(guard_raw.get("no_allowlist", "confirm")),
                allow_requirements_txt=bool(guard_raw.get("allow_requirements_txt", True)),
                show_console=bool(guard_raw.get("show_console", False)),
            ),
            catalogs=catalogs,
            ui_language=str(data.get("ui_language") or "auto").strip() or "auto",
        )


def parse_package_list(text: str) -> list[str]:
    """Legacy helper: names only (tests / callers that still pass commas)."""
    return [r.name for r in rules_from_legacy_text(text)]


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
    settings.allowlist.packages = [
        r.normalized() for r in settings.allowlist.packages if r.normalized().name
    ]
    settings.blocklist.packages = [
        r.normalized() for r in settings.blocklist.packages if r.normalized().name
    ]
    settings.catalogs = [
        CatalogRef(path=c.path.strip(), enabled=bool(c.enabled))
        for c in settings.catalogs
        if c.path and str(c.path).strip()
    ]
    payload = {
        "version": 2,
        "xlsx": asdict(settings.xlsx),
        "proxy": asdict(settings.proxy),
        "allowlist": {
            "enabled": settings.allowlist.enabled,
            "mode": settings.allowlist.mode,
            "packages": rules_to_dicts(settings.allowlist.packages),
        },
        "blocklist": {
            "enabled": settings.blocklist.enabled,
            "packages": rules_to_dicts(settings.blocklist.packages),
        },
        "guard": asdict(settings.guard),
        "catalogs": [asdict(c) for c in settings.catalogs],
        "ui_language": settings.ui_language or "auto",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_default_settings() -> Settings:
    path = settings_path()
    if not path.is_file():
        s = Settings()
        save_settings(s)
        return s
    return load_settings()


def proxy_environ(settings: Settings | None = None) -> dict[str, str]:
    """Env vars for child processes (uv / urllib-friendly)."""
    s = settings or load_settings()
    if not s.proxy.enabled:
        return {}
    out: dict[str, str] = {}
    http = s.proxy.http or s.proxy.https
    https = s.proxy.https or s.proxy.http
    if http:
        out["HTTP_PROXY"] = http
        out["http_proxy"] = http
    if https:
        out["HTTPS_PROXY"] = https
        out["https_proxy"] = https
        out["ALL_PROXY"] = https
        out["all_proxy"] = https
    if s.proxy.no_proxy:
        out["NO_PROXY"] = s.proxy.no_proxy
        out["no_proxy"] = s.proxy.no_proxy
    return out
