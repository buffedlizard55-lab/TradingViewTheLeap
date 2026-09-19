#!/usr/bin/env python3
"""Unit tests for the TradingView export importer (intel/tv_import.py).

Covers the CSV path on the committed synthetic fixture plus the stdlib XLSX
reader on workbooks assembled in-memory with zipfile: shared strings, inline
strings, numbers, date-formatted serials, first-sheet selection, and loud
failure on unreadable workbooks. No network, no credentials, no real exports.

Run: python3 -m unittest discover -s scripts -p "test_*.py"
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import tv_import as tvi  # noqa: E402


def write_xlsx(path: str, sheets: list, shared: tuple = (), styles: str | None = None) -> None:
    """Assemble a minimal .xlsx workbook.

    sheets: list of (name, rows); rows: list of (row_number, cells);
    cells: list of (ref, type, style, value) with type in n/s/inlineStr/b.
    """
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/xl/workbook.xml" ContentType="x"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="x"/></Types>')
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{name}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
                       for i, (name, _) in enumerate(sheets))
            + "</sheets></workbook>")
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i + 1}" Target="worksheets/sheet{i + 1}.xml"/>'
                       for i in range(len(sheets)))
            + "</Relationships>")
        if shared:
            archive.writestr(
                "xl/sharedStrings.xml",
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + "".join(f"<si><t>{text}</t></si>" for text in shared) + "</sst>")
        if styles:
            archive.writestr("xl/styles.xml", styles)
        for i, (_, rows) in enumerate(sheets):
            body = ""
            for number, cells in rows:
                parts = []
                for ref, typ, style, value in cells:
                    if typ == "inlineStr":
                        parts.append(
                            f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>')
                    else:
                        parts.append(
                            f'<c r="{ref}" t="{typ}" s="{style}"><v>{value}</v></c>')
                body += f'<row r="{number}">' + "".join(parts) + "</row>"
            archive.writestr(
                f"xl/worksheets/sheet{i + 1}.xml",
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"<sheetData>{body}</sheetData></worksheet>")


DATE_STYLES = (
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd hh:mm:ss"/></numFmts>'
    '<cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs></styleSheet>')


class XlsxReaderTests(unittest.TestCase):
    def test_first_sheet_cells_decode(self):
        shared = ("Trade #", "Type", "Date/Time", "Signal", "Price", "Contracts",
                  "Entry Long", "Buy")
        rows = [
            (1, [("A1", "s", 0, "0"), ("B1", "s", 0, "1"), ("C1", "s", 0, "2"),
                 ("D1", "s", 0, "3"), ("E1", "s", 0, "4"), ("F1", "s", 0, "5")]),
            (2, [("A2", "n", 0, "1"), ("B2", "s", 0, "6"), ("C2", "n", 1, "45812.5"),
                 ("D2", "s", 0, "7"), ("E2", "n", 0, "29742"), ("F2", "n", 0, "2")]),
            (3, [("A3", "inlineStr", 0, "note"), ("B3", "s", 0, "6")]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trades.xlsx")
            write_xlsx(path, [("List of Trades", rows),
                              ("Ignored", [(1, [("A1", "s", 0, "0")])])],
                       shared, DATE_STYLES)
            decoded = tvi._read_xlsx_rows(path)
        self.assertEqual(decoded[0], ["Trade #", "Type", "Date/Time", "Signal",
                                     "Price", "Contracts"])
        self.assertEqual(decoded[1][2], "2025-06-04 12:00:00")  # serial 45812.5
        self.assertEqual(decoded[1][4], "29742")
        self.assertEqual(decoded[2], ["note", "Entry Long"])

    def test_import_any_accepts_xlsx_trades(self):
        shared = ("Trade #", "Type", "Date/Time", "Signal", "Price", "Contracts",
                  "Entry Long", "Buy", "Exit Long", "Sell")
        rows = [
            (1, [("A1", "s", 0, "0"), ("B1", "s", 0, "1"), ("C1", "s", 0, "2"),
                 ("D1", "s", 0, "3"), ("E1", "s", 0, "4"), ("F1", "s", 0, "5")]),
            (2, [("A2", "n", 0, "1"), ("B2", "s", 0, "6"), ("C2", "n", 1, "45812.5"),
                 ("D2", "s", 0, "7"), ("E2", "n", 0, "100"), ("F2", "n", 0, "2")]),
            (3, [("A3", "n", 0, "1"), ("B3", "s", 0, "8"), ("C3", "n", 1, "45813.5"),
                 ("D3", "s", 0, "9"), ("E3", "n", 0, "110"), ("F3", "n", 0, "2")]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "synthetic_trades.xlsx")
            write_xlsx(path, [("List of Trades", rows)], shared, DATE_STYLES)
            report = tvi.import_any(path)
        self.assertEqual(report.kind, "list_of_trades")
        self.assertTrue(report.is_fixture)
        self.assertEqual(len(report.trades), 2)
        self.assertEqual(report.trades[0].phase, "entry")
        self.assertEqual(report.trades[1].phase, "exit")
        self.assertEqual(len(report.metrics["round_trips"]), 1)

    def test_import_any_accepts_xlsx_performance_summary(self):
        shared = ("Total Net Profit", "1000")
        rows = [(1, [("A1", "s", 0, "0"), ("B1", "n", 0, "1500.25")])]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "synthetic_summary.xlsx")
            write_xlsx(path, [("Performance Summary", rows)], shared)
            report = tvi.import_any(path)
        self.assertEqual(report.kind, "performance_summary")
        self.assertAlmostEqual(report.metrics["total_net_profit"], 1500.25)

    def test_unreadable_workbook_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "broken.xlsx")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("not a zip file")
            with self.assertRaises(tvi.ImportError_):
                tvi._read_xlsx_rows(path)
            empty = os.path.join(tmp, "empty.xlsx")
            with zipfile.ZipFile(empty, "w"):
                pass
            with self.assertRaises(tvi.ImportError_):
                tvi._read_xlsx_rows(empty)


class CsvRegressionTests(unittest.TestCase):
    def test_committed_fixture_still_imports(self):
        path = os.path.join(ROOT, "data", "tv_reports", "_fixtures",
                            "synthetic_list_of_trades.csv")
        report = tvi.import_any(path)
        self.assertEqual(report.kind, "list_of_trades")
        self.assertTrue(report.is_fixture)
        self.assertGreater(len(report.trades), 0)
        self.assertIn("round_trips", report.metrics)


if __name__ == "__main__":
    unittest.main()
