#!/usr/bin/env python3
"""Build the forward-test PnL ledger for the volatile-equity shadow competition.

Replays every username on ``data/competition/stock_roster.json`` through the exact
engine of the committed season run (``intel.competition.run_participant_window``
with ``return_fills=True``) on the LATEST window of each division - the same
``latest_window`` behind ``latest_edition`` in ``data/stock_competition_results.json``
- and records every closed tranche (date, fill price, size, side, net P/L) with a
running cumulative realized P/L per username, plus division leaderboards.

Output: ``data/forward_test_ledger.json`` (deterministic with ``--stamp``). The
offline verifier re-runs this script at the artifact's stored stamp and requires
field-for-field equality, and cross-checks each username's summed tranche P/L
against the season artifact's ``latest_edition`` aggregate.

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
from intel.competition import RULE_PROFILES  # noqa: E402
from intel.forward_ledger import build_ledger  # noqa: E402
from intel.intraday import IntradayError, load_all, load_index  # noqa: E402

PRIMARY_SCENARIO = "moderate"
PRIMARY_PROFILE = "stocks_official_leap"


def load_json(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


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
                          ("data/competition/stock_roster.json", ("created_utc",))):
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

    doc = build_ledger(captures, roster_doc, competition_doc, profile, scenario, stamp)

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
        print(f"  {name}: window {w['start_date']} -> {w['end_date']} ({w['sessions']} sessions) "
              f"| top: {tops}")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
