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
from intel.competition import RULE_PROFILES, Series  # noqa: E402
from intel.data import Bar  # noqa: E402
from intel.forward_ledger import build_futures_division, build_ledger  # noqa: E402

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
        self.assertEqual(meta["engine"], "forward-ledger-2")
        self.assertTrue(meta["not_a_forecast"])
        self.assertIn("not investment advice", meta["honesty_note"])
        self.assertEqual(meta["latest_edition_cross_checks"], 2)
        # No futures bundle -> the futures division is an explicit not_run with a reason,
        # and the futures price source is not cited.
        fut = doc["divisions"]["futures"]
        self.assertEqual(fut["status"], "not_run")
        self.assertTrue(fut["reason"])
        self.assertNotIn("YAHOO-FUTURES-CHART", meta["source_ids"])
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


def _synthetic_futures_world(rows=None):
    """Futures bundle: C1 fires on the engineered crash; C1-on-flat never fires."""
    t0, step = T0, 86400

    def flat(n, price, start=0):
        return [Bar(t0 + (start + i) * step, price, price + 0.5, price - 0.5, price, 1000)
                for i in range(n)]

    bars = flat(65, 100.0)
    bars.append(Bar(t0 + 65 * step, 100.0, 101.0, 89.0, 90.0, 9999))  # capitulation bar
    bars += flat(15, 90.0, start=66)
    crash = Series("FUT1", tuple(bars), contract_multiplier=1.0, rules_cap_contracts=5)
    quiet_bars = flat(80, 100.0)
    quiet = Series("FUT2", tuple(quiet_bars), contract_multiplier=1.0, rules_cap_contracts=5)
    series_map = {"FUT1": crash, "FUT2": quiet}
    roster = {
        "_meta": {"kind": "competition_roster", "created_utc": "2026-09-22"},
        "participants": [
            {"username": "CrashCarl", "model": "C1", "variant": None, "pool": ["FUT1"]},
            {"username": "FlatFran", "model": "C1", "variant": None, "pool": ["FUT2"]},
        ],
    }
    if rows is None:
        rows = [
            {"username": "CrashCarl", "realized_pnl_usd": 0.0},
            {"username": "FlatFran", "realized_pnl_usd": 0.0},
        ]
    competition = {
        "_meta": {"kind": "own_shadow_competition_simulation"},
        "latest_edition": {
            "edition_id": "LATEST",
            "start_date": bars[65].date,
            "end_date": bars[-1].date,
            "rows": rows,
        },
    }
    bundle = {
        "series_map": series_map,
        "roster_doc": roster,
        "competition_doc": competition,
        "profile": RULE_PROFILES["futures_amp_sep2026"],
        "scenario": COST_SCENARIOS["moderate"],
    }
    return bundle


