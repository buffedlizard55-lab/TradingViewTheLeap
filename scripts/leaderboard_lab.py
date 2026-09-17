#!/usr/bin/env python3
"""Leaderboard and prize arithmetic lab — deterministic arithmetic, NOT a backtest.

Answers, from committed and independently verified sources only:

1. What P/L each publicly visible frontier needs, at every capture, expressed as a multiple of
   the 250,000 virtual starting balance and as an average accumulation rate since the start.
2. What a *fresh* account would have to compound daily, from the capture it was measured at, to
   match those levels by the 2026-09-30 12:00 UTC deadline — and what underlying move that implies
   at the rules' 20:1 futures leverage.
3. What each balance multiple (5x/10x/20x/50x/100x) demands in daily compounding over the window
   that is left, and how many consecutive full-leverage winning days at a 1% underlying move that
   equals.
4. The leverage floor/ruin arithmetic: at maximum notional a 1% underlying move is 20% of the
   starting balance and a 5% adverse move is the whole starting balance (the rules forbid resetting
   the account).
5. How the current cash-prize edge compares with the completed-edition champion sample, and how
   dense the visible board is.

Every number is either transcribed from an official source (dates, balance, leverage, prize
ladder) or arithmetic on such a number. Nothing here is a forecast, a strategy result, or a claim
that any of these levels can be reached.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_MULTIPLES = (5, 10, 20, 50, 100)
TRACKED_RANKS = (1, 50, 100, 250)
ILLUSTRATIVE_UNDERLYING_DAILY_MOVE_PCT = 1.0


def load(path: str):
    return json.loads((ROOT / path).read_text())


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def round_half_up(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return math.floor(value * factor + 0.5) / factor


def required_daily_compound_pct(multiple: float, days: float) -> float:
    """Daily growth rate that turns 1x into `multiple` over `days` days."""
    if multiple <= 0 or days <= 0:
        raise ValueError("multiple and days must be positive")
    return 100.0 * (multiple ** (1.0 / days) - 1.0)


def full_leverage_winning_days(target_multiple: float, underlying_daily_pct: float) -> int:
    """Consecutive all-in winning days needed, assuming equity compounds at leverage x move."""
    per_day_equity_gain = 1.0 + (20.0 * underlying_daily_pct / 100.0)
    if per_day_equity_gain <= 1.0:
        raise ValueError("underlying move must be positive at 20:1")
    return math.ceil(math.log(target_multiple) / math.log(per_day_equity_gain))


def build() -> dict:
    cfg = load("data/contest_config.json")
    fh = load("data/frontier_history.json")
    returns = load("data/verified_explosive_returns.json")
    capacity = load("data/initial_capacity.json")
    volatility = load("data/volatility_intelligence.json")

    balance = float(cfg["starting_balance_virtual_usd"])
    leverage = float(cfg["futures_leverage_ratio"])
    start = parse_utc(cfg["competition_start_utc"])
    end = parse_utc(cfg["competition_end_utc"])
    registration_close = parse_utc(cfg["registration_close_utc"])
    total_days = (end - start).total_seconds() / 86400.0

    # ---- prize ladder, summed straight from the official transcription -------------
    cash_sum = 0.0
    cash_recipients = 0
    plan_recipients = 0
    tiers = []
    for tier in cfg["prize_tiers"]:
        count = tier["to_rank"] - tier["from_rank"] + 1
        cash_each = tier["cash_usd_each"]
        months_each = tier["plan_months_each"]
        tiers.append({
            "from_rank": tier["from_rank"],
            "to_rank": tier["to_rank"],
            "recipients": count,
            "cash_usd_each": cash_each,
            "plan_months_each": months_each,
            "cash_tier_total_usd": None if cash_each is None else round_half_up(cash_each * count, 2),
        })
        if cash_each is not None:
            cash_sum += cash_each * count
            cash_recipients += count
        if months_each is not None:
            plan_recipients += count
    prize_ladder = {
        "tiers": tiers,
        "cash_recipients": cash_recipients,
        "plan_recipients": plan_recipients,
        "prize_recipients_total": cash_recipients + plan_recipients,
        "declared_cash_arv_usd": cfg["cash_prize_total_arv_usd"],
        "summed_cash_from_tiers_usd": round_half_up(cash_sum, 2),
        "last_cash_rank": max(t["to_rank"] for t in cfg["prize_tiers"] if t["cash_usd_each"]),
        "first_plan_only_rank": min(t["from_rank"] for t in cfg["prize_tiers"] if t["cash_usd_each"] is None),
        "top_prize_usd": tiers[0]["cash_usd_each"],
    }

    # ---- per-capture frontier arithmetic ------------------------------------------
    captures = []
    for cap in fh["captures"]:
        at = parse_utc(cap["captured_at_utc"])
        elapsed = (at - start).total_seconds() / 86400.0
        remaining = (end - at).total_seconds() / 86400.0
        reg_left = (registration_close - at).total_seconds() / 86400.0
        rows = {}
        for rank_key, row in sorted(cap["rows"].items(), key=lambda kv: int(kv[0])):
            pct = float(row["realized_profit_pct"])
            usd = float(row["realized_profit_usd"])
            multiple = 1.0 + pct / 100.0
            daily = required_daily_compound_pct(multiple, remaining)
            rows[str(int(rank_key))] = {
                "trader": row["trader"],
                "realized_profit_usd": usd,
                "realized_profit_pct": pct,
                "balance_multiple": round_half_up(multiple, 6),
                "average_usd_per_day_since_start": round_half_up(usd / elapsed, 6),
                "fresh_account_required_daily_compound_pct": round_half_up(daily, 6),
                "fresh_account_required_underlying_pct_per_day_at_20x": round_half_up(daily / leverage, 6),
            }
        captures.append({
            "captured_at_utc": cap["captured_at_utc"],
            "source_id": cap["source_id"],
            "participants_displayed": cap["participants_displayed"],
            "elapsed_days_since_start": round_half_up(elapsed, 6),
            "remaining_days_to_deadline": round_half_up(remaining, 6),
            "registration_days_left": round_half_up(reg_left, 6),
            "rows": rows,
        })

    latest = captures[-1]
    latest_rank50 = latest["rows"]["50"]

    # ---- board density ------------------------------------------------------------
    participants = latest["participants_displayed"]
    board = {
        "visible_ranks": cfg["public_leaderboard_last_visible_rank"],
        "cash_ranks": prize_ladder["cash_recipients"],
        "participants_displayed": participants,
        "visible_share_of_participants_pct": round_half_up(
            100.0 * cfg["public_leaderboard_last_visible_rank"] / participants, 6),
        "cash_share_of_participants_pct": round_half_up(100.0 * prize_ladder["cash_recipients"] / participants, 6),
        "rank50_to_rank100_gap_pct": round_half_up(
            100.0 * (latest["rows"]["50"]["realized_profit_usd"] / latest["rows"]["100"]["realized_profit_usd"] - 1.0), 6),
        "rank100_to_rank250_gap_pct": round_half_up(
            100.0 * (latest["rows"]["100"]["realized_profit_usd"] / latest["rows"]["250"]["realized_profit_usd"] - 1.0), 6),
    }

    # ---- balance-multiple targets over the remaining window ------------------------
    remaining = latest["remaining_days_to_deadline"]
    completed_multiples = sorted(
        float(r["return_multiple"]) for r in returns["records"] if r["status"] == "final")
    targets = []
    for multiple in TARGET_MULTIPLES:
        required_profit = balance * (multiple - 1)
        daily = required_daily_compound_pct(multiple, remaining)
        targets.append({
            "balance_multiple": multiple,
            "required_net_profit_usd": round_half_up(required_profit, 2),
            "required_net_profit_pct": 100 * (multiple - 1),
            "required_daily_compound_pct_over_remaining_window": round_half_up(daily, 6),
            "required_underlying_pct_per_day_at_20x": round_half_up(daily / leverage, 6),
            "full_leverage_winning_days_at_1pct_underlying": full_leverage_winning_days(
                multiple, ILLUSTRATIVE_UNDERLYING_DAILY_MOVE_PCT),
            "completed_champion_sample_at_or_above": sum(m >= multiple for m in completed_multiples),
        })

    # ---- leverage floor / ruin arithmetic ------------------------------------------
    max_notional = balance * leverage
    leverage_math = {
        "starting_balance_usd": balance,
        "leverage_ratio": leverage,
        "maximum_initial_notional_usd": max_notional,
        "usd_per_1pct_underlying_move_at_max_notional": round_half_up(max_notional * 0.01, 2),
        "pct_of_starting_balance_per_1pct_underlying_move": round_half_up(100.0 * leverage * 0.01, 6),
        "adverse_underlying_move_pct_to_erase_half_the_balance": round_half_up(50.0 / leverage, 6),
        "adverse_underlying_move_pct_to_erase_the_whole_balance": round_half_up(100.0 / leverage, 6),
        "account_reset_allowed": cfg["account_reset_allowed"],
        "note": "Arithmetic at full 20:1 exposure with no fees, no intraday margin path and no liquidation "
                "simulation. The rules forbid resetting the competition account (section 08).",
    }

    # ---- champion sample comparison ------------------------------------------------
    completed = [r for r in returns["records"] if r["status"] == "final"]
    multiples = sorted(float(r["return_multiple"]) for r in completed)
    mid = len(multiples) // 2
    median = (multiples[mid - 1] + multiples[mid]) / 2 if len(multiples) % 2 == 0 else multiples[mid]
    rank50_multiple = latest_rank50["balance_multiple"]
    champion_sample = {
        "completed_records": len(completed),
        "maximum_completed_multiple": max(multiples),
        "median_completed_multiple": round_half_up(median, 6),
        "minimum_completed_multiple": min(multiples),
        "capture5_rank50_multiple": rank50_multiple,
        "completed_champions_strictly_below_capture5_rank50": sum(m < rank50_multiple for m in multiples),
        "completed_champions_at_or_above_capture5_rank50": sum(m >= rank50_multiple for m in multiples),
        "note": "Cross-edition comparison only: the completed records span stocks, crypto, forex, multi-asset and "
                "futures editions with different rules and different participant counts. It is evidence of what has "
                "been published, not a like-for-like benchmark and not a success probability.",
    }

    # ---- what the cash-prize edge would require from the selected instruments -------
    vol_by_symbol = {r["symbol"]: r for r in volatility["records"]}
    required_rank50_move = 100.0 * latest_rank50["realized_profit_usd"]
    instruments = []
    for entry in capacity["entries"]:
        symbol = entry["symbol"]
        notional = float(entry["modeled_initial_notional_usd"])
        move_needed_pct = required_rank50_move / notional
        vol = vol_by_symbol.get(symbol)
        row = {
            "symbol": symbol,
            "modeled_initial_notional_usd": notional,
            "max_whole_contracts_at_initial_balance": entry["max_whole_contracts_at_initial_balance"],
            "favorable_move_pct_needed_for_capture5_rank50_level": round_half_up(move_needed_pct, 6),
            "vendor_history_sessions": None if vol is None else vol["sessions"],
            "best_30d_up_move_pct_in_vendor_history": None if vol is None else vol["best_30d_up_move_pct"],
            "history_contains_a_30d_window_as_large_as_that_requirement": (
                None if vol is None else bool(vol["best_30d_up_move_pct"] >= move_needed_pct)
            ),
        }
        instruments.append(row)
    instruments.sort(key=lambda r: r["favorable_move_pct_needed_for_capture5_rank50_level"])

    return {
        "_meta": {
            "kind": "deterministic_arithmetic_not_backtest",
            "description": "Leaderboard placement and prize arithmetic derived from official contest facts only: "
                "what each rank costs and what reaching it would require. Arithmetic, not a forecast.",
            "generated_utc": "2026-09-17",
            "reference_capture_utc": latest["captured_at_utc"],
            "input_files": [
                "data/contest_config.json",
                "data/frontier_history.json",
                "data/verified_explosive_returns.json",
                "data/initial_capacity.json",
                "data/volatility_intelligence.json",
            ],
            "source_ids": [
                "TV-RULES-AMP-SEP2026-R5",
                "TV-CONTEST-AMP-SEP2026-R5",
                "TV-THELEAP-LANDING-R5",
            ],
            "assumptions": [
                "A balance multiple means ending balance / 250,000 starting balance; 5x means +400% net profit, "
                "not +500%.",
                "Fresh-account requirement = the daily compound rate that would take a brand-new 250,000 account "
                "from 0% to the captured level in exactly the days remaining at that capture; it assumes a "
                "non-stop positive return, which no tested strategy in this repository has produced.",
                "The underlying-move equivalents divide that rate by the 20:1 leverage, i.e. a linear, "
                "no-compounding, no-fee approximation of a fully invested position.",
                "The winning-days figures assume an unbroken sequence of full-exposure wins at the stated "
                "underlying move; a single adverse day of the same size removes the same amount of equity.",
                "Average USD/day since start divides the displayed total by elapsed days; it assumes the "
                "participant's P/L accumulated evenly from the opening bell, which the capture-to-capture data "
                "shows is false. It is an average of a display, not a trade log.",
                "Champion comparison uses the 15 completed-edition #1 records transcribed from the official "
                "landing page; cross-edition context only.",
                "'history_contains_a_30d_window_as_large_as_that_requirement' is a historical envelope from "
                "overlapping vendor windows, requires perfect single-direction timing and captures nothing about "
                "execution, cost or roll effects.",
            ],
            "not_a_forecast": True,
        },
        "deadline": {
            "competition_start_utc": cfg["competition_start_utc"],
            "competition_end_utc": cfg["competition_end_utc"],
            "registration_close_utc": cfg["registration_close_utc"],
            "total_competition_days": round_half_up(total_days, 6),
            "remaining_days_at_latest_capture": latest["remaining_days_to_deadline"],
            "registration_days_left_at_latest_capture": latest["registration_days_left"],
        },
        "prize_ladder": prize_ladder,
        "board": board,
        "captures": captures,
        "targets": targets,
        "leverage_math": leverage_math,
        "champion_sample": champion_sample,
        "cash_frontier_instrument_requirements": instruments,
    }


if __name__ == "__main__":
    path = ROOT / "data/leaderboard_lab.json"
    payload = build()
    path.write_text(json.dumps(payload, indent=2) + "\n")
    t = payload["targets"]
    print(f"Wrote {path.name}: {len(payload['captures'])} captures, "
          f"{len(payload['prize_ladder']['tiers'])} prize tiers, {len(t)} targets, "
          f"{len(payload['cash_frontier_instrument_requirements'])} instrument rows; no backtest results")
