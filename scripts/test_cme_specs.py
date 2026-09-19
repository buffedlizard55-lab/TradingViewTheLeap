#!/usr/bin/env python3
"""Unit tests for the CME contract-spec transcriber (scripts/fetch_cme_specs.py).

The HTML fixture below is synthetic - it is shaped like CME's real contractSpecs table
(`<tr><th>label</th><td>value</td></tr>` rows, `<br>` separated sub-lines) but its numbers
are invented on purpose so that no test can be mistaken for transcribed market data. The
tests assert the *extraction behaviour*: labels resolve, `<br>` becomes a newline,
entities decode, absent labels become null and are reported as missing, and a page with no
Trading Hours row is refused rather than half-transcribed.
"""

import importlib.util
import re
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location(
    "fetch_cme_specs", os.path.join(ROOT, "scripts", "fetch_cme_specs.py")
)
fcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fcs)


SPEC_PAGE = """
<html><body>
<nav><a href="/x.html">SI - Silver</a></nav>
<h2>Silver Futures - Contract Specs</h2>
<table>
  <tr><th>Contract Unit</th><td>5,000 troy ounces</td></tr>
  <tr><th>Price Quotation</th><td>U.S. dollars and cents per troy ounce</td></tr>
  <tr><th>Trading Hours</th><td>CME Globex:<br>Sunday - Friday 6:00 p.m. - 5:00 p.m. ET
      (5:00 p.m. - 4:00 p.m. CT)<br>with a 60-minute break each day beginning at 5:00 p.m.
      (4:00 p.m. CT)<br>TAS: Sunday - Friday 6:00 p.m. - 1:25 p.m. ET</td></tr>
  <tr><th>Minimum Price Fluctuation</th><td>0.005 per troy ounce = $25.00</td></tr>
  <tr><th>Product Code</th><td>CME Globex: SI<br>Clearing: SI</td></tr>
  <tr><th>Listed Contracts</th><td>Monthly contracts listed for the current year and the
      next 2 calendar years&nbsp;and the nearest 3 serial months</td></tr>
  <tr><th>Settlement Method</th><td>Deliverable</td></tr>
  <tr><th>Termination of Trading</th><td>12:25 p.m. CT on the third last business day of
      the contract month</td></tr>
</table>
<table>
  <tr><th>Position Limits</th><td><a href="/pl.xlsx">NYMEX Position Limits</a></td></tr>
</table>
</body></html>
"""


class TestExtractSpecFields(unittest.TestCase):
    def test_every_label_resolves_verbatim(self):
        fields, missing = fcs.extract_spec_fields(SPEC_PAGE)
        self.assertEqual(missing, [])
        self.assertEqual(fields["contract_unit"], "5,000 troy ounces")
        self.assertEqual(fields["termination_of_trading"],
                         "12:25 p.m. CT on the third last business day of the contract month")
        self.assertEqual(fields["settlement_method"], "Deliverable")

    def test_br_becomes_newline_and_entities_decode(self):
        fields, _ = fcs.extract_spec_fields(SPEC_PAGE)
        hours = fields["trading_hours"]
        self.assertIn("CME Globex:", hours)
        self.assertIn("\n", hours, "<br> must survive as a newline, not be flattened away")
        self.assertNotIn("<br>", hours)
        self.assertNotIn("&nbsp;", fields["listed_contracts"])
        self.assertIn("years and the nearest", fields["listed_contracts"])

    def test_missing_label_is_null_and_reported(self):
        page = SPEC_PAGE.replace("<tr><th>Settlement Method</th><td>Deliverable</td></tr>", "")
        fields, missing = fcs.extract_spec_fields(page)
        self.assertIsNone(fields["settlement_method"])
        self.assertIn("settlement_method", missing)
        self.assertNotIn("contract_unit", missing)

    def test_trading_hours_absent_is_detected(self):
        page = SPEC_PAGE.replace("Trading Hours", "Sessions")
        fields, missing = fcs.extract_spec_fields(page)
        self.assertIsNone(fields["trading_hours"])
        self.assertIn("trading_hours", missing)

    def test_alias_labels_are_accepted(self):
        page = SPEC_PAGE.replace("Termination of Trading", "Last Trading Day")
        fields, _ = fcs.extract_spec_fields(page)
        self.assertIsNotNone(fields["termination_of_trading"])

    def test_empty_document_extracts_nothing_and_reports_every_field(self):
        fields, missing = fcs.extract_spec_fields("<html></html>")
        self.assertIsNone(fields["trading_hours"])
        self.assertEqual(len(missing), len(fcs.FIELD_LABELS))

    def test_extraction_is_deterministic(self):
        a = fcs.extract_spec_fields(SPEC_PAGE)
        b = fcs.extract_spec_fields(SPEC_PAGE)
        self.assertEqual(a, b)

    def test_minified_and_wrapped_html_extract_identically(self):
        """A page's source wrapping must not change the transcription."""
        # A real minifier collapses whitespace runs to one space; it never glues tokens.
        minified = re.sub(r"\s+", " ", SPEC_PAGE)
        # Extra wrapping inserted at an existing word boundary.
        wrapped = SPEC_PAGE.replace(" p.m. ", "\n        p.m.\n        ")
        self.assertEqual(fcs.extract_spec_fields(minified),
                         fcs.extract_spec_fields(SPEC_PAGE))
        self.assertEqual(fcs.extract_spec_fields(wrapped),
                         fcs.extract_spec_fields(SPEC_PAGE))


