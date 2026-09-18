#!/usr/bin/env python3
"""Build the auditable intelligence/status layer from committed research artifacts.

This report deliberately summarizes existing evidence; it does not fetch data, tune a model,
or turn a paper result into a forecast. It is pure stdlib and deterministic so CI can re-run it.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "intelligence_report.json"
STAMP = "2026-09-18"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def rounded(value, digits=6):
    return round(float(value), digits)


def build_report() -> dict:
    competition = load("data/competition_results.json")
    roster = load("data/competition/roster.json")
    backtests = load("data/backtest_results.json")
    models = load("research/strategy/models.json")
    market = load("data/market_history_index.json")
    stocks = load("data/volatile_stocks.json")
    sources = load("research/sources/sources.json")
    frontier = load("data/frontier_history.json")

    # Optional artifacts: present once the capture-intraday workflow has committed bars and
    # the derived builders have run in a networked environment. Absence is recorded as a
    # blocked workstream, never silently smoothed over.
    def load_if_present(rel: str):
        path = ROOT / rel
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    intraday_index = load_if_present("data/intraday_index.json")
    intraday_study = load_if_present("data/intraday_study.json")
    stock_competition = load_if_present("data/stock_competition_results.json")
    stock_roster = load_if_present("data/competition/stock_roster.json")
    exec_summary = load_if_present("data/exec_summary.json")
    tv_benchmark = load_if_present("data/tv_benchmark.json")

    intraday_captured = []
    if intraday_index:
        intraday_captured = [c for c in intraday_index["captures"] if c.get("status") == "captured"]
    intraday_missing = []
    if intraday_index:
        intraday_missing = [c for c in intraday_index["captures"] if c.get("status") != "captured"]
    intraday_cover = {
        "captured_series": len(intraday_captured),
        "by_interval": intraday_index["_meta"].get("captured_by_interval") if intraday_index else {},
        "captured_bar_total": sum(c.get("bar_count", 0) for c in intraday_captured),
        "failed_or_not_attempted": len(intraday_missing),
        "index": "data/intraday_index.json" if intraday_index else None,
        "index_stamp": intraday_index["_meta"].get("fetched_at_utc") if intraday_index else None,
        "vendor_rate_limited_direct": intraday_index["_meta"].get("direct_rate_limited")
        if intraday_index else None,
        "boundary": (
            "Vendor intraday prints, not exchange data and not contest fills. The study measures "
            "price distances on these bars (did a session gap fill, what a delayed fill cost); it "
            "makes no claim that a participant could transact at these prices."
        ),
    }
    stock_division = {
        "roster_usernames": len(stock_roster["participants"]) if stock_roster else 0,
        "artifact": "data/stock_competition_results.json" if stock_competition else None,
        "primary_profile": intraday_index is not None and stock_roster is not None,
        "boundary": (
            "Repository-generated usernames and outcomes on vendor equity bars under the official "
            "stocks-edition constants (with a clearly-declared 20:1 counterfactual). Not TradingView "
            "participants, not observed contest results."
        ),
    }

    by_user = {p["username"]: p for p in competition["participants"]}
    latest_rows = {r["username"]: r for r in competition["latest_edition"]["rows"]}
    model_defs = {m["model"]: m for m in competition["models"]}
    groups = {}
    for participant in competition["participants"]:
        groups.setdefault(participant["model"], []).append(participant)

    model_results = []
    for model_id, definition in model_defs.items():
        rows = groups.get(model_id, [])
        best = [p["best_edition_multiple"] for p in rows]
        latest = [p["latest_edition_multiple"] for p in rows]
        ruined = [p["ruined_editions"] for p in rows]
        model_results.append({
            "model": model_id,
            "name": definition["name"],
            "kind": definition["kind"],
            "claim": definition["claim"],
            "participants": len(rows),
            "usernames": sorted(p["username"] for p in rows),
            "best_single_edition_multiple_max": rounded(max(best), 6) if best else None,
            "best_single_edition_multiple_median": rounded(statistics.median(best), 6) if best else None,
            "latest_edition_multiple_median": rounded(statistics.median(latest), 6) if latest else None,
            "participant_editions_ge_5x": sum(p["editions_ge_5x"] for p in rows),
            "participant_editions_ge_10x": sum(p["editions_ge_10x"] for p in rows),
            "ruined_editions": sum(ruined),
            "positive_season_participants": sum(p["season_realized_pnl_usd"] > 0 for p in rows),
            "latest_leaders": sorted(
                [{"username": p["username"], "multiple": rounded(latest_rows[p["username"]]["equity_multiple"], 6)}
                 for p in rows if p["username"] in latest_rows],
                key=lambda x: (-x["multiple"], x["username"]),
            )[:3],
        })

    captured = [c for c in market["captures"] if c.get("status") == "captured"]
    failed = [c for c in market["captures"] if c.get("status") != "captured"]
    official_sources = [s["source_id"] for s in sources["sources"] if s.get("tier") == "official_primary"]
    tradingview_sources = sorted(sid for sid in official_sources if sid.startswith("TV-"))
    cme_sources = sorted(sid for sid in official_sources if sid.startswith("CME-"))
    vendor_sources = [s["source_id"] for s in sources["sources"] if s.get("tier") == "market_data_vendor"]
    latest_frontier = frontier["captures"][-1]

    report = {
        "_meta": {
            "description": "Auditable intelligence layer: provenance, model status, comparison statistics, and explicit blocked/unrun work. This is a research status report, not a signal or forecast.",
            "engine": "intelligence-report-1",
            "generated_utc": STAMP,
            "deterministic": True,
            "not_a_forecast": True,
            "not_trading_advice": True,
            "input_artifacts": [
                "data/competition_results.json", "data/competition/roster.json",
                "data/backtest_results.json", "data/market_history_index.json",
                "data/volatile_stocks.json", "research/strategy/models.json",
                "research/sources/sources.json", "data/frontier_history.json",
            ],
        },
        "provenance": {
            "tradingview_official": {
                "status": "verified",
                "source_ids": tradingview_sources,
                "uses": ["edition rules", "point-in-time public leaderboard captures", "participant count", "published contest outcomes"],
                "boundary": "Official pages do not expose the listed traders' full trade histories, instruments, entry/exit prices, or strategies.",
            },
            "cme_official": {
                "status": "verified",
                "source_ids": cme_sources,
                "uses": ["contract specifications, multipliers, and exchange reference material"],
                "boundary": "CME reference material supports contract arithmetic; it is not evidence of a TradingView contest fill.",
            },
            "market_data_vendor": {
                "status": "captured_and_hash_verified",
                "source_ids": sorted(vendor_sources),
                "captured_series": len(captured),
                "failed_series": len(failed),
                "intraday_captured_series": intraday_cover["captured_series"],
                "intraday_captured_bars": intraday_cover["captured_bar_total"],
                "intraday_index_stamp": intraday_cover["index_stamp"],
                "boundary": "Yahoo front-month continuous futures are vendor evidence with unadjusted roll splices; they are not official TradingView contest fills. Intraday equity/futures bars are vendor prints under the same boundary.",
            },
            "repository_simulation": {
                "status": "reproducible_paper_simulation",
                "price_input": "data/market_history_index.json",
                "rules_input": "data/contest_config.json",
                "participant_count": len(roster["participants"]),
                "season_editions": competition["_meta"]["season_editions"],
                "boundary": "Shadow usernames and outcomes are generated by this repository's engines; they are not TradingView participants or observed contest results.",
            },
        },
        "status_register": [
            {
                "workstream": "official rules and public frontier",
                "status": "verified",
                "evidence": ["data/frontier_history.json", "data/contest_config.json", "research/evidence/TV-CONTEST-AMP-SEP2026-2026-09-18-R8.md"],
                "next_step": "Continue point-in-time captures if the moving board is still relevant; do not infer a final cutoff from a displayed row.",
            },
            {
                "workstream": "vendor futures history and volatility screen",
                "status": "captured",
                "evidence": ["data/market_history_index.json", "data/volatility_intelligence.json"],
                "next_step": "Refresh the window and separately validate contract rolls, costs, and intraday execution before using any candidate operationally.",
            },
            {
                "workstream": "independent walk-forward baselines",
                "status": "completed_with_caveats",
                "evidence": ["data/backtest_results.json", "research/strategy/testing-plan.md"],
                "next_step": "Run frozen holdouts and sensitivity analysis on a new, untouched capture; the current sample is not sufficient to claim generalization.",
            },
            {
                "workstream": "contrarian shadow competition",
                "status": "completed_with_caveats",
                "evidence": ["data/competition_results.json", "data/competition/roster.json", "intel/competition.py", "intel/contrarian.py"],
                "next_step": "Add a genuinely out-of-sample season and validate fills against a higher-frequency source; do not optimize to the current vendor window.",
            },
            {
                "workstream": "intraday vendor captures (15m / 1h / long 1d) for the volatile pool",
                "status": "captured" if intraday_index else "blocked_or_unrun",
                "evidence": (["data/intraday_index.json", "scripts/fetch_intraday.py", "intel/intraday.py",
                              "research/evidence/YAHOO-INTRADAY-CAPTURE.md"]
                             if intraday_index else
                             ["scripts/fetch_intraday.py", "intel/intraday.py",
                              "research/evidence/YAHOO-INTRADAY-CAPTURE.md",
                              ".github/workflows/capture-intraday.yml"]),
                "next_step": ("Top up any series the vendor rate-limited (scripts/fetch_intraday.py "
                              "--only-failed) and re-run the study after each capture."
                              if intraday_index else
                              "The capture workflow has not committed data/intraday_index.json yet; "
                              "dispatch .github/workflows/capture-intraday.yml (the repository sandbox "
                              "has no egress to the vendor)."),
                "detail": intraday_cover,
            },
            {
                "workstream": "intra-session gap fill and execution latency (our own measurement)",
                "status": "completed_with_caveats" if intraday_study else "blocked_or_unrun",
                "evidence": (["data/intraday_study.json", "scripts/run_intraday_study.py"]
                             if intraday_study else ["scripts/run_intraday_study.py", "intel/intraday.py"]),
                "next_step": ("Extend the latency measurement with the vendor's own bid/ask or with "
                              "a second vendor before drawing conclusions about real slippage."
                              if intraday_study else
                              "Run scripts/run_intraday_study.py once data/intraday_index.json exists."),
            },
            {
                "workstream": "volatile-stock division of the paper competition (20 usernames)",
                "status": ("completed_with_caveats" if stock_competition and stock_division["roster_usernames"]
                           else "blocked_or_unrun"),
                "evidence": (["data/stock_competition_results.json", "data/competition/stock_roster.json",
                              "intel/stock_strategies.py", "scripts/run_stock_competition.py"]
                             if stock_competition else
                             ["data/competition/stock_roster.json", "intel/stock_strategies.py",
                              "scripts/run_stock_competition.py"]),
                "next_step": ("Add an out-of-sample season on bars captured after this run; the current "
                              "division is fitted to one finite vendor window."
                              if stock_competition else
                              "Run scripts/run_stock_competition.py once the intraday captures exist."),
                "detail": stock_division,
            },
            {
                "workstream": "executive summary of mechanically-implied upcoming orders",
                "status": "captured" if exec_summary else "blocked_or_unrun",
                "evidence": (["data/exec_summary.json", "scripts/build_exec_summary.py"]
                             if exec_summary else ["scripts/build_exec_summary.py"]),
                "next_step": ("Re-derive after every capture and after every competition re-run; the "
                              "sizes are indicative rule-arithmetic, never advice."
                              if exec_summary else "Run scripts/build_exec_summary.py."),
                "detail": ({
                    "pending_order_count": exec_summary["_meta"]["pending_order_count"],
                    "divisions": exec_summary["_meta"]["divisions"],
                    "sizing_note": exec_summary["_meta"]["sizing_note"],
                } if exec_summary else {}),
            },
            {
                "workstream": "Pine broker-emulator rules vs the Python fill model",
                "status": "completed_with_caveats" if tv_benchmark else "blocked_or_unrun",
                "evidence": (["data/tv_benchmark.json", "intel/pine_emulator.py", "scripts/tv_benchmark.py"]
                             if tv_benchmark else ["intel/pine_emulator.py", "scripts/tv_benchmark.py"]),
                "next_step": ("The rules are encoded from TradingView's own Pine documentation and the "
                              "import path is proven on a synthetic fixture; the numbers are not yet "
                              "validated against a real platform run."
                              if tv_benchmark else "Run scripts/tv_benchmark.py."),
                "detail": ({
                    "status": tv_benchmark["_meta"]["status"],
                    "real_exports_found": tv_benchmark["_meta"]["real_exports_found"],
                    "fixture_exports_found": tv_benchmark["_meta"]["fixture_exports_found"],
                } if tv_benchmark else {}),
            },
            {
                "workstream": "authenticated TradingView Strategy Report import",
                "status": "blocked_or_unrun",
                "evidence": ["intel/tv_import.py", "scripts/tv_benchmark.py",
                             "research/strategy/models.json",
                             "research/strategy/the-leap-hypothesis-lab.pine"],
                "next_step": "Requires a signed-in TradingView account with Strategy Report export entitlement. The importer (intel/tv_import.py) accepts the official List-of-Trades CSV, the Performance-Summary CSV and the 5-sheet XLSX and fails loudly on gating; drop an export into data/tv_reports/ and re-run scripts/tv_benchmark.py. No figure on this site is claimed to come from a real export.",
            },
            {
                "workstream": "official listed-trader strategy attribution",
                "status": "blocked_by_public_data",
                "evidence": ["data/frontier_history.json"],
                "next_step": "Requires public trade-history disclosure or direct participant records; leaderboard P/L alone cannot identify a strategy.",
            },
        ],
        "model_comparison": {
            "basis": "24-edition moderate-cost shadow competition; each row is a repository username bound to a frozen model/variant.",
            "thresholds": [5, 10, 20, 50, 100],
            "latest_edition": competition["latest_edition"]["edition_id"],
            "results": model_results,
            "kind_contrast": competition["kind_contrast"],
            "decision": {
                "best_contrarian_single_edition_multiple": competition["kind_contrast"]["contrarian"]["best_single_edition_multiple"],
                "best_baseline_single_edition_multiple": competition["kind_contrast"]["baseline"]["best_single_edition_multiple"],
                "any_shadow_10x": competition["target_summary"]["ge_10x"] > 0,
                "any_shadow_20x": competition["target_summary"]["ge_20x"] > 0,
                "any_shadow_50x": competition["target_summary"]["ge_50x"] > 0,
                "any_shadow_100x": competition["target_summary"]["ge_100x"] > 0,
                "interpretation": "Contrarian models produced the highest observed single-edition multiple in this finite simulation, but none reached 10x and the season-level results include ruin and negative outcomes. This is comparative evidence about this engine/window, not proof of edge or a forecast.",
            },
        },
        "coverage": {
            "intraday_capture": intraday_cover,
            "stock_division": stock_division,
            "latest_official_frontier_capture": latest_frontier["captured_at_utc"],
            "latest_official_participants_displayed": latest_frontier["participants_displayed"],
            "vendor_captured_symbols": sorted(c["tradingview_symbol"] for c in captured),
            "vendor_failed_symbols": sorted(c["tradingview_symbol"] for c in failed),
            "walk_forward_models": [m["id"] for m in backtests["models"]],
            "pre_registered_strategy_candidates": [m["id"] for m in models["models"]],
            "historical_stock_records": stocks["_meta"]["record_count"],
            "historical_stock_boundary": "Stock ratios use vendor adjusted-close windows and are separate from futures contest evidence; no stock result is a contest forecast.",
        },
    }
    return report


def main() -> None:
    report = build_report()
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
