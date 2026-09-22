#!/usr/bin/env python3
"""Run the repository's own shadow competition on captured vendor daily bars.

Every username in data/competition/roster.json competes in every edition with
a fresh 250,000 virtual USD account under the official rule constants
(data/contest_config.json): 20:1 buying power, whole contracts, official
per-symbol caps, realized-P/L ranking, end-of-edition auto-close, no resets.

Prices are the committed vendor captures (data/market_history/, front-month
continuous futures, unadjusted roll splices) — a market_data_vendor tier
source, not an exchange feed and not contest data.

Outputs (deterministic; pin the timestamp with --stamp so scripts/verify.py
can re-run the engine and require byte-identical output):

  data/competition_results.json

This is the repository's own simulation. It is NOT a TradingView Strategy
Report, NOT a Paper Trading account, NOT the official contest, and NOT a
prediction.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.competition import (  # noqa: E402
    ENGINE_VERSION,
    MIN_EDITION_SESSIONS,
    EDITION_CALENDAR_DAYS,
    SEASON_STEP_CALENDAR_DAYS,
    START_BALANCE,
    Participant,
    Series,
    edition_windows,
    model_params_label,
    prepare_decisions,
    run_participant_edition,
)
from intel.contrarian import MODEL_CLAIMS, MODEL_KIND, MODEL_NAMES  # noqa: E402
from intel.data import load_index, load_series  # noqa: E402

PRIMARY_SCENARIO = "moderate"
MIN_SERIES_BARS = 150  # consistent with intel.walkforward.MIN_SERIES_BARS


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def build_series_map(index: dict, capacity: dict) -> tuple[dict[str, Series], list[str]]:
    cap_by_symbol = {e["symbol"]: e for e in capacity["entries"]}
    series: dict[str, Series] = {}
    for cap_row in index["captures"]:
        if cap_row.get("status") != "captured":
            continue
        sym = cap_row["tradingview_symbol"]
        if cap_row.get("sessions_valid", 0) < MIN_SERIES_BARS:
            continue
        bars = load_series(sym)
        spec = cap_by_symbol[sym]
        series[sym] = Series(
            symbol=sym,
            bars=tuple(bars),
            contract_multiplier=float(spec["contract_multiplier"]),
            rules_cap_contracts=int(spec["rules_position_cap_contracts"]),
        )
    eligible = sorted(series)
    return series, eligible


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=None, help="pin generated_utc for reproducibility")
    ap.add_argument("--out-dir", default="data")
    args = ap.parse_args()
    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cfg = load_json("data/contest_config.json")
    capacity = load_json("data/initial_capacity.json")
    index = load_json("data/market_history_index.json")
    roster = load_json("data/competition/roster.json")

    series_map, eligible = build_series_map(index, capacity)
    if not eligible:
        raise SystemExit("no eligible captured series")

    participants = []
    for row in roster["participants"]:
        participants.append(Participant(
            username=row["username"],
            model=row["model"],
            variant=row.get("variant"),
            pool=tuple(s for s in row["pool"] if s in series_map),
        ))
    usernames = [p.username for p in participants]
    if len(usernames) != len(set(usernames)):
        raise SystemExit("duplicate usernames in roster")

    union_dates = sorted({b.date for sym in eligible for b in series_map[sym].bars})
    windows = edition_windows(union_dates, final_window=True)
    if len(windows) < 2:
        raise SystemExit("not enough shared history for a season plus a latest edition")
    season_windows = windows[:-1]
    latest_window = windows[-1]

    decisions_cache: dict[tuple[str, str | None], dict[str, list]] = {}

    def decisions_for(model: str, variant: str | None, pool: tuple[str, ...]) -> dict[str, list]:
        key = (model, variant)
        if key not in decisions_cache:
            decisions_cache[key] = prepare_decisions(series_map, model, variant)
        return {sym: decisions_cache[key].get(sym, []) for sym in pool}

    def slices_and_starts(pool: tuple[str, ...], window: tuple[str, str]):
        start, end = window
        slices, starts = {}, {}
        for sym in pool:
            bars = list(series_map[sym].bars)
            idxs = [i for i, b in enumerate(bars) if start <= b.date <= end]
            if not idxs:
                continue
            slices[sym] = [bars[i] for i in idxs]
            starts[sym] = idxs[0]
        return slices, starts

    def run_all(window: tuple[str, str], scenario_key: str) -> dict[str, dict]:
        scenario = COST_SCENARIOS[scenario_key]
        out = {}
        for p in participants:
            dec = decisions_for(p.model, p.variant, p.pool)
            slices, starts = slices_and_starts(p.pool, window)
            res = run_participant_edition(dec, slices, starts, series_map, scenario)
            out[p.username] = res
        return out

    def rows_of(results: dict[str, dict]) -> list[dict]:
        rows = []
        for p in participants:
            r = results[p.username]
            rows.append({
                "username": p.username,
                "realized_pnl_usd": round(r.realized_pnl_usd, 2),
                "equity_multiple": round(r.equity_multiple, 6),
                "trades": r.trades,
                "active_days": r.active_days,
                "meets_min_active_days": r.active_days >= cfg["minimum_active_days"],
                "ruined": r.ruined,
                "margin_breach_bars": r.margin_breach_bars,
                "add_tranches": r.add_tranches,
                "long_trades": r.long_trades,
                "short_trades": r.short_trades,
                "skipped_entries": r.skipped_entries,
                "max_drawdown_usd": round(r.max_drawdown_usd, 2),
                "multiple_buckets": r.multiple_buckets,
            })
        rows.sort(key=lambda x: (-x["realized_pnl_usd"], x["username"]))
        for i, row in enumerate(rows, 1):
            row["rank"] = i
        return rows

    def edition_doc(edition_id: str, window: tuple[str, str], results: dict[str, dict]) -> dict:
        rows = rows_of(results)
        sessions = sum(
            1 for d in union_dates if window[0] <= d <= window[1]
        )
        return {
            "edition_id": edition_id,
            "start_date": window[0],
            "end_date": window[1],
            "calendar_days": EDITION_CALENDAR_DAYS,
            "sessions_in_window": sessions,
            "participants": len(rows),
            "leader": {
                "username": rows[0]["username"],
                "realized_pnl_usd": rows[0]["realized_pnl_usd"],
                "equity_multiple": rows[0]["equity_multiple"],
            },
            "rows": rows,
        }

    # ---- primary scenario: full season + latest edition ----
    primary_editions = []
    for n, window in enumerate(season_windows, 1):
        results = run_all(window, PRIMARY_SCENARIO)
        primary_editions.append(edition_doc(f"E{n:02d}", window, results))
    latest_results = run_all(latest_window, PRIMARY_SCENARIO)
    latest_doc = edition_doc("LATEST", latest_window, latest_results)

    # ---- per-participant season aggregates (primary scenario) ----
    participants_doc = []
    for p in participants:
        per_edition = []
        for ed in primary_editions:
            row = next(r for r in ed["rows"] if r["username"] == p.username)
            per_edition.append(row)
        mults = [max(r["equity_multiple"], 0.0) for r in per_edition]
        season_multiple = 1.0
        for m in mults:
            season_multiple *= m
        aggregates = {
            "username": p.username,
            "kind": MODEL_KIND.get(p.model, "baseline"),
            "model": p.model,
            "model_name": MODEL_NAMES[p.model],
            "variant": p.variant,
            "params_label": model_params_label(p.model, p.variant),
            "pool": list(p.pool),
            "editions_played": len(per_edition),
            "ruined_editions": sum(1 for r in per_edition if r["ruined"]),
            "negative_editions": sum(1 for r in per_edition if r["equity_multiple"] < 0),
            "season_realized_pnl_usd": round(sum(r["realized_pnl_usd"] for r in per_edition), 2),
            "season_multiple": round(season_multiple, 6),
            "best_edition_multiple": round(max(r["equity_multiple"] for r in per_edition), 6),
            "worst_edition_multiple": round(min(r["equity_multiple"] for r in per_edition), 6),
            "editions_ge_5x": sum(1 for r in per_edition if r["equity_multiple"] >= 5),
            "editions_ge_10x": sum(1 for r in per_edition if r["equity_multiple"] >= 10),
            "editions_ge_20x": sum(1 for r in per_edition if r["equity_multiple"] >= 20),
            "editions_ge_50x": sum(1 for r in per_edition if r["equity_multiple"] >= 50),
            "editions_ge_100x": sum(1 for r in per_edition if r["equity_multiple"] >= 100),
            "total_trades": sum(r["trades"] for r in per_edition),
            "total_add_tranches": sum(r["add_tranches"] for r in per_edition),
            "median_active_days": statistics.median(r["active_days"] for r in per_edition),
            "editions_meeting_min_active_days": sum(1 for r in per_edition if r["meets_min_active_days"]),
            "latest_edition_rank": next(
                r["rank"] for r in latest_doc["rows"] if r["username"] == p.username
            ),
            "latest_edition_multiple": next(
                r["equity_multiple"] for r in latest_doc["rows"] if r["username"] == p.username
            ),
        }
        participants_doc.append(aggregates)

    leaderboard = sorted(
        participants_doc,
        key=lambda a: (-a["season_realized_pnl_usd"], a["username"]),
    )
    for i, row in enumerate(leaderboard, 1):
        row["season_rank"] = i

    # ---- zero-cost scenario summary (robustness check, not the ranking basis) ----
    zero_season = []
    for window in season_windows:
        results = run_all(window, "zero")
        rows = rows_of(results)
        zero_season.append(rows[0])
    zero_counts: dict[str, int] = {}
    for row in zero_season:
        zero_counts[row["username"]] = zero_counts.get(row["username"], 0) + 1
    zero_top = sorted(zero_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # ---- target and contrast summaries ----
    def kind_aggregates(kind: str) -> dict:
        rows = [a for a in participants_doc if a["kind"] == kind]
        if not rows:
            return {"participants": 0}
        return {
            "participants": len(rows),
            "best_single_edition_multiple": round(
                max(a["best_edition_multiple"] for a in rows), 6),
            "best_season_multiple": round(
                max(a["season_multiple"] for a in rows), 6),
            "median_best_edition_multiple": round(
                statistics.median(a["best_edition_multiple"] for a in rows), 6),
            "participant_editions_ge_5x": sum(a["editions_ge_5x"] for a in rows),
            "participant_editions_ge_10x": sum(a["editions_ge_10x"] for a in rows),
            "ruined_editions": sum(a["ruined_editions"] for a in rows),
            "season_positive_participants": sum(1 for a in rows if a["season_realized_pnl_usd"] > 0),
        }

    pe_rows = [r for ed in primary_editions for r in ed["rows"]]
    target_summary = {
        "basis": f"participant-editions at {PRIMARY_SCENARIO} cost across {len(primary_editions)} season editions",
        "participant_editions": len(pe_rows),
        "ge_5x": sum(1 for r in pe_rows if r["equity_multiple"] >= 5),
        "ge_10x": sum(1 for r in pe_rows if r["equity_multiple"] >= 10),
        "ge_20x": sum(1 for r in pe_rows if r["equity_multiple"] >= 20),
        "ge_50x": sum(1 for r in pe_rows if r["equity_multiple"] >= 50),
        "ge_100x": sum(1 for r in pe_rows if r["equity_multiple"] >= 100),
        "users_reaching_5x_any_edition": sum(1 for a in participants_doc if a["editions_ge_5x"] > 0),
        "users_reaching_10x_any_edition": sum(1 for a in participants_doc if a["editions_ge_10x"] > 0),
        "users_reaching_20x_any_edition": sum(1 for a in participants_doc if a["editions_ge_20x"] > 0),
        "users_reaching_50x_any_edition": sum(1 for a in participants_doc if a["editions_ge_50x"] > 0),
        "users_reaching_100x_any_edition": sum(1 for a in participants_doc if a["editions_ge_100x"] > 0),
        "ruined_participant_editions": sum(1 for r in pe_rows if r["ruined"]),
    }

    model_cards = []
    seen = set()
    for p in participants:
        if p.model in seen:
            continue
        seen.add(p.model)
        model_cards.append({
            "model": p.model,
            "name": MODEL_NAMES[p.model],
            "kind": MODEL_KIND[p.model],
            "claim": MODEL_CLAIMS[p.model],
            "params": "frozen in intel/contrarian.py (DEFAULT_PARAMS/VARIANTS)"
            if p.model.startswith(("C", "F")) else "frozen in intel/strategy.py (DEFAULT_PARAMS)",
        })

    doc = {
        "_meta": {
            "kind": "own_shadow_competition_simulation",
            "description": (
                "The repository's own paper competition: every username in "
                "data/competition/roster.json trades a frozen contrarian or baseline "
                "strategy on captured vendor daily bars with a fresh 250,000 virtual USD "
                "account per edition, under the official rule constants. NOT the official "
                "contest, NOT a TradingView Strategy Report, NOT a prediction."
            ),
            "engine": ENGINE_VERSION,
            "generated_utc": stamp,
            "primary_scenario": PRIMARY_SCENARIO,
            "price_source": "data/market_history_index.json (market_data_vendor tier; front-month continuous, unadjusted rolls)",
            "rules_source": "data/contest_config.json (official rules transcription, TV-RULES-AMP-SEP2026)",
            "roster_source": "data/competition/roster.json",
            "season_editions": len(primary_editions),
            "edition_design": {
                "edition_calendar_days": EDITION_CALENDAR_DAYS,
                "step_calendar_days": SEASON_STEP_CALENDAR_DAYS,
                "min_edition_sessions": MIN_EDITION_SESSIONS,
                "shared_union_calendar": True,
                "final_window_note": "LATEST is the 30-calendar-day window ending at the last captured session; it may overlap the final season edition and is excluded from season standings.",
            },
            "cost_scenarios": {
                k: {"label": v.label,
                    "commission_per_contract_per_side_usd": v.commission_per_contract_per_side_usd,
                    "slippage_atr_fraction": v.slippage_atr_fraction}
                for k, v in COST_SCENARIOS.items()
            },
            "eligible_symbols": eligible,
            "assumptions": [
                "Daily bars only; the official contest allows intraday trading, so this simulation understates achievable trade frequency (hypothesis H27).",
                "Signals evaluate on a bar's close and fill at that series' next bar open; slippage is a declared fraction of the decision bar's ATR(14) on both legs; commission per contract per side.",
                "Notional accounting uses entry prices marked at each symbol's most recent processed open; no intra-bar margin calls are simulated (breaches are counted, not acted on).",
                "Season multiple is the product of edition multiples with each edition floored at 0 (a real margin account cannot lose more than its balance); negative-multiple editions are counted separately.",
                "Vendor series are front-month continuous futures with unadjusted roll splices; roll gaps can create artificial gap-fade signals.",
                "Every edition gives every participant a fresh 250,000 account; season standings sum realized P/L across editions.",
                "Universe limitation: the live September 2026 edition admits 0 equities, so this competition runs on volatile futures captures; a highly volatile STOCKS division requires new committed stock OHLC captures (the sandbox has no direct market-data egress; the capture workflow runs on GitHub Actions) and is queued for the next session.",
            ],
            "not_a_forecast": True,
        },
        "rules": {
            "starting_balance_virtual_usd": cfg["starting_balance_virtual_usd"],
            "futures_leverage_ratio": cfg["futures_leverage_ratio"],
            "ranking_metric": cfg["ranking_metric"],
            "end_of_competition_auto_close": cfg["end_of_competition_auto_close"],
            "account_reset_allowed": cfg["account_reset_allowed"],
            "minimum_active_days": cfg["minimum_active_days"],
            "source_ids": ["TV-RULES-AMP-SEP2026"],
        },
        "roster": [
            {
                "username": p.username,
                "kind": MODEL_KIND.get(p.model, "baseline"),
                "model": p.model,
                "model_name": MODEL_NAMES[p.model],
                "variant": p.variant,
                "params_label": model_params_label(p.model, p.variant),
                "pool": list(p.pool),
            }
            for p in participants
        ],
        "models": model_cards,
        "editions": primary_editions,
        "latest_edition": latest_doc,
        "participants": sorted(participants_doc, key=lambda a: a["season_rank"]),
        "leaderboard": [
            {"season_rank": a["season_rank"], "username": a["username"],
             "season_realized_pnl_usd": a["season_realized_pnl_usd"],
             "season_multiple": a["season_multiple"],
             "best_edition_multiple": a["best_edition_multiple"],
             "editions_ge_5x": a["editions_ge_5x"]}
            for a in leaderboard
        ],
        "scenario_zero_season_leaders": [
            {"edition_id": primary_editions[i]["edition_id"],
             "username": row["username"],
             "realized_pnl_usd": row["realized_pnl_usd"],
             "equity_multiple": row["equity_multiple"]}
            for i, row in enumerate(zero_season)
        ],
        "scenario_zero_leader_wins": zero_top[:3],
        "target_summary": target_summary,
        "kind_contrast": {
            "contrarian": kind_aggregates("contrarian"),
            "baseline": kind_aggregates("baseline"),
        },
    }

    out_dir = os.path.join(ROOT, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "competition_results.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"shadow competition: {len(participants)} participants, "
          f"{len(primary_editions)} season editions + 1 latest edition, "
          f"scenario={PRIMARY_SCENARIO}")
    print(f"season champion: {doc['leaderboard'][0]['username']} "
          f"${doc['leaderboard'][0]['season_realized_pnl_usd']:,.2f} "
          f"({doc['leaderboard'][0]['season_multiple']}x season multiple)")
    print(f"latest edition winner: {latest_doc['leader']['username']} "
          f"${latest_doc['leader']['realized_pnl_usd']:,.2f} "
          f"({latest_doc['leader']['equity_multiple']}x)")
    print(f"target summary: {json.dumps(target_summary)}")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