class TestFuturesDivision(unittest.TestCase):
    def test_futures_division_crosscheck_and_empty_ledger(self):
        # Phase 1: learn the true realized P/Ls from a first replay.
        bundle = _synthetic_futures_world()
        div1, users1, tranches1, checks1 = build_futures_division(bundle)
        self.assertEqual(div1["status"], "replayed")
        self.assertEqual(users1, 2)
        by1 = {u["username"]: u for u in div1["usernames"]}
        carl = by1["CrashCarl"]
        # The capitulation bar is present: C1 must take and close a tranche.
        self.assertGreater(carl["closed_tranches"], 0)
        self.assertGreater(carl["round_trips"], 0)
        self.assertEqual(carl["kind"], "contrarian")
        self.assertEqual(carl["roster_division"], "futures")
        self.assertEqual(carl["starting_balance_usd"], 250000.0)
        # Flat series: explicit empty ledger, never a modelled curve.
        fran = by1["FlatFran"]
        self.assertEqual(fran["closed_tranches"], 0)
        self.assertEqual(fran["tranche_ledger"], [])
        self.assertEqual(fran["realized_pnl_usd"], 0.0)
        self.assertIsNone(fran["win_rate_tranches"])

        # Phase 2: rebuild against latest_edition rows that agree - cross-checks fire.
        rows = [{"username": u["username"], "realized_pnl_usd": u["realized_pnl_usd"]}
                for u in div1["usernames"]]
        bundle2 = _synthetic_futures_world(rows=rows)
        div2, users2, tranches2, checks2 = build_futures_division(bundle2)
        self.assertEqual(checks2, 2)
        for u in div2["usernames"]:
            self.assertTrue(u.get("ledger_matches_latest_edition"), u["username"])
            summed = round(sum(r["net_pnl_usd"] for r in u["tranche_ledger"]), 2)
            self.assertEqual(summed, u["realized_pnl_usd"])
            running = 0.0
            for r in u["tranche_ledger"]:
                running = round(running + r["net_pnl_usd"], 2)
                self.assertEqual(running, r["cum_realized_pnl_usd"])
        # Window is the season artifact's own latest_edition window, not an invention.
        self.assertEqual(div2["window"]["start_date"],
                         bundle2["competition_doc"]["latest_edition"]["start_date"])
        self.assertEqual(div2["window"]["end_date"],
                         bundle2["competition_doc"]["latest_edition"]["end_date"])
        self.assertGreater(div2["window"]["sessions"], 0)
        self.assertEqual(div2["latest_edition_id"], "LATEST")
        lb = div2["leaderboard"]
        self.assertEqual([r["rank"] for r in lb], [1, 2])
        pnls = [r["realized_pnl_usd"] for r in lb]
        self.assertEqual(pnls, sorted(pnls, reverse=True))

        # Determinism: same inputs + stamp -> identical division document.
        again, u3, t3, c3 = build_futures_division(_synthetic_futures_world(rows=rows))
        self.assertEqual(json.dumps(div2, sort_keys=True), json.dumps(again, sort_keys=True))
        self.assertEqual((users2, tranches2, checks2), (u3, t3, c3))

    def test_futures_incomplete_inputs_are_not_invented(self):
        div, users, tranches, checks = build_futures_division(None)
        self.assertEqual(div["status"], "not_run")
        self.assertTrue(div["reason"])
        self.assertEqual((users, tranches, checks), (0, 0, 0))

        bundle = _synthetic_futures_world()
        bundle["competition_doc"] = {"latest_edition": {}}
        div, *_ = build_futures_division(bundle)
        self.assertEqual(div["status"], "not_run")
        self.assertIn("latest_edition", div["reason"])

        bundle = _synthetic_futures_world()
        bundle["series_map"] = {}
        div, *_ = build_futures_division(bundle)
        self.assertEqual(div["status"], "not_run")
        self.assertIn("series", div["reason"])

    def test_full_build_routes_futures_and_cites_futures_sources(self):
        captures, roster, competition = _synthetic_world()
        bundle = _synthetic_futures_world()
        doc = build_ledger(captures, roster, competition,
                           RULE_PROFILES["stocks_official_leap"],
                           COST_SCENARIOS["moderate"], "2026-09-22T00:00:00+00:00",
                           futures=bundle)
        meta = doc["_meta"]
        self.assertEqual(meta["engine"], "forward-ledger-2")
        self.assertEqual(meta["participant_count"], 4)  # 2 futures + 2 stock
        self.assertEqual(meta["rule_profiles"]["futures"]["profile_id"], "futures_amp_sep2026")
        self.assertEqual(meta["rule_profiles"]["stocks"]["profile_id"], "stocks_official_leap")
        self.assertIn("YAHOO-FUTURES-CHART", meta["source_ids"])
        self.assertIn("YAHOO-INTRADAY-CHART", meta["source_ids"])
        self.assertIn("TV-RULES-AMP-SEP2026", meta["source_ids"])
        self.assertEqual(meta["latest_edition_cross_checks"], 4)  # 2 futures + 2 stock
        self.assertEqual(list(doc["divisions"])[0], "futures")
        self.assertEqual(doc["divisions"]["futures"]["status"], "replayed")


if __name__ == "__main__":
    unittest.main()
