#!/usr/bin/env python3
"""Build the executive summary: what the top simulated strategies would place next.

This is the machine-derived half of the site's executive summary section. It does not
describe strategies in prose and it does not forecast prices. It takes the top-performing
usernames from the repository's own paper competitions and answers, mechanically:

    for each of those usernames, given its frozen model and the committed bars up to the
    latest captured session, what order would it place at the NEXT bar open, at what size
    under the official rule constants, and what is it waiting for if it would place nothing?

Method, in order:
  1. rank usernames by season realized P/L in data/competition_results.json (futures) and, when
     present, data/stock_competition_results.json (volatile-equity division), plus each
     division's latest-window leader;
  2. recompute that username's frozen model decisions on the FULL committed series
     (intel.competition.prepare_decisions for futures models, intel.stock_strategies for the
     equity models);
  3. replay the decisions with intel.competition.replay_order_state, which reports the open
     position and any order still awaiting its fill bar;
  4. size the pending order with the official rule constants (20:1 futures buying power with
     the section-08 per-symbol cap, or the stocks-edition 100,000 balance / 1:1 / 50-unit cap)
     at the last captured close — labelled as indicative, because the next open is unknown.

Output: data/exec_summary.json (deterministic with --stamp).

The output is a SIMULATION of mechanical rules on vendor history. It is not investment
advice, not a prediction, and not a route to a prize.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.competition import (  # noqa: E402
    RULE_PROFILES,
    Series,
    model_params_label,
    prepare_decisions,
    replay_order_state,
)
from intel.data import Bar, load_series  # noqa: E402
from intel.intraday import IntradayError, load_captures_for_symbols  # noqa: E402
from intel.stock_strategies import (  # noqa: E402
    MODEL_CLAIMS as STOCK_CLAIMS,
    MODEL_NAMES as STOCK_NAMES,
    STOCK_MODEL_IDS,
    generate_stock_decisions,
    warmup,
)
from intel.contrarian import MODEL_CLAIMS as FUTURES_CLAIMS  # noqa: E402
from intel.contrarian import generate_decisions  # noqa: E402
from intel.strategy import warmup_bars  # noqa: E402
from intel.contrarian import MODEL_NAMES as FUTURES_NAMES  # noqa: E402

TOP_N_PER_DIVISION = 3
RANKING_MIN_ROWS = 5          # rows published in each division's ranking before any extension
FUTURES_PROFILE = "futures_amp_sep2026"
STOCKS_PROFILE = "stocks_official_leap"


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def futures_series_map(capacity: dict, index: dict) -> dict[str, Series]:
    cap_by = {e["symbol"]: e for e in capacity["entries"]}
    out = {}
    for row in index["captures"]:
        if row.get("status") != "captured" or row.get("sessions_valid", 0) < 150:
            continue
        symbol = row["tradingview_symbol"]
        spec = cap_by[symbol]
        out[symbol] = Series(symbol, tuple(load_series(symbol)),
                             float(spec["contract_multiplier"]),
                             int(spec["rules_position_cap_contracts"]))
    return out


def stock_series_map(interval: str = "1d") -> dict[str, Series]:
    try:
        captures = load_captures_for_symbols(interval=interval)
    except IntradayError:
        return {}
    out = {}
    for symbol, capture in captures.items():
        bars = [Bar(b.ts, b.open, b.high, b.low, b.close, b.volume) for b in capture.bars]
        if len(bars) < 150:
            continue
        out[symbol] = Series(symbol, tuple(bars), 1.0, 50)
    return out


def indicative_futures_qty(profile, series: Series, price: float) -> int:
    multiplier = series.contract_multiplier
    unit = price * multiplier
    if unit <= 0:
        return 0
    room = min(profile.starting_balance * profile.leverage, series.rules_cap_contracts * unit)
    return int(room // unit)


def indicative_stock_qty(profile, price: float) -> int:
    if price <= 0:
        return 0
    return int(min(profile.per_symbol_cap_units or 0,
                   (profile.starting_balance * profile.leverage) // price))


def publish_prefix(board: list[dict], rows: list[dict]) -> list[dict]:
    """The ranking rows the artifact publishes: a true leaderboard prefix.

    It is at least RANKING_MIN_ROWS long and is extended so that every username the
    recommendations are drawn from is visible in the ranking. A reader must never be told to
    trade a username whose row the division's own ranking does not show (the offline verifier
    requires exactly this), and the prefix property keeps season_rank = 1..N.
    """
    deepest = RANKING_MIN_ROWS
    for row in rows:
        if not row:
            continue
        rank = row.get("season_rank") or row.get("season_rank_latest") or 0
        try:
            deepest = max(deepest, int(rank))
        except (TypeError, ValueError):
            continue
    return board[:deepest]


def build_entries(rows: list[dict], series_map: dict, roster_by_user: dict,
                  profile_key: str, division: str, is_stock: bool) -> list[dict]:
    profile = RULE_PROFILES[profile_key]
    entries = []
    for row in rows:
        username = row["username"]
        roster_row = roster_by_user[username]
        pool = [s for s in roster_row["pool"] if s in series_map]
        if not pool:
            continue
        model, variant = roster_row["model"], roster_row.get("variant")
        if not is_stock:
            decisions = prepare_decisions({s: series_map[s] for s in pool}, model, variant)
        else:
            # Equity divisions run the C6-C19 contrarian models plus the B1 control. The control
            # is a baseline from intel.strategy, not a stock model, so it must be dispatched the
            # same way scripts/run_stock_competition.py dispatches it -- otherwise building the
            # executive summary raises as soon as a stock division exists (found by the
            # synthetic-capture smoke test before the real captures landed).
            decisions = {}
            for s in pool:
                bars = list(series_map[s].bars)
                if model in STOCK_MODEL_IDS:
                    if len(bars) > warmup(model, variant):
                        decisions[s] = generate_stock_decisions(bars, model, variant)
                elif model == "B1":
                    # B1 is the buy-and-hold CONTROL: scripts/run_stock_competition.py runs it
                    # with an empty decision stream on one control symbol rather than through a
                    # signal generator, so the executive summary must mirror that (a control has
                    # no timing orders to publish).
                    continue
                elif len(bars) > warmup_bars(model):
                    decisions[s] = generate_decisions(bars, model, variant)
        # Stock divisions contain both the C6-C19 stock models (intel.stock_strategies) and the
        # S1-S3 baselines / B1 control, whose claims live with the futures models, so look in
        # both maps instead of publishing an empty "waiting for" string.
        claims = STOCK_CLAIMS.get(model) or FUTURES_CLAIMS.get(model) or ""
        names = STOCK_NAMES if is_stock else FUTURES_NAMES
        state_summary = []
        for symbol in pool:
            bars = list(series_map[symbol].bars)
            state = replay_order_state(decisions.get(symbol, []), bars)
            last_close = bars[-1].close if bars else None
            state_summary.append({
                "symbol": symbol,
                "position": state["position"],
                "position_since": state["position_since"],
                "last_bar_date": state["last_bar_date"],
                "last_close": last_close,
                "pending": [
                    {
                        "action": order["action"],
                        "reason": order["reason"],
                        "decided_date": order["decided_date"],
                        "decided_close": order["decided_close"],
                        "due_index": order["due_index"],
                    }
                    for order in state["pending"]
                ],
                "last_decision": state["last_decision"],
            })
        pending = [s for s in state_summary if s["pending"]]
        grouped = []
        for state in pending:
            by_symbol: dict[str, list] = {}
            for order in state["pending"]:
                by_symbol.setdefault(state["symbol"], []).append(order)
            for symbol, orders in by_symbol.items():
                exit_order = next((o for o in orders if o["action"] == "exit"), None)
                entry_orders = [o for o in orders if o["action"] in ("long", "short", "add")]
                entry_order = entry_orders[0] if entry_orders else None
                if exit_order and entry_order:
                    action = f"exit and reverse to {entry_order['action'].upper()}"
                elif exit_order:
                    action = "exit (close the open position)"
                elif entry_order:
                    if entry_order["action"] == "add":
                        # An "add" decision is only ever emitted while the model already
                        # holds the position (see intel/stock_strategies.py and
                        # intel/contrarian.py: adds fire inside the position branch), so
                        # labelling it a new position would be wrong. First observed in
                        # the wild on BreakoutBea/MSTR (stocks_daily, 2026-09-18 bar).
                        action = "ADD (increase the open position)"
                    else:
                        action = f"{entry_order['action'].upper()} (new position)"
                else:
                    continue
                token = entry_order or exit_order
                grouped.append((state, symbol, action, token, bool(exit_order)))
        pending_groups = grouped
        entries.append({
            "username": username,
            "division": division,
            "model": model,
            "model_name": names.get(model, model),
            "variant": variant,
            "params_label": model_params_label(model, variant),
            "rule_profile": profile_key,
            "season_realized_pnl_usd": row.get("season_realized_pnl_usd"),
            "season_rank": row.get("season_rank") or row.get("season_rank_latest"),
            "best_edition_multiple": row.get("best_edition_multiple"),
            "entry_condition": claims,
            "as_of_last_bar": max(
                (s["last_bar_date"] or "" for s in state_summary), default=None),
            "open_positions": [
                {"symbol": s["symbol"], "side": s["position"], "since": s["position_since"],
                 "last_close": s["last_close"]}
                for s in state_summary if s["position"]
            ],
            "pending_orders": [
                {
                    "symbol": symbol,
                    "action": action,
                    "reason": token["reason"],
                    "decided_on": token["decided_date"],
                    "decided_close": token["decided_close"],
                    "order_type": "market at the next bar open of the same series",
                    "sizing_rule": (
                        "the exit leg closes the position the model already holds; the entry leg "
                        "is sized by the rule below"
                    ) if is_exit and "reverse" in action else (
                        "close the open position; no new size"
                    ) if is_exit else (
                        f"{int(profile.per_symbol_cap_units)} units max per instrument "
                        f"(official stocks-edition cap); balance {profile.starting_balance:,.0f} "
                        f"x leverage {profile.leverage:g}"
                    ) if is_stock else (
                        f"{profile.leverage:g}:1 buying power on {profile.starting_balance:,.0f} "
                        f"with the official section-08 per-symbol cap"
                    ),
                    "indicative_size_units": (
                        None if is_exit and "reverse" not in action else
                        indicative_stock_qty(profile, state["last_close"])
                        if is_stock and state["last_close"]
                        else indicative_futures_qty(profile, series_map[symbol],
                                                    state["last_close"])
                        if state["last_close"] else None
                    ),
                    "indicative_size_note": (
                        "an exit leg carries no size: it closes whatever the position is"
                        if is_exit and "reverse" not in action else
                        "indicative only: computed from the last captured close and the official "
                        "rule constants; the actual fill price at the next open is unknown"
                    ),
                }
                for state, symbol, action, token, is_exit in pending_groups
            ],
            "waiting_for": None if pending_groups else (
                "nothing further: this is the buy-and-hold control and it places no timing orders"
                if model == "B1" else claims
            ),
            "strategy_kind": "buy_and_hold_control" if model == "B1" else "signal_timed",
            "symbols_watched": pool,
        })
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--out", default="data/exec_summary.json")
    args = ap.parse_args()

    def default_stamp() -> str:
        """Deterministic 'as of': the newest stamp among the input artifacts."""
        stamps = []
        for rel, keys in (("data/competition_results.json", ("generated_utc",)),
                          ("data/stock_competition_results.json", ("generated_utc",)),
                          ("data/intraday_index.json", ("fetched_at_utc",)),
                          ("data/market_history_index.json", ("fetched_at_utc",))):
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            meta = json.load(open(path, encoding="utf-8")).get("_meta", {})
            for key in keys:
                if meta.get(key):
                    stamps.append(meta[key])
        return max(stamps) if stamps else "unknown"

    stamp = args.stamp or default_stamp()

    capacity = load_json("data/initial_capacity.json")
    index = load_json("data/market_history_index.json")
    futures_roster = load_json("data/competition/roster.json")
    futures_results = load_json("data/competition_results.json")
    futures_by_user = {r["username"]: r for r in futures_roster["participants"]}

    futures_series = futures_series_map(capacity, index)
    futures_board = futures_results["leaderboard"]
    futures_top = [row for row in futures_board[:TOP_N_PER_DIVISION]]
    latest_winner = futures_results["latest_edition"]["leader"]
    if all(row["username"] != latest_winner["username"] for row in futures_top):
        futures_top.append({
            "username": latest_winner["username"],
            "season_realized_pnl_usd": next(
                r["season_realized_pnl_usd"] for r in futures_board
                if r["username"] == latest_winner["username"]),
            "best_edition_multiple": next(
                r["best_edition_multiple"] for r in futures_board
                if r["username"] == latest_winner["username"]),
            "season_rank": next(
                r["season_rank"] for r in futures_board
                if r["username"] == latest_winner["username"]),
            "latest_edition_leader": True,
        })

    divisions = {}
    divisions["futures"] = {
        "division": "futures",
        "rule_profile": FUTURES_PROFILE,
        "price_source": "data/market_history/ (vendor daily bars, front-month continuous futures)",
        "competition_source": "data/competition_results.json",
        "ranking": [
            {"season_rank": row["season_rank"], "username": row["username"],
             "season_realized_pnl_usd": row["season_realized_pnl_usd"],
             "best_edition_multiple": row["best_edition_multiple"]}
            for row in publish_prefix(futures_board, futures_top)
        ],
        "recommendations": build_entries(futures_top, futures_series, futures_by_user,
                                         FUTURES_PROFILE, "futures", is_stock=False),
    }

    stock_path = os.path.join(ROOT, "data/stock_competition_results.json")
    if os.path.exists(stock_path):
        stocks = load_json("data/stock_competition_results.json")
        stock_roster = load_json("data/competition/stock_roster.json")
        stock_by_user = {r["username"]: r for r in stock_roster["participants"]}
        daily = stocks.get("divisions", {}).get("daily", {})
        for name, interval in (("stocks_daily", "1d"), ("stocks_hourly", "1h")):
            key = "daily" if interval == "1d" else "hourly"
            div = stocks.get("divisions", {}).get(key, {})
            if not div.get("leaderboard"):
                divisions[name] = {
                    "division": name,
                    "status": div.get("status", "not_run"),
                    "rule_profile": STOCKS_PROFILE,
                    "recommendations": [],
                }
                continue
            series_map = stock_series_map(interval)
            board = div["leaderboard"]
            top = board[:TOP_N_PER_DIVISION]
            latest = div.get("latest_edition", {}).get("leader")
            if latest and all(row["username"] != latest["username"] for row in top):
                top.append(next((row for row in board if row["username"] == latest["username"]),
                                {}))
            divisions[name] = {
                "division": name,
                "rule_profile": STOCKS_PROFILE,
                "interval": interval,
                "price_source": (
                    f"data/intraday/ ({interval} vendor bars for the 20-stock volatile pool)"),
                "competition_source": "data/stock_competition_results.json",
                "ranking": [
                    {"season_rank": row["season_rank"], "username": row["username"],
                     "season_realized_pnl_usd": row["season_realized_pnl_usd"],
                     "best_edition_multiple": row["best_edition_multiple"]}
                    for row in publish_prefix(board, top)
                ],
                "recommendations": build_entries(
                    [row for row in top if row], series_map, stock_by_user,
                    STOCKS_PROFILE, name, is_stock=True) if series_map else [],
            }
    else:
        divisions["stocks_daily"] = {
            "division": "stocks_daily",
            "status": "not_run",
            "reason": (
                "data/stock_competition_results.json is produced by "
                "scripts/run_stock_competition.py after the intraday capture lands "
                "(data/intraday_index.json)"
            ),
            "rule_profile": STOCKS_PROFILE,
            "recommendations": [],
        }

    pending_total = sum(len(entry["pending_orders"])
                        for div in divisions.values() for entry in div.get("recommendations", []))
    doc = {
        "_meta": {
            "kind": "executive_summary_recommendations",
            "description": (
                "Machine-derived 'what would be placed next' table for the top-performing "
                "usernames of the repository's own paper competitions. Orders are mechanical "
                "replays of frozen models on committed vendor bars; sizes are indicative and "
                "computed from the official rule constants at the last captured close."
            ),
            "engine": "exec-summary-1",
            "generated_utc": stamp,
            "top_n_per_division": TOP_N_PER_DIVISION,
            "divisions": list(divisions),
            "pending_order_count": pending_total,
            "sizing_note": (
                "Indicative sizes use the official rule constants only: futures = 250,000 x 20 "
                "buying power with the section-08 per-symbol cap; stocks edition = 100,000 x 1 "
                "with a 50-unit cap. Actual size in a live account depends on the real equity and "
                "the fill price."
            ),
            "honesty_note": (
                "This is a simulation of mechanical rules on vendor history for a PAPER "
                "competition. It is not investment advice, not a forecast, and not a claim that "
                "any of these orders would win a prize. Historical and simulated returns do not "
                "imply future results."
            ),
            "not_a_forecast": True,
        },
        "divisions": divisions,
    }
    # The rendered size label lives in the artifact rather than in each renderer, so the console
    # line, the exec-summary table and the strategy cards cannot disagree ("~1 units" once did).
    # Labels are therefore finalised BEFORE the document is serialised.
    for div in divisions.values():
        for entry in div.get("recommendations", []):
            for order in entry["pending_orders"]:
                size = order["indicative_size_units"]
                order["indicative_size_label"] = (
                    f"~{size} unit" + ("" if size == 1 else "s")) if size is not None \
                    else "closes existing position"

    out_path = os.path.join(ROOT, args.out)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"exec summary: {len(divisions)} divisions, {pending_total} pending orders")
    for name, div in divisions.items():
        for entry in div.get("recommendations", []):
            for order in entry["pending_orders"]:
                print(f"  {name}: {entry['username']} ({entry['model']}) "
                      f"{order['action'].upper()} {order['symbol']} @ next open "
                      f"({order['indicative_size_label']})")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
