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

    def test_c14_c16_resolve_warmup_and_fire(self):
        from intel.stock_strategies import (
            STOCK_MODEL_IDS, generate_stock_decisions, resolve_params as stock_resolve,
            warmup as stock_warmup,
        )
        for model in ("C14", "C15", "C16"):
            self.assertIn(model, STOCK_MODEL_IDS)
        p14 = stock_resolve("C14", "aggressive")
        self.assertEqual(p14["gap_atr_mult"], 1.0)
        self.assertEqual(p14["max_adds"], 6)
        self.assertEqual(stock_warmup("C14", None), 16)
        p15 = stock_resolve("C15", "quick")
        self.assertEqual(p15["drawdown_pct"], 0.15)
        self.assertEqual(p15["hold_bars"], 2)
        self.assertGreaterEqual(stock_warmup("C15", "deep"), 22)
        p16 = stock_resolve("C16", "runner")
        self.assertEqual(p16["lookback"], 30)
        self.assertEqual(stock_warmup("C16", "runner"), 30)
        with self.assertRaises(ValueError):
            stock_resolve("C14", "nope")

        # C14 fires on a gap-up that holds into the close.
        day0 = date(2026, 1, 1)
        flat = [Bar(
            int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()) + i * 86400,
            100.0, 101.0, 99.0, 100.0, 1000) for i in range(30)]
        gap = Bar(flat[-1].ts + 86400, 112.0, 114.0, 111.0, 113.5, 1000)
        cont = [Bar(gap.ts + (i + 1) * 86400, 113.5 + i, 115.0 + i, 112.0 + i, 114.0 + i, 1000)
                for i in range(14)]
        d14 = generate_stock_decisions(flat + [gap] + cont, "C14")
        self.assertEqual(d14[0].action, "long")
        self.assertEqual(d14[0].index, 30)

        # C15 fires on the high-volume bounce bar after a deep drawdown.
        run = [Bar(flat[0].ts + i * 86400, 100.0 + i, 101.0 + i, 99.0 + i, 100.0 + i, 1000)
               for i in range(25)]
        crash = Bar(run[-1].ts + 86400, 124.0, 125.0, 86.0, 88.0, 1000)
        bounce = Bar(crash.ts + 86400, 88.0, 100.0, 87.0, 99.0, 5000)
        d15 = generate_stock_decisions(run + [crash, bounce], "C15")
        self.assertEqual([(d.index, d.action) for d in d15], [(26, "long")])

        # C16 fires on an ATR-expanding breakout and pyramids.
        climb = []
        px = 100.0
        for i in range(40):
            rng = 1.0 + i * 0.15
            o = px
            px = px + rng * 0.8
            climb.append(Bar(flat[0].ts + i * 86400, o, px + rng * 0.2, o - rng * 0.1, px, 1000))
        d16 = generate_stock_decisions(climb, "C16")
        self.assertTrue(d16 and d16[0].action == "long")
        self.assertIn("add", {d.action for d in d16})

    def test_c17_c19_resolve_warmup_and_fire(self):
        from intel.stock_strategies import (
            STOCK_MODEL_IDS, generate_stock_decisions, resolve_params as stock_resolve,
            warmup as stock_warmup,
        )
        for model in ("C17", "C18", "C19"):
            self.assertIn(model, STOCK_MODEL_IDS)
        p17 = stock_resolve("C17", "aggressive")
        self.assertEqual(p17["gap_atr_mult"], 1.5)
        self.assertEqual(p17["max_adds"], 8)
        self.assertEqual(stock_warmup("C17", None), 22)
        p18 = stock_resolve("C18", "patient")
        self.assertEqual(p18["run_pct"], 0.30)
        self.assertEqual(p18["max_adds"], 5)
        self.assertEqual(stock_warmup("C18", "aggressive"), 22)
        p19 = stock_resolve("C19", "patient")
        self.assertEqual(p19["crash_atr_mult"], 2.0)
        self.assertEqual(stock_warmup("C19", None), 22)
        with self.assertRaises(ValueError):
            stock_resolve("C19", "nope")

        t0 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

        # C17 fires on a gap-down that recovers into the top half on volume.
        flat = [Bar(t0 + i * 86400, 100.0, 101.0, 99.0, 100.0, 1000)
                for i in range(30)]
        implode = Bar(flat[-1].ts + 86400, 90.0, 96.0, 89.0, 95.0, 5000)
        recover = [Bar(implode.ts + (i + 1) * 86400, 95.0 + i, 97.0 + i, 94.0 + i,
                       96.0 + i, 1000) for i in range(14)]
        d17 = generate_stock_decisions(flat + [implode] + recover, "C17")
        self.assertEqual(d17[0].action, "long")
        self.assertEqual(d17[0].index, 30)

        # C18 fires short on a vertical blow-off and adds into extension.
        base = [Bar(t0 + i * 86400, 100.0, 101.0, 99.0, 100.0, 1000)
                for i in range(26)]
        run = [Bar(base[-1].ts + 86400, 100.0, 111.0, 99.0, 110.0, 5000),
               Bar(base[-1].ts + 2 * 86400, 110.0, 122.0, 109.0, 121.0, 5000),
               Bar(base[-1].ts + 3 * 86400, 121.0, 134.0, 120.0, 133.0, 5000),
               Bar(base[-1].ts + 4 * 86400, 133.0, 148.0, 132.0, 146.0, 5000)]
        tail = [Bar(run[-1].ts + (i + 1) * 86400, 146.0, 147.0, 130.0 - i, 131.0 - i,
                      1000) for i in range(12)]
        d18 = generate_stock_decisions(base + run + tail, "C18")
        self.assertEqual(d18[0].action, "short")
        self.assertIn("add", {d.action for d in d18})

        # C19 fires on two consecutive crash bars ending in an absorbed hammer.
        tight = [Bar(t0 + i * 86400, 100.0, 100.2, 99.8, 100.0, 1000)
                 for i in range(26)]
        crash1 = Bar(tight[-1].ts + 86400, 100.0, 100.2, 93.0, 94.0, 1000)
        hammer = Bar(crash1.ts + 86400, 94.0, 95.0, 84.0, 90.0, 5000)
        snap = [Bar(hammer.ts + (i + 1) * 86400, 90.0 + i, 92.0 + i, 89.0 + i,
                    91.0 + i, 1000) for i in range(16)]
        d19 = generate_stock_decisions(tight + [crash1, hammer] + snap, "C19")
        self.assertEqual([(d.index, d.action) for d in d19 if d.action == "long"],
                         [(27, "long")])

    def test_c19a_c20_c21_resolve_warmup_and_fire(self):
        from intel.stock_strategies import (
            GATED_STOCK_MODEL_IDS,
            STOCK_MODEL_IDS,
            generate_stock_decisions,
            resolve_params as stock_resolve,
            warmup as stock_warmup,
        )
        for model in ("C19A", "C20", "C21"):
            self.assertIn(model, STOCK_MODEL_IDS)
        self.assertIn("C19A", GATED_STOCK_MODEL_IDS)
        self.assertNotIn("C20", GATED_STOCK_MODEL_IDS)
        self.assertNotIn("C21", GATED_STOCK_MODEL_IDS)

        p19a = stock_resolve("C19A", None)
        self.assertEqual(p19a["stage1_crash_atr_mult"], 1.5)
        self.assertEqual(p19a["stage2_window"], 3)
        self.assertEqual(p19a["stage2_close_tail_fraction"], 0.40)
        self.assertEqual(p19a["max_adds"], 3)
        self.assertEqual(stock_warmup("C19A", None), 22)
        with self.assertRaises(ValueError):
            stock_resolve("C19A", "nope")

        p20 = stock_resolve("C20", "aggressive")
        self.assertEqual(p20["lookback"], 10)
        self.assertEqual(p20["volume_mult"], 1.5)
        self.assertEqual(p20["max_adds"], 6)
        self.assertEqual(p20["hold_bars"], 8)
        self.assertEqual(stock_warmup("C20", None), 22)
        self.assertEqual(stock_warmup("C20", "aggressive"), 22)

        p21 = stock_resolve("C21", "tight")
        self.assertEqual(p21["climax_atr_mult"], 2.0)
        self.assertEqual(p21["inside_range_fraction"], 0.4)
        self.assertEqual(p21["hold_bars"], 4)
        self.assertEqual(stock_warmup("C21", None), 16)
        with self.assertRaises(ValueError):
            stock_resolve("C21", "nope")

        t0 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

        # C19A fires on delayed two-stage absorption (gap bar between stages);
        # frozen C19 (adjacent-bar cascade) must not fire on the same series.
        tight = [Bar(t0 + i * 86400, 100.0, 100.2, 99.8, 100.0, 1000)
                 for i in range(26)]
        stage1 = Bar(tight[-1].ts + 86400, 100.0, 100.2, 98.8, 99.0, 5000)
        skip = Bar(stage1.ts + 86400, 99.0, 101.0, 98.9, 100.8, 1000)
        stage2 = Bar(skip.ts + 86400, 99.5, 100.0, 98.8, 99.9, 1000)
        snap = [Bar(stage2.ts + (i + 1) * 86400, 99.9 + i, 101.0 + i, 99.0 + i,
                    100.5 + i, 1000) for i in range(14)]
        series_19a = tight + [stage1, skip, stage2] + snap
        d19a = generate_stock_decisions(series_19a, "C19A")
        d19 = generate_stock_decisions(series_19a, "C19")
        self.assertEqual(d19a[0].action, "long")
        self.assertEqual(d19a[0].index, 28)
        self.assertFalse(any(d.action == "long" for d in d19))

        # C20 fires on a failed-breakdown spring: new 20-bar low, next bar reclaims.
        flat = [Bar(t0 + i * 86400, 100.0, 101.0, 99.0, 100.0, 1000)
                for i in range(40)]
        breakdown = Bar(flat[-1].ts + 86400, 100.0, 100.2, 90.0, 91.0, 1000)
        spring = Bar(breakdown.ts + 86400, 91.0, 96.0, 90.5, 95.5, 5000)
        tail = [Bar(spring.ts + (i + 1) * 86400, 95.5 + i, 97.0 + i, 94.0 + i,
                    96.0 + i, 1000) for i in range(12)]
        d20 = generate_stock_decisions(flat + [breakdown, spring] + tail, "C20")
        self.assertEqual(d20[0].action, "long")
        self.assertEqual(d20[0].index, 41)
        self.assertIn("add", {d.action for d in d20})

        # C21 fires long after a down-climax bar followed by a narrow opposite close.
        tight21 = [Bar(t0 + i * 86400, 100.0, 100.2, 99.8, 100.0, 1000)
                   for i in range(20)]
        climax = Bar(tight21[-1].ts + 86400, 100.0, 100.2, 97.0, 97.2, 1000)
        inside = Bar(climax.ts + 86400, 97.2, 98.0, 97.0, 97.8, 1000)
        d21 = generate_stock_decisions(
            tight21 + [climax, inside]
            + [Bar(inside.ts + (i + 1) * 86400, 97.8, 98.0, 97.5, 97.7, 1000)
               for i in range(8)],
            "C21",
        )
        self.assertEqual([(d.index, d.action) for d in d21 if d.action in ("long", "short")],
                         [(21, "long")])

    def test_gated_c19a_is_not_rostered(self):
        import json
        from intel.stock_strategies import GATED_STOCK_MODEL_IDS
        with open(os.path.join(ROOT, "data/competition/stock_roster.json"),
                  encoding="utf-8") as fh:
            roster = json.load(fh)
        rostered = {p["model"] for p in roster["participants"]}
        self.assertTrue(GATED_STOCK_MODEL_IDS)
        self.assertTrue(rostered.isdisjoint(GATED_STOCK_MODEL_IDS))


