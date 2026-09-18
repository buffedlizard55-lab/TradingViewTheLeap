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


if __name__ == "__main__":
    unittest.main()
