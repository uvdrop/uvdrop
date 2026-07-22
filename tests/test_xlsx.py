"""Tests for xlsx allowlist parsing (stdlib)."""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree.ElementTree import Element, SubElement, tostring

from uvdrop.xlsx_policy import parse_package_names_from_xlsx


def _minimal_xlsx(names: list[str]) -> bytes:
    """Build a tiny xlsx with column A values (inline strings)."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet = Element(f"{{{ns}}}worksheet")
    data = SubElement(sheet, f"{{{ns}}}sheetData")
    for i, name in enumerate(names, start=1):
        row = SubElement(data, f"{{{ns}}}row", r=str(i))
        cell = SubElement(row, f"{{{ns}}}c", r=f"A{i}", t="inlineStr")
        is_el = SubElement(cell, f"{{{ns}}}is")
        t_el = SubElement(is_el, f"{{{ns}}}t")
        t_el.text = name

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

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        # ElementTree may emit ns0 — use string sheet with shared strings instead for reliability
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
        )
        # Use shared strings for compatibility with parser
        shared_parts = []
        for i, name in enumerate(names):
            shared_parts.append(f"<si><t>{name}</t></si>")
            sheet_xml += f'<row r="{i+1}"><c r="A{i+1}" t="s"><v>{i}</v></c></row>'
        sheet_xml += "</sheetData></worksheet>"
        shared = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{len(names)}" uniqueCount="{len(names)}">'
            + "".join(shared_parts)
            + "</sst>"
        )
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def test_parse_package_names_from_xlsx() -> None:
    data = _minimal_xlsx(["Package", "Requests", "httpx", "requests"])
    names = parse_package_names_from_xlsx(data)
    assert names == ["requests", "httpx"]
