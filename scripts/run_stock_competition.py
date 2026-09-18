#!/usr/bin/env python3
"""Run the volatile-equity division of the repository's own shadow competition.

Two divisions run on the same engine (intel.competition.run_participant_window) with real
captured vendor bars:

  daily   - the 20-stock volatile pool on ~10 years of daily bars  (multi-season)
  hourly  - the same pool on ~2 years of hourly bars               (multi-season, intraday)

Every username in data/competition/stock_roster.json competes in every edition with a fresh
account under a RuleProfile:

  stocks_official_leap        (PRIMARY)  100,000 virtual USD, stocks leverage 1:1,
                                          commission 0.01%, <=50 units per instrument
  stocks_20x_counterfactual   (declared counterfactual)
                                         100,000, commission 0.01%, <=50 units, 20:1 buying power

The primary profile's constants are transcribed from the official Magnificent Seven (March
2026) rules page, the only stocks edition whose rules TradingView has published in this
repository's evidence set. The counterfactual profile exists ONLY to measure how much of the
explosive-return question is buying power rather than signal; no official rule grants 20:1 on
stocks and every artifact built from it says so.

Also produced, all arithmetic on the same captured bars:

- latency_sensitivity: the same editions re-run with fills delayed by 1, 2 and 5 bars, so the
  cost of execution latency is visible in realised P/L rather than asserted.
- official_rule_bound: the arithmetic ceiling on an edition multiple under the official stock
  rule profile, computed from the actual first-session prices of every edition and the best
  favourable excursion any pool name actually made inside that edition. It answers "could a
  5x have happened in a stocks edition" without any modelling.

Outputs (deterministic; pin the timestamp with --stamp so scripts/verify.py can re-run the
engine and require byte-identical output):

  data/stock_competition_results.json

This is the repository's own simulation on vendor bars. It is NOT the official contest, NOT a
TradingView Strategy Report, NOT a Paper Trading account, and NOT a prediction.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.competition import (  # noqa: E402
    DIVISION_ENGINE_VERSION,
    EDITION_CALENDAR_DAYS,
    MIN_EDITION_SESSIONS,
    RULE_PROFILES,
    SEASON_STEP_CALENDAR_DAYS,
    Participant,
    Series,
    edition_windows,
    max_edition_multiple_bound,
    model_params_label,
    run_participant_window,
)
from intel.data import Bar  # noqa: E402
from intel.intraday import IntradayError, load_all, load_index  # noqa: E402
from intel.stock_strategies import (  # noqa: E402
    MODEL_CLAIMS,
    MODEL_KIND,
    MODEL_NAMES,
    STOCK_MODEL_IDS,
    generate_stock_decisions,
    resolve_params,
    trailing_volatility,
    warmup,
)
from intel.contrarian import MODEL_CLAIMS as BASELINE_CLAIMS  # noqa: E402
from intel.contrarian import MODEL_NAMES as BASELINE_NAMES  # noqa: E402
from intel.contrarian import generate_decisions  # noqa: E402

PRIMARY_SCENARIO = "moderate"
PRIMARY_PROFILE = "stocks_official_leap"
COUNTERFACTUAL_PROFILE = "stocks_20x_counterfactual"
MIN_SERIES_BARS = 150
DEFAULT_DAILY_START = "2020-01-01"
LATENCY_STEPS = (0, 1, 2, 5)


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def build_series(captures: dict, interval: str, symbol_of_key) -> dict[str, Series]:
    """Series objects (multiplier 1.0 for equities) from the intraday captures."""
    out: dict[str, Series] = {}
    for key, capture in captures.items():
        if capture.interval != interval:
            continue
        symbol = symbol_of_key(capture.symbol)
        bars = [Bar(b.ts, b.open, b.high, b.low, b.close, b.volume) for b in capture.bars]
        if len(bars) < MIN_SERIES_BARS:
            continue
        out[symbol] = Series(
            symbol=symbol,
            bars=tuple(bars),
            contract_multiplier=1.0,
            rules_cap_contracts=50,       # official stocks-edition cap; one unit = one share
        )
    return out


def decisions_for_model(series_map: dict[str, Series], model: str, variant: str | None) -> dict:
    """Decisions for one (model, variant) on every series. C6-C10 or the S1-S3 baselines."""
    out: dict[str, list] = {}
    for symbol in sorted(series_map):
        bars = list(series_map[symbol].bars)
        if model in STOCK_MODEL_IDS:
            if len(bars) <= warmup(model, variant):
                out[symbol] = []
                continue
            out[symbol] = generate_stock_decisions(bars, model, variant)
        else:                                   # baseline S1-S3 reuse intel.strategy
            from intel.strategy import warmup_bars
            if len(bars) <= warmup_bars(model):
                out[symbol] = []
                continue
            out[symbol] = generate_decisions(bars, model, variant)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", default="data/intraday_index.json")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--out", default="data/stock_competition_results.json")
    ap.add_argument("--daily-start", default=DEFAULT_DAILY_START)
    ap.add_argument("--max-editions", type=int, default=120,
                    help="cap on season editions per division (most recent kept)")
    ap.add_argument("--counterfactual-editions", type=int, default=12)
    ap.add_argument("--latency-editions", type=int, default=6)
    args = ap.parse_args()
    def default_stamp() -> str:
        """Newest input capture stamp, so an un-stamped run still reproduces exactly.

        The engine is deterministic given (bars, roster, rules); only the timestamp is
        environmental. Pinning it to the capture index (and the futures/competition
        artifacts that the exec summary reads) keeps every rerun byte-identical, which is
        what scripts/verify.py requires.
        """
        stamps = []
        for rel, keys in ((args.index, ("fetched_at_utc",)),
                          ("data/market_history_index.json", ("fetched_at_utc",)),
                          ("data/competition_results.json", ("generated_utc",))):
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                meta = json.load(fh).get("_meta", {})
            for key in keys:
                if meta.get(key):
                    stamps.append(meta[key])
        return max(stamps) if stamps else "unknown"

    stamp = args.stamp or default_stamp()
    started = time.time()

    try:
        index = load_index(args.index)
        captures = load_all(index)
    except IntradayError as exc:
        print(f"::error::{exc}", flush=True)
        return 1

    roster_doc = load_json("data/competition/stock_roster.json")
    pool = [s for s, _ in [(r["symbol"], r) for r in load_json("data/volatile_stocks.json")["records"]]]

    daily_series = build_series(captures, "1d", lambda s: s)
    hourly_series = build_series(captures, "1h", lambda s: s)
    quarter_hour_series = build_series(captures, "15m", lambda s: s)
    series_divisions = (("daily", daily_series), ("hourly", hourly_series),
                        ("15minute", quarter_hour_series))
    for _, series_map in series_divisions:
        for symbol in set(series_map) - set(pool):
            del series_map[symbol]
    if not any(series for _, series in series_divisions):
        print("::error::no eligible stock series captured", flush=True)
        return 1

    primary = RULE_PROFILES[PRIMARY_PROFILE]
    counterfactual = RULE_PROFILES[COUNTERFACTUAL_PROFILE]
    scenario = COST_SCENARIOS[PRIMARY_SCENARIO]

    participants = []
    for row in roster_doc["participants"]:
        participants.append(Participant(
            username=row["username"],
            model=row["model"],
            variant=row.get("variant"),
            pool=tuple(s for s in row["pool"] if any(s in series for _, series in series_divisions)),
        ))
    usernames = [p.username for p in participants]
    if len(usernames) != len(set(usernames)):
        raise SystemExit("duplicate usernames in the stock roster")
    division_of = {row["username"]: row.get("division", "daily") for row in roster_doc["participants"]}

    decision_cache: dict[tuple[str, str | None], dict] = {}

    def decisions(model: str, variant: str | None, series_map: dict) -> dict:
        key = (model, variant, id(series_map))
        if key not in decision_cache:
            decision_cache[key] = decisions_for_model(series_map, model, variant)
        return decision_cache[key]

    def windows_for(series_map: dict, start_after: str | None) -> list[tuple[str, str]]:
        union_dates = sorted({b.date for sym in series_map for b in series_map[sym].bars})
        if start_after:
            union_dates = [d for d in union_dates if d >= start_after]
        return edition_windows(union_dates, final_window=True)

    def slices_and_starts(pool_symbols, series_map, window):
        start, end = window
        slices, starts = {}, {}
        for symbol in pool_symbols:
            bars = list(series_map[symbol].bars)
            idxs = [i for i, b in enumerate(bars) if start <= b.date <= end]
            if not idxs:
                continue
            slices[symbol] = [bars[i] for i in idxs]
            starts[symbol] = idxs[0]
        return slices, starts

    def control_symbol_for(pool_symbols, series_map, window) -> str | None:
        """Highest trailing-volatility (60 daily returns) name strictly before the window."""
        best, best_vol = None, None
        for symbol in pool_symbols:
            bars = list(series_map[symbol].bars)
            before = [i for i, b in enumerate(bars) if b.date < window[0]]
            if not before:
                continue
            vol = trailing_volatility(bars, before[-1])
            if vol is not None and (best_vol is None or vol > best_vol):
                best, best_vol = symbol, vol
        return best

    def run_edition(series_map, window, profile, latency_bars=0, only_pool=None) -> dict[str, object]:
        out = {}
        for p in participants:
            if only_pool and p.username not in only_pool:
                continue
            pool_symbols = tuple(s for s in p.pool if s in series_map)
            if not pool_symbols:
                continue
            slices, starts = slices_and_starts(pool_symbols, series_map, window)
            if not slices:
                continue
            control = None
            if p.model == "B1":
                control = control_symbol_for(pool_symbols, series_map, window)
                if control is None:
                    continue
            dec = {} if p.model == "B1" else decisions(p.model, p.variant, series_map)
            out[p.username] = run_participant_window(
                dec, slices, starts, series_map, profile, scenario,
                latency_bars=latency_bars, control_symbol=control,
            )
        return out

    def rows_of(results: dict, min_active_days: int) -> list[dict]:
        rows = []
        for username, r in results.items():
            rows.append({
                "username": username,
                "realized_pnl_usd": round(r.realized_pnl_usd, 2),
                "equity_multiple": round(r.equity_multiple, 6),
                "trades": r.trades,
                "active_days": r.active_days,
                "meets_min_active_days": r.active_days >= min_active_days,
                "ruined": r.ruined,
                "add_tranches": r.add_tranches,
                "long_trades": r.long_trades,
                "short_trades": r.short_trades,
                "skipped_entries": r.skipped_entries,
                "expired_orders": getattr(r, "expired_orders", 0),
                "margin_breach_bars": r.margin_breach_bars,
                "max_drawdown_usd": round(r.max_drawdown_usd, 2),
                "multiple_buckets": r.multiple_buckets,
            })
        rows.sort(key=lambda row: (-row["realized_pnl_usd"], row["username"]))
        for i, row in enumerate(rows, 1):
            row["rank"] = i
        return rows

    def edition_doc(edition_id, window, results, min_active_days) -> dict:
        rows = rows_of(results, min_active_days)
        return {
            "edition_id": edition_id,
            "start_date": window[0],
            "end_date": window[1],
            "participants": len(rows),
            "leader": {"username": rows[0]["username"], "realized_pnl_usd": rows[0]["realized_pnl_usd"],
                       "equity_multiple": rows[0]["equity_multiple"]} if rows else None,
            "rows": rows,
        }

    def season_aggregates(editions, latest_doc, profile) -> list[dict]:
        out = []
        for p in participants:
            per = [next((r for r in ed["rows"] if r["username"] == p.username), None)
                   for ed in editions]
            per = [r for r in per if r is not None]
            if not per:
                continue
            season_multiple = 1.0
            for row in per:
                season_multiple *= max(row["equity_multiple"], 0.0)
            latest_row = next((r for r in latest_doc["rows"] if r["username"] == p.username), None)
            out.append({
                "username": p.username,
                "division": division_of[p.username],
                "kind": MODEL_KIND.get(p.model, "baseline"),
                "model": p.model,
                "model_name": MODEL_NAMES.get(p.model) or BASELINE_NAMES.get(p.model, p.model),
                "variant": p.variant,
                "params_label": model_params_label(p.model, p.variant),
                "pool": list(p.pool),
                "editions_played": len(per),
                "ruined_editions": sum(1 for r in per if r["ruined"]),
                "negative_editions": sum(1 for r in per if r["equity_multiple"] < 0),
                "season_realized_pnl_usd": round(sum(r["realized_pnl_usd"] for r in per), 2),
                "season_multiple": round(season_multiple, 6),
                "best_edition_multiple": round(max(r["equity_multiple"] for r in per), 6),
                "worst_edition_multiple": round(min(r["equity_multiple"] for r in per), 6),
                "editions_ge_2x": sum(1 for r in per if r["equity_multiple"] >= 2),
                "editions_ge_5x": sum(1 for r in per if r["equity_multiple"] >= 5),
                "editions_ge_10x": sum(1 for r in per if r["equity_multiple"] >= 10),
                "editions_ge_20x": sum(1 for r in per if r["equity_multiple"] >= 20),
                "median_edition_multiple": round(statistics.median(
                    r["equity_multiple"] for r in per), 6),
                "total_trades": sum(r["trades"] for r in per),
                "total_add_tranches": sum(r["add_tranches"] for r in per),
                "editions_meeting_min_active_days": sum(
                    1 for r in per if r["meets_min_active_days"]),
                "latest_edition_rank": latest_row["rank"] if latest_row else None,
                "latest_edition_multiple": latest_row["equity_multiple"] if latest_row else None,
            })
        return out

    def target_summary(editions) -> dict:
        rows = [r for ed in editions for r in ed["rows"]]
        return {
            "participant_editions": len(rows),
            "ge_1.1x": sum(1 for r in rows if r["equity_multiple"] >= 1.1),
            "ge_2x": sum(1 for r in rows if r["equity_multiple"] >= 2),
            "ge_5x": sum(1 for r in rows if r["equity_multiple"] >= 5),
            "ge_10x": sum(1 for r in rows if r["equity_multiple"] >= 10),
            "ge_20x": sum(1 for r in rows if r["equity_multiple"] >= 20),
            "ge_50x": sum(1 for r in rows if r["equity_multiple"] >= 50),
            "ge_100x": sum(1 for r in rows if r["equity_multiple"] >= 100),
            "ruined_participant_editions": sum(1 for r in rows if r["ruined"]),
            "mean_equity_multiple": round(
                statistics.fmean(r["equity_multiple"] for r in rows), 6) if rows else None,
            "median_equity_multiple": round(
                statistics.median(r["equity_multiple"] for r in rows), 6) if rows else None,
        }

    def leaderboard_of(participants_doc) -> list[dict]:
        rows = sorted(participants_doc, key=lambda a: (-a["season_realized_pnl_usd"], a["username"]))
        for i, row in enumerate(rows, 1):
            row["season_rank"] = i
        return [{"season_rank": r["season_rank"], "username": r["username"],
                 "division": r["division"], "model": r["model"],
                 "season_realized_pnl_usd": r["season_realized_pnl_usd"],
                 "season_multiple": r["season_multiple"],
                 "best_edition_multiple": r["best_edition_multiple"],
                 "median_edition_multiple": r["median_edition_multiple"],
                 "editions_ge_2x": r["editions_ge_2x"]} for r in rows]

    divisions: dict[str, dict] = {}
    for name, series_map in series_divisions:
        if not series_map:
            divisions[name] = {"status": "no_captured_series"}
            continue
        start_after = args.daily_start if name == "daily" else None
        windows = windows_for(series_map, start_after)
        if len(windows) < 2:
            divisions[name] = {"status": "insufficient_history", "eligible_symbols": sorted(series_map)}
            continue
        season_windows, latest_window = windows[:-1], windows[-1]
        if len(season_windows) > args.max_editions:
            season_windows = season_windows[-args.max_editions:]
        editions = []
        for n, window in enumerate(season_windows, 1):
            results = run_edition(series_map, window, primary)
            editions.append(edition_doc(f"{name[0].upper()}{n:03d}", window, results,
                                        primary.min_active_days))
        latest_results = run_edition(series_map, latest_window, primary)
        latest_doc = edition_doc(f"{name[0].upper()}LATEST", latest_window, latest_results,
                                 primary.min_active_days)
        part_doc = season_aggregates(editions, latest_doc, primary)
        divisions[name] = {
            "coverage_complete": set(series_map) == set(pool),
            "missing_symbols": sorted(set(pool) - set(series_map)),
            "profile": primary.profile_id,
            "eligible_symbols": sorted(series_map),
            "bars_per_symbol": {s: len(series_map[s].bars) for s in sorted(series_map)},
            "season_editions": len(editions),
            "first_edition": editions[0]["start_date"] if editions else None,
            "last_season_end": editions[-1]["end_date"] if editions else None,
            "latest_window": {"start_date": latest_window[0], "end_date": latest_window[1]},
            "editions": editions,
            "latest_edition": latest_doc,
            "participants": sorted(part_doc, key=lambda a: (-a["season_realized_pnl_usd"],
                                                            a["username"])),
            "leaderboard": leaderboard_of(part_doc),
            "target_summary": target_summary(editions),
        }
        print(f"[{name}] {len(editions)} season editions on {len(series_map)} symbols; "
              f"champion {divisions[name]['leaderboard'][0]['username']} "
              f"${divisions[name]['leaderboard'][0]['season_realized_pnl_usd']:,.2f}", flush=True)

    # ---- counterfactual 20:1 runs on the most recent editions only ----
    counterfactual_doc: dict[str, dict] = {}
    for name, series_map in series_divisions:
        if not series_map or divisions.get(name, {}).get("status"):
            continue
        windows = windows_for(series_map, args.daily_start if name == "daily" else None)[:-1]
        windows = windows[-args.counterfactual_editions:]
        editions = []
        for n, window in enumerate(windows, 1):
            results = run_edition(series_map, window, counterfactual)
            editions.append(edition_doc(f"X{n:02d}", window, results,
                                        counterfactual.min_active_days))
        part_doc = season_aggregates(editions, {"rows": []}, counterfactual)
        counterfactual_doc[name] = {
            "profile": counterfactual.profile_id,
            "is_counterfactual": True,
            "editions_covered": len(editions),
            "first_edition": editions[0]["start_date"] if editions else None,
            "last_edition_end": editions[-1]["end_date"] if editions else None,
            "editions": editions,
            "participants": sorted(part_doc, key=lambda a: (-a["season_realized_pnl_usd"],
                                                            a["username"])),
            "target_summary": target_summary(editions),
        }
        print(f"[{name}/counterfactual] {len(editions)} editions; "
              f"{counterfactual_doc[name]['target_summary']}", flush=True)

    # ---- latency sensitivity: same editions, delayed fills ----
    latency_doc: dict[str, list] = {}
    for name, series_map in series_divisions:
        if not series_map or divisions.get(name, {}).get("status"):
            continue
        windows = windows_for(series_map, args.daily_start if name == "daily" else None)[:-1]
        windows = windows[-args.latency_editions:]
        rows = []
        for latency in LATENCY_STEPS:
            per_participant: dict[str, list[float]] = {}
            total_trades = 0
            best_multiple = 0.0
            champion = None
            champion_pnl = None
            for window in windows:
                results = run_edition(series_map, window, primary, latency_bars=latency)
                for username, r in results.items():
                    per_participant.setdefault(username, []).append(r.equity_multiple)
                    total_trades += r.trades
                    if r.equity_multiple > best_multiple:
                        best_multiple, champion = r.equity_multiple, username
                    if champion is None or (champion_pnl is not None and
                                            r.realized_pnl_usd > champion_pnl):
                        champion_pnl = r.realized_pnl_usd
            rows.append({
                "latency_bars": latency,
                "editions": len(windows),
                "participants": len(per_participant),
                "total_trades": total_trades,
                "best_edition_multiple": round(best_multiple, 6),
                "best_edition_username": champion,
                "mean_edition_multiple": round(statistics.fmean(
                    m for values in per_participant.values() for m in values), 6)
                if per_participant else None,
                "median_edition_multiple": round(statistics.median(
                    m for values in per_participant.values() for m in values), 6)
                if per_participant else None,
                "per_participant_mean_multiple": {
                    username: round(statistics.fmean(values), 6)
                    for username, values in sorted(per_participant.items())
                },
            })
        latency_doc[name] = rows
        print(f"[{name}/latency] " + "; ".join(
            f"L={r['latency_bars']} trades={r['total_trades']} "
            f"mean_mult={r['mean_edition_multiple']}" for r in rows), flush=True)

    # ---- official-rule arithmetic bound, per edition, from real captured prices ----
    bound_rows = []
    if daily_series:
        windows = windows_for(daily_series, args.daily_start)[:-1]
        if len(windows) > args.max_editions:
            windows = windows[-args.max_editions:]
        for window in windows:
            first_closes, excursions = [], []
            for symbol, series in sorted(daily_series.items()):
                bars = [b for b in series.bars if window[0] <= b.date <= window[1]]
                if not bars:
                    continue
                first_closes.append(bars[0].close)
                excursions.append(max(b.high for b in bars) / bars[0].close - 1.0)
            if not first_closes:
                continue
            bound = max_edition_multiple_bound(
                primary, first_closes, max(excursions))
            bound_rows.append({
                "start_date": window[0],
                "end_date": window[1],
                "symbols": len(first_closes),
                "sum_first_closes": round(sum(first_closes), 4),
                "best_favourable_excursion": round(max(excursions), 6),
                "max_notional_usd": bound["max_notional_usd"],
                "binding_notional_usd": bound["binding_notional_usd"],
                "max_edition_multiple": bound["max_edition_multiple"],
            })
    bound_summary = {}
    if bound_rows:
        worst = max(bound_rows, key=lambda r: r["max_edition_multiple"])
        bound_summary = {
            "method": (
                "For each edition: every pool symbol that traded in the window at its first "
                "session close, all of them held at the official 50-unit cap simultaneously "
                "(notional capped by balance x leverage = 100,000 x 1), and every one of them "
                "moving by the largest favourable excursion any single pool name actually made "
                "inside that same window. This is a single-hold long-only scenario, NOT an "
                "upper bound on repeated trading, short selling or compounding. "
                "It cannot establish whether 5x or 10x is reachable in a competition."
            ),
            "editions_evaluated": len(bound_rows),
            "max_edition_multiple_observed_bound": worst["max_edition_multiple"],
            "max_edition_multiple_bound_start": worst["start_date"],
            "single_hold_scenario_ge_5x": any(r["max_edition_multiple"] >= 5 for r in bound_rows),
            "single_hold_scenario_ge_10x": any(r["max_edition_multiple"] >= 10 for r in bound_rows),
            "coverage_complete": set(daily_series) == set(pool),
            "missing_symbols": sorted(set(pool) - set(daily_series)),
            "profile": primary.profile_id,
        }

    model_cards = []
    for model in (*STOCK_MODEL_IDS, "B1", "S1", "S2", "S3"):
        if model in STOCK_MODEL_IDS or model == "B1":
            cards = MODEL_CLAIMS.get(model)
            names = MODEL_NAMES
        else:
            cards = BASELINE_CLAIMS.get(model)
            names = BASELINE_NAMES
        if cards is None:
            continue
        model_cards.append({
            "model": model,
            "name": names.get(model, model),
            "kind": MODEL_KIND.get(model, "baseline"),
            "claim": cards,
            "params": "frozen in intel/stock_strategies.py (DEFAULT_PARAMS/VARIANTS)"
            if model in STOCK_MODEL_IDS else "frozen in intel/strategy.py (DEFAULT_PARAMS)",
        })

    doc = {
        "_meta": {
            "kind": "own_stock_competition_simulation",
            "description": (
                "The volatile-equity division of the repository's own paper competition: "
                "usernames from data/competition/stock_roster.json trade frozen contrarian or "
                "baseline models on captured vendor bars of the 20-stock volatile pool, with a "
                "fresh account per edition under an official rule profile. NOT the official "
                "contest, NOT a TradingView Strategy Report, NOT a Paper Trading account, NOT a "
                "prediction."
            ),
            "engine": DIVISION_ENGINE_VERSION,
            "generated_utc": stamp,
            "primary_scenario": PRIMARY_SCENARIO,
            "primary_profile": PRIMARY_PROFILE,
            "counterfactual_profile": COUNTERFACTUAL_PROFILE,
            "price_source": args.index,
            "source_metadata": index.get("_meta", {}),
            "rules_source": "data/contest_config.json + the rule profiles transcribed in intel/competition.py",
            "roster_source": "data/competition/stock_roster.json",
            "pool_source": "data/volatile_stocks.json (20-stock volatile pool)",
            "edition_design": {
                "edition_calendar_days": EDITION_CALENDAR_DAYS,
                "step_calendar_days": SEASON_STEP_CALENDAR_DAYS,
                "min_edition_sessions": MIN_EDITION_SESSIONS,
                "daily_season_start": args.daily_start,
                "max_editions_per_division": args.max_editions,
                "counterfactual_editions": args.counterfactual_editions,
                "latency_editions": args.latency_editions,
                "final_window_note": (
                    "The LATEST window is the 30-calendar-day window ending at the last captured "
                    "session; it is reported separately and excluded from season standings."
                ),
            },
            "cost_scenario": {
                "key": PRIMARY_SCENARIO,
                "label": scenario.label,
                "slippage_atr_fraction": scenario.slippage_atr_fraction,
                "commission_note": (
                    "The official stock-edition commission is 0.01% of notional (percent model) "
                    "and is applied per leg by the profile; the per-contract figure in the cost "
                    "scenario applies only to per-unit profiles. Slippage is the declared "
                    "ATR-fraction model from intel.backtest and is not an official figure."
                ),
            },
            "profiles": {
                pid: {
                    "label": profile.label,
                    "starting_balance": profile.starting_balance,
                    "leverage": profile.leverage,
                    "commission_model": profile.commission_model,
                    "commission_pct_of_notional": profile.commission_pct_of_notional,
                    "per_symbol_cap_units": profile.per_symbol_cap_units,
                    "min_active_days": profile.min_active_days,
                    "source_ids": list(profile.source_ids),
                    "is_counterfactual": profile.is_counterfactual,
                    "notes": profile.notes,
                }
                for pid, profile in (("stocks_official_leap", primary),
                                     ("stocks_20x_counterfactual", counterfactual))
            },
            "latency_steps_bars": list(LATENCY_STEPS),
            "assumptions": [
                "Equities are modelled as whole units (one unit = one share) with multiplier 1.0, "
                "so sizing is floor(notional / price).",
                "The official stock-edition cap of 50 units per instrument is applied to every "
                "symbol; the official page states it for its own seven instruments.",
                "Decisions evaluate on a bar's close and fill at that series' next bar open. On "
                "daily bars that means the next session's open; on hourly bars the next hour.",
                "Vendor captures are unadjusted for splits and dividends. A split inside a "
                "window appears as a large price jump and can create a spurious signal; the "
                "affected symbols are listed in the intraday capture index.",
                "Hourly captures cover roughly 730 days (vendor retention), so the hourly "
                "division's season is shorter than the daily division's.",
                "No borrow costs, locate fees or short-sale restrictions are modelled; shorts are "
                "sized exactly like longs.",
                "Ruin (equity <= 0) is terminal for an edition because the official rules forbid "
                "account resets; editions with equity below zero are floored at 0 in season "
                "products.",
                "The counterfactual 20:1 profile is NOT an official rule set. It is reported "
                "separately and must never be read as an achievable contest outcome.",
            ],
            "not_a_forecast": True,
        },
        "models": model_cards,
        "roster": [
            {"username": p.username, "kind": MODEL_KIND.get(p.model, "baseline"),
             "model": p.model, "variant": p.variant, "division": division_of[p.username],
             "pool": list(p.pool), "params_label": model_params_label(p.model, p.variant)}
            for p in participants
        ],
        "pool": pool,
        "divisions": divisions,
        "counterfactual_20x": counterfactual_doc,
        "latency_sensitivity": latency_doc,
        "official_rule_bound": {"summary": bound_summary, "editions": bound_rows},
        # No wall-clock field: scripts/verify.py re-runs this engine at the stored stamp and
        # requires the artifact field-for-field, so a runtime measurement would make every
        # capture-time artifact irreproducible. Runtime stays on stdout / in the CI log.
    }

    out_path = os.path.join(ROOT, args.out)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(f"latency sensitivity (daily): " + "; ".join(
        f"L={r['latency_bars']}: mean_mult={r['mean_edition_multiple']}, "
        f"trades={r['total_trades']}" for r in latency_doc.get("daily", [])))
    print(f"official-rule bound: {bound_summary}")
    print(f"wrote {os.path.relpath(out_path, ROOT)} in {time.time() - started:.3f}s "
          f"(run time is deliberately not stored: the artifact must reproduce exactly)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
