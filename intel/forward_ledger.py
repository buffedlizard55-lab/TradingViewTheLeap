"""Forward-test PnL ledger for the volatile-equity shadow competition.

What this is
------------
A trade-by-trade paper PnL ledger for EVERY username on the stock roster
(``data/competition/stock_roster.json``), replayed with the exact engine, rule
profile, cost scenario and window semantics of the committed season run
(``intel.competition.run_participant_window`` with ``return_fills=True``), on
the LATEST window of each division - the same ``latest_window`` that produced
``latest_edition`` in ``data/stock_competition_results.json``.

Why the latest window
---------------------
Editions are chronological and every model is frozen before any window runs
(see ``intel/stock_strategies.py`` and the hypothesis register), so the latest
window is the closest thing this repository has to a forward paper test: the
same frozen rules, pointed at the newest captured sessions, producing an
auditable trade ledger instead of an aggregate. It is still a replay of
captured vendor history inside a simulation - it is NOT a live account, NOT a
forecast, and NOT investment advice.

What is recorded per username
-----------------------------
Every closed tranche from the engine's own fill log (entry/exit dates and fill
prices, size, side, net P/L) with a running cumulative realized P/L attached in
exit order, plus the engine's aggregates (round trips, adds, drawdown, ruin)
and a division leaderboard by realized P/L. Nothing is synthesized: a username
with no fills gets an explicit empty ledger and zero counts, never a modelled
curve. Cross-check: each username's summed tranche P/L equals the
``latest_edition`` aggregate for the same username in the season artifact
(scripts/verify.py fails if they disagree).

Determinism
-----------
``build_ledger`` is a pure function of (captures, roster, competition artifact,
profile, scenario, stamp). ``scripts/run_forward_test.py`` exposes it behind
``--out`` / ``--stamp`` so ``scripts/verify.py`` can re-run it and require
field-for-field equality.
"""

from __future__ import annotations

from .backtest import CostScenario
from .competition import (
    Participant,
    RuleProfile,
    Series,
    run_participant_window,
    slices_and_starts,
)
from .contrarian import MODEL_CLAIMS as BASELINE_CLAIMS  # noqa: F401
from .contrarian import MODEL_NAMES as BASELINE_NAMES
from .contrarian import generate_decisions
from .data import Bar
from .stock_strategies import (
    MODEL_CLAIMS as STOCK_CLAIMS,  # noqa: F401
    MODEL_KIND,
    MODEL_NAMES,
    STOCK_MODEL_IDS,
    generate_stock_decisions,
    trailing_volatility,
    warmup,
)

DIVISION_INTERVALS = {"daily": "1d", "hourly": "1h", "15minute": "15m"}


def build_series(captures: dict, interval: str) -> dict[str, Series]:
    """Series objects (equity multiplier 1.0, official 50-unit cap) for one interval."""
    out: dict[str, Series] = {}
    for capture in captures.values():
        if capture.interval != interval:
            continue
        bars = [Bar(b.ts, b.open, b.high, b.low, b.close, b.volume) for b in capture.bars]
        if len(bars) < 30:
            continue
        out[capture.symbol] = Series(
            symbol=capture.symbol,
            bars=tuple(bars),
            contract_multiplier=1.0,
            rules_cap_contracts=50,
        )
    return out


def decisions_for_model(series_map: dict[str, Series], model: str, variant: str | None) -> dict:
    """Ordered decisions for one (model, variant) on every series of a division."""
    out: dict[str, list] = {}
    for symbol in sorted(series_map):
        bars = list(series_map[symbol].bars)
        if model in STOCK_MODEL_IDS:
            if len(bars) <= warmup(model, variant):
                out[symbol] = []
                continue
            out[symbol] = generate_stock_decisions(bars, model, variant)
        else:                                   # baselines S1-S3 reuse intel.contrarian
            if len(bars) <= 30:
                out[symbol] = []
                continue
            out[symbol] = generate_decisions(bars, model, variant)
    return out


def control_symbol_for(pool_symbols, series_map: dict[str, Series], window) -> str | None:
    """Highest trailing-volatility (60 daily returns) name strictly before the window."""
    best, best_vol = None, None
    for symbol in pool_symbols:
        if symbol not in series_map:
            continue
        bars = list(series_map[symbol].bars)
        before = [i for i, b in enumerate(bars) if b.date < window[0]]
        if not before:
            continue
        vol = trailing_volatility(bars, before[-1])
        if vol is not None and (best_vol is None or vol > best_vol):
            best, best_vol = symbol, vol
    return best


