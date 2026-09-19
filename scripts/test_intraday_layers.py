#!/usr/bin/env python3
"""Unit tests for the eleventh-pass layers: Pine emulator, TV import, intraday loader, renderers.

These tests are deliberately dataset-independent: they run with or without the CI intraday
captures (only the committed synthetic fixture is required) so a regression in the fill rules,
the import audit or the page renderers fails immediately, before any capture has to land.

Run: python3 -m unittest discover -s scripts -p "test_*.py"
"""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import pine_emulator as pe  # noqa: E402
from intel import tv_import as tvi  # noqa: E402
from intel.intraday import IntradayError, load_capture  # noqa: E402

Bar = collections.namedtuple("Bar", "open high low close")


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


site = load_module("build_site_under_test", "scripts/build_site.py")


class TestPineEmulator(unittest.TestCase):
    def test_intrabar_path_follows_the_documented_ordering(self):
        self.assertEqual(pe.intrabar_path(10.0, 10.5, 9.0, 9.5),
                         ("open", "high", "low", "close"))
        self.assertEqual(pe.intrabar_path(10.0, 12.0, 9.9, 11.0),
                         ("open", "low", "high", "close"))

    def test_market_order_fills_at_the_next_bar_open(self):
        bars = [Bar(10, 11, 9, 10.5), Bar(12, 13, 11.5, 12.5), Bar(13, 14, 12, 13.5)]
        fill = pe.fill_market_order(bars, 0)
        self.assertEqual((fill.index, fill.price), (1, 12.0))
        self.assertIn("next-open", fill.reason)
        self.assertIsNone(pe.fill_market_order(bars, len(bars) - 1))

    def test_limit_inside_the_bar_range_uses_the_level(self):
        bars = [Bar(10, 11, 9, 10.5), Bar(11, 12, 10.0, 11.5)]
        fill = pe.fill_limit_order(bars, 0, 10.5, direction="long")
        self.assertEqual((fill.index, fill.price), (1, 10.5))
        self.assertIn("no-intrabar-gap", fill.reason)

    def test_limit_gapped_through_fills_at_the_next_open(self):
        bars = [Bar(10, 11, 9, 10.5), Bar(8, 8.5, 7.5, 8.0)]
        fill = pe.fill_limit_order(bars, 0, 9.5, direction="long")
        self.assertEqual((fill.index, fill.price), (1, 8.0))
        self.assertIn("gap rule", fill.reason)

    def test_limit_that_is_never_reached_does_not_fill(self):
        # Regression guard: before this test the gap branch fired whenever the bar OPENED above
        # a long limit, filling an order the market never reached.
        bars = [Bar(10, 11, 9, 10.5), Bar(10.2, 10.6, 9.8, 10.4)]
        self.assertIsNone(pe.fill_limit_order(bars, 0, 9.5, direction="long"))
        short_bars = [Bar(10, 11, 9, 10.5), Bar(9.8, 10.2, 9.5, 10.0)]
        self.assertIsNone(pe.fill_limit_order(short_bars, 0, 10.5, direction="short"))

    def test_stop_gapped_through_fills_at_the_next_open(self):
        bars = [Bar(10, 11, 9, 10.5), Bar(13, 13.5, 12.5, 13.0)]
        fill = pe.fill_stop_order(bars, 0, 12.0, direction="long")
        self.assertEqual((fill.index, fill.price), (1, 13.0))
        self.assertIn("gap rule", fill.reason)

    def test_commission_models(self):
        self.assertAlmostEqual(pe.commission_for_fill(100.0, 2.0, "percent", 0.01), 0.02)
        self.assertAlmostEqual(pe.commission_for_fill(100.0, 2.0, "cash_per_order", 5.0), 5.0)
        self.assertAlmostEqual(pe.commission_for_fill(100.0, 2.0, "cash_per_contract", 2.5), 5.0)
        with self.assertRaises(ValueError):
            pe.commission_for_fill(1.0, 1.0, "unknown", 1.0)

    def test_slippage_applied_against_the_direction(self):
        fill = pe.Fill(index=1, price=100.0, reason="test")
        self.assertAlmostEqual(fill.with_slippage("long", 2, 0.25).price, 100.5)
        self.assertAlmostEqual(fill.with_slippage("short", 2, 0.25).price, 99.5)


