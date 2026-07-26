"""Tests for xlsx / CSV allowlist parsing (stdlib)."""

from __future__ import annotations

import zipfile
from io import BytesIO

from uvdrop.xlsx_policy import (
    parse_package_names_from_xlsx,
    parse_package_rules_from_csv,
    parse_package_rules_from_xlsx,
)


def _minimal_xlsx(rows: list[tuple[str, str | None]]) -> bytes:
    """Build a tiny xlsx with A=name, optional B=version via shared strings."""
    content_types = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    workbook = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    wb_rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    shared_parts: list[str] = []
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
    )
    idx = 0
    for i, (name, ver) in enumerate(rows, start=1):
        shared_parts.append(f"<si><t>{name}</t></si>")
        a_i = idx
        idx += 1
        cells = f'<c r="A{i}" t="s"><v>{a_i}</v></c>'
        if ver is not None:
            shared_parts.append(f"<si><t>{ver}</t></si>")
            b_i = idx
            idx += 1
            cells += f'<c r="B{i}" t="s"><v>{b_i}</v></c>'
        sheet_xml += f'<row r="{i}">{cells}</row>'
    sheet_xml += "</sheetData></worksheet>"
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_parts)}" uniqueCount="{len(shared_parts)}">'
        + "".join(shared_parts)
        + "</sst>"
    )

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def test_parse_package_names_from_xlsx() -> None:
    data = _minimal_xlsx([("Package", None), ("Requests", None), ("httpx", None), ("requests", None)])
    names = parse_package_names_from_xlsx(data)
    assert names == ["requests", "httpx"]


def test_parse_package_rules_with_versions() -> None:
    data = _minimal_xlsx(
        [("Package", "Version"), ("httpx", "0.27.*"), ("requests", ">=2.28"), ("rich", None)]
    )
    rules = parse_package_rules_from_xlsx(data)
    assert [(r.name, r.version) for r in rules] == [
        ("httpx", "0.27.*"),
        ("requests", ">=2.28"),
        ("rich", "*"),
    ]


def test_parse_csv_rules() -> None:
    text = "package,version\nhttpx,0.*\nrequests,\n"
    rules = parse_package_rules_from_csv(text)
    assert [(r.name, r.version) for r in rules] == [("httpx", "0.*"), ("requests", "*")]
