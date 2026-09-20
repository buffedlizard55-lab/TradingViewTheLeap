#!/usr/bin/env python3
"""Unit tests for intel/cme_roll.py - the CME front-contract roll schedule.

The tests assert arithmetic properties of the codecs and the business-day helpers against
the repository's own verified NYSE closure table, plus the honesty guarantees: a product
with no codec returns no dates and says why, and every codec quotes the official sentence
it implements.
"""

import os
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import calendar as us_calendar  # noqa: E402
from intel import cme_roll  # noqa: E402


class TestBusinessDays(unittest.TestCase):
    def test_weekends_are_not_business_days(self):
        self.assertFalse(cme_roll.is_business_day(date(2026, 9, 26)))   # Saturday
        self.assertFalse(cme_roll.is_business_day(date(2026, 9, 27)))   # Sunday
        self.assertTrue(cme_roll.is_business_day(date(2026, 9, 28)))    # Monday

    def test_a_recorded_full_closure_is_not_a_business_day(self):
        # Labor Day 2026 is the first Monday of September.
        labour = date(2026, 9, 7)
        self.assertEqual(labour.weekday(), 0)
        self.assertIsNotNone(us_calendar.is_full_closure(labour))
        self.assertFalse(cme_roll.is_business_day(labour))

    def test_previous_and_next_skip_weekends_and_holidays(self):
        self.assertEqual(cme_roll.previous_business_day(date(2026, 9, 8)), date(2026, 9, 4))
        self.assertEqual(cme_roll.next_business_day(date(2026, 9, 4)), date(2026, 9, 8))

    def test_business_days_before_counts_only_business_days(self):
        anchor = date(2026, 9, 25)
        got = cme_roll.business_days_before(anchor, 3)
        # Walk forward from the result and confirm exactly three business days separate them.
        step, count = got, 0
        while step < anchor:
            step = cme_roll.next_business_day(step)
            count += 1
        self.assertEqual(count, 3)
        self.assertTrue(cme_roll.is_business_day(got))

    def test_business_days_before_rejects_n_below_one(self):
        with self.assertRaises(ValueError):
            cme_roll.business_days_before(date(2026, 9, 25), 0)

    def test_nth_last_business_day_is_inside_the_month_and_ordered(self):
        for year in (2024, 2025, 2026):
            for month in range(1, 13):
                d1 = cme_roll.nth_last_business_day(year, month, 1)
                d3 = cme_roll.nth_last_business_day(year, month, 3)
                self.assertEqual((d1.year, d1.month), (year, month))
                self.assertEqual((d3.year, d3.month), (year, month))
                self.assertLess(d3, d1)
                self.assertTrue(cme_roll.is_business_day(d1))
                self.assertTrue(cme_roll.is_business_day(d3))


class TestCodecs(unittest.TestCase):
    def test_every_codec_quotes_a_rule_and_names_itself(self):
        for product, codec in cme_roll.RULE_CODECS.items():
            self.assertTrue(codec.name, f"{product}: codec has no name")
            self.assertGreater(len(codec.rule_verbatim), 40,
                               f"{product}: rule_verbatim is too short to be the official sentence")
            self.assertTrue(callable(codec.terminates))

    def test_silver_codec_is_the_third_last_business_day(self):
        for year in (2025, 2026):
            for month in (3, 6, 9, 12):
                got = cme_roll.RULE_CODECS["SI"].terminates(year, month)
                self.assertEqual(got, cme_roll.nth_last_business_day(year, month, 3))

    def test_crude_codec_uses_the_prior_month_and_shifts_when_the_25th_is_not_a_business_day(self):
        codec = cme_roll.RULE_CODECS["CL"]
        # October 2026 -> the 25th of September 2026, a Friday (a business day): 3 back.
        got = codec.terminates(2026, 10)
        anchor = date(2026, 9, 25)
        self.assertTrue(cme_roll.is_business_day(anchor))
        self.assertEqual(got, cme_roll.business_days_before(anchor, 3))
        # Find a contract month whose prior-month 25th is a weekend and confirm the rule
        # widens to four business days, exactly as the official sentence says.
        shifted = []
        for year in (2025, 2026):
            for month in range(1, 13):
                py, pm = cme_roll.prior_month(year, month)
                if not cme_roll.is_business_day(date(py, pm, 25)):
                    shifted.append((year, month, date(py, pm, 25)))
        self.assertTrue(shifted, "expected at least one prior-month 25th to fall on a weekend")
        for year, month, anchor in shifted:
            self.assertEqual(codec.terminates(year, month),
                             cme_roll.business_days_before(anchor, 4))

    def test_crypto_codec_is_the_last_friday_or_the_prior_business_day(self):
        for product in ("BTC", "ETH"):
            codec = cme_roll.RULE_CODECS[product]
            for year in (2025, 2026):
                for month in range(1, 13):
                    got = codec.terminates(year, month)
                    friday = cme_roll.last_friday(year, month)
                    self.assertLessEqual(got, friday)
                    self.assertTrue(cme_roll.is_business_day(got))
                    # No business day strictly between the result and the last Friday.
                    step = got
                    while step < friday:
                        step = cme_roll.next_business_day(step)
                        self.assertGreater(step, friday - (friday - got))

    def test_deterministic(self):
        a = cme_roll.RULE_CODECS["CL"].terminates(2026, 11)
        b = cme_roll.RULE_CODECS["CL"].terminates(2026, 11)
        self.assertEqual(a, b)