class TestTradingViewImport(unittest.TestCase):
    FIXTURE = os.path.join(ROOT, "data", "tv_reports", "_fixtures",
                           "synthetic_list_of_trades.csv")

    def test_committed_fixture_is_audited_row_by_row(self):
        report = tvi.import_trades(self.FIXTURE)
        self.assertEqual(report.kind, "list_of_trades")
        self.assertEqual(len(report.trades), 12)
        self.assertEqual(len(report.rejected_rows), 1)
        self.assertIn("non-positive", report.rejected_rows[0]["reason"])
        self.assertEqual(report.symbol, "CME_MINI:NQ1!")
        self.assertEqual(sum(1 for t in report.trades if t.phase == "entry"), 6)

    def test_unclassifiable_labels_are_kept_verbatim_and_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mystery.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("alpha,beta\n1,2\n")
            report = tvi.import_any(path)
            self.assertTrue(report.warnings, "unrecognised labels must be flagged, not silently kept")
            self.assertNotIn("total_net_profit", report.metrics)

    def test_gated_export_with_no_usable_values_fails_loudly(self):
        # A Strategy Report whose numbers are gated/unparsable must raise rather than import empty.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "gated.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Metric,Value\nNet Profit,n/a\nTotal Closed Trades,\n")
            with self.assertRaises(tvi.ImportError_):
                tvi.import_any(path)

    def test_performance_summary_is_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "perf.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Metric,Value\nNet Profit,1234.5\nTotal Closed Trades,42\n")
            report = tvi.import_any(path)
            self.assertEqual(report.kind, "performance_summary")
            self.assertEqual(report.metrics["total_net_profit"], 1234.5)
            self.assertEqual(report.metrics["total_closed_trades"], 42.0)


class TestIntradayLoader(unittest.TestCase):
    def _capture(self, tmp: str, tamper: bool = False) -> dict:
        document = {
            "_meta": {"kind": "intraday_vendor_capture"},
            "symbol": "TESTX",
            "interval": "15m",
            "raw_response_sha256": "a" * 64,
            "bar_count": 2,
            "bars": [[1758100000, 10.0, 10.5, 9.5, 10.2, 1000],
                     [1758100900, 10.2, 10.8, 10.1, 10.7, 1200]],
        }
        text = json.dumps(document, separators=(",", ":")) + "\n"
        if tamper:
            text = text.replace("10.7", "10.9")
        with open(os.path.join(tmp, "testx_15m.json"), "w", encoding="utf-8") as fh:
            fh.write(text)
        return {
            "symbol": "TESTX", "interval": "15m", "kind": "equity",
            "endpoint": "https://example.invalid/x", "file": "testx_15m.json",
            "stored_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "raw_response_sha256": "a" * 64, "bar_count": 2,
            "first_utc": "2026-09-17T09:06:40+00:00", "last_utc": "2026-09-17T09:21:40+00:00",
        }

    def test_valid_capture_loads_and_reports_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture = load_capture(self._capture(tmp), rel_dir=tmp)
            self.assertEqual(len(capture.bars), 2)
            self.assertEqual(capture.bars[1].close, 10.7)

    def test_tampered_file_fails_the_digest_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._capture(tmp, tamper=True)
            with self.assertRaises(IntradayError):
                load_capture(record, rel_dir=tmp)


