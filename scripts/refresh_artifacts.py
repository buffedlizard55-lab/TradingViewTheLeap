#!/usr/bin/env python3
"""Re-derive downstream artifacts after the raw market-history captures change.

This is the single command that keeps the repository internally consistent after
``scripts/fetch_market_data.py`` (manual or CI) writes new vendor captures:

1. Re-run the walk-forward simulation + volatility screen
   (``scripts/run_backtests.py``) with the deterministic stamp
   (the capture index's ``fetched_at_utc``), regenerating
   ``data/backtest_results.json`` and ``data/volatility_intelligence.json``.
2. Sync ``research/strategy/models.json`` result stamps/summaries to the new artifact.
3. Rebuild the GitHub Pages document (``scripts/build_site.py`` -> root ``index.html``).

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
    print("=== step 3: rebuild index.html ===")
    build_site()
    print("done. Run 'python3 scripts/verify.py' to confirm the repository is green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
