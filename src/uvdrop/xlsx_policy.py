"""Fetch allowlist packages from Excel (.xlsx) or CSV (URL or local path).

Format:
  A column = package name
  B column = version rule (optional; * / 1.* / >=1.0 / …)
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO, StringIO
from pathlib import Path

from uvdrop.http_util import urlopen
from uvdrop.i18n import t
from uvdrop.package_spec import PackageRule, rules_to_dicts
from uvdrop.paths import ensure_layout, policies_dir
from uvdrop.settings import load_settings

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

_HEADER = {
    "package",
    "packages",
    "name",
    "名前",
    "パッケージ",
    "パッケージ名",
    "version",
    "versions",
    "バージョン",
}


def _cache_path() -> Path:
    ensure_layout()
    return policies_dir() / "allowlist.from-file.json"


def _legacy_cache_path() -> Path:
    return policies_dir() / "allowlist.from-xlsx.json"


def _meta_path() -> Path:
    return policies_dir() / "allowlist.from-file.meta.json"


def _col_row(cell_ref: str) -> tuple[str, int]:
    m = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if not m:
        return "A", 1
    return m.group(1), int(m.group(2))


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out: list[str] = []
    for si in root.findall("m:si", _NS):
        texts = [t.text or "" for t in si.findall(".//m:t", _NS)]
        out.append("".join(texts))
    return out


def _sheet_paths(zf: zipfile.ZipFile) -> list[str]:
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return ["xl/worksheets/sheet1.xml"]
    rid_to_target: dict[str, str] = {}
    for rel in rels:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            rid_to_target[rid] = target
    paths: list[str] = []
    for sheet in wb.findall("m:sheets/m:sheet", _NS):
        rid = sheet.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if rid and rid in rid_to_target:
            paths.append(rid_to_target[rid])
    return paths or ["xl/worksheets/sheet1.xml"]


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    v = cell.find("m:v", _NS)
    if v is None or v.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared[int(v.text)]
        except (IndexError, ValueError):
            return ""
    return v.text


def parse_package_rules_from_xlsx(data: bytes) -> list[PackageRule]:
    """Read A=name, B=version from the first worksheet."""
    rows: dict[int, dict[str, str]] = {}
    with zipfile.ZipFile(BytesIO(data)) as zf:
        shared = _shared_strings(zf)
        sheets = _sheet_paths(zf)
        root = ET.fromstring(zf.read(sheets[0]))
        for row in root.findall("m:sheetData/m:row", _NS):
            for cell in row.findall("m:c", _NS):
                ref = cell.attrib.get("r", "A1")
                col, row_i = _col_row(ref)
                if col not in {"A", "B"}:
                    continue
                text = _cell_text(cell, shared).strip()
                rows.setdefault(row_i, {})[col] = text

    out: list[PackageRule] = []
    seen: set[str] = set()
    for row_i in sorted(rows):
        name = (rows[row_i].get("A") or "").strip()
        ver = (rows[row_i].get("B") or "").strip() or "*"
        if not name or name.lower() in _HEADER:
            continue
        rule = PackageRule(name=name, version=ver).normalized()
        if not rule.name or rule.name in seen:
            continue
        seen.add(rule.name)
        out.append(rule)
    return out


def parse_package_names_from_xlsx(data: bytes) -> list[str]:
    """Back-compat: names only."""
    return [r.name for r in parse_package_rules_from_xlsx(data)]


def parse_package_rules_from_csv(text: str) -> list[PackageRule]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(StringIO(text), dialect)
    out: list[PackageRule] = []
    seen: set[str] = set()
    for row in reader:
        if not row:
            continue
        name = (row[0] if len(row) > 0 else "").strip()
        ver = (row[1] if len(row) > 1 else "").strip() or "*"
        if not name or name.lower() in _HEADER:
            continue
        rule = PackageRule(name=name, version=ver).normalized()
        if not rule.name or rule.name in seen:
            continue
        seen.add(rule.name)
        out.append(rule)
    return out


def _looks_like_csv(source: str, data: bytes) -> bool:
    lower = source.lower().split("?", 1)[0]
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return True
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        return False
    head = data[:8]
    # ZIP/xlsx magic
    if head.startswith(b"PK"):
        return False
    try:
        data[:200].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _load_bytes(source: str) -> bytes:
    path = Path(source)
    if path.is_file():
        return path.read_bytes()
    req = urllib.request.Request(source, headers={"User-Agent": "uvdrop"}, method="GET")
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def sync_file_allowlist(*, force: bool = False) -> Path | None:
    """Download / read Excel or CSV; write allowlist.from-file.json."""
    settings = load_settings()
    if not settings.xlsx.enabled or not settings.xlsx.url:
        return None

    meta = _meta_path()
    cache = _cache_path()
    now = time.time()
    if not force and cache.is_file() and meta.is_file():
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            age_h = (now - float(m.get("fetched_at", 0))) / 3600.0
            if age_h < settings.xlsx.cache_hours:
                return cache
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    source = settings.xlsx.url.strip()
    try:
        data = _load_bytes(source)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if cache.is_file():
            return cache
        legacy = _legacy_cache_path()
        if legacy.is_file():
            return legacy
        raise RuntimeError(t("xlsx.load_fail", e=e)) from e

    if _looks_like_csv(source, data):
        text = data.decode("utf-8-sig", errors="replace")
        rules = parse_package_rules_from_csv(text)
    else:
        rules = parse_package_rules_from_xlsx(data)

    payload = {
        "version": 2,
        "mode": "warn",
        "source": source,
        "packages": rules_to_dicts(rules),
    }
    cache.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta.write_text(
        json.dumps({"fetched_at": now, "count": len(rules)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return cache


# Back-compat name used by older callers
def sync_xlsx_allowlist(*, force: bool = False) -> Path | None:
    return sync_file_allowlist(force=force)
