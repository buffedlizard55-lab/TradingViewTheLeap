"""Regression tests. All prices below are SYNTHETIC, never market evidence."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from intel.competition import Series, RULE_PROFILES, run_participant_window, run_participant_edition
from intel.backtest import COST_SCENARIOS
from intel.contrarian import Decision
from intel.data import Bar
from intel.intraday import _validate_bars, IntradayError
from intel.tv_import import _parse_float
from fetch_official_bars import fetch
from tv_benchmark import index_of_timestamp


class ExecutionRegression(unittest.TestCase):
    def setUp(self):
        self.bars = [Bar(1767225600 + i * 3600, o, max(o, c), min(o, c), c, 10)
                     for i, (o, c) in enumerate([(100, 100), (100, 105), (120, 180)])]
        self.spec = Series("TEST", tuple(self.bars), 1, 1)

    def run_engine(self, decisions, modern=True, scenario="zero", latency=0):
        args = ( {"TEST": decisions}, {"TEST": self.bars}, {"TEST": 0}, {"TEST": self.spec})
        if modern:
            return run_participant_window(*args, RULE_PROFILES["futures_amp_sep2026"],
                                          COST_SCENARIOS[scenario], latency_bars=latency)
        return run_participant_edition(*args, COST_SCENARIOS[scenario])

    def test_intraday_exit_at_open_not_close(self):
        r = self.run_engine([Decision(0, "long", 0), Decision(1, "exit", 0)])
        self.assertEqual(r.realized_pnl_usd, 20)
        self.assertEqual(r.active_days, 1)

    def test_terminal_close_still_uses_close(self):
        r = self.run_engine([Decision(0, "long", 0)])
        self.assertEqual(r.realized_pnl_usd, 80)

    def test_future_decisions_cannot_change_terminal_slippage(self):
        base = [Decision(0, "long", 1)]
        with_future = base + [Decision(999, "exit", 900)]
        for modern in (True, False):
            # Legacy is a daily engine: use distinct dates for its regression.
            if not modern:
                for i, b in enumerate(self.bars):
                    b.date = f"2026-01-0{i+1}"
            a = self.run_engine(base, modern, "moderate")
            b = self.run_engine(with_future, modern, "moderate")
            self.assertEqual(a.realized_pnl_usd, b.realized_pnl_usd)

    def test_latency_delays_and_expires(self):
        r = self.run_engine([Decision(0, "long", 0)], latency=1)
        self.assertEqual(r.realized_pnl_usd, 60)
        r = self.run_engine([Decision(0, "long", 0)], latency=2)
        self.assertEqual(r.trades, 0)
        self.assertEqual(r.expired_orders, 1)
        for latency in (-1, 0.5, True):
            with self.assertRaises(ValueError):
                self.run_engine([], latency=latency)

    def test_no_same_day_intraday_timestamp_guess(self):
        self.assertIsNone(index_of_timestamp(self.bars, "2026-01-01 00:30:00"))
        self.assertIsNone(index_of_timestamp(self.bars, "2026-01-01"))


class SourceRegression(unittest.TestCase):
    def test_nonfinite_or_fractional_values_rejected(self):
        for column, value in ((0, 1.2), (1, float("inf")), (5, float("nan")), (5, 1.5), (0, True)):
            row = [1767225600, 100, 101, 99, 100, 10]
            row[column] = value
            with self.assertRaises(IntradayError):
                _validate_bars([row], "TEST", "15m")
        for value in ("nan", "inf", "-inf"):
            self.assertIsNone(_parse_float(value))

    def test_direct_paginated_capture_and_raw_hashes(self):
        urls = []
        pages = [
            {"bars": {"TEST": [{"t": "2026-01-01T00:00:00Z", "o": 100, "h": 101, "l": 99, "c": 100, "v": 10}]}, "next_page_token": "page2"},
            {"bars": {"TEST": [{"t": "2026-01-01T00:15:00Z", "o": 100, "h": 102, "l": 99, "c": 101, "v": 20}]}, "next_page_token": None}]
        def opener(request, timeout):
            urls.append(request.full_url)
            return io.BytesIO(json.dumps(pages.pop(0)).encode())
        with tempfile.TemporaryDirectory() as td:
            rows, chunks = fetch("TEST", "15m", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", {}, Path(td), opener)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(list(Path(td).glob("*.json"))), 2)
            self.assertTrue(all(u.startswith("https://data.alpaca.markets/") for u in urls))
            self.assertIn("page_token=page2", urls[1])
            self.assertEqual(chunks[0]["transport"], "direct_https")


if __name__ == "__main__":
    unittest.main()