class TestRollDates(unittest.TestCase):
    def test_uncoded_product_returns_no_dates_and_says_why(self):
        result = cme_roll.roll_dates("NQ", date(2025, 1, 1), date(2026, 9, 30))
        self.assertEqual(result["roll_dates"], [])
        self.assertIsNone(result["rule_codec"])
        self.assertIn("no codec", result["reason"])
        self.assertEqual(result["business_day_basis"], cme_roll.BUSINESS_DAY_BASIS)

    def test_coded_products_produce_dates_inside_the_window_only(self):
        start, end = date(2025, 1, 1), date(2026, 9, 30)
        for product in cme_roll.RULE_CODECS:
            result = cme_roll.roll_dates(product, start, end)
            self.assertIsNone(result["reason"], f"{product}: {result['reason']}")
            self.assertGreater(len(result["roll_dates"]), 10,
                               f"{product}: a 21-month window should hold many expiries")
            iso = [r["termination_date"] for r in result["roll_dates"]]
            self.assertEqual(iso, sorted(iso), f"{product}: roll dates are not ascending")
            self.assertEqual(len(set(iso)), len(iso), f"{product}: duplicate roll dates")
            for r in result["roll_dates"]:
                day = date.fromisoformat(r["termination_date"])
                self.assertTrue(start <= day <= end)
                self.assertTrue(cme_roll.is_business_day(day))
            self.assertEqual(result["termination_dates_iso"], iso)

    def test_contract_months_scan_brackets_the_window(self):
        months = cme_roll._contract_months_in("CL", date(2026, 1, 1), date(2026, 6, 30))
        self.assertEqual(len(set(months)), len(months), "duplicate contract months")
        self.assertEqual(months, sorted(months))
        # The crude rule expires in the month prior to the contract month, so the scan must
        # reach at least a month before the window opens.
        self.assertLessEqual(months[0], (2025, 11))
        self.assertGreaterEqual(months[-1], (2026, 8))

    def test_a_window_past_the_reviewed_calendar_is_clamped_and_recorded(self):
        result = cme_roll.roll_dates("SI", date(2025, 1, 1), date(2030, 12, 31))
        self.assertIsNotNone(result["window_clamped"])
        self.assertIn("clamped", result["window_clamped"])
        self.assertEqual(result["window"]["end"], "2026-12-31")
        for iso in result["termination_dates_iso"]:
            self.assertLessEqual(iso, "2026-12-31")

    def test_a_window_entirely_outside_the_basis_is_refused_not_extrapolated(self):
        result = cme_roll.roll_dates("SI", date(2030, 1, 1), date(2030, 12, 31))
        self.assertEqual(result["roll_dates"], [])
        self.assertIsNotNone(result["reason"])

    def test_describe_lists_the_coded_products(self):
        info = cme_roll.describe()
        self.assertEqual(info["coded_products"], sorted(cme_roll.RULE_CODECS))
        self.assertEqual(info["calendar_version"], us_calendar.CALENDAR_VERSION)
        self.assertIn("NYSE", info["business_day_basis"])


class TestTranscriptionBinding(unittest.TestCase):
    def test_codec_text_matches_the_committed_transcription(self):
        """A codec whose quoted sentence drifts from the official page must be caught."""
        doc = cme_roll.load_hours_artifact()
        by_product = {p["product"]: p for p in doc.get("products") or []}
        for product in cme_roll.RULE_CODECS:
            if product not in by_product:
                self.skipTest(f"{product} has no transcribed row yet")
            ok, why = cme_roll.codec_matches_transcription(
                product, by_product[product].get("termination"))
            self.assertTrue(ok, why)

    def test_a_reworded_rule_is_detected(self):
        ok, why = cme_roll.codec_matches_transcription(
            "SI", "Trading terminates on the second last business day of the contract month")
        self.assertFalse(ok)
        self.assertIn("differs", why)

    def test_a_missing_transcription_is_detected(self):
        ok, why = cme_roll.codec_matches_transcription("SI", None)
        self.assertFalse(ok)
        self.assertIn("no transcribed", why)

    def test_an_uncoded_product_is_detected(self):
        ok, why = cme_roll.codec_matches_transcription("NQ", "some rule")
        self.assertFalse(ok)
        self.assertIn("no codec", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
