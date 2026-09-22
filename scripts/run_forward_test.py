#!/usr/bin/env python3
"""Build the forward-test PnL ledger for the shadow competitions (futures + stocks).

Replays every username on BOTH rosters through the exact engine of the committed
season runs (``intel.competition.run_participant_window`` with ``return_fills=True``):

- division ``futures``: ``data/competition/roster.json`` over the LATEST edition
  window of ``data/competition_results.json`` under the futures rule profile;
- divisions ``daily`` / ``hourly`` / ``15minute``: ``data/competition/stock_roster.json``
  on the LATEST ``latest_window`` of ``data/stock_competition_results.json`` under the
  stocks rule profile.

Every closed tranche is recorded (date, fill price, size, side, net P/L) with a
running cumulative realized P/L per username, plus division leaderboards.

Output: ``data/forward_test_ledger.json`` (deterministic with ``--stamp``). The
offline verifier re-runs this script at the artifact's stored stamp and requires
field-for-field equality, and cross-checks each username's summed tranche P/L
against its division's ``latest_edition`` aggregate.

This is a forward paper test on captured vendor history - not a live account, not
a forecast, and not investment advice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel.backtest import COST_SCENARIOS  # noqa: E402
from intel.competition import RULE_PROFILES, Series  # noqa: E402
from intel.data import load_series  # noqa: E402
from intel.forward_ledger import build_ledger  # noqa: E402
from intel.intraday import IntradayError, load_all, load_index  # noqa: E402

PRIMARY_SCENARIO = "moderate"
PRIMARY_PROFILE = "stocks_official_leap"
FUTURES_PROFILE = "futures_amp_sep2026"
MIN_SERIES_BARS = 150  # consistent with scripts/run_competition.py


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def load_json_optional(rel: str) -> dict | None:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_futures_bundle(profile, scenario) -> dict | None:
    """Inputs of the committed futures run; None when any of them is unavailable."""
    try:
        cfg_rel = "data/market_history_index.json"
        index = load_json_optional(cfg_rel)
        capacity = load_json_optional("data/initial_capacity.json")
        roster = load_json_optional("data/competition/roster.json")
        competition = load_json_optional("data/competition_results.json")
        if not index or not capacity or not roster or not competition:
            return None
        # Same eligibility build as scripts/run_competition.py so the ledger replays
        # exactly the series set the season run used.
        cap_by_symbol = {e["symbol"]: e for e in capacity["entries"]}
        series_map = {}
        for cap_row in index["captures"]:
            if cap_row.get("status") != "captured":
                continue
            sym = cap_row["tradingview_symbol"]
            if cap_row.get("sessions_valid", 0) < MIN_SERIES_BARS:
                continue
            bars = load_series(sym)
            spec = cap_by_symbol[sym]
            series_map[sym] = Series(
                symbol=sym,
                bars=tuple(bars),
                contract_multiplier=float(spec["contract_multiplier"]),
                rules_cap_contracts=int(spec["rules_position_cap_contracts"]),
            )
        if not series_map:
            return None
        return {
            "series_map": series_map,
            "roster_doc": roster,
            "competition_doc": competition,
            "profile": profile,
            "scenario": scenario,
        }
    except (OSError, KeyError, ValueError, TypeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", default="data/intraday_index.json")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--out", default="data/forward_test_ledger.json")
    args = ap.parse_args()

    def default_stamp() -> str:
        """Newest input stamp, so an un-stamped run still reproduces exactly."""
        stamps = []
        for rel, keys in ((args.index, ("fetched_at_utc",)),
                          ("data/stock_competition_results.json", ("generated_utc",)),
                          ("data/competition/stock_roster.json", ("created_utc",)),
                          ("data/competition_results.json", ("generated_utc",)),
                          ("data/competition/roster.json", ("created_utc",))):
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                meta = json.load(fh).get("_meta", {})
            for key in keys:
                if meta.get(key):
                    stamps.append(meta[key])
        return max(stamps) if stamps else datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    stamp = args.stamp or default_stamp()

    try:
        index = load_index(args.index)
        captures = load_all(index)
    except IntradayError as exc:
        print(f"::error::{exc}", flush=True)
        return 1

    roster_doc = load_json("data/competition/stock_roster.json")
    competition_doc = load_json("data/stock_competition_results.json")
    profile = RULE_PROFILES[PRIMARY_PROFILE]
    scenario = COST_SCENARIOS[PRIMARY_SCENARIO]

    futures_bundle = load_futures_bundle(
        RULE_PROFILES[FUTURES_PROFILE], COST_SCENARIOS[PRIMARY_SCENARIO],
    )

    doc = build_ledger(
        captures, roster_doc, competition_doc, profile, scenario, stamp,
        futures=futures_bundle,
    )

    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    meta = doc["_meta"]
    print(f"forward-test ledger: {meta['participant_count']} usernames, "
          f"{meta['closed_tranche_count']} closed tranches, "
          f"{meta['latest_edition_cross_checks']} latest-edition cross-checks")
    for name, div in doc["divisions"].items():
        if div.get("status") != "replayed":
            print(f"  {name}: {div.get('status')} ({div.get('reason', '')})")
            continue
        top = div["leaderboard"][:3]
        tops = ", ".join(f"{r['username']} {r['realized_pnl_usd']:+,.2f}" for r in top)
        w = div["window"]
        misses = [u["username"] for u in div["usernames"]
                  if u.get("ledger_matches_latest_edition") is False]
        note = f" | cross-check MISSES: {', '.join(misses)}" if misses else ""
        print(f"  {name}: window {w['start_date']} -> {w['end_date']} ({w['sessions']} sessions) "
              f"| top: {tops}{note}")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
