#!/usr/bin/env python3
"""Re-derive downstream artifacts after the raw market-history captures change.

This is the single command that keeps the repository internally consistent after
``scripts/fetch_market_data.py`` (manual or CI) writes new vendor captures:

1. Re-run the walk-forward simulation + volatility screen
   (``scripts/run_backtests.py``) with the deterministic stamp
   (the capture index's ``fetched_at_utc``), regenerating
   ``data/backtest_results.json`` and ``data/volatility_intelligence.json``.
2. Sync ``research/strategy/models.json`` result stamps/summaries to the new artifact.
3. Re-derive the leaderboard/prize arithmetic lab (``scripts/leaderboard_lab.py`` ->
   ``data/leaderboard_lab.json``).
4. Rebuild the deterministic intelligence/provenance report (``scripts/build_intelligence.py`` ->
   ``data/intelligence_report.json``).
5. Re-derive everything that depends on the intraday captures *when they exist*:
   the gap-fill / execution-latency study (``scripts/run_intraday_study.py`` ->
   ``data/intraday_study.json``), the volatile-stock division
   (``scripts/run_stock_competition.py`` -> ``data/stock_competition_results.json``) and the
   mechanical upcoming-order summary (``scripts/build_exec_summary.py`` ->
   ``data/exec_summary.json``). Missing captures skip these steps with a printed reason
   instead of failing or inventing data.
6. Re-run the TradingView export benchmark (``scripts/tv_benchmark.py`` ->
   ``data/tv_benchmark.json``); it reports ``blocked`` while no real export is committed.
7. Rebuild the deterministic intelligence/provenance report
   (``scripts/build_intelligence.py`` -> ``data/intelligence_report.json``).
8. Rebuild the GitHub Pages document (``scripts/build_site.py`` -> root ``index.html``).

The offline verifier (``scripts/verify.py``) re-runs step 1 with the committed stamp and requires
byte-identical artifacts, so after this script runs the repository is back to a green state with
no other edits needed. No network access is used.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def save(rel: str, obj) -> None:
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def run_backtests() -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "run_backtests.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"run_backtests.py failed with exit code {proc.returncode}")


def sync_models() -> None:
    bt = load("data/backtest_results.json")
    stamp = bt["_meta"]["generated_utc"]
    models = load("research/strategy/models.json")
    by_id = {m["id"]: m for m in bt["models"]}
    for row in models["models"]:
        b = by_id[row["id"]]
        z = b["scenarios"]["zero"]
        row["result"] = {
            "basis": "independent daily-bar simulation (intel engine; NOT a TradingView Strategy Report)",
            "artifact": "data/backtest_results.json",
            "run_stamp_utc": stamp,
            "windows": z["windows"],
            "trades_zero_cost": z["trades"],
            "median_net_profit_usd_zero_cost": z["median_net_profit_usd"],
            "mean_net_profit_usd_zero_cost": z["mean_net_profit_usd"],
            "windows_ge_5x_zero_cost": z["windows_ge_5x"],
            "verdict_reasons": b["verdict_reasons"],
        }
    save("research/strategy/models.json", models)
    print(f"models.json synced to run stamp {stamp}")


def run_placement_lab() -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "leaderboard_lab.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"leaderboard_lab.py failed with exit code {proc.returncode}")


def run_script(script: str, *args: str) -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"{script} failed with exit code {proc.returncode}")


def intraday_steps() -> None:
    """Re-derive everything that depends on data/intraday/ (skipped when absent)."""
    index = os.path.join(ROOT, "data", "intraday_index.json")
    if not os.path.exists(index):
        print("no data/intraday_index.json yet - the intraday capture workflow has not "
              "committed bars, so the intraday study and the stock division are skipped")
        return
    print("=== step 4: intraday gap-fill / latency study ===")
    run_script("run_intraday_study.py")
    print("=== step 5: volatile-stock division (multi-season) ===")
    run_script("run_stock_competition.py")
    print("=== step 6: executive-summary orders ===")
    run_script("build_exec_summary.py")


def tv_benchmark_step() -> None:
    print("=== step 7: TradingView export benchmark (blocked when no real export is present) ===")
    run_script("tv_benchmark.py")


def build_intelligence() -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_intelligence.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"build_intelligence.py failed with exit code {proc.returncode}")


def build_site() -> None:
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_site.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"build_site.py failed with exit code {proc.returncode}")


def main() -> int:
    print("=== step 1: re-run backtests + volatility screen ===")
    run_backtests()
    print("=== step 2: sync models.json ===")
    sync_models()
    print("=== step 3: re-derive the placement arithmetic ===")
    run_placement_lab()
    intraday_steps()
    tv_benchmark_step()
    print("=== step 8: rebuild intelligence report ===")
    build_intelligence()
    print("=== step 9: rebuild index.html ===")
    build_site()
    print("done. Run 'python3 scripts/verify.py' to confirm the repository is green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
