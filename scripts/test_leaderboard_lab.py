"""Independent arithmetic/coverage tests for the placement lab; no return claims."""
import json
import math
import unittest
from datetime import datetime, timezone
from pathlib import Path

from leaderboard_lab import (
    build,
    full_leverage_winning_days,
    required_daily_compound_pct,
    round_half_up,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class LeaderboardLabTests(unittest.TestCase):
    def test_required_rate_is_compounded_not_linear(self):
        # A 10x over 12.6264 days is a compounding problem, not 900%/12.6264 days.
        rate = required_daily_compound_pct(10.0, 12.626389)
        self.assertAlmostEqual(rate, 20.004963, places=5)
        self.assertEqual(round_half_up(required_daily_compound_pct(5.0, 12.626389), 4), 13.5946)
        with self.assertRaises(ValueError):
            required_daily_compound_pct(5.0, 0)

    def test_winning_days_at_one_percent_underlying(self):
        self.assertEqual(full_leverage_winning_days(5.0, 1.0), 9)
        self.assertEqual(full_leverage_winning_days(100.0, 1.0), 26)
        with self.assertRaises(ValueError):
            full_leverage_winning_days(5.0, 0.0)

    def test_prize_ladder_reconciles_to_declared_arv(self):
        result = build()
        ladder = result["prize_ladder"]
        cfg = json.loads((ROOT / "data/contest_config.json").read_text())
        self.assertEqual(ladder["summed_cash_from_tiers_usd"], ladder["declared_cash_arv_usd"])
        self.assertEqual(ladder["declared_cash_arv_usd"], cfg["cash_prize_total_arv_usd"])
        self.assertEqual(ladder["cash_recipients"], 50)
        self.assertEqual(ladder["plan_recipients"], 250)
        self.assertEqual(ladder["prize_recipients_total"], cfg["maximum_prize_recipients"])

    def test_every_capture_row_is_recomputable(self):
        result = build()
        start = parse_utc("2026-09-01T08:00:00Z")
        end = parse_utc("2026-09-30T12:00:00Z")
        for cap in result["captures"]:
            at = parse_utc(cap["captured_at_utc"])
            elapsed = (at - start).total_seconds() / 86400
            remaining = (end - at).total_seconds() / 86400
            self.assertAlmostEqual(cap["elapsed_days_since_start"], round_half_up(elapsed, 6), places=6)
            self.assertAlmostEqual(cap["remaining_days_to_deadline"], round_half_up(remaining, 6), places=6)
            for row in cap["rows"].values():
                multiple = 1 + row["realized_profit_pct"] / 100
                self.assertAlmostEqual(row["balance_multiple"], round_half_up(multiple, 6), places=6)
                self.assertAlmostEqual(
                    row["fresh_account_required_daily_compound_pct"],
                    round_half_up(required_daily_compound_pct(multiple, remaining), 6), places=5)
                self.assertAlmostEqual(
                    row["fresh_account_required_underlying_pct_per_day_at_20x"],
                    round_half_up(required_daily_compound_pct(multiple, remaining) / 20, 6), places=5)

    def test_leverage_and_ruin_arithmetic(self):
        lm = build()["leverage_math"]
        self.assertEqual(lm["maximum_initial_notional_usd"], 250_000 * 20)
        self.assertEqual(lm["usd_per_1pct_underlying_move_at_max_notional"], 50_000)
        self.assertEqual(lm["adverse_underlying_move_pct_to_erase_the_whole_balance"], 5.0)
        self.assertEqual(lm["adverse_underlying_move_pct_to_erase_half_the_balance"], 2.5)
        self.assertFalse(lm["account_reset_allowed"])

    def test_champion_sample_counts_recomputed_from_records(self):
        result = build()
        records = json.loads((ROOT / "data/verified_explosive_returns.json").read_text())["records"]
        multiples = sorted(float(r["return_multiple"]) for r in records if r["status"] == "final")
        cs = result["champion_sample"]
        self.assertEqual(cs["completed_records"], len(multiples))
        self.assertEqual(cs["maximum_completed_multiple"], max(multiples))
        for target in result["targets"]:
            expected = sum(m >= target["balance_multiple"] for m in multiples)
            self.assertEqual(target["completed_champion_sample_at_or_above"], expected)
        self.assertEqual(cs["completed_champions_at_or_above_capture5_rank50"], 1)

    def test_daily_equity_path_matches_stated_rate(self):
        # Growth at the stated daily rate must reach the target multiple it was derived from.
        for t in build()["targets"]:
            grew = (1 + t["required_daily_compound_pct_over_remaining_window"] / 100) ** 12.626389
            self.assertLess(abs(grew - t["balance_multiple"]), 0.01)
        for row in build()["captures"][-1]["rows"].values():
            grew = (1 + row["fresh_account_required_daily_compound_pct"] / 100) ** 12.626389
            self.assertLess(abs(grew - row["balance_multiple"]), 0.01)

    def test_instrument_rows_join_capacity_and_volatility(self):
        result = build()
        capacity = {e["symbol"]: e for e in
                    json.loads((ROOT / "data/initial_capacity.json").read_text())["entries"]}
        vol = {r["symbol"]: r for r in
               json.loads((ROOT / "data/volatility_intelligence.json").read_text())["records"]}
        rank50_usd = result["captures"][-1]["rows"]["50"]["realized_profit_usd"]
        for row in result["cash_frontier_instrument_requirements"]:
            self.assertIn(row["symbol"], capacity)
            self.assertEqual(row["modeled_initial_notional_usd"],
                             capacity[row["symbol"]]["modeled_initial_notional_usd"])
            needed = 100 * rank50_usd / row["modeled_initial_notional_usd"]
            self.assertAlmostEqual(row["favorable_move_pct_needed_for_capture5_rank50_level"],
                                   round_half_up(needed, 6), places=6)
            if row["vendor_history_sessions"] is not None:
                self.assertEqual(row["vendor_history_sessions"], vol[row["symbol"]]["sessions"])
                self.assertEqual(row["history_contains_a_30d_window_as_large_as_that_requirement"],
                                 vol[row["symbol"]]["best_30d_up_move_pct"] >= needed)

    def test_artifact_freshness(self):
        self.assertEqual(json.loads((ROOT / "data/leaderboard_lab.json").read_text()), build())

    def test_no_forecast_or_strategy_language(self):
        meta = build()["_meta"]
        self.assertTrue(meta["not_a_forecast"])
        self.assertIn("not a forecast", json.dumps(meta).lower())
        self.assertIn("no tested strategy", json.dumps(build()).lower())
        self.assertTrue(all(math.isfinite(v) for v in
                            [t["required_daily_compound_pct_over_remaining_window"]
                             for t in build()["targets"]]))

    def test_site_coverage(self):
        html = (ROOT / "index.html").read_text()
        section = html.split('<section id="placement">')[1].split("</section>")[0]
        flat = " ".join(section.split())
        self.assertIn("Maximum exposure cuts both ways", flat)
        self.assertIn("It is arithmetic, not a forecast or a strategy result.", flat)
        self.assertIn("data/leaderboard_lab.json", flat)
        # the section must link to the same official pages the capture sources point at
        sources = {s["source_id"]: s["url"] for s in
                   json.loads((ROOT / "research/sources/sources.json").read_text())["sources"]}
        for sid in ("TV-CONTEST-AMP-SEP2026-R5", "TV-RULES-AMP-SEP2026-R5", "TV-THELEAP-LANDING-R5"):
            self.assertIn(f'href="{sources[sid]}"', flat)
        # every rendered figure traces back to the artifact
        lab = build()
        self.assertIn(f"{lab['captures'][-1]['rows']['50']['balance_multiple']}×", flat)
        self.assertIn(f"+{round(lab['captures'][-1]['rows']['50']['fresh_account_required_daily_compound_pct'], 2)}%/day", flat)


if __name__ == "__main__":
    unittest.main()