class TestExecutiveSummaryRenderers(unittest.TestCase):
    """The exec-summary section must render from the artifact, never from hand-written rows."""

    def _artifact(self) -> dict:
        return {
            "_meta": {"pending_order_count": 2, "not_a_forecast": True,
                      "generated_utc": "2026-09-18T00:00:00Z",
                      "sizing_note": "indicative only",
                      "honesty_note": "not advice, not a forecast"},
            "divisions": {
                "futures": {
                    "division": "futures", "rule_profile": "futures_amp_sep2026", "status": "run",
                    "ranking": [{"season_rank": 1, "username": "Alpha", "season_realized_pnl_usd": 100.0,
                                 "best_edition_multiple": 2.0}],
                    "recommendations": [{
                        "username": "Alpha", "division": "futures", "model": "C5",
                        "model_name": "Capitulation pyramider", "variant": "patient",
                        "params_label": "x=1", "rule_profile": "futures_amp_sep2026",
                        "season_realized_pnl_usd": 100.0, "season_rank": 1,
                        "best_edition_multiple": 2.0, "entry_condition": "capitulation",
                        "as_of_last_bar": "2026-09-17",
                        "open_positions": [{"symbol": "NYMEX:CL1!", "side": "long",
                                            "since": "2026-09-01", "last_close": 100.0}],
                        "pending_orders": [
                            {"symbol": "CME:ETH1!", "action": "exit", "reason": "signal",
                             "decided_on": "2026-09-17", "decided_close": 2422.0,
                             "order_type": "market at next open", "sizing_rule": "no new size",
                             "indicative_size_units": None},
                            {"symbol": "CME:ETH1!", "action": "enter LONG", "reason": "reverse",
                             "decided_on": "2026-09-17", "decided_close": 2422.0,
                             "order_type": "market at next open", "sizing_rule": "rule cap",
                             "indicative_size_units": 1}],
                        "waiting_for": None, "symbols_watched": ["NYMEX:CL1!"],
                    }],
                },
                "stocks_daily": {"division": "stocks_daily", "status": "not_run",
                                 "reason": "awaiting intraday capture"},
            },
        }

    def test_orders_table_renders_every_pending_order(self):
        html = site.render_exec_orders(self._artifact(), None)
        self.assertIn("CME:ETH1!", html)
        self.assertIn("2 order(s)", html)
        self.assertIn("closes existing position", html)
        self.assertEqual(html.count('data-ord="'), 2)

    def test_cards_render_positions_and_waiting_state(self):
        html = site.render_top_performer_cards(self._artifact(), None, {}, {}, {})
        self.assertIn("Alpha", html)
        self.assertIn("NYMEX:CL1!", html)
        self.assertIn("market at next open", html)

    def test_signal_matrix_marks_missing_division_status(self):
        html = site.render_signal_matrix(self._artifact(), {}, {}, {})
        self.assertIn("not_run", html)
        self.assertIn("CME:ETH1!", html)

    def test_renderers_survive_absent_and_empty_artifacts(self):
        self.assertIn("PENDING DATA", site.render_exec_orders(None, None))
        self.assertEqual(site.render_top_performer_cards(None, None, {}, {}, {}), "")
        self.assertEqual(site.render_signal_matrix(None, {}, {}, {}), "")
        self.assertIn("Pending the intraday capture", site.render_intraday_study(None, None))
        self.assertIn("Pending", site.render_tv_benchmark(None))
        self.assertIn("Pending: intraday", site.render_stock_division(None, None))


class TestIntradayStudyRenderer(unittest.TestCase):
    def _study(self) -> dict:
        return {
            "_meta": {"kind": "intraday_study", "engine": "intraday-study-1",
                      "generated_utc": "2026-09-18T00:00:00Z", "not_a_forecast": True,
                      "methodology": ["m"], "assumptions": ["a"]},
            "coverage": [{"symbol": "MARA", "kind": "equity", "interval": "15m", "bars": 100,
                          "first_utc": "2026-08-01T13:30:00+00:00",
                          "last_utc": "2026-09-17T19:45:00+00:00",
                          "stored_sha256": "b" * 64}],
            "gap_fill": {
                "aggregate_by_kind": {"equity": {"sessions_with_gap": 10, "fill_rate_all": 0.5,
                                                 "sessions_with_gap_ge_1_atr": 2,
                                                 "fill_rate_ge_1_atr": 0.5,
                                                 "median_abs_gap_atr": 0.3,
                                                 "median_bars_to_fill": 4.0}},
                "buckets": [{"kind": "equity", "bucket": "lt_0.25_atr", "direction": "up",
                             "sessions": 5, "fill_rate": 0.6, "median_bars_to_fill": 3.0,
                             "median_fill_fraction_of_session": 0.4, "close_through_rate": 0.2}],
                "per_symbol": [{"symbol": "MARA", "kind": "equity", "interval": "15m",
                                "sessions": 11, "gaps_analyzed": 10}],
            },
            "execution_latency": {"by_kind_interval": [
                {"kind": "equity", "interval": "15m",
                 "same_session_next_open": {"observations": 0},
                 "session_boundary_next_open": {"observations": 2, "median_abs_bps": 12.5,
                                                "mean_signed_bps": 3.0,
                                                "share_above_50bps_abs": 0.0},
                 "delay_2_bar_close_delta": {"observations": 2, "median_abs_bps": 30.0,
                                             "mean_signed_bps": 10.0},
                 "delay_5_bar_close_delta": {"observations": 2, "median_abs_bps": 80.0,
                                            "mean_signed_bps": 40.0}},
            ]},
        }

    def test_study_section_renders_measured_values(self):
        html = site.render_intraday_study(self._study(), {"_meta": {"captured_count": 1}})
        self.assertIn("MARA", html)
        self.assertIn('data-icov="MARA"', html)
        self.assertIn("12.50", html)
        # an empty latency bucket must render as a dash, never as "None"
        self.assertNotIn("None", html)


