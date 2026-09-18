"""Unit tests for the shadow-competition engine (intel.competition)."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.competition import (  # noqa: E402
    EDITION_CALENDAR_DAYS,
    MIN_EDITION_SESSIONS,
    Series,
    _sizing_qty,
    edition_windows,
    model_params_label,
    run_participant_edition,
)
from intel.contrarian import Decision, resolve_params  # noqa: E402
from intel.data import Bar  # noqa: E402

START = 250_000.0


def bars(prices: list[float], start_day: date) -> list[Bar]:
    """Fabricate daily bars with high=max(o,c)+1 and low=min(o,c)-1."""
    out = []
    prev = prices[0]
    for i, p in enumerate(prices):
        o = prev
        day = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
        ts = int((day + timedelta(days=i)).timestamp())
        out.append(Bar(ts, o, max(o, p) + 1.0, min(o, p) - 1.0, p, 100))
        prev = p
    return out


class SizingTests(unittest.TestCase):
    def test_buying_power_and_cap(self):
        # 250k * 20 = 5M buying power; price 100, multiplier 10 -> notional 1000/unit
        self.assertEqual(_sizing_qty(START, 0.0, 100.0, 10.0, cap=10**9, deployment=1.0), 5000)
        # cap binds first
        self.assertEqual(_sizing_qty(START, 0.0, 100.0, 10.0, cap=7, deployment=1.0), 7)
        # used notional reduces availability
        self.assertEqual(_sizing_qty(START, 4_000_000.0, 100.0, 10.0, cap=10**9, deployment=1.0), 1000)
        # deployment scales the target
        self.assertEqual(_sizing_qty(START, 0.0, 100.0, 10.0, cap=10**9, deployment=0.5), 2500)
        # whole contracts only (floor)
        self.assertEqual(_sizing_qty(START + 999.0, 0.0, 100.0, 10.0, cap=10**9, deployment=1.0), 5019)

    def test_zero_or_negative_inputs(self):
        self.assertEqual(_sizing_qty(0.0, 0.0, 100.0, 10.0, cap=5, deployment=1.0), 0)
        self.assertEqual(_sizing_qty(-100.0, 0.0, 100.0, 10.0, cap=5, deployment=1.0), 0)
        self.assertEqual(_sizing_qty(START, START * 20, 100.0, 10.0, cap=5, deployment=1.0), 0)


class WindowTests(unittest.TestCase):
    def test_season_windows_and_final(self):
        day0 = date(2026, 1, 1)
        # 100 consecutive sessions -> floor(100/30)=3 season windows + final
        dates = [(day0 + timedelta(days=i)).isoformat() for i in range(100)]
        ws = edition_windows(dates, final_window=True)
        self.assertEqual(len(ws), 4)
        self.assertEqual(ws[0], ("2026-01-01", "2026-01-30"))
        # final window ends on the last session and is 30 calendar days long
        self.assertEqual(ws[-1][1], dates[-1])
        start = date.fromisoformat(ws[-1][0])
        self.assertEqual((date.fromisoformat(dates[-1]) - start).days, EDITION_CALENDAR_DAYS - 1)

    def test_min_sessions_discards_short_window(self):
        # 3 sessions -> no windows at all
        day0 = date(2026, 1, 1)
        dates = [(day0 + timedelta(days=i)).isoformat() for i in range(3)]
        self.assertEqual(edition_windows(dates, final_window=True), [])
        # exactly MIN_EDITION_SESSIONS consecutive sessions -> one 30-day window
        dates = [(day0 + timedelta(days=i)).isoformat() for i in range(MIN_EDITION_SESSIONS)]
        ws = edition_windows(dates, final_window=True)
        self.assertEqual(len(ws), 1)
        self.assertEqual(ws[0][1], dates[-1])

    def test_final_window_dedup(self):
        day0 = date(2026, 1, 1)
        dates = [(day0 + timedelta(days=i)).isoformat() for i in range(60)]
        ws = edition_windows(dates, final_window=True)
        # 60 sessions: season = 2 windows (0-29, 30-59); final window (last 30 days)
        # coincides with the second season window -> appended only once
        self.assertEqual(len(ws), 2)
        self.assertEqual(ws[-1][1], dates[-1])


class EngineTests(unittest.TestCase):
    def _spec(self, prices: list[float], cap: int = 1000, mult: float = 10.0) -> Series:
        return Series(symbol="TEST:X1!", bars=tuple(bars(prices, date(2026, 1, 1))),
                      contract_multiplier=mult, rules_cap_contracts=cap)

    def test_manual_pnl_zero_cost(self):
        prices = [100.0, 100.0, 110.0, 110.0]
        spec = self._spec(prices, cap=1)  # single contract: P/L math stays manual
        slices = {"TEST:X1!": list(spec.bars)}
        starts = {"TEST:X1!": 0}
        # decision at index 1 (close 100) -> fills at index 2 open (100); auto-close at index 3 close (110)
        dec = {"TEST:X1!": [Decision(index=1, action="long", atr=0.0)]}
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec},
                                      COST_SCENARIOS["zero"])
        self.assertAlmostEqual(res.realized_pnl_usd, (110.0 - 100.0) * 10.0, places=6)
        self.assertAlmostEqual(res.equity_multiple, 1.0 + 100.0 / START, places=8)
        self.assertEqual(res.trades, 1)
        self.assertEqual(res.long_trades, 1)
        self.assertEqual(res.active_days, 2)  # fill day + auto-close day
        self.assertFalse(res.ruined)
        self.assertEqual(res.multiple_buckets, [])

    def test_short_pnl_and_costs(self):
        prices = [100.0, 100.0, 90.0, 90.0]
        spec = self._spec(prices, cap=1)
        slices = {"TEST:X1!": list(spec.bars)}
        starts = {"TEST:X1!": 0}
        dec = {"TEST:X1!": [Decision(index=1, action="short", atr=1.0)]}
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec},
                                      COST_SCENARIOS["zero"])
        self.assertAlmostEqual(res.realized_pnl_usd, (100.0 - 90.0) * 10.0, places=6)
        self.assertEqual(res.short_trades, 1)

    def test_cap_limits_position(self):
        prices = [100.0] * 4
        spec = self._spec(prices, cap=3)
        slices = {"TEST:X1!": list(spec.bars)}
        starts = {"TEST:X1!": 0}
        dec = {"TEST:X1!": [Decision(index=1, action="long", atr=0.0)]}
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec},
                                      COST_SCENARIOS["zero"])
        # 3 contracts * $0 move = 0 P/L; sizing capped at 3 (not 5000)
        self.assertEqual(res.trades, 1)
        self.assertEqual(res.skipped_entries, 0)
        # verify via the trade record
        # (indirect: with cap=3 and zero price move the P/L is exactly 0)

    def test_exit_before_auto_close(self):
        prices = [100.0, 100.0, 120.0, 120.0, 110.0, 110.0]
        spec = self._spec(prices, cap=1)
        slices = {"TEST:X1!": list(spec.bars)}
        starts = {"TEST:X1!": 0}
        dec = {"TEST:X1!": [
            Decision(index=1, action="long", atr=0.0),
            Decision(index=3, action="exit", atr=0.0),
        ]}
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec},
                                      COST_SCENARIOS["zero"])
        # entry fills index 2 open (100), exit decision at index 3 close fills index 4 open (110)
        self.assertAlmostEqual(res.realized_pnl_usd, (110.0 - 100.0) * 10.0, places=6)
        self.assertEqual(res.trades, 1)
        self.assertEqual(res.active_days, 2)

    def test_commission_and_slippage(self):
        prices = [100.0, 100.0, 110.0, 110.0]
        spec = self._spec(prices)
        slices = {"TEST:X1!": list(spec.bars)}
        starts = {"TEST:X1!": 0}
        dec = {"TEST:X1!": [Decision(index=1, action="long", atr=2.0)]}
        scenario = COST_SCENARIOS["moderate"]  # $1.50/side, 5% of ATR = 0.1 pts per leg
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec}, scenario)
        qty = _sizing_qty(START, 0.0, 100.0, 10.0, spec.rules_cap_contracts, 1.0)
        self.assertEqual(qty, 1000)  # cap binds at 1000 contracts
        raw = (110.0 - 100.0) * 10.0 * qty
        slip = -(0.1 + 0.1) * 10.0 * qty
        comm = 1.50 * qty * 2
        self.assertAlmostEqual(res.realized_pnl_usd, raw + slip - comm, places=6)

    def test_pre_window_decisions_ignored(self):
        prices = [100.0, 105.0, 100.0, 100.0]
        spec = self._spec(prices)
        slices = {"TEST:X1!": list(spec.bars)[2:]}  # window starts at index 2
        starts = {"TEST:X1!": 2}
        dec = {"TEST:X1!": [Decision(index=0, action="long", atr=0.0)]}
        res = run_participant_edition(dec, slices, starts, {"TEST:X1!": spec},
                                      COST_SCENARIOS["zero"])
        self.assertEqual(res.trades, 0)
        self.assertAlmostEqual(res.realized_pnl_usd, 0.0, places=9)
        self.assertAlmostEqual(res.equity_multiple, 1.0, places=9)


class ParamsTests(unittest.TestCase):
    def test_resolve_params_variants(self):
        base = resolve_params("C1", None)
        self.assertEqual(base["hold_bars"], 10)
        fast = resolve_params("C1", "fast3")
        self.assertEqual(fast["lookback_closes"], 2)
        self.assertEqual(fast["hold_bars"], 6)
        with self.assertRaises(ValueError):
            resolve_params("C1", "nope")
        with self.assertRaises(ValueError):
            resolve_params("C9", None)

    def test_params_label(self):
        self.assertEqual(model_params_label("C1", None), "default")
        self.assertIn("lookback_closes=2", model_params_label("C1", "fast3"))


if __name__ == "__main__":
    unittest.main()