class TestPooledProducts(unittest.TestCase):
    def test_every_pooled_future_resolves_to_a_registered_official_url(self):
        products = fcs.pooled_products()
        self.assertEqual(len(products), 20)
        for item in products:
            self.assertTrue(item["url"], f"{item['product']} has no official spec URL")
            self.assertIn("cmegroup.com", item["url"])
            self.assertEqual(item["tier"], "official_primary")
            # Verbatim from research/sources/sources.json, which records the legal name.
            self.assertEqual(item["publisher"], "CME Group Inc.")

    def test_product_codes_are_unique(self):
        products = fcs.pooled_products()
        self.assertEqual(len({p["product"] for p in products}), len(products))


class TestHoursArtifact(unittest.TestCase):
    def test_artifact_is_rebuilt_from_records_and_omits_failures_explicitly(self):
        import json
        import tempfile

        index = {
            "_meta": {"generated_utc": "2026-09-19T00:00:00+00:00"},
            "records": [
                {
                    "product": "SI", "tradingview_symbol": "COMEX:SI1!",
                    "source_id": "CME-SPEC-SI1!", "url": "https://www.cmegroup.com/si",
                    "status": "captured", "accessed_utc": "2026-09-19T00:00:00+00:00",
                    "raw_sha256": "a" * 64, "missing_fields": [],
                    "fields": {"trading_hours": "Sun-Fri", "contract_unit": "5,000 oz",
                               "product_code": "SI", "listed_contracts": "monthly",
                               "termination_of_trading": "3rd last business day",
                               "minimum_price_fluctuation": None,
                               "settlement_method": None,
                               "additional_hours_rows": None},
                },
                {
                    "product": "PL", "tradingview_symbol": "NYMEX:PL1!",
                    "source_id": "CME-SPEC-PL1!", "url": "https://www.cmegroup.com/pl",
                    "status": "failed", "reason": "HTTP 404",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hours.json")
            original = fcs.HOURS_PATH
            try:
                from pathlib import Path
                fcs.HOURS_PATH = Path(target)
                fcs.write_hours_artifact(index)
                with open(target, encoding="utf-8") as fh:
                    doc = json.load(fh)
            finally:
                fcs.HOURS_PATH = original
        self.assertEqual(doc["_meta"]["product_count"], 1)
        self.assertEqual([p["product"] for p in doc["products"]], ["SI"])
        self.assertEqual(doc["products"][0]["globex_hours"], "Sun-Fri")
        self.assertEqual([o["product"] for o in doc["_meta"]["omitted"]], ["PL"])
        self.assertEqual(doc["_meta"]["omitted"][0]["reason"], "HTTP 404")


if __name__ == "__main__":
    unittest.main(verbosity=2)