def build_ledger(
    captures: dict,
    roster_doc: dict,
    competition_doc: dict,
    profile: RuleProfile,
    scenario: CostScenario,
    stamp: str,
) -> dict:
    """Build the full ledger document. Pure function of its inputs plus the stamp."""
    divisions_out: dict[str, dict] = {}
    total_tranches = 0
    total_users = 0
    cross_checks = 0

    for division, interval in DIVISION_INTERVALS.items():
        div = (competition_doc.get("divisions") or {}).get(division) or {}
        window_doc = div.get("latest_window")
        latest_edition = div.get("latest_edition") or {}
        if not window_doc or not div.get("editions"):
            divisions_out[division] = {
                "status": "not_run",
                "reason": "the season has no completed latest window to forward-test on",
                "usernames": [],
                "leaderboard": [],
            }
            continue
        window = (window_doc["start_date"], window_doc["end_date"])
        series_map = build_series(captures, interval)
        if not series_map:
            divisions_out[division] = {
                "status": "not_run",
                "reason": f"no captured {interval} series in data/intraday_index.json",
                "usernames": [],
                "leaderboard": [],
            }
            continue

        season_row_by_user = {r["username"]: r for r in latest_edition.get("rows") or []}
        rows: list[dict] = []
        for entry in roster_doc["participants"]:
            pool_symbols = tuple(s for s in entry["pool"] if s in series_map)
            if not pool_symbols:
                continue
            slices, starts = slices_and_starts(pool_symbols, series_map, window)
            if not slices:
                continue
            p = Participant(
                username=entry["username"],
                model=entry["model"],
                variant=entry.get("variant"),
                pool=pool_symbols,
            )
            control = None
            if p.model == "B1":
                control = control_symbol_for(pool_symbols, series_map, window)
                if control is None:
                    continue
            dec = {} if p.model == "B1" else decisions_for_model(series_map, p.model, p.variant)
            result = run_participant_window(
                dec, slices, starts, series_map, profile, scenario,
                latency_bars=0, control_symbol=control, return_fills=True,
            )
            tranche_rows = []
            running = 0.0
            fills = sorted(
                getattr(result, "fill_log", []) or [],
                key=lambda r: (r.get("exit_ts") or 0, r.get("entry_ts") or 0, r.get("symbol") or ""),
            )
            for fill in fills:
                running = round(running + fill["net_pnl_usd"], 2)
                row = dict(fill)
                row["cum_realized_pnl_usd"] = running
                tranche_rows.append(row)
            record = _username_record(
                p, result, tranche_rows, profile,
                roster_division=entry.get("division", "daily"),
                control_symbol=control,
            )
            season_row = season_row_by_user.get(p.username)
            if season_row is not None:
                record["latest_edition_realized_pnl_usd"] = season_row["realized_pnl_usd"]
                # The season artifact sums the engine's unrounded per-trade floats; the ledger
                # sums 2dp tranche rows. Each tranche can round by <= 0.005, so the honest
                # cross-check bound is one cent per tranche plus one cent of slack. The
                # recorded delta makes the (tiny) rounding difference explicit rather than
                # hiding it, and the ledger's own rows sum exactly to its own totals.
                tolerance = round(0.01 * record["closed_tranches"] + 0.01, 2)
                delta = round(record["realized_pnl_usd"] - season_row["realized_pnl_usd"], 2)
                record["latest_edition_delta_usd"] = delta
                record["latest_edition_match_tolerance_usd"] = tolerance
                record["ledger_matches_latest_edition"] = abs(delta) <= tolerance
                cross_checks += 1
            rows.append(record)

        rows.sort(key=lambda r: (-r["realized_pnl_usd"], r["username"]))
        leaderboard = [
            {
                "rank": i,
                "username": r["username"],
                "model": r["model"],
                "variant": r["variant"],
                "model_name": r["model_name"],
                "kind": r["kind"],
                "roster_division": r["roster_division"],
                "realized_pnl_usd": r["realized_pnl_usd"],
                "equity_multiple": r["equity_multiple"],
                "round_trips": r["round_trips"],
                "closed_tranches": r["closed_tranches"],
                "winning_tranches": r["winning_tranches"],
            }
            for i, r in enumerate(rows, 1)
        ]
        sessions = sorted({b.date for s in series_map.values() for b in s.bars
                           if window[0] <= b.date <= window[1]})
        divisions_out[division] = {
            "status": "replayed",
            "window": {
                "start_date": window[0],
                "end_date": window[1],
                "sessions": len(sessions),
            },
            "latest_edition_id": latest_edition.get("edition_id"),
            "symbols_with_bars": len(series_map),
            "usernames": rows,
            "leaderboard": leaderboard,
        }
        total_tranches += sum(r["closed_tranches"] for r in rows)
        total_users += len(rows)

    return {
        "_meta": {
            "kind": "forward_test_pnl_ledger",
            "engine": "forward-ledger-1",
            "generated_utc": stamp,
            "description": (
                "Forward-test paper PnL ledger: every stock-roster username replayed on the "
                "latest window of each division (the same latest_window that produced "
                "latest_edition in data/stock_competition_results.json) with the same engine, "
                "rule profile and cost scenario as the committed season run. Every closed "
                "tranche is the engine's own fill log (date, fill price, size, side, net P/L) "
                "with a running cumulative realized P/L in exit order. Nothing is synthesized."
            ),
            "window_definition": (
                "latest_window per division in data/stock_competition_results.json (editions "
                "are chronological; models are frozen before any window runs, so this window "
                "is forward with respect to every parameter choice)"
            ),
            "rule_profile": profile.profile_id,
            "rule_profile_label": profile.label,
            "cost_scenario": getattr(scenario, "name", None) or "moderate",
            "starting_balance_usd": profile.starting_balance,
            "min_active_days": profile.min_active_days,
            "source_ids": list(profile.source_ids) + ["YAHOO-INTRADAY-CHART"],
            "participant_count": total_users,
            "closed_tranche_count": total_tranches,
            "latest_edition_cross_checks": cross_checks,
            "end_of_window_auto_close": True,
            "honesty_note": (
                "This is a simulation of mechanical rules on captured vendor history for a "
                "PAPER competition. It is not investment advice, not a forecast, and not a "
                "claim that any of these trades would win a prize. Historical and simulated "
                "returns do not imply future results."
            ),
            "not_a_forecast": True,
        },
        "divisions": divisions_out,
    }


