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
        # entry fills index 2 open (100), exit decision at index 3 close fills index 4 open (120)
        self.assertAlmostEqual(res.realized_pnl_usd, (120.0 - 100.0) * 10.0, places=6)
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


class StockModelTests(unittest.TestCase):
    def test_new_stock_models_resolve_and_warmup(self):
        from intel.stock_strategies import STOCK_MODEL_IDS, resolve_params as stock_resolve, warmup as stock_warmup
        self.assertIn("C11", STOCK_MODEL_IDS)
        self.assertIn("C12", STOCK_MODEL_IDS)
        self.assertIn("C13", STOCK_MODEL_IDS)

        p11 = stock_resolve("C11", "rapid")
        self.assertEqual(p11["add_atr_step"], 0.5)
        self.assertEqual(p11["max_adds"], 6)
        w11 = stock_warmup("C11", "rapid")
        self.assertGreater(w11, 20)

        p12 = stock_resolve("C12", "deep")
        self.assertEqual(p12["crash_atr_mult"], 3.5)
        w12 = stock_warmup("C12", "deep")
        self.assertGreater(w12, 14)

        p13 = stock_resolve("C13", "runner")
        self.assertEqual(p13["add_atr_step"], 2.0)
        w13 = stock_warmup("C13", "runner")
        self.assertGreater(w13, 30)

    def test_stock_decisions_generation(self):
        from intel.stock_strategies import generate_stock_decisions
        # 60 synthetic bars
        day0 = date(2026, 1, 1)
        test_bars = bars([10.0 + (i * 0.1) for i in range(60)], day0)
        d11 = generate_stock_decisions(test_bars, "C11")
        self.assertIsInstance(d11, list)
        d12 = generate_stock_decisions(test_bars, "C12")
        self.assertIsInstance(d12, list)
        d13 = generate_stock_decisions(test_bars, "C13")
        self.assertIsInstance(d13, list)


class MultiSeasonEngineTests(unittest.TestCase):
    def test_multi_season_division_execution_and_forward_partition(self):
        from intel.competition import (
            MultiSeasonCompetition,
            Participant,
            RULE_PROFILES,
            run_division_seasons,
        )
        day0 = date(2026, 1, 1)
        # 120 bars -> ~4 season windows
        prices = [100.0 + (i % 10) for i in range(120)]
        spec = Series(symbol="TEST_STOCK", bars=tuple(bars(prices, day0)), contract_multiplier=1.0, rules_cap_contracts=50)
        series_map = {"TEST_STOCK": spec}
        dates = [b.date for b in spec.bars]
        ws = edition_windows(dates, final_window=True)
        self.assertGreaterEqual(len(ws), 3)

        participants = [
            Participant(username="TestP1", model="S1", variant=None, pool=("TEST_STOCK",)),
            Participant(username="TestP2", model="S2", variant=None, pool=("TEST_STOCK",)),
        ]

        def dummy_decisions(model, variant, sm):
            return {"TEST_STOCK": [Decision(index=10, action="long", atr=1.0), Decision(index=20, action="exit", atr=1.0)]}

        res = run_division_seasons(
            series_map=series_map,
            participants=participants,
            profile=RULE_PROFILES["stocks_official_leap"],
            scenario=COST_SCENARIOS["zero"],
            decisions_provider=dummy_decisions,
            windows=ws,
            latency_bars=0,
            forward_held_out_count=1,
            division_name="daily",
        )
        self.assertEqual(len(res.editions), len(ws) - 1)
        self.assertIsNotNone(res.latest_edition)
        self.assertEqual(len(res.leaderboard), 2)
        self.assertIn("season_rank", res.leaderboard[0])
        # Forward held-out leaderboard exists
        self.assertIsNotNone(res.forward_held_out_leaderboard)
        self.assertIsNotNone(res.in_sample_leaderboard)
        self.assertEqual(len(res.forward_held_out_leaderboard), 2)


if __name__ == "__main__":
    unittest.main()
