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


class TestZeroCaptureResilience(unittest.TestCase):
    """A 403'd runner pass must preserve the audited evidence AND stay verifiable.

    cmegroup.com answers HTTP 403 to GitHub-hosted runners (IR-33), so the committed
    capture lane periodically rewrites data/cme_specs_index.json with zero captures.
    The committed hours artifact is deliberately left untouched on such a run - which
    means the verifier's regeneration from the new index must still reproduce the
    committed artifact byte-for-byte, or main goes red on the next runner pass.
    """

    def test_a_total_403_pass_keeps_machine_rows_and_stays_regenerable(self):
        import argparse
        import json
        import shutil
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp(prefix="cme403-"))
        try:
            shutil.copytree(Path(fcs.SPECS_DIR), tmp / "specs")
            shutil.copy(Path(fcs.INDEX_PATH), tmp / "index.json")
            shutil.copy(Path(fcs.HOURS_PATH), tmp / "hours.json")
            committed_hours = json.loads((tmp / "hours.json").read_text(encoding="utf-8"))

            saved = (fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH)
            try:
                fcs.SPECS_DIR = tmp / "specs"
                fcs.INDEX_PATH = tmp / "index.json"
                fcs.HOURS_PATH = tmp / "hours.json"

                def boom(url, timeout=25):
                    raise RuntimeError(f"GET failed with every header set: {url} (timed out)")

                fcs.fetch = boom
                rc = fcs.build(argparse.Namespace(offline=False, timeout=5,
                                                  allow_failures=True))
                self.assertEqual(rc, 0)

                doc = json.loads((tmp / "index.json").read_text(encoding="utf-8"))
                by_product = {r["product"]: r for r in doc["records"]}
                machine = [r for r in doc["records"]
                           if r["status"] in ("captured", "kept_previous")
                           and (r.get("fields") or {}).get("trading_hours")]
                self.assertEqual(len(machine), 17,
                                 "the 17 adopted machine transcriptions must survive")
                for r in machine:
                    self.assertEqual(r["status"], "kept_previous")
                    self.assertEqual(r.get("body_format"), "markdown",
                                     "body_format must be carried or the verifier cannot "
                                     "dispatch the markdown extractor")
                    self.assertNotIn("retained_row", r,
                                     "a machine row must not be re-labelled hand-read")
                for product in ("BTC", "ETH", "SI"):
                    rec = by_product[product]
                    self.assertEqual(rec["status"], "failed")
                    self.assertIn("retained_row", rec)
                    # The retained explanation is preserved verbatim, not recomputed from
                    # this run's transport error, so consecutive failures are byte-stable.
                    committed_reason = next(
                        p["retained_reason"] for p in committed_hours["products"]
                        if p["product"] == product)
                    self.assertEqual(rec["retained_row"].get("retained_reason"),
                                     committed_reason)

                # The invariant the verifier checks: the artifact regenerated from the
                # post-403 index matches the committed artifact (which the run leaves
                # untouched) on every compared field.
                fcs.write_hours_artifact(doc)
                regenerated = json.loads((tmp / "hours.json").read_text(encoding="utf-8"))
                self.assertEqual(fcs.hours_artifact_divergences(regenerated,
                                                                committed_hours), [])

                # A SECOND consecutive 403 pass (its 'previous' index is now itself a
                # post-403 one, statuses kept_previous) must keep the machine rows too -
                # this exact case regressed when the carry-forward only recognised a
                # previous status of 'captured'.
                rc2 = fcs.build(argparse.Namespace(offline=False, timeout=5,
                                                   allow_failures=True))
                self.assertEqual(rc2, 0)
                doc2 = json.loads((tmp / "index.json").read_text(encoding="utf-8"))
                machine2 = [r for r in doc2["records"]
                            if r["status"] in ("captured", "kept_previous")
                            and (r.get("fields") or {}).get("trading_hours")]
                self.assertEqual(len(machine2), 17,
                                 "a second consecutive 403 pass must also keep the "
                                 "17 machine transcriptions")
                for r in machine2:
                    self.assertEqual(r["status"], "kept_previous")
                    self.assertEqual(r.get("body_format"), "markdown")
                    self.assertNotIn("retained_row", r)
                fcs.write_hours_artifact(doc2)
                regenerated2 = json.loads((tmp / "hours.json").read_text(encoding="utf-8"))
                self.assertEqual(fcs.hours_artifact_divergences(regenerated2,
                                                                committed_hours), [])
            finally:
                fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH = saved
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestMarkdownExtraction(unittest.TestCase):
    """The arena-fetch-page adoption lane parses the proxy's markdown pipe tables.

    The page-fetch proxy renders the official contractSpecs HTML to markdown; the spec
    table arrives as `| Label | Value |` rows with `<br>` markers preserved. These tests
    pin the extraction behaviour: labels resolve through the same FIELD_LABELS map as the
    HTML path, `<br>` becomes a newline, separator/empty-header rows and empty values are
    skipped, missing labels are reported, and an HTML page and its markdown rendering of
    the same table transcribe identically.
    """

    MD_PAGE = """
# Synthetic Silver

##### Futures

## Synthetic Silver Futures - Contract Specs

|     |     |
| --- | --- |
| Contract Unit | 5,000 troy ounces |
| Price Quotation | U.S. dollars and cents per troy ounce |
| Trading Hours | CME Globex:<br>Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT)<br>TAS: Sunday - Friday 6:00 p.m. - 1:25 p.m. (5:00 p.m. - 12:25 p.m. CT) |
| Minimum Price Fluctuation | 0.005 per troy ounces = $25.00 |
| Product Code | CME Globex: SYN<br>Clearing: SYN |
| Listed Contracts | Monthly contracts listed for the current year |
| Settlement Method | Deliverable |
| Termination of Trading | 12:25 p.m. CT on the third last business day of the contract month |
| TAM or TAS Rules | Synthetic TAS rules prose |
| Floating Price |  |
| Days Or Hours |  |
"""

    def test_every_label_resolves_and_br_becomes_newline(self):
        fields, missing = fcs.extract_spec_fields_markdown(self.MD_PAGE)
        self.assertEqual(fields["contract_unit"], "5,000 troy ounces")
        self.assertEqual(
            fields["trading_hours"],
            "CME Globex:\nSunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT)\n"
            "TAS: Sunday - Friday 6:00 p.m. - 1:25 p.m. (5:00 p.m. - 12:25 p.m. CT)")
        self.assertEqual(fields["termination_of_trading"],
                         "12:25 p.m. CT on the third last business day of the contract month")
        self.assertEqual(fields["listed_contracts"],
                         "Monthly contracts listed for the current year")
        self.assertEqual(fields["settlement_method"], "Deliverable")
        self.assertEqual(fields["product_code"], "CME Globex: SYN\nClearing: SYN")
        self.assertEqual(missing, [])
        self.assertIsNone(fields["additional_hours_rows"])

    def test_separator_and_empty_header_rows_and_empty_values_are_skipped(self):
        # The empty header, the | --- | --- | separator, the empty "Floating Price" and
        # "Days Or Hours" cells must not be transcribed as anything.
        fields, _ = fcs.extract_spec_fields_markdown(self.MD_PAGE)
        self.assertNotIn("", fields.values())

    def test_missing_label_is_null_and_reported(self):
        doc = self.MD_PAGE.replace(
            "| Termination of Trading | 12:25 p.m. CT on the third last business day of the contract month |\n", "")
        fields, missing = fcs.extract_spec_fields_markdown(doc)
        self.assertIsNone(fields["termination_of_trading"])
        self.assertIn("termination_of_trading", missing)

    def test_a_page_without_a_trading_hours_row_is_refused_by_the_extractor(self):
        doc = self.MD_PAGE.replace("| Trading Hours |", "| Not Hours |")
        fields, missing = fcs.extract_spec_fields_markdown(doc)
        self.assertIsNone(fields["trading_hours"])
        self.assertIn("trading_hours", missing)

    def test_markdown_and_html_of_the_same_table_transcribe_identically(self):
        html_doc = """
        <table>
          <tr><th>Contract Unit</th><td>5,000 troy ounces</td></tr>
          <tr><th>Trading Hours</th><td>CME Globex:<br>Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT)</td></tr>
          <tr><th>Termination of Trading</th><td>12:25 p.m. CT on the third last business day of the contract month</td></tr>
        </table>"""
        md_doc = """
| Contract Unit | 5,000 troy ounces |
| Trading Hours | CME Globex:<br>Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) |
| Termination of Trading | 12:25 p.m. CT on the third last business day of the contract month |
"""
        html_fields, _ = fcs.extract_spec_fields(html_doc)
        md_fields, _ = fcs.extract_spec_fields_markdown(md_doc)
        for key in ("contract_unit", "trading_hours", "termination_of_trading"):
            self.assertEqual(html_fields[key], md_fields[key], key)

    def test_extraction_is_deterministic(self):
        a = fcs.extract_spec_fields_markdown(self.MD_PAGE)
        b = fcs.extract_spec_fields_markdown(self.MD_PAGE)
        self.assertEqual(a, b)


