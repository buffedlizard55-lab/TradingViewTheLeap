#!/usr/bin/env python3
"""Run the pre-registered walk-forward backtests and write audited artifacts.

Reads only committed repository data (raw vendor captures + contest facts) and
writes:

  data/backtest_results.json        - walk-forward results and verdicts for S1/S2/S3
  data/volatility_intelligence.json - realized-volatility and explosive-move metrics

Everything is deterministic (fixed bootstrap seed); pass --stamp to pin the
generated timestamp so a re-run reproduces byte-identical files, which is exactly
what scripts/verify.py does to audit the committed artifacts.

These are independent daily-bar simulations. They are NOT TradingView Strategy
Report results, NOT Paper Trading account results, and NOT predictions.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import indicators as ind  # noqa: E402
from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.data import load_index, load_series  # noqa: E402
from intel.strategy import DEFAULT_PARAMS, MODEL_IDS  # noqa: E402
from intel.walkforward import (  # noqa: E402
    MIN_SERIES_BARS,
    SENSITIVITY_GRID,
    SIZING_MODES,
    SymbolInput,
    aggregate,
    concentration_check,
    run_symbol,
)

ENGINE_VERSION = "intel-1"
MODELS_META = {
    "S1": "Donchian trend breakout",
    "S2": "EMA impulse continuation",
    "S3": "Bollinger squeeze release",
}


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def log_returns(closes: list[float]) -> list[float]:
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]


def ann_vol_pct(closes: list[float]) -> float:
    if len(closes) < 20:
        return float("nan")
    r = log_returns(closes)
    return statistics.stdev(r) * math.sqrt(252) * 100.0


def build_volatility_intelligence(inputs: list[SymbolInput], stamp: str) -> dict:
    capacity = load_json("data/initial_capacity.json")
    cap_by_symbol = {e["symbol"]: e for e in capacity["entries"]}
    target = load_json("data/live_contest_snapshot.json")
    rank250 = next(r for r in target["leaderboard"] if r["rank"] == 250)

    rows = []
    for inp in inputs:
        bars = inp.bars
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        atr_series = ind.atr(highs, lows, closes, DEFAULT_PARAMS["atr_length"])
        atr_pcts = [a / c * 100 for a, c in zip(atr_series, closes) if a is not None]

        gaps = [
            (abs(bars[i].open / bars[i - 1].close - 1) * 100.0, bars[i].date)
            for i in range(1, len(bars))
        ]
        max_gap, max_gap_date = max(gaps) if gaps else (None, None)
        daily_moves = [
            (abs(closes[i] / closes[i - 1] - 1) * 100.0, bars[i].date,
             "up" if closes[i] >= closes[i - 1] else "down")
            for i in range(1, len(bars))
        ]
        top_moves = sorted(daily_moves, reverse=True)[:3]

        # Rolling 30-calendar-day directional move scan (overlapping windows,
        # one window per bar start): best close-to-extreme move inside 30 days.
        best_up = (0.0, None)
        best_down = (0.0, None)
        ge10 = ge25 = ge50 = 0
        ge10_down = ge25_down = ge50_down = 0
        n_windows = 0
        for i in range(len(bars)):
            start = date.fromisoformat(bars[i].date)
            end = start + timedelta(days=29)
            j = i
            window_closes = []
            while j < len(bars) and date.fromisoformat(bars[j].date) <= end:
                window_closes.append(closes[j])
                j += 1
            if len(window_closes) < 5:
                continue
            n_windows += 1
            up = (max(window_closes) / closes[i] - 1) * 100.0
            down = (min(window_closes) / closes[i] - 1) * 100.0
            if up > best_up[0]:
                best_up = (up, bars[i].date)
            if -down > best_down[0]:
                best_down = (-down, bars[i].date)
            ge10 += up >= 10
            ge25 += up >= 25
            ge50 += up >= 50
            ge10_down += -down >= 10
            ge25_down += -down >= 25
            ge50_down += -down >= 50

        cap_row = cap_by_symbol.get(inp.symbol)
        notional = cap_row["modeled_initial_notional_usd"] if cap_row else None
        needed = (
            cap_row["favorable_move_pct_needed_for_rank250_snapshot"] if cap_row else None
        )
        # Compute from the ROUNDED stored move so the verifier's re-derivation from
        # stored fields is exact.
        best_up_rounded = round(best_up[0], 2)
        best_up_pnl = round(best_up_rounded / 100.0 * notional, 2) if notional else None

        rows.append({
            "symbol": inp.symbol,
            "sessions": len(bars),
            "first_session": bars[0].date,
            "last_session": bars[-1].date,
            "last_close": closes[-1],
            "ann_vol_full_pct": round(ann_vol_pct(closes), 2),
            "ann_vol_last_1y_pct": round(ann_vol_pct(closes[-252:]), 2),
            "mean_atr14_pct": round(statistics.fmean(atr_pcts), 3) if atr_pcts else None,
            "max_atr14_pct": round(max(atr_pcts), 3) if atr_pcts else None,
            "largest_abs_overnight_gap_pct": round(max_gap, 2) if max_gap is not None else None,
            "largest_gap_date": max_gap_date,
            "top3_abs_daily_moves_pct": [
                {"date": d, "abs_move_pct": round(m, 2), "direction": dr}
                for m, d, dr in top_moves
            ],
            "rolling_30d_windows_scanned": n_windows,
            "windows_30d_ge_10pct_up": ge10,
            "windows_30d_ge_25pct_up": ge25,
            "windows_30d_ge_50pct_up": ge50,
            "windows_30d_ge_10pct_down": ge10_down,
            "windows_30d_ge_25pct_down": ge25_down,
            "windows_30d_ge_50pct_down": ge50_down,
            "best_30d_up_move_pct": round(best_up[0], 2),
            "best_30d_up_start_date": best_up[1],
            "best_30d_down_move_pct": round(best_down[0], 2),
            "best_30d_down_start_date": best_down[1],
            "modeled_initial_notional_usd": notional,
            "favorable_move_pct_needed_for_rank250_snapshot": needed,
            "rank250_pnl_if_best_30d_up_move_recurred_usd": best_up_pnl,
            "note_if_best_move_exceeds_rank250_requirement": (
                best_up_pnl is not None and best_up[0] >= (needed or float("inf"))
            ),
        })

    rows.sort(key=lambda r: -(r["best_30d_up_move_pct"] or 0))
    return {
        "_meta": {
            "description": (
                "Realized-volatility and explosive-move metrics recomputed from the committed "
                "vendor captures. Rolling 30-day windows overlap (one window per bar). "
                "The 'if best move recurred' fields are arithmetic illustrations at the modeled "
                "initial notional - an upper envelope of what history offered, NOT a forecast "
                "and NOT a backtest."
            ),
            "engine": ENGINE_VERSION,
            "generated_utc": stamp,
            "data_source": "data/market_history_index.json",
            "rank250_target_usd": rank250["realized_profit_usd"],
            "rank250_target_snapshot_utc": target["_meta"]["captured_at_utc"],
            "symbol_count": len(rows),
            "metric_definitions": {
                "ann_vol_pct": "stddev of daily log returns x sqrt(252) x 100",
                "atr14_pct": "ATR(14) / close x 100",
                "best_30d_up_move_pct": (
                    "max over overlapping 30-calendar-day windows of "
                    "(max close in window / first close - 1) x 100"
                ),
                "best_30d_down_move_pct": "mirror of best_30d_up_move_pct using the window minimum",
                "largest_abs_overnight_gap_pct": "max |open/prev close - 1| x 100 (roll-gap proxy)",
            },
        },
        "records": rows,
    }


def evaluate_model(model: str, detail: dict) -> tuple[str, list[str]]:
    """Verdict per the model's registered falsification rule plus plan T5."""
    reasons: list[str] = []
    refuted = False
    inconclusive = False

    zero = detail["scenarios"]["zero"]
    moderate = detail["scenarios"]["moderate"]
    high = detail["scenarios"]["high"]
    conc = detail["concentration"]

    if zero["windows"] == 0:
        return "inconclusive", ["no testable windows were produced"]

    median = zero["median_net_profit_usd"]
    ci = zero["bootstrap95_median_ci_usd"]
    if median is None or median <= 0:
        refuted = True
        reasons.append(
            f"walk-forward median net profit (zero-cost) is ${median}, not positive"
        )
    elif ci[0] <= 0:
        refuted = True
        reasons.append(
            f"bootstrap 95% lower bound of the median is ${ci[0]} (median ${median})"
        )

    if conc.get("single_symbol_dependent"):
        refuted = True
        reasons.append(
            "excluding the single best symbol flips the pooled median non-positive "
            f"(${conc.get('median_excluding_best_symbol_usd')}) - the result depends on one symbol"
        )
    if conc.get("single_window_dependent"):
        refuted = True
        reasons.append(
            "excluding the single best window flips the pooled median non-positive "
            f"(${conc.get('median_excluding_best_window_usd')}) - the result depends on one window"
        )

    if model == "S2":
        if moderate["median_net_profit_usd"] is not None and moderate["median_net_profit_usd"] <= 0:
            refuted = True
            reasons.append(
                "out-of-sample median net profit after moderate costs is "
                f"${moderate['median_net_profit_usd']} (non-positive)"
            )
        for label, agg in detail["sensitivity"].items():
            if agg["zero"]["median_net_profit_usd"] is not None and \
                    agg["zero"]["median_net_profit_usd"] <= 0:
                refuted = True
                reasons.append(
                    f"nearby parameters ({label}) reverse the result "
                    f"(median ${agg['zero']['median_net_profit_usd']})"
                )

    if model == "S3":
        total_trades = zero["trades"]
        if total_trades < 100:
            inconclusive = True
            reasons.append(
                f"total closed trades ({total_trades}) is too small for the declared "
                "bootstrap confidence interval"
            )
        for label, agg in detail["sensitivity"].items():
            if agg["zero"]["median_net_profit_usd"] is not None and \
                    agg["zero"]["median_net_profit_usd"] <= 0:
                refuted = True
                reasons.append(
                    f"small parameter change ({label}) erases the result "
                    f"(median ${agg['zero']['median_net_profit_usd']})"
                )

    if refuted:
        return "refuted", reasons
    if inconclusive:
        return "inconclusive", reasons

    # Supported requires the plan's T5 bar: positive and cost-robust everywhere.
    cost_ok = all(
        (detail["scenarios"][s]["median_net_profit_usd"] or 0) > 0
        and (detail["scenarios"][s]["bootstrap95_median_ci_usd"] or [0, 0])[0] > 0
        for s in ("zero", "moderate", "high")
    )
    sensitivity_ok = all(
        (agg["zero"]["median_net_profit_usd"] or 0) > 0
        for agg in detail["sensitivity"].values()
    )
    breadth_ok = zero["windows"] >= 20 and len(zero["by_symbol_median_net_profit_usd"]) >= 3
    if cost_ok and sensitivity_ok and breadth_ok:
        reasons.append(
            "median net profit is positive with a positive bootstrap lower bound across "
            "cost scenarios, nearby parameters, symbols and windows"
        )
        return "supported", reasons
    if not cost_ok:
        reasons.append("median turns non-positive under at least one declared cost scenario")
    if not sensitivity_ok:
        reasons.append("a nearby-parameter variant is non-positive")
    if not breadth_ok:
        reasons.append("window or symbol coverage is below the pre-declared breadth bar")
    return "inconclusive", reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", default=None, help="pin generated_utc for reproducibility")
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()

    stamp = args.stamp or load_index()["_meta"]["fetched_at_utc"]

    cfg = load_json("data/contest_config.json")
    universe = {r["tradingview_symbol"]: r for r in load_json("data/contest_universe.json")["instruments"]}
    master = {e["symbol"]: e for e in load_json("data/master_list.json")["entries"]}
    snapshot = load_json("data/live_contest_snapshot.json")
    rank250 = next(r for r in snapshot["leaderboard"] if r["rank"] == 250)
    target_usd = rank250["realized_profit_usd"]

    index = load_index()
    captured = [c for c in index["captures"] if c.get("status") == "captured"]
    inputs: list[SymbolInput] = []
    excluded: list[dict] = []
    for c in captured:
        symbol = c["tradingview_symbol"]
        if symbol not in master or symbol not in universe:
            excluded.append({"symbol": symbol, "reason": "not in the selected master list"})
            continue
        bars = load_series(symbol)
        if len(bars) < MIN_SERIES_BARS:
            excluded.append({
                "symbol": symbol,
                "reason": (
                    f"insufficient vendor history: {len(bars)} bars < {MIN_SERIES_BARS} required "
                    f"({c['first_session_utc']} -> {c['last_session_utc']})"
                ),
            })
            continue
        inputs.append(SymbolInput(
            symbol=symbol,
            bars=bars,
            contract_multiplier=master[symbol]["contract_multiplier"],
            rules_cap_contracts=int(master[symbol]["max_open_position_contracts"]),
        ))

    if not inputs:
        print("no symbol has enough captured history to test", file=sys.stderr)
        return 1

    models_out = []
    for model in MODEL_IDS:
        detail: dict = {"scenarios": {}, "sensitivity": {}}
        window_rows: dict = {}
        for sizing in SIZING_MODES:
            for scenario_key in COST_SCENARIOS:
                results = []
                for inp in inputs:
                    results.extend(run_symbol(
                        inp, model,
                        scenario_key=scenario_key,
                        sizing=sizing,
                        target_usd=target_usd,
                    ))
                if sizing == "compounding":
                    window_rows[scenario_key] = results
                    detail["scenarios"][scenario_key] = aggregate(results)
                else:
                    detail.setdefault("initial_fixed", {})[scenario_key] = aggregate(results)

        for label, params in SENSITIVITY_GRID[model]:
            agg = {}
            for scenario_key in ("zero", "moderate"):
                results = []
                for inp in inputs:
                    results.extend(run_symbol(
                        inp, model,
                        scenario_key=scenario_key,
                        sizing="compounding",
                        params=params,
                        params_label=label,
                        target_usd=target_usd,
                    ))
                agg[scenario_key] = aggregate(results)
            detail["sensitivity"][label] = agg

        detail["concentration"] = concentration_check(window_rows["zero"])
        verdict, reasons = evaluate_model(model, detail)
        models_out.append({
            "id": model,
            "name": MODELS_META[model],
            "verdict": verdict,
            "verdict_reasons": reasons,
            "scenarios": detail["scenarios"],
            "initial_fixed_sizing": detail.get("initial_fixed", {}),
            "sensitivity": detail["sensitivity"],
            "concentration": detail["concentration"],
            "window_rows": {
                scenario_key: [
                    {
                        "symbol": w.symbol,
                        "start": w.start_date,
                        "end": w.end_date,
                        "bars": w.bars,
                        "trades": len(w.trades),
                        "net_profit_usd": round(w.net_profit_usd, 2),
                        "equity_multiple": round(w.equity_multiple, 4),
                        "profitable_trades": w.profitable_trades,
                        "profit_factor": w.profit_factor,
                        "max_drawdown_pct": round(w.max_drawdown_pct * 100, 2),
                        "long_trades": w.long_trades,
                        "short_trades": w.short_trades,
                        "hit_target_usd": w.hit_target_usd,
                        "multiple_buckets": w.multiple_buckets,
                        "ruined": w.ruined,
                    }
                    for w in rows
                ]
                for scenario_key, rows in window_rows.items()
            },
        })

    results_doc = {
        "_meta": {
            "description": (
                "Independent walk-forward simulation of the three pre-registered candidate "
                "models on committed vendor daily bars. NOT a TradingView Strategy Report "
                "result, NOT a Paper Trading account result, NOT a prediction or "
                "recommendation."
            ),
            "engine": ENGINE_VERSION,
            "generated_utc": stamp,
            "data_source": "data/market_history_index.json",
            "test_protocol": "research/strategy/testing-plan.md (T2 walk-forward, T3 costs, T4 metrics, T5 verdicts)",
            "parameters": DEFAULT_PARAMS,
            "sensitivity_grid": {
                model: {label: params for label, params in SENSITIVITY_GRID[model]}
                for model in MODEL_IDS
            },
            "cost_scenarios": {
                k: {
                    "commission_per_contract_per_side_usd": v.commission_per_contract_per_side_usd,
                    "slippage_atr_fraction": v.slippage_atr_fraction,
                    "label": v.label,
                }
                for k, v in COST_SCENARIOS.items()
            },
            "sizing_models": {
                "compounding": "qty = min(cap, floor(equity x 20 / notional)) with running equity",
                "initial_fixed": "same, but sizing equity fixed at the 250,000 start balance",
            },
            "window_design": {
                "window_calendar_days": 30,
                "step_calendar_days": 30,
                "min_window_bars": 15,
                "min_series_bars": MIN_SERIES_BARS,
                "fresh_account_per_window": True,
                "bootstrap_seed": 1729,
            },
            "contest_constants": {
                "starting_balance_virtual_usd": cfg["starting_balance_virtual_usd"],
                "futures_leverage_ratio": cfg["futures_leverage_ratio"],
                "rank250_target_usd": target_usd,
                "rank250_target_snapshot_utc": snapshot["_meta"]["captured_at_utc"],
            },
            "symbols_tested": [inp.symbol for inp in inputs],
            "symbols_excluded": excluded,
            "assumptions": [
                "Signals on bar close fill at the next bar's open (Pine broker-emulator default).",
                "End-of-window open positions close at the final bar's close (contest auto-close analog).",
                "Whole contracts; position size min(rules cap, buying power); no pyramiding.",
                "No margin-call liquidation simulated; margin breaches are counted, not acted on.",
                "Slippage is a declared fraction of signal-bar ATR(14) on both legs; commissions per side.",
                "Vendor series are front-month continuous futures with unadjusted rolls; roll gaps can create artificial signals.",
            ],
        },
        "models": models_out,
    }

    vol_doc = build_volatility_intelligence(inputs, stamp)

    out_dir = os.path.join(ROOT, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "backtest_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results_doc, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(out_dir, "volatility_intelligence.json"), "w", encoding="utf-8") as fh:
        json.dump(vol_doc, fh, indent=1)
        fh.write("\n")

    for m in models_out:
        zero = m["scenarios"]["zero"]
        print(
            f"{m['id']} {m['name']}: {m['verdict']} | zero-cost median "
            f"${zero['median_net_profit_usd']} | windows {zero['windows']} | "
            f"trades {zero['trades']} | ge5x {zero['windows_ge_5x']} | "
            f"ge10x {zero['windows_ge_10x']}"
        )
    print(f"tested {len(inputs)} symbols; excluded {len(excluded)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
