"""Shared catalogs — JSON is the source of truth (file or HTTP).

No directory auto-scanning. uvdrop reads registered catalog sources, lists the
apps they declare, and only then touches each app's ``path``. Existing launch
guards (confirm / allow / block / resolved tree) stay intact.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from uvdrop.http_util import urlopen
from uvdrop.i18n import t
from uvdrop.paths import slugify


CATALOG_VERSION = 1


def is_catalog_url(source: str) -> bool:
    s = (source or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")


@dataclass(frozen=True)
class CatalogApp:
    """One app entry declared in a catalog file or HTTP catalog."""

    name: str
    path: str  # absolute / UNC / relative to path_base
    summary: str = ""
    command: str = ""  # preferred entry command (pre-filled in confirm)
    id: str = ""  # optional stable id for app_key
    catalog_title: str = ""
    catalog_path: str = ""  # file path or URL this entry came from
    path_base: str = ""  # directory (or catalog ``base``) for relative paths

    @property
    def app_key_hint(self) -> str:
        return slugify(self.id or self.name)

    def resolved_path(self) -> Path:
        """Resolve ``path`` relative to ``path_base`` when needed."""
        raw = Path(self.path)
        if raw.is_absolute() or str(self.path).startswith("\\\\"):
            return raw
        base = Path(self.path_base) if self.path_base else Path.cwd()
        return (base / raw).resolve()


@dataclass
class CatalogLoadResult:
    apps: list[CatalogApp] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    title: str = ""


def _as_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _default_path_base(catalog_path: str, data: dict) -> str:
    """Where relative ``apps[].path`` values resolve from."""
    explicit = _as_str(data.get("base") or data.get("path_base"))
    if explicit:
        return explicit
    if not catalog_path:
        return ""
    if is_catalog_url(catalog_path):
        # HTTP catalogs need an explicit ``base`` (share / local root).
        # Without it, relative paths stay unresolved until check time.
        return ""
    return str(Path(catalog_path).parent)


def parse_catalog_dict(data: dict, *, catalog_path: str = "") -> CatalogLoadResult:
    """Parse an already-loaded catalog document."""
    out = CatalogLoadResult()
    if not isinstance(data, dict):
        out.errors.append(t("catalog.err_not_object"))
        return out

    out.title = _as_str(data.get("catalog") or data.get("title") or data.get("name"))
    path_base = _default_path_base(catalog_path, data)
    apps_raw = data.get("apps")
    if apps_raw is None:
        out.errors.append(t("catalog.err_no_apps"))
        return out
    if not isinstance(apps_raw, list):
        out.errors.append(t("catalog.err_apps_not_list"))
        return out

    for i, item in enumerate(apps_raw):
        if not isinstance(item, dict):
            out.errors.append(t("catalog.err_entry_not_object", n=i + 1))
            continue
        name = _as_str(item.get("name"))
        path = _as_str(item.get("path"))
        if not name or not path:
            out.errors.append(t("catalog.err_entry_incomplete", n=i + 1))
            continue
        out.apps.append(
            CatalogApp(
                name=name,
                path=path,
                summary=_as_str(item.get("summary") or item.get("description")),
                command=_as_str(item.get("command") or item.get("entry")),
                id=_as_str(item.get("id")),
                catalog_title=out.title,
                catalog_path=catalog_path,
                path_base=path_base,
            )
        )
    return out


def load_catalog_file(path: Path) -> CatalogLoadResult:
    """Load one catalog JSON file. Does not touch any app ``path`` yet."""
    out = CatalogLoadResult()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        out.errors.append(t("catalog.err_read", path=path, e=e))
        return out
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        out.errors.append(t("catalog.err_json", path=path, e=e))
        return out
    return parse_catalog_dict(data, catalog_path=str(path))


def load_catalog_url(url: str, *, timeout: float = 30.0) -> CatalogLoadResult:
    """Fetch a catalog JSON over HTTP(S). Does not touch any app ``path`` yet."""
    out = CatalogLoadResult()
    source = (url or "").strip()
    if not is_catalog_url(source):
        out.errors.append(t("catalog.err_not_url", url=source))
        return out
    parsed = urlparse(source)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        out.errors.append(t("catalog.err_not_url", url=source))
        return out
    req = urllib.request.Request(
        source,
        headers={"User-Agent": "uvdrop", "Accept": "application/json, text/plain, */*"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        out.errors.append(t("catalog.err_http", url=source, e=f"HTTP {e.code}"))
        return out
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        out.errors.append(t("catalog.err_http", url=source, e=e))
        return out
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        out.errors.append(t("catalog.err_json", path=source, e=e))
        return out
    return parse_catalog_dict(data, catalog_path=source)


def load_catalog_source(source: str, *, timeout: float = 30.0) -> CatalogLoadResult:
    """Load a catalog from a local path or an HTTP(S) URL."""
    raw = (source or "").strip()
    if not raw:
        return CatalogLoadResult()
    if is_catalog_url(raw):
        return load_catalog_url(raw, timeout=timeout)
    return load_catalog_file(Path(raw))


def load_all_catalogs(sources: list[str], *, timeout: float = 30.0) -> CatalogLoadResult:
    """Merge apps from several catalog files / URLs. Later sources append."""
    merged = CatalogLoadResult()
    for raw in sources:
        src = (raw or "").strip()
        if not src:
            continue
        if is_catalog_url(src):
            part = load_catalog_url(src, timeout=timeout)
        else:
            p = Path(src)
            if not p.is_file():
                merged.errors.append(t("catalog.err_missing", path=p))
                continue
            part = load_catalog_file(p)
        merged.errors.extend(part.errors)
        merged.apps.extend(part.apps)
        if not merged.title and part.title:
            merged.title = part.title
    return merged


def check_app_path(app: CatalogApp) -> Path:
    """Resolve and verify the app path exists (folder or .zip).

    Raises FileNotFoundError / ValueError with a localized message.
    """
    # Relative path under an HTTP catalog without ``base`` cannot be resolved.
    raw = Path(app.path)
    if (
        not raw.is_absolute()
        and not str(app.path).startswith("\\\\")
        and not app.path_base
        and is_catalog_url(app.catalog_path)
    ):
        raise ValueError(t("catalog.err_http_relative", path=app.path))

    target = app.resolved_path()
    # UNC / network paths: existence check is the first real access.
    if not target.exists():
        raise FileNotFoundError(t("catalog.err_path_missing", path=target))
    if target.is_dir():
        return target
    if target.is_file() and target.suffix.lower() == ".zip":
        return target
    raise ValueError(t("catalog.err_path_kind", path=target))