class TestBuildFailClosed(unittest.TestCase):
    """The lane must record a transport failure, never crash on one."""

    def _run(self, fetch_stub, tmpdir):
        import argparse
        from pathlib import Path

        saved = (fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH)
        try:
            fcs.fetch = fetch_stub
            fcs.SPECS_DIR = Path(tmpdir) / "specs"
            fcs.INDEX_PATH = Path(tmpdir) / "index.json"
            fcs.HOURS_PATH = Path(tmpdir) / "hours.json"
            args = argparse.Namespace(offline=False, timeout=5, allow_failures=False)
            return fcs.build(args)
        finally:
            fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH = saved

    def test_a_transport_error_is_recorded_and_exits_two(self):
        import json
        import tempfile

        def boom(url, timeout=25):
            raise RuntimeError(f"GET failed with every header set: {url} (timed out)")

        with tempfile.TemporaryDirectory() as tmp:
            rc = self._run(boom, tmp)
            self.assertEqual(rc, 2, "a short table must exit non-zero")
            doc = json.load(open(os.path.join(tmp, "index.json")))
            self.assertEqual(doc["_meta"]["captured_count"], 0)
            self.assertEqual(doc["_meta"]["failed_count"], doc["_meta"]["product_count"])
            for rec in doc["records"]:
                self.assertEqual(rec["status"], "failed")
                self.assertIn("timed out", rec["reason"])

    def test_a_total_wipe_carries_the_previous_row_onto_the_index(self):
        """Regression guard for commit 4f5604f.

        The first run of this lane had 20/20 fetches fail, and the artifact writer rebuilt
        data/cme_product_hours.json from the capture index alone - so all three hand-read
        transcriptions (SI, ETH, BTC) were deleted and committed. build() must now leave the
        artifact untouched *and* carry each audited row onto its index record as
        ``retained_row``, which is what lets write_hours_artifact() stay a pure function of
        the index so the verifier can regenerate and compare it.
        """
        import json
        import tempfile
        from pathlib import Path

        def boom(url, timeout=25):
            raise RuntimeError(f"GET failed with every header set: {url} (timed out)")

        previous = {"products": [{
            "product": "SI", "tradingview_symbol": "COMEX:SI1!",
            "source_id": "CME-SPEC-SI1!",
            "spec_url": "https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html",
            "globex_hours": "Sunday - Friday 6:00 p.m. - 5:00 p.m. ET",
            "termination": "12:25 p.m. CT on the third last business day of the contract month",
        }]}

        with tempfile.TemporaryDirectory() as tmp:
            hours_path = Path(tmp) / "hours.json"
            hours_path.write_text(json.dumps(previous), encoding="utf-8")
            saved = fcs.HOURS_PATH
            fcs.HOURS_PATH = hours_path
            try:
                rc = self._run(boom, tmp)
                self.assertEqual(rc, 2)
                # (a) the audited transcription is not destroyed
                doc = json.loads(hours_path.read_text(encoding="utf-8"))
                self.assertEqual([r["product"] for r in doc["products"]], ["SI"])
                # (b) ... and the row was carried onto the index record
                idx = json.load(open(os.path.join(tmp, "index.json")))
                carried = {r["product"]: r.get("retained_row") for r in idx["records"]}
                self.assertIsNotNone(carried["SI"], "SI row must ride on its index record")
                self.assertTrue(carried["SI"]["retained_from_previous"])
                self.assertIn("timed out", carried["SI"]["retained_reason"])
                self.assertEqual(
                    carried["SI"]["globex_hours"], previous["products"][0]["globex_hours"])
                # a product that was never transcribed gets no phantom row
                self.assertIsNone(carried["NQ"])
                # (c) regenerating from that index reproduces the audited hours exactly
                fcs.write_hours_artifact(idx)
                again = json.loads(hours_path.read_text(encoding="utf-8"))
                self.assertEqual([r["product"] for r in again["products"]], ["SI"])
                self.assertEqual(again["products"][0]["globex_hours"],
                                 previous["products"][0]["globex_hours"])
            finally:
                fcs.HOURS_PATH = saved

    def test_provenance_keys_survive_a_rebuild(self):
        """_meta is rebuilt from scratch each run, so an honesty annotation must be carried.

        Without this the record that an earlier offline pass destroyed the per-record failure
        reasons would silently vanish on the next capture, and the carried rows would start
        quoting the overwritten "<file> not stored yet" text as if it were the finding.
        """
        import json
        import tempfile
        from pathlib import Path

        def boom(url, timeout=25):
            raise RuntimeError(f"GET failed with every header set: {url} (timed out)")

        with tempfile.TemporaryDirectory() as tmp:
            hours_path = Path(tmp) / "hours.json"
            hours_path.write_text(json.dumps({"products": [{
                "product": "SI", "tradingview_symbol": "COMEX:SI1!",
                "source_id": "CME-SPEC-SI1!",
                "spec_url": "https://www.cmegroup.com/si",
                "globex_hours": "Sunday - Friday 6:00 p.m. - 5:00 p.m. ET",
            }]}), encoding="utf-8")
            index_path = Path(tmp) / "index.json"
            index_path.write_text(json.dumps({"_meta": {
                "provenance_note": "an earlier offline pass destroyed the reasons",
                "reasons_overwritten_by_offline_pass": True,
            }, "records": []}), encoding="utf-8")
            saved = fcs.HOURS_PATH
            fcs.HOURS_PATH = hours_path
            try:
                rc = self._run(boom, tmp)
                self.assertEqual(rc, 2)
                doc = json.loads(index_path.read_text(encoding="utf-8"))
                self.assertTrue(doc["_meta"]["reasons_overwritten_by_offline_pass"])
                self.assertIn("destroyed", doc["_meta"]["provenance_note"])
                si = [r for r in doc["records"] if r["product"] == "SI"][0]
                # ... and the carried row therefore refuses to quote the bogus reason
                self.assertNotIn("not stored yet", si["retained_row"]["retained_reason"])
                self.assertIn("not recoverable", si["retained_row"]["retained_reason"])
            finally:
                fcs.HOURS_PATH = saved

    def test_a_page_without_a_trading_hours_row_is_refused(self):
        import json
        import tempfile

        def no_hours(url, timeout=25):
            return 200, b"<html><body><table><tr><th>Contract Unit</th><td>x</td></tr></table></body></html>"

        with tempfile.TemporaryDirectory() as tmp:
            rc = self._run(no_hours, tmp)
            self.assertEqual(rc, 2)
            doc = json.load(open(os.path.join(tmp, "index.json")))
            self.assertEqual(doc["_meta"]["captured_count"], 0)
            self.assertTrue(all("Trading Hours" in r["reason"] for r in doc["records"]))

    def test_a_successful_page_is_stored_hashed_and_transcribed(self):
        import hashlib
        import json
        import tempfile

        body = SPEC_PAGE.encode("utf-8")

        def ok(url, timeout=25):
            return 200, body

        with tempfile.TemporaryDirectory() as tmp:
            rc = self._run(ok, tmp)
            self.assertEqual(rc, 0)
            doc = json.load(open(os.path.join(tmp, "index.json")))
            self.assertEqual(doc["_meta"]["captured_count"], doc["_meta"]["product_count"])
            rec = doc["records"][0]
            self.assertEqual(rec["http_status"], 200)
            self.assertEqual(rec["raw_sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(rec["raw_bytes"], len(body))
            self.assertIn("Sunday - Friday", rec["fields"]["trading_hours"])
            stored = os.path.join(tmp, "specs", f"{rec['product']}.html")
            self.assertEqual(open(stored, "rb").read(), body)
            hours = json.load(open(os.path.join(tmp, "hours.json")))
            self.assertEqual(hours["_meta"]["product_count"], doc["_meta"]["product_count"])

    def test_allow_failures_exits_zero_but_still_records_the_failure(self):
        import argparse
        import json
        import tempfile

        def boom(url, timeout=25):
            raise RuntimeError("nope")

        with tempfile.TemporaryDirectory() as tmp:
            saved = (fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH)
            try:
                from pathlib import Path
                fcs.fetch = boom
                fcs.SPECS_DIR = Path(tmp) / "specs"
                fcs.INDEX_PATH = Path(tmp) / "index.json"
                fcs.HOURS_PATH = Path(tmp) / "hours.json"
                rc = fcs.build(argparse.Namespace(offline=False, timeout=5,
                                                  allow_failures=True))
            finally:
                fcs.fetch, fcs.SPECS_DIR, fcs.INDEX_PATH, fcs.HOURS_PATH = saved
            self.assertEqual(rc, 0)
            doc = json.load(open(os.path.join(tmp, "index.json")))
            self.assertEqual(doc["_meta"]["failed_count"], doc["_meta"]["product_count"])


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


class TestRetainedReasonHonesty(unittest.TestCase):
    """A carried-forward row must not launder a destroyed failure reason into a finding."""

    def test_a_live_reason_is_quoted(self):
        text = fcs.retained_reason("SI", "URLError: connection refused", {})
        self.assertIn("URLError: connection refused", text)
        self.assertIn("kept unchanged", text)

    def test_a_destroyed_reason_says_it_was_destroyed(self):
        # The first offline pass overwrote every reason with "<file> not stored yet" and the
        # commit step saved that, so the index records the loss. Quoting it verbatim would
        # present a destroyed transport error as the finding.
        meta = {"reasons_overwritten_by_offline_pass": True,
                "provenance_note": "reasons destroyed"}
        text = fcs.retained_reason("SI", "specs/SI.html not stored yet; run without --offline",
                                   meta)
        self.assertNotIn("not stored yet", text)
        self.assertIn("destroyed", text)
        self.assertIn("not recoverable", text)
        self.assertIn("kept unchanged", text)

    def test_no_reason_yet_is_not_rendered_as_none(self):
        text = fcs.retained_reason("NQ", None, {})
        self.assertNotIn("None", text)
        self.assertIn("kept unchanged", text)


class TestOfflineReproductionAudit(unittest.TestCase):
    """The stored HTML must reproduce the committed transcription - and only that.

    The audit re-extracts offline, so transport metadata legitimately differs between the
    two passes. Comparing it would fail every partial capture for a reason unrelated to
    whether the bytes still say what was transcribed.
    """

    def _rec(self, **over):
        rec = {"product": "SI", "tradingview_symbol": "COMEX:SI1!",
               "source_id": "CME-SPEC-SI1!",
               "url": "https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html",
               "status": "failed", "reason": "URLError: connection refused",
               "raw_sha256": "aa", "raw_bytes": 10,
               "fields": {"trading_hours": "Sunday - Friday 6:00 p.m. - 5:00 p.m."}}
        rec.update(over)
        return rec

    def test_transport_metadata_difference_is_not_a_divergence(self):
        net = {"records": [self._rec()]}
        off = {"records": [self._rec(
            status="failed",
            reason="specs/SI.html not stored yet; run without --offline",
            accessed_utc="2026-09-20T00:00:00+00:00",
            transport="stored_html", http_status=200,
            retained_row={"product": "SI", "globex_hours": "x"})]}
        self.assertEqual(fcs.offline_divergences(net, off), [])

    def test_an_edited_hour_is_a_divergence(self):
        net = {"records": [self._rec()]}
        off = {"records": [self._rec(
            fields={"trading_hours": "Monday - Friday 9:00 a.m. - 5:00 p.m. CT"})]}
        diff = fcs.offline_divergences(net, off)
        self.assertEqual(len(diff), 1)
        self.assertIn("SI.fields", diff[0])

    def test_a_changed_hash_is_a_divergence(self):
        net = {"records": [self._rec()]}
        off = {"records": [self._rec(raw_sha256="bb")]}
        self.assertTrue(any("raw_sha256" in d for d in fcs.offline_divergences(net, off)))

    def test_a_vanished_product_is_reported(self):
        net = {"records": [self._rec()]}
        off = {"records": []}
        diff = fcs.offline_divergences(net, off)
        self.assertTrue(any("only present in the network pass" in d for d in diff))

    def test_a_full_capture_passes_clean(self):
        net = {"records": [self._rec(status="captured", reason=None,
                                    accessed_utc="2026-09-19T00:00:00+00:00")]}
        off = {"records": [self._rec(status="captured", reason=None,
                                    accessed_utc="2026-09-19T03:00:00+00:00")]}
        self.assertEqual(fcs.offline_divergences(net, off), [])


class TestHoursArtifactAudit(unittest.TestCase):
    """The audit exists to catch an edited hour, and must not fail on run bookkeeping.

    The lane leaves data/cme_product_hours.json untouched when it transcribes nothing, so a
    fresh regeneration can never match it on _meta.generated_utc or _meta.omitted[].reason.
    A byte-for-byte comparison therefore failed every zero-capture run for a reason that had
    nothing to do with whether an hour had been edited.
    """

    def _doc(self, **over):
        doc = {"_meta": {"kind": "cme_product_hours", "generated_utc": "2026-09-19T00:00:00+00:00",
                         "product_count": 1, "engine_applies_hours": False,
                         "omitted": [{"product": "CL", "reason": "HTTP 403"}]},
               "products": [{"product": "SI", "tradingview_symbol": "COMEX:SI1!",
                             "source_id": "CME-SPEC-SI1!",
                             "spec_url": "https://www.cmegroup.com/si",
                             "globex_hours": "Sunday - Friday 6:00 p.m. - 5:00 p.m. ET",
                             "termination": "third last business day"}]}
        doc.update(over)
        return doc

    def test_run_bookkeeping_is_not_a_divergence(self):
        expected = self._doc()
        actual = self._doc()
        actual["_meta"]["generated_utc"] = "2026-09-20T09:00:00+00:00"
        actual["_meta"]["omitted"] = [{"product": "CL",
                                       "reason": "CL.html not stored yet; run without --offline"}]
        self.assertEqual(fcs.hours_artifact_divergences(expected, actual), [])

    def test_an_edited_hour_is_a_divergence(self):
        expected = self._doc()
        actual = self._doc()
        actual["products"][0]["globex_hours"] = "Monday - Friday 9:00 a.m. - 5:00 p.m. CT"
        diff = fcs.hours_artifact_divergences(expected, actual)
        self.assertEqual(len(diff), 1)
        self.assertIn("products[SI].globex_hours", diff[0])

    def test_a_dropped_product_is_a_divergence(self):
        expected = self._doc()
        actual = self._doc(products=[])
        diff = fcs.hours_artifact_divergences(expected, actual)
        self.assertTrue(any("products[SI]" in d for d in diff))

    def test_a_flipped_honesty_flag_is_a_divergence(self):
        expected = self._doc()
        actual = self._doc()
        actual["_meta"]["engine_applies_hours"] = True
        self.assertTrue(any("engine_applies_hours" in d
                            for d in fcs.hours_artifact_divergences(expected, actual)))

    def test_an_omitted_product_vanishing_is_a_divergence(self):
        expected = self._doc()
        actual = self._doc()
        actual["_meta"]["omitted"] = []
        self.assertTrue(any("_meta.omitted" in d
                            for d in fcs.hours_artifact_divergences(expected, actual)))


class TestHoursArtifactMerge(unittest.TestCase):
    """A failed fetch must not destroy a transcription a previous run audited."""

    def _write(self, index, tmp):
        """write_hours_artifact is a pure function of the index, so nothing else is passed in.

        Retained rows ride on the index record (``retained_row``) rather than being merged from
        the artifact being rebuilt - that is what lets the verifier regenerate the file and
        compare it, instead of feeding a hand-edited hour back in as its own previous value.
        """
        import json
        from pathlib import Path

        target = os.path.join(tmp, "hours.json")
        original = fcs.HOURS_PATH
        try:
            fcs.HOURS_PATH = Path(target)
            fcs.write_hours_artifact(index)
            with open(target, encoding="utf-8") as fh:
                return json.load(fh)
        finally:
            fcs.HOURS_PATH = original

    PREVIOUS = {"products": [{
        "product": "SI", "tradingview_symbol": "COMEX:SI1!",
        "source_id": "CME-SPEC-SI1!",
        "spec_url": "https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html",
        "globex_hours": "Sunday - Friday 6:00 p.m. - 5:00 p.m.",
        "termination": "third last business day",
    }]}

    def test_a_failed_product_keeps_its_previous_row_and_says_why(self):
        import tempfile

        index = {"_meta": {"generated_utc": "2026-09-19T00:00:00+00:00"},
                 "records": [{"product": "SI", "tradingview_symbol": "COMEX:SI1!",
                              "source_id": "CME-SPEC-SI1!",
                              "url": "https://www.cmegroup.com/si",
                              "status": "failed", "reason": "HTTP 403",
                              "retained_row": dict(
                                  self.PREVIOUS["products"][0],
                                  retained_from_previous=True,
                                  retained_reason=(
                                      "this run could not transcribe SI (HTTP 403); the "
                                      "previously audited row is kept unchanged"))}]}
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._write(index, tmp)
        self.assertEqual(doc["_meta"]["product_count"], 1)
        row = doc["products"][0]
        self.assertTrue(row["retained_from_previous"])
        self.assertIn("HTTP 403", row["retained_reason"])
        self.assertEqual(row["globex_hours"], "Sunday - Friday 6:00 p.m. - 5:00 p.m.")
        self.assertEqual(doc["_meta"]["retained_from_previous_count"], 1)
        self.assertEqual(doc["_meta"]["machine_transcribed_count"], 0)
        self.assertEqual(doc["_meta"]["omitted"], [])

    def test_a_product_with_no_previous_row_is_omitted_with_a_reason(self):
        import tempfile

        index = {"_meta": {"generated_utc": "2026-09-19T00:00:00+00:00"},
                 "records": [{"product": "NQ", "tradingview_symbol": "CME_MINI:NQ1!",
                              "source_id": "CME-SPEC-NQ1!",
                              "url": "https://www.cmegroup.com/nq",
                              "status": "failed", "reason": "HTTP 503"}]}
        with tempfile.TemporaryDirectory() as tmp:
            doc = self._write(index, tmp)
        self.assertEqual(doc["products"], [])
        self.assertEqual(doc["_meta"]["omitted"], [{"product": "NQ", "reason": "HTTP 503"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