class TestTvBenchmarkRenderer(unittest.TestCase):
    def test_blocked_benchmark_renders_reason_and_fixture_rows(self):
        doc = {
            "_meta": {"status": "blocked", "blocked_reason": "no export present",
                      "how_to_complete_this_benchmark": ["export the report", "commit it"],
                      "pine_emulator_rules": {"market_order_default": "next bar open",
                                              "intrabar_assumption": "open-high-low-close",
                                              "gap_rule": "next open",
                                              "source": "https://www.tradingview.com/x"}},
            "exports": [],
            "fixtures": [{"path": "data/tv_reports/_fixtures/f.csv", "is_fixture": True,
                          "trade_rows": 12, "round_trips": 6,
                          "fill_benchmark": {"status": "measured", "fills_compared": 12,
                                             "share_exact_open_match": 0.9167,
                                             "median_abs_delta_vs_bar_open_bps": 0.0,
                                             "median_abs_delta_vs_python_fill_bps": 11.9}}],
            "fixture_notice": "SYNTHETIC files written by this repository",
        }
        html = site.render_tv_benchmark(doc)
        self.assertIn("BLOCKED", html)
        self.assertIn("no export present", html)
        self.assertIn("SYNTHETIC", html)
        self.assertIn("0.9167", html)

    def test_record_without_a_fill_benchmark_does_not_crash(self):
        doc = {"_meta": {"status": "blocked", "blocked_reason": "r",
                         "how_to_complete_this_benchmark": ["x"],
                         "pine_emulator_rules": {"market_order_default": "a",
                                                 "intrabar_assumption": "b", "gap_rule": "c",
                                                 "source": "https://www.tradingview.com/y"}},
               "exports": [{"path": "data/tv_reports/broken.csv", "status": "import_failed"}],
               "fixtures": [], "fixture_notice": ""}
        html = site.render_tv_benchmark(doc)
        self.assertIn("import_failed", html)
        self.assertNotIn("None", html)


