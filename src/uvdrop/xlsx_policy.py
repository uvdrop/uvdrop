"""Fetch allowlist packages from a remote xlsx URL (stdlib only)."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from pathlib import Path

from uvdrop.paths import ensure_layout, policies_dir
from uvdrop.settings import load_settings

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _cache_path() -> Path:
    ensure_layout()
    return policies_dir() / "allowlist.from-xlsx.json"


def _meta_path() -> Path:
    return policies_dir() / "allowlist.from-xlsx.meta.json"


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


def parse_package_names_from_xlsx(data: bytes) -> list[str]:
    """Read first column values from the first worksheet as package names."""
    names: list[str] = []
    with zipfile.ZipFile(BytesIO(data)) as zf:
        shared = _shared_strings(zf)
        sheets = _sheet_paths(zf)
        xml = zf.read(sheets[0])
        root = ET.fromstring(xml)
        for row in root.findall("m:sheetData/m:row", _NS):
            for cell in row.findall("m:c", _NS):
                ref = cell.attrib.get("r", "A1")
                col, _row = _col_row(ref)
                if col != "A":
                    continue
                cell_type = cell.attrib.get("t")
                v = cell.find("m:v", _NS)
                if v is None or v.text is None:
                    continue
                if cell_type == "s":
                    try:
                        text = shared[int(v.text)]
                    except (IndexError, ValueError):
                        continue
                else:
                    text = v.text
                text = text.strip()
                if not text or text.lower() in {"package", "name", "packages", "パッケージ"}:
                    continue
                names.append(text.lower().replace("_", "-"))
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def sync_xlsx_allowlist(*, force: bool = False) -> Path | None:
    """Download xlsx if configured; write allowlist.from-xlsx.json. Returns cache path."""
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

    req = urllib.request.Request(
        settings.xlsx.url,
        headers={"User-Agent": "uvdrop"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        if cache.is_file():
            return cache
        raise RuntimeError(f"xlsx download failed: {e}") from e

    packages = parse_package_names_from_xlsx(data)
    payload = {
        "version": 1,
        "mode": "warn",
        "source": settings.xlsx.url,
        "packages": packages,
    }
    cache.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta.write_text(
        json.dumps({"fetched_at": now, "count": len(packages)}, indent=2) + "\n",
        encoding="utf-8",
    )
    return cache
