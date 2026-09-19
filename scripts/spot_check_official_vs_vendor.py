#!/usr/bin/env python3
"""Spot-check official-provider bars (Alpaca IEX) against vendor bars (Yahoo) per symbol.

Purpose: detect corporate-action / adjustment drift between the two sources before a
strategy verdict is trusted. For every (symbol, interval) present in BOTH indexes the
script aligns bars on their UTC epoch, computes the close-to-close relative delta in
basis points, and reports:

* ``matched_bars`` / ``official_only`` / ``vendor_only`` counts,
* ``median_abs_delta_bps``, ``p95_abs_delta_bps``, ``max_abs_delta_bps``,
* the epoch of the largest delta and both closes on that bar,
* ``suspected_split_boundary``: the first epoch after which the running median of the
  ratio official/vendor changes by more than 1% (a split-adjustment mismatch shows up
  as a step in that ratio, not as noise).

Nothing is corrected or re-priced here: the artifact is a comparison record for review.
IEX is a single exchange, so small close differences versus a consolidated-tape vendor
are expected; a persistent multiplicative step is not.

Offline and deterministic given the two committed indexes; exits 0 when at least one
pair was compared, 2 when nothing could be compared (a status the caller records, not an
error to hide).
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
from intel import intraday  # noqa: E402


def _load_series(index_rel: str) -> dict[tuple[str, str], intraday.Capture]:
    idx = intraday.load_index(index_rel)
    out = {}
    for rec in idx.get("captures", []):
        if rec.get("status") != "captured":
            continue
        cap = intraday.load_capture(rec)
        out[(cap.symbol, cap.interval)] = cap
    return out


def compare(official: intraday.Capture, vendor: intraday.Capture) -> dict:
    o = {b.ts: b for b in official.bars}
    v = {b.ts: b for b in vendor.bars}
    common = sorted(set(o) & set(v))
    row = {
        "symbol": official.symbol, "interval": official.interval,
        "official_bars": len(o), "vendor_bars": len(v), "matched_bars": len(common),
        "official_only": len(set(o) - set(v)), "vendor_only": len(set(v) - set(o)),
    }
    if not common:
        row["status"] = "no_overlap"
        return row
    deltas = []
    ratios = []
    worst = (-1.0, common[0])
    for ts in common:
        oc, vc = o[ts].close, v[ts].close
        bps = (oc - vc) / vc * 1e4
        deltas.append(abs(bps))
        ratios.append(oc / vc)
        if abs(bps) > worst[0]:
            worst = (abs(bps), ts)
    deltas_sorted = sorted(deltas)
    p95 = deltas_sorted[min(len(deltas_sorted) - 1, int(round(0.95 * (len(deltas_sorted) - 1))))]
    row.update({
        "median_abs_delta_bps": round(statistics.median(deltas), 3),
        "p95_abs_delta_bps": round(p95, 3),
        "max_abs_delta_bps": round(worst[0], 3),
        "max_delta_epoch": worst[1],
        "max_delta_utc": datetime.fromtimestamp(worst[1], tz=timezone.utc).isoformat(),
        "max_delta_official_close": o[worst[1]].close,
        "max_delta_vendor_close": v[worst[1]].close,
    })
    # Step detection on the official/vendor ratio: compare the median ratio of the first
    # and second half of a sliding window; a persistent >1% step marks a split mismatch.
    boundary = None
    window = max(10, min(40, len(ratios) // 10))
    if len(ratios) >= 2 * window:
        for i in range(window, len(ratios) - window):
            left = statistics.median(ratios[i - window:i])
            right = statistics.median(ratios[i:i + window])
            if left > 0 and abs(right / left - 1.0) > 0.01:
                boundary = common[i]
                break
    row["suspected_split_boundary_epoch"] = boundary
    row["suspected_split_boundary_utc"] = (
        datetime.fromtimestamp(boundary, tz=timezone.utc).isoformat() if boundary else None)
    row["status"] = "drift_suspected" if boundary else "compared"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--official-index", default="data/official_bars/index.json")
    ap.add_argument("--vendor-index", default="data/intraday_index.json")
    ap.add_argument("--out", default="data/official_bars/spot_check.json")
    ap.add_argument("--symbols", default=None, help="comma-separated subset (default: every overlap)")
    ap.add_argument("--stamp", default=None)
    args = ap.parse_args()

    official = _load_series(args.official_index)
    vendor = _load_series(args.vendor_index)
    keys = sorted(set(official) & set(vendor))
    if args.symbols:
        wanted = {s.strip() for s in args.symbols.split(",") if s.strip()}
        keys = [k for k in keys if k[0] in wanted]
    rows = [compare(official[k], vendor[k]) for k in keys]
    report = {
        "_meta": {
            "kind": "official_vs_vendor_spot_check",
            "generated_utc": args.stamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "official_index": args.official_index,
            "vendor_index": args.vendor_index,
            "official_provider": "Alpaca Basic IEX feed (https://docs.alpaca.markets/us/reference/stockbars)",
            "vendor": "Yahoo Finance chart API (market_data_vendor tier)",
            "method": ("closes aligned on UTC epoch; |official-vendor|/vendor in bps; split-mismatch "
                       "step detector on the official/vendor ratio (>1% persistent change)"),
            "pairs_compared": len(rows),
            "drift_suspected": sum(1 for r in rows if r.get("status") == "drift_suspected"),
            "not_a_forecast": "Comparison record only; no price is corrected or invented.",
        },
        "pairs": rows,
    }
    os.makedirs(os.path.dirname(os.path.join(ROOT, args.out)), exist_ok=True)
    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(f"spot-check: {len(rows)} pair(s) compared, "
          f"{report['_meta']['drift_suspected']} drift suspected -> {args.out}")
    return 0 if rows else 2


if __name__ == "__main__":
    sys.exit(main())