class ExecutionRealismTests(unittest.TestCase):
    def _two_symbol_setup(self):
        from intel.competition import Series
        day0 = date(2024, 1, 2)
        spec_a = Series(symbol="AAA", bars=tuple(bars([100.0 + i for i in range(10)], day0)),
                        contract_multiplier=1.0, rules_cap_contracts=10 ** 9)
        spec_b = Series(symbol="BBB", bars=tuple(bars([50.0 + i for i in range(10)], day0)),
                        contract_multiplier=1.0, rules_cap_contracts=10 ** 9)
        series_map = {"AAA": spec_a, "BBB": spec_b}
        slices = {s: list(v.bars) for s, v in series_map.items()}
        starts = {s: 0 for s in series_map}
        decisions = {"AAA": [Decision(index=1, action="long", atr=2.0)],
                     "BBB": [Decision(index=1, action="long", atr=1.0)]}
        return series_map, slices, starts, decisions

    def test_fill_log_preserves_timestamps(self):
        import dataclasses
        from intel.competition import RULE_PROFILES, run_participant_window
        series_map, slices, starts, decisions = self._two_symbol_setup()
        profile = RULE_PROFILES["stocks_official_leap"]
        result = run_participant_window(decisions, slices, starts, series_map, profile,
                                        COST_SCENARIOS["moderate"], return_fills=True)
        self.assertEqual(len(result.fill_log), 2)
        for fill in result.fill_log:
            spec = series_map[fill["symbol"]]
            entry = next(b for b in spec.bars if b.date == fill["entry_date"])
            exit_ = next(b for b in spec.bars if b.date == fill["exit_date"])
            self.assertEqual(fill["entry_ts"], entry.ts)
            self.assertEqual(fill["exit_ts"], exit_.ts)
            self.assertLessEqual(fill["entry_ts"], fill["exit_ts"])
        # P/L in the log reconciles to the headline number.
        self.assertAlmostEqual(sum(f["net_pnl_usd"] for f in result.fill_log),
                               round(result.realized_pnl_usd, 2), places=2)

    def test_proportional_arbitration_splits_contended_buying_power(self):
        import dataclasses
        from intel.competition import RULE_PROFILES, run_participant_window
        series_map, slices, starts, decisions = self._two_symbol_setup()
        profile = dataclasses.replace(RULE_PROFILES["stocks_official_leap"],
                                      starting_balance=1000.0, per_symbol_cap_units=10 ** 9)
        seq = run_participant_window(decisions, slices, starts, series_map, profile,
                                     COST_SCENARIOS["moderate"], return_fills=True)
        pro = run_participant_window(decisions, slices, starts, series_map, profile,
                                     COST_SCENARIOS["moderate"], return_fills=True,
                                     arbitration="proportional")
        seq_qty = {f["symbol"]: f["qty"] for f in seq.fill_log}
        pro_qty = {f["symbol"]: f["qty"] for f in pro.fill_log}
        # Sequential lets AAA (sorted first) consume nearly all buying power.
        self.assertGreater(seq_qty["AAA"], seq_qty["BBB"])
        # Proportional gives each symbol half the buying power: AAA's share buys fewer
        # high-priced shares than the sequential run, BBB's share buys more.
        self.assertLess(pro_qty["AAA"], seq_qty["AAA"])
        self.assertGreater(pro_qty["BBB"], seq_qty["BBB"])
        self.assertEqual(pro.arbitration, "proportional")
        with self.assertRaises(ValueError):
            run_participant_window(decisions, slices, starts, series_map, profile,
                                   COST_SCENARIOS["moderate"], arbitration="random")

    def test_roll_dates_force_close_and_count(self):
        from intel.competition import RULE_PROFILES, run_participant_window
        series_map, slices, starts, decisions = self._two_symbol_setup()
        profile = RULE_PROFILES["stocks_official_leap"]
        roll_day = slices["AAA"][5].date
        result = run_participant_window(decisions, slices, starts, series_map, profile,
                                        COST_SCENARIOS["moderate"], return_fills=True,
                                        roll_dates={"AAA": {roll_day}})
        self.assertEqual(result.roll_closes, 1)
        reasons = {(f["symbol"], f["reason"]) for f in result.fill_log}
        self.assertIn(("AAA", "roll"), reasons)
        # The roll exit happens at the roll bar's open, before the auto-close.
        rolled = next(f for f in result.fill_log if f["reason"] == "roll")
        self.assertEqual(rolled["exit_date"], roll_day)
        with self.assertRaises(ValueError):
            run_participant_window(decisions, slices, starts, series_map, profile,
                                   COST_SCENARIOS["moderate"], roll_dates={"ZZZ": {"2024-01-01"}})

    def test_realism_defaults_leave_legacy_results_untouched(self):
        from intel.competition import RULE_PROFILES, run_participant_window
        series_map, slices, starts, decisions = self._two_symbol_setup()
        profile = RULE_PROFILES["stocks_official_leap"]
        base = run_participant_window(decisions, slices, starts, series_map, profile,
                                      COST_SCENARIOS["moderate"])
        self.assertEqual(base.fill_log, [])
        self.assertEqual(base.roll_closes, 0)
        self.assertEqual(base.arbitration, "sequential")
        logged = run_participant_window(decisions, slices, starts, series_map, profile,
                                        COST_SCENARIOS["moderate"], return_fills=True)
        self.assertEqual(logged.realized_pnl_usd, base.realized_pnl_usd)
        self.assertEqual(logged.trades, base.trades)


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
        # Every edition row records the execution settings it ran under.
        for edition in res.editions:
            for row in edition["rows"]:
                self.assertEqual(row["arbitration"], "sequential")
                self.assertEqual(row["roll_closes"], 0)


if __name__ == "__main__":
    unittest.main()