class TestCaptureTransportRetry(unittest.TestCase):
    """Regression tests for the capture-lane failures observed on a GitHub runner.

    Observed in run 35391995169: direct requests answered HTTP 429, both public relays answered
    HTTP 522, one relay closed a chunked body early (`http.client.IncompleteRead`), and that
    escaping read error killed the process before the provenance index was written -- so the
    workflow committed nothing and its steps still reported success.
    """

    @classmethod
    def setUpClass(cls):
        cls.fetch = load_module("fetch_intraday_under_test", "scripts/fetch_intraday.py")

    def _run_capture(self, tmp, failing_calls: int, always_fail: bool = False):
        """Run the fetch script offline with the first `failing_calls` HTTP calls failing."""
        import urllib.error

        state = {"calls": 0}

        def fake_get(self, url):
            state["calls"] += 1
            if always_fail or state["calls"] <= failing_calls:
                raise urllib.error.URLError(
                    "truncated response body: IncompleteRead(82203 bytes read)")
            return fake_payload(url)

        def fake_payload(url):
            import urllib.parse as up

            parsed = up.urlparse(url)
            query = up.parse_qs(parsed.query)
            ticker = parsed.path.rsplit("/", 1)[-1]
            interval = query["interval"][0]
            p1, p2 = int(query["period1"][0]), int(query["period2"][0])
            step = {"15m": 900, "1h": 3600, "1d": 86400}[interval]
            ts, price = p1 + step, 10.0
            stamps, o, h, l, c, v = [], [], [], [], [], []
            while ts <= p2 and len(stamps) < 50:
                price *= 1.0005
                stamps.append(ts)
                o.append(price)
                h.append(price * 1.01)
                l.append(price * 0.99)
                c.append(price * 1.001)
                v.append(100)
                ts += step
            return json.dumps({"chart": {"result": [{
                "meta": {"symbol": ticker, "dataGranularity": interval, "gmtoffset": -14400,
                         "exchangeTimezoneName": "America/New_York"},
                "timestamp": stamps,
                "indicators": {"quote": [{"open": o, "high": h, "low": l, "close": c,
                                          "volume": v}]}}], "error": None}}).encode()

        self.fetch.Transport._get = fake_get
        # the transport backs off between attempts; the tests exercise the retry logic, not the
        # waiting, so the clock is neutralised and the suite stays fast
        real_sleep, self.fetch.time.sleep = self.fetch.time.sleep, lambda *_: None
        out_dir = os.path.join(tmp, "intraday")
        index = os.path.join(tmp, "intraday_index.json")
        old_argv, old_symbols = sys.argv, self.fetch.stock_symbols
        sys.argv = ["fetch_intraday.py", "--interval", "1d", "--out-dir", out_dir,
                    "--index", index, "--pacing-seconds", "0"]
        self.fetch.stock_symbols = lambda: [("MARA", "MARA")]
        try:
            code = self.fetch.main()
        finally:
            sys.argv, self.fetch.stock_symbols = old_argv, old_symbols
            self.fetch.time.sleep = real_sleep
        with open(index, encoding="utf-8") as fh:
            return code, json.load(fh)

    def test_transient_transport_failure_is_retried_and_still_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, index = self._run_capture(tmp, failing_calls=3)
        self.assertEqual(code, 0)
        self.assertEqual([c["status"] for c in index["captures"]], ["captured"])
        self.assertEqual(index["_meta"]["captured_count"], 1)

    def test_a_run_that_cannot_fetch_still_writes_one_failure_record_per_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, index = self._run_capture(tmp, failing_calls=0, always_fail=True)
        self.assertEqual(code, 0, "a fully rate-limited run must still exit cleanly")
        self.assertEqual(len(index["captures"]), 1, index["captures"])
        record = index["captures"][0]
        self.assertEqual(record["status"], "failed")
        self.assertIn("IncompleteRead", record["error"])
        self.assertEqual(index["_meta"]["captured_count"], 0)
        self.assertEqual(index["_meta"]["failed_count"], 1)
        self.assertEqual(index["_meta"]["script_version"], "3")


class TestEquityCalendar(unittest.TestCase):
    def test_known_closures_and_observance(self):
        from intel import calendar as cal
        self.assertIn("Christmas", cal.is_full_closure("2021-12-24") or "")
        self.assertIn("Juneteenth", cal.is_full_closure("2022-06-20") or "")
        self.assertIsNone(cal.is_full_closure("2021-06-19"))  # not observed before 2022
        self.assertIn("New Year", cal.is_full_closure("2021-12-31") or "")
        self.assertIsNone(cal.is_full_closure("2022-01-01"))  # Saturday itself is not the closure
        self.assertIn("Bush", cal.is_full_closure("2018-12-05") or "")
        self.assertIn("Carter", cal.is_full_closure("2025-01-09") or "")
        self.assertIsNone(cal.is_full_closure("2026-09-18"))  # ordinary Friday
        self.assertIn("Good Friday", cal.is_full_closure("2026-04-03") or "")
        self.assertIn("Thanksgiving", cal.is_full_closure("2026-11-26") or "")

    def test_every_closure_is_a_weekday_and_unique(self):
        from datetime import date as date_cls
        from intel import calendar as cal
        seen: set[str] = set()
        for year in range(cal.FIRST_YEAR, cal.LAST_YEAR + 1):
            for iso in cal.holidays_for_year(year):
                self.assertLess(date_cls.fromisoformat(iso).weekday(), 5, iso)
                self.assertNotIn(iso, seen, iso)
                seen.add(iso)
        self.assertGreater(len(seen), 90)

    def test_range_guard_and_early_close_hygiene(self):
        from intel import calendar as cal
        with self.assertRaises(ValueError):
            cal.holidays_for_year(2015)
        with self.assertRaises(ValueError):
            cal.holidays_for_year(2027)
        with self.assertRaises(ValueError):
            cal.full_closures_between("2026-01-10", "2026-01-01")
        for year in range(cal.FIRST_YEAR, cal.LAST_YEAR + 1):
            full = set(cal.holidays_for_year(year))
            early = cal.early_closes_for_year(year)
            self.assertTrue(set(early) & full == set(), year)  # never both
            # the day after Thanksgiving is always an early close
            nov = [d for d in early if d.startswith(f"{year}-11-")]
            self.assertEqual(len(nov), 1, year)

    def test_describe_carries_sources_and_caveat(self):
        from intel import calendar as cal
        identity = cal.describe()
        self.assertEqual(identity["version"], cal.CALENDAR_VERSION)
        self.assertIn("https://www.nyse.com/markets/hours-calendars", identity["sources"])
        self.assertIn("re-verified", identity["verification"])


