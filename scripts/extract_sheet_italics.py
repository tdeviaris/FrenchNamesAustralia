#!/usr/bin/env python3
"""Extract rich-text italics from the Google Sheet into popup metadata.

The CSV/GViz export used for place data keeps cell values but discards partial
font formatting. The XLSX export retains rich-text runs, so this script records
the italic fragments separately without changing the place text itself.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict
from pathlib import Path, PurePosixPath


SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"x": SHEET_NS, "r": DOC_REL_NS}
FIELD_COLUMNS = {
    "N": "characteristic_fr",
    "O": "characteristic",
    "P": "history_fr",
    "Q": "history",
}


def column_letters(reference: str) -> str:
    match = re.match(r"[A-Z]+", reference)
    return match.group(0) if match else ""


def node_text(node: ET.Element) -> str:
    return "".join(part.text or "" for part in node.findall(".//x:t", NS))


def shared_string_data(shared_strings: ET.Element) -> list[tuple[str, list[str]]]:
    values: list[tuple[str, list[str]]] = []
    for item in shared_strings.findall("x:si", NS):
        runs = item.findall("x:r", NS)
        if not runs:
            values.append((node_text(item), []))
            continue

        plain_parts: list[str] = []
        italic_fragments: list[str] = []
        active_italic: list[str] = []
        for run in runs:
            text = node_text(run)
            plain_parts.append(text)
            is_italic = run.find("x:rPr/x:i", NS) is not None
            if is_italic:
                active_italic.append(text)
            elif active_italic:
                fragment = "".join(active_italic).strip()
                if fragment:
                    italic_fragments.append(fragment)
                active_italic = []

        if active_italic:
            fragment = "".join(active_italic).strip()
            if fragment:
                italic_fragments.append(fragment)

        values.append(("".join(plain_parts), italic_fragments))
    return values


def resolve_worksheet(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships.findall(f"{{{REL_NS}}}Relationship")
    }

    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        if sheet.attrib.get("name") != sheet_name:
            continue
        relationship_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
        target = targets.get(relationship_id or "")
        if not target:
            break
        return str(PurePosixPath("xl") / PurePosixPath(target))

    raise ValueError(f"Worksheet not found in XLSX export: {sheet_name}")


def extract_metadata(xlsx_path: Path, sheet_name: str) -> OrderedDict[str, object]:
    records: OrderedDict[str, object] = OrderedDict()
    with zipfile.ZipFile(xlsx_path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = shared_string_data(shared_root)
        worksheet_path = resolve_worksheet(archive, sheet_name)
        worksheet = ET.fromstring(archive.read(worksheet_path))

        for row in worksheet.findall("x:sheetData/x:row", NS):
            cells = {column_letters(cell.attrib.get("r", "")): cell for cell in row.findall("x:c", NS)}
            code_cell = cells.get("A")
            if code_cell is None or code_cell.attrib.get("t") != "s":
                continue
            code_value = code_cell.find("x:v", NS)
            if code_value is None or code_value.text is None:
                continue
            code = shared[int(code_value.text)][0].strip()
            if not re.fullmatch(r"(?:Baudin\d{3}|Entre\d{2})", code):
                continue

            fields: OrderedDict[str, list[str]] = OrderedDict()
            for column, field in FIELD_COLUMNS.items():
                cell = cells.get(column)
                if cell is None or cell.attrib.get("t") != "s":
                    continue
                value_node = cell.find("x:v", NS)
                if value_node is None or value_node.text is None:
                    continue
                fragments = shared[int(value_node.text)][1]
                unique_fragments = list(dict.fromkeys(fragment for fragment in fragments if fragment))
                if unique_fragments:
                    fields[field] = unique_fragments

            if fields:
                records[code] = fields

    return records


def download_xlsx(spreadsheet_id: str, destination: Path) -> None:
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
    request = urllib.request.Request(url, headers={"User-Agent": "FrenchNamesAustralia/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spreadsheet-id",
        default="1bF_fuVv-rr-KbWFBcYbGhPihuRE0fXr3Q2_0XhxvQfs",
    )
    parser.add_argument("--sheet-name", default="Source")
    parser.add_argument("--xlsx", type=Path, help="Use an existing XLSX export instead of downloading it")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/popup_italics.json"),
    )
    args = parser.parse_args()

    if args.xlsx:
        xlsx_path = args.xlsx
        metadata = extract_metadata(xlsx_path, args.sheet_name)
    else:
        with tempfile.TemporaryDirectory(prefix="fna-sheet-") as temp_dir:
            xlsx_path = Path(temp_dir) / "toponymes.xlsx"
            download_xlsx(args.spreadsheet_id, xlsx_path)
            metadata = extract_metadata(xlsx_path, args.sheet_name)

    output = OrderedDict(
        [
            (
                "_meta",
                {
                    "spreadsheetId": args.spreadsheet_id,
                    "sheet": args.sheet_name,
                    "fields": list(FIELD_COLUMNS.values()),
                },
            ),
            *metadata.items(),
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(metadata)} formatted notices to {args.output}")


if __name__ == "__main__":
    main()