def _username_record(
    p: Participant,
    result,
    tranche_rows: list[dict],
    profile: RuleProfile,
    roster_division: str,
    control_symbol: str | None = None,
) -> dict:
    model_name = MODEL_NAMES.get(p.model) or BASELINE_NAMES.get(p.model, p.model)
    kind = MODEL_KIND.get(p.model, "baseline")
    # The ledger is self-consistent by construction: the recorded totals are the exact sum
    # of the recorded 2dp tranche rows, so any reader can add the column and land on the
    # published figure. The engine's own unrounded aggregate may differ by at most half a
    # cent per tranche (see the latest_edition cross-check in build_ledger).
    realized = round(sum(r["net_pnl_usd"] for r in tranche_rows), 2)
    ending = round(profile.starting_balance + realized, 2)
    winning = sum(1 for r in tranche_rows if r["net_pnl_usd"] > 0)
    losing = sum(1 for r in tranche_rows if r["net_pnl_usd"] < 0)
    flat = len(tranche_rows) - winning - losing
    return {
        "username": p.username,
        "model": p.model,
        "variant": p.variant,
        "model_name": model_name,
        "kind": kind,
        "roster_division": roster_division,
        "pool": list(p.pool),
        "control_symbol": control_symbol,
        "starting_balance_usd": profile.starting_balance,
        "ending_equity_usd": ending,
        "realized_pnl_usd": realized,
        "equity_multiple": round(ending / profile.starting_balance, 6),
        "round_trips": result.trades,
        "active_days": result.active_days,
        "ruined": result.ruined,
        "add_tranches": result.add_tranches,
        "long_trades": result.long_trades,
        "short_trades": result.short_trades,
        "skipped_entries": result.skipped_entries,
        "margin_breach_bars": result.margin_breach_bars,
        "max_drawdown_usd": round(result.max_drawdown_usd, 2),
        "closed_tranches": len(tranche_rows),
        "winning_tranches": winning,
        "losing_tranches": losing,
        "flat_tranches": flat,
        "win_rate_tranches": round(winning / len(tranche_rows), 6) if tranche_rows else None,
        "tranche_ledger": tranche_rows,
    }
