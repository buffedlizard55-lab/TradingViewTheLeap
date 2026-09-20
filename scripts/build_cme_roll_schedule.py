#!/usr/bin/env python3
"""Commit the CME front-contract roll schedule for every pooled future.

`intel/competition.py` can force-close a position at a declared roll boundary
(`roll_dates=...`), but the repository has never had dates to declare: the CME
transcriptions carried the rule *text* and set `roll_dates_transcribed: false`. This
script derives the dates from that text - via the rule codecs in `intel/cme_roll.py`, each
of which quotes the official sentence it implements - and commits them to
`data/cme_roll_schedule.json` for every product whose published rule is mechanically
decidable.

Window. Each product's window is the span of the daily continuous-series bars this
repository actually holds (`data/market_history/<SYMBOL>.json`), so the schedule covers
exactly the sessions the simulation can run on and no further. Nothing is extrapolated
past the years the business-day basis was reviewed for; `intel/cme_roll.py` clamps and
records that.

Honesty. A product with no codec gets `roll_dates: []` and a reason naming the gap. No
date is ever borrowed from a neighbouring product, and no rule is restated from memory:
`scripts/verify.py` re-runs every codec and re-compares each quoted sentence against the
stored transcription, so a hand-edited date or a reworded CME rule fails the build.

Engine wiring status is recorded in the artifact. Committing the schedule does not by
itself change any published result; `scripts/run_competition.py` still runs without
`roll_dates`, and that is stated here rather than implied.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import cme_roll  # noqa: E402

HOURS_PATH = os.path.join(ROOT, "data", "cme_product_hours.json")
HISTORY_INDEX_PATH = os.path.join(ROOT, "data", "market_history_index.json")
OUT_PATH = os.path.join(ROOT, "data", "cme_roll_schedule.json")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def bar_window(rel_path: str) -> tuple[date, date] | None:
    """First and last UTC calendar date of the captured daily bars for one symbol."""
    path = os.path.join(ROOT, rel_path)
    if not os.path.exists(path):
        return None
    doc = load(path)
    stamps = []
    for result in (doc.get("chart", {}).get("result") or []):
        stamps.extend(result.get("timestamp") or [])
    if not stamps:
        return None
    lo = datetime.fromtimestamp(min(stamps), tz=timezone.utc).date()
    hi = datetime.fromtimestamp(max(stamps), tz=timezone.utc).date()
    return lo, hi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    hours = load(HOURS_PATH)
    by_product = {p["product"]: p for p in hours.get("products") or []}
    history = load(HISTORY_INDEX_PATH)

    products = []
    coded = 0
    dated = 0
    total_dates = 0
    for rec in sorted(history["captures"], key=lambda r: r["tradingview_symbol"]):
        tv = rec["tradingview_symbol"]
        product = tv.split(":")[-1].split("1!")[0]
        window = bar_window(rec.get("file", ""))
        if window is None:
            products.append({
                "product": product, "tradingview_symbol": tv, "roll_dates": [],
                "reason": f"no captured daily bars at {rec.get('file')!r}, so no window to schedule",
            })
            continue
        start, end = window
        result = cme_roll.roll_dates(product, start, end)
        result["tradingview_symbol"] = tv
        result["captured_bar_window"] = {"start": start.isoformat(), "end": end.isoformat()}
        transcribed = (by_product.get(product) or {}).get("termination")
        ok, why = cme_roll.codec_matches_transcription(product, transcribed)
        result["rule_matches_transcription"] = ok if product in cme_roll.RULE_CODECS else None
        if product in cme_roll.RULE_CODECS and not ok:
            result["reason"] = why
            result["roll_dates"] = []
            result["termination_dates_iso"] = []
        if result["roll_dates"]:
            coded += 1
            dated += 1
            total_dates += len(result["roll_dates"])
        products.append(result)

    doc = {
        "_meta": {
            "kind": "cme_roll_schedule",
            "description": (
                "Front-contract termination dates for every pooled future, derived from the "
                "official termination rule of each product by the codecs in intel/cme_roll.py. "
                "A product with no codec carries an empty list and a reason; no date is inferred "
                "from another product. scripts/verify.py re-runs every codec and re-compares each "
                "quoted rule sentence against data/cme_product_hours.json."
            ),
            "engine": "cme-roll-1",
            "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "module": cme_roll.describe(),
            "business_day_basis": cme_roll.BUSINESS_DAY_BASIS,
            "hours_artifact": "data/cme_product_hours.json",
            "product_count": len(products),
            "products_with_dates": dated,
            "products_without_dates": len(products) - dated,
            "roll_date_count": total_dates,
            "not_a_forecast": True,
            "engine_wiring": {
                "wired_into_competition": False,
                "note": (
                    "intel/competition.py accepts roll_dates= and force-closes at the roll bar's "
                    "open, but scripts/run_competition.py does not pass them yet: doing so changes "
                    "the published futures season and needs its own before/after comparison. The "
                    "schedule is committed and audited; the wiring is a separate, tracked step."
                ),
            },
            "declared_limitations": [
                "Business days come from the NYSE full-closure table, not a transcribed CME Globex "
                "closure set; where the two differ a derived date can be off by one session (IR-30).",
                "The cryptocurrency codecs apply the rule's London-business-day leg as 'not a "
                "weekend' because only the U.S. leg is checkable here.",
                "Dates are the termination dates of successive contract months, which is the "
                "boundary at which a 1! continuous series changes front contract; the repository "
                "holds vendor continuous bars, not per-bar contract identity, so the mapping is "
                "by rule and not by observed contract switch.",
            ],
        },
        "products": products,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")

    print(f"wrote {os.path.relpath(args.out, ROOT)}: {dated}/{len(products)} products with "
          f"{total_dates} roll dates; {len(products) - dated} without (codec or window missing)")
    for p in products:
        if not p.get("roll_dates"):
            print(f"  no dates: {p['product']:<5} {p.get('reason')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