class TestCalendarAwareSessions(unittest.TestCase):
    def _bars(self, days: list[str]):
        from datetime import datetime, timezone
        from intel.intraday import IBar
        out = []
        for day in days:
            ts = int(datetime.fromisoformat(day + "T14:30:00+00:00").timestamp())
            out.append(IBar(ts, 100.0, 101.0, 99.0, 100.5, 1000))
        return tuple(out)

    def test_annotation_matches_plain_grouping_and_flags_closures(self):
        from intel.intraday import IntradayError, sessions, sessions_calendar_aware
        bars = self._bars(["2026-07-01", "2026-07-02", "2026-07-06"])
        plain = sessions(bars)
        annotated = sessions_calendar_aware(bars)
        self.assertEqual([day for day, _ in plain], [s["date"] for s in annotated])
        self.assertEqual([len(b) for _, b in plain], [s["bar_count"] for s in annotated])
        # 2026-07-03 (Friday, Independence Day observed) falls between 07-02 and 07-06.
        spanned = next(s for s in annotated if s["date"] == "2026-07-06")
        self.assertEqual(spanned["closures_spanned"], ["2026-07-03"])
        self.assertFalse(any(s["is_full_closure"] for s in annotated))

    def test_holiday_session_is_reported_not_dropped(self):
        from intel.intraday import sessions_calendar_aware
        bars = self._bars(["2026-12-24", "2026-12-25", "2026-12-28"])
        annotated = sessions_calendar_aware(bars)
        self.assertEqual(len(annotated), 3)  # nothing is deleted
        christmas = next(s for s in annotated if s["date"] == "2026-12-25")
        self.assertTrue(christmas["is_full_closure"])
        self.assertIn("Christmas", christmas["closure_name"] or "")

    def test_unknown_calendar_refuses_to_guess(self):
        from intel.intraday import IntradayError, sessions_calendar_aware
        with self.assertRaises(IntradayError):
            sessions_calendar_aware(self._bars(["2026-07-01"]), calendar_id="CME")

    def test_out_of_window_fails_closed(self):
        from intel import calendar as cal
        with self.assertRaises(ValueError):
            cal.full_closures_between("2015-12-01", "2016-02-01")
        with self.assertRaises(ValueError):
            cal.full_closures_between("2026-11-01", "2027-02-01")

    def test_study_calendar_row_counts_closure_spans(self):
        import collections
        study = load_module("run_intraday_study_under_test", "scripts/run_intraday_study.py")
        fake = collections.namedtuple("FakeCapture", "symbol kind interval bars")
        bars = self._bars(["2026-07-01", "2026-07-02", "2026-07-06"])
        gaps = [{"date": "2026-07-02"}, {"date": "2026-07-06"}]
        row = study.calendar_row_for_capture(fake("TEST", "equity", "1h", bars), gaps)
        self.assertTrue(row["calendar_applies"])
        self.assertEqual(row["sessions_on_full_closure"], 0)
        self.assertEqual(row["boundaries_spanning_closure"], 1)
        self.assertEqual(row["gaps_spanning_closure"], 1)  # only the 07-06 boundary spans 07-03
        fut = study.calendar_row_for_capture(fake("FUT", "future", "1h", bars), gaps)
        self.assertFalse(fut["calendar_applies"])
        self.assertEqual(fut["boundaries_spanning_closure"], 0)


if __name__ == "__main__":
    unittest.main()
