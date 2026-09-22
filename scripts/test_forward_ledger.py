"""Tests for intel/forward_ledger.py and the forward-test PnL ledger contract.

The ledger must be self-consistent (rows sum exactly to totals, cumulative chain
holds), must honour the roster/competition joins, must record an explicit empty
ledger for usernames with no fills, and must be reproducible at a pinned stamp.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.competition import RULE_PROFILES  # noqa: E402
from intel.data import Bar  # noqa: E402
from intel.forward_ledger import build_ledger  # noqa: E402

T0 = 1700000000


def _mk_bars(specs, t0=T0, step=86400):
    return [Bar(t0 + i * step, o, h, l, c, v)
            for i, (o, h, l, c, v) in enumerate(specs)]


def _mk_capture(symbol, interval, bars):
    return types.SimpleNamespace(symbol=symbol, interval=interval, bars=list(bars))


def _synthetic_world(season_rows=None):
    """One symbol, one roster username (C34 with a guaranteed engulfing gap)."""
    specs = [(100.0, 100.5, 99.5, 100.0, 1000)] * 40
    engulf = (112.0, 113.0, 98.0, 99.0, 5000)
    # Declining path after the engulf so the C34 short closes profitable.
    after = [(98.5 - i, 99.5 - i, 97.5 - i, 98.0 - i, 1000) for i in range(20)]
    bars = _mk_bars(specs + [engulf] + after)
    captures = {"AAA|1d": _mk_capture("AAA", "1d", bars)}
    roster = {
        "_meta": {"kind": "stock_competition_roster", "participant_count": 2,
                  "created_utc": "2026-09-22"},
        "participants": [
            {"username": "ExhaustionEzra", "kind": "contrarian", "model": "C34",
             "variant": None, "division": "daily", "pool": ["AAA"]},
            {"username": "FlatFiona", "kind": "contrarian", "model": "C32",
             "variant": None, "division": "daily", "pool": ["AAA"]},
        ],
    }
    if season_rows is None:
        season_rows = [
            {"username": "ExhaustionEzra", "realized_pnl_usd": 0.0},
            {"username": "FlatFiona", "realized_pnl_usd": 0.0},
        ]
    # The window starts ON the engulfing signal bar so its next-open fill falls inside.
    start = bars[40].date
    end = bars[-1].date
    competition = {
        "_meta": {"kind": "stock_competition_results"},
        "divisions": {
            "daily": {
                "editions": [{"edition_id": "D001", "start_date": bars[0].date,
                              "end_date": bars[39].date}],
                "latest_window": {"start_date": start, "end_date": end},
                "latest_edition": {"edition_id": "DLATEST", "rows": season_rows},
            },
        },
    }
    return captures, roster, competition


class TestForwardLedger(unittest.TestCase):
    def test_ledger_shape_and_self_consistency(self):
        # Phase 1: learn the true realized P/Ls from a first replay.
        captures, roster, competition = _synthetic_world()
        first = build_ledger(captures, roster, competition,
                             RULE_PROFILES["stocks_official_leap"],
                             COST_SCENARIOS["moderate"], "2026-09-22T00:00:00+00:00")
        first_by = {u["username"]: u for u in first["divisions"]["daily"]["usernames"]}
        season_rows = [
            {"username": "ExhaustionEzra",
             "realized_pnl_usd": first_by["ExhaustionEzra"]["realized_pnl_usd"]},
            {"username": "FlatFiona",
             "realized_pnl_usd": first_by["FlatFiona"]["realized_pnl_usd"]},
        ]
        # Phase 2: rebuild against latest_edition rows that agree - the cross-check fires.
        captures, roster, competition = _synthetic_world(season_rows=season_rows)
        doc = build_ledger(captures, roster, competition,
                           RULE_PROFILES["stocks_official_leap"],
                           COST_SCENARIOS["moderate"], "2026-09-22T00:00:00+00:00")
        meta = doc["_meta"]
        self.assertEqual(meta["kind"], "forward_test_pnl_ledger")
        self.assertEqual(meta["engine"], "forward-ledger-1")
        self.assertTrue(meta["not_a_forecast"])
        self.assertIn("not investment advice", meta["honesty_note"])
        self.assertEqual(meta["latest_edition_cross_checks"], 2)
        daily = doc["divisions"]["daily"]
        self.assertEqual(daily["status"], "replayed")
        self.assertEqual(len(daily["usernames"]), 2)

        by_user = {u["username"]: u for u in daily["usernames"]}
        ezra = by_user["ExhaustionEzra"]
        # The engulfing gap is present, so the short must trade and profit on the
        # declining follow-through.
        self.assertGreater(ezra["closed_tranches"], 0)
        self.assertGreater(ezra["realized_pnl_usd"], 0)
        summed = round(sum(r["net_pnl_usd"] for r in ezra["tranche_ledger"]), 2)
        self.assertEqual(summed, ezra["realized_pnl_usd"])
        running = 0.0
        for r in ezra["tranche_ledger"]:
            running = round(running + r["net_pnl_usd"], 2)
            self.assertEqual(running, r["cum_realized_pnl_usd"])
        self.assertEqual(ezra["winning_tranches"] + ezra["losing_tranches"]
                         + ezra["flat_tranches"], ezra["closed_tranches"])
        self.assertTrue(ezra.get("ledger_matches_latest_edition"))
        self.assertLessEqual(abs(ezra["latest_edition_delta_usd"]),
                             ezra["latest_edition_match_tolerance_usd"])

        # The hammer model on this synthetic series never fires: explicit empty ledger.
        fiona = by_user["FlatFiona"]
        self.assertEqual(fiona["tranche_ledger"], [])
        self.assertEqual(fiona["closed_tranches"], 0)
        self.assertEqual(fiona["realized_pnl_usd"], 0.0)
        self.assertIsNone(fiona["win_rate_tranches"])

        # Leaderboard is sorted and covers every username.
        lb = daily["leaderboard"]
        self.assertEqual([r["rank"] for r in lb], [1, 2])
        self.assertEqual(lb[0]["username"], "ExhaustionEzra")

        # Determinism: same inputs + stamp -> identical document.
        again = build_ledger(captures, roster, competition,
                             RULE_PROFILES["stocks_official_leap"],
                             COST_SCENARIOS["moderate"], "2026-09-22T00:00:00+00:00")
        self.assertEqual(json.dumps(doc, sort_keys=True), json.dumps(again, sort_keys=True))

    def test_missing_division_is_explicit_not_invented(self):
        captures, roster, competition = _synthetic_world()
        competition["divisions"]["hourly"] = {"status": "insufficient_history"}
        doc = build_ledger(captures, roster, competition,
                           RULE_PROFILES["stocks_official_leap"],
                           COST_SCENARIOS["moderate"], "2026-09-22T00:00:00+00:00")
        hourly = doc["divisions"]["hourly"]
        self.assertEqual(hourly["status"], "not_run")
        self.assertTrue(hourly["reason"])
        self.assertEqual(hourly["usernames"], [])


if __name__ == "__main__":
    unittest.main()
