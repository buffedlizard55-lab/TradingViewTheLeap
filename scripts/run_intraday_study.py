#!/usr/bin/env python3
"""Intraday study: intra-session gap fills and execution latency, measured on captures.

Input (committed, offline, no network):

  data/intraday_index.json + data/intraday/*.json   (scripts/fetch_intraday.py output)

Output:

  data/intraday_study.json

Two measurements, both arithmetic on stored vendor bars — nothing is modelled, fitted,
or forecast:

1. GAP FILL. Every session boundary in a capture produces one observation:

     gap          = session_open - prior_session_close
     gap_atr      = gap / prior session-bar ATR(14)
     filled       = did the session trade back through prior_session_close?
                    (gap up: session low <= prior close; gap down: session high >= prior close)
     bars_to_fill = bars from the session open until the first bar that filled it

   Results are bucketed by |gap_atr| so a reviewer can see whether large vendor gaps
   behave differently from small ones. "Gap" here is a difference between two stored
   vendor prints across a session boundary, not an exchange opening auction.

2. EXECUTION LATENCY. For every decision bar i the study measures what a fill would
   have cost relative to the decision bar's close:

     same-session next open   : open(i+1) - close(i)   (the Pine broker-emulator default)
     session-boundary next open: the same quantity when i+1 is a new session (the gap)
     k-bar delay              : close(i+k) - close(i) for k in {1, 2, 3, 5}

   Reported in basis points of the decision close, split by interval and asset kind.
   Positive means the delayed fill is at a HIGHER price than the decision close (adverse
   for a long, favourable for a short); negatives are the mirror image.

Everything is deterministic; pin the timestamp with --stamp so scripts/verify.py can
re-run this script and require byte-identical output.
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

from intel.intraday import IBar, IntradayError, atr, load_all, load_index, sessions  # noqa: E402

GAP_BUCKETS = (
    (0.0, 0.25, "lt_0.25_atr"),
    (0.25, 0.5, "0.25_0.5_atr"),
    (0.5, 1.0, "0.5_1.0_atr"),
    (1.0, 2.0, "1.0_2.0_atr"),
    (2.0, float("inf"), "ge_2.0_atr"),
)

LATENCY_STEPS = (1, 2, 3, 5)


def bucket_of(abs_gap_atr: float) -> str:
    for low, high, name in GAP_BUCKETS:
        if low <= abs_gap_atr < high:
            return name
    return GAP_BUCKETS[-1][2]


def session_bars(day_bars: list[IBar]) -> IBar:
    """Aggregate one session's intraday bars into a synthetic daily bar."""
    return IBar(
        ts=day_bars[0].ts,
        open=day_bars[0].open,
        high=max(b.high for b in day_bars),
        low=min(b.low for b in day_bars),
        close=day_bars[-1].close,
        volume=sum(b.volume for b in day_bars),
    )


def median_or_none(values: list[float]) -> float | None:
    return round(statistics.median(values), 6) if values else None


def mean_or_none(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return round(ordered[idx], 6)


def study_capture(capture) -> dict:
    """Gap-fill + latency observations for one captured series."""
    day_groups = sessions(capture.bars)
    daily = [session_bars(bars) for _, bars in day_groups]
    daily_atr = atr(daily, 14)

    gaps: list[dict] = []
    skipped_no_atr = 0        # ATR(14) is undefined until 14 sessions exist
    skipped_zero_gap = 0      # the session opened exactly at the prior close
    for i in range(1, len(day_groups)):
        prior_close = daily[i - 1].close
        atr_prev = daily_atr[i - 1]
        if atr_prev is None or atr_prev <= 0 or prior_close <= 0:
            skipped_no_atr += 1
            continue
        day, bars = day_groups[i]
        session_open = bars[0].open
        gap = session_open - prior_close
        gap_atr = gap / atr_prev
        session_low = min(b.low for b in bars)
        session_high = max(b.high for b in bars)
        if gap > 0:
            direction = "up"
            filled = session_low <= prior_close
            bars_to_fill = next(
                (j for j, b in enumerate(bars) if b.low <= prior_close), None
            )
        elif gap < 0:
            direction = "down"
            filled = session_high >= prior_close
            bars_to_fill = next(
                (j for j, b in enumerate(bars) if b.high >= prior_close), None
            )
        else:
            skipped_zero_gap += 1
            continue
        session_close = bars[-1].close
        gaps.append({
            "date": day,
            "direction": direction,
            "gap": round(gap, 6),
            "gap_atr": round(gap_atr, 6),
            "abs_gap_atr": abs(gap_atr),
            "bucket": bucket_of(abs(gap_atr)),
            "filled": filled,
            "bars_to_fill": bars_to_fill,
            "session_bars": len(bars),
            "fill_fraction": round((bars_to_fill + 1) / len(bars), 6)
            if bars_to_fill is not None else None,
            "closed_through": (session_close <= prior_close) if direction == "up"
            else (session_close >= prior_close),
        })

    latency: dict[str, list[float]] = {"same_session_next_open": [], "session_boundary_next_open": []}
    for step in LATENCY_STEPS:
        latency[f"delay_{step}_bar_close_delta"] = []
    for day_index, (day, bars) in enumerate(day_groups):
        for j, bar in enumerate(bars):
            if j + 1 < len(bars):
                nxt = bars[j + 1]
                latency["same_session_next_open"].append(
                    (nxt.open - bar.close) / bar.close * 10_000.0
                )
            elif day_index + 1 < len(day_groups):
                nxt = day_groups[day_index + 1][1][0]
                latency["session_boundary_next_open"].append(
                    (nxt.open - bar.close) / bar.close * 10_000.0
                )
            for step in LATENCY_STEPS:
                if j + step < len(bars):
                    later = bars[j + step]
                elif day_index + 1 < len(day_groups):
                    following = day_groups[day_index + 1][1]
                    later = following[j + step - len(bars)] if j + step - len(bars) < len(following) else None
                else:
                    later = None
                if later is not None:
                    latency[f"delay_{step}_bar_close_delta"].append(
                        (later.close - bar.close) / bar.close * 10_000.0
                    )
    # Every session after the first either yields a gap row or is skipped for one of exactly
    # two measured reasons. Making that identity explicit (and publishing it) is what lets the
    # offline verifier prove no session silently disappeared: "sessions - 1" alone is wrong,
    # because the first 14 sessions have no ATR baseline yet.
    candidates = max(len(day_groups) - 1, 0)
    if len(gaps) + skipped_no_atr + skipped_zero_gap != candidates:
        raise IntradayError(
            f"{capture.symbol}[{capture.interval}]: gap accounting does not close: "
            f"{len(gaps)} gaps + {skipped_no_atr} no-ATR + {skipped_zero_gap} zero-gap "
            f"!= {candidates} sessions after the first"
        )
    return {"gaps": gaps, "latency": latency, "sessions": len(day_groups),
            "first_session": day_groups[0][0] if day_groups else None,
            "last_session": day_groups[-1][0] if day_groups else None,
            "gap_candidates": candidates,
            "gaps_skipped_no_atr": skipped_no_atr,
            "gaps_skipped_zero_gap": skipped_zero_gap}


def summarize_bucket(rows: list[dict], kind: str, bucket: str, direction: str) -> dict | None:
    subset = [r for r in rows if r["bucket"] == bucket and r["direction"] == direction]
    if not subset:
        return None
    filled = [r for r in subset if r["filled"]]
    return {
        "kind": kind,
        "bucket": bucket,
        "direction": direction,
        "sessions": len(subset),
        "fill_rate": round(len(filled) / len(subset), 6),
        "median_bars_to_fill": median_or_none([r["bars_to_fill"] for r in filled]),
        "median_fill_fraction_of_session": median_or_none(
            [r["fill_fraction"] for r in filled if r["fill_fraction"] is not None]
        ),
        "close_through_rate": round(sum(1 for r in subset if r["closed_through"]) / len(subset), 6),
        "median_abs_gap_atr": median_or_none([r["abs_gap_atr"] for r in subset]),
    }


def latency_summary(values: list[float]) -> dict:
    if not values:
        return {"observations": 0}
    absolute = [abs(v) for v in values]
    return {
        "observations": len(values),
        "median_signed_bps": median_or_none(values),
        "mean_signed_bps": mean_or_none(values),
        "median_abs_bps": median_or_none(absolute),
        "p90_abs_bps": percentile(absolute, 0.90),
        "share_above_10bps_abs": round(sum(1 for v in absolute if v > 10.0) / len(absolute), 6),
        "share_above_50bps_abs": round(sum(1 for v in absolute if v > 50.0) / len(absolute), 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", default=None, help="pin generated_utc for reproducibility")
    parser.add_argument("--out", default="data/intraday_study.json")
    args = parser.parse_args()
    if args.stamp:
        stamp = args.stamp
    else:
        stamp = (load_index().get("_meta") or {}).get("fetched_at_utc") or "unknown"

    try:
        index = load_index()
        captures = load_all(index)
    except IntradayError as exc:
        print(f"::error::{exc}", flush=True)
        return 1
    if not captures:
        print("::error::no captured intraday series available", flush=True)
        return 1

    per_symbol = []
    all_gaps_by_kind: dict[str, list[dict]] = {"equity": [], "future": []}
    latency_by_kind_interval: dict[tuple[str, str], dict[str, list[float]]] = {}
    coverage = []

    for key in sorted(captures):
        capture = captures[key]
        if capture.interval == "1d":
            continue
        result = study_capture(capture)
        gaps = result["gaps"]
        all_gaps_by_kind.setdefault(capture.kind, []).extend(gaps)
        slot = latency_by_kind_interval.setdefault(
            (capture.kind, capture.interval), {name: [] for name in result["latency"]}
        )
        for name, values in result["latency"].items():
            slot.setdefault(name, []).extend(values)
        filled = [g for g in gaps if g["filled"]]
        per_symbol.append({
            "symbol": capture.symbol,
            "kind": capture.kind,
            "interval": capture.interval,
            "sessions": result["sessions"],
            "first_session": result["first_session"],
            "last_session": result["last_session"],
            "bars": len(capture.bars),
            "gaps_analyzed": len(gaps),
            "gap_candidates": result["gap_candidates"],
            "gaps_skipped_no_atr": result["gaps_skipped_no_atr"],
            "gaps_skipped_zero_gap": result["gaps_skipped_zero_gap"],
            "gap_up_sessions": sum(1 for g in gaps if g["direction"] == "up"),
            "gap_down_sessions": sum(1 for g in gaps if g["direction"] == "down"),
            "fill_rate_all": round(len(filled) / len(gaps), 6) if gaps else None,
            "median_abs_gap_atr": median_or_none([g["abs_gap_atr"] for g in gaps]),
            "median_bars_to_fill": median_or_none(
                [g["bars_to_fill"] for g in filled if g["bars_to_fill"] is not None]
            ),
        })
        coverage.append({
            "symbol": capture.symbol,
            "kind": capture.kind,
            "interval": capture.interval,
            "bars": len(capture.bars),
            "first_utc": capture.first_utc,
            "last_utc": capture.last_utc,
            "raw_response_sha256": capture.raw_response_sha256,
            "stored_sha256": capture.stored_sha256,
            "endpoint": capture.endpoint,
        })

    bucket_rows = []
    for kind in ("equity", "future"):
        for _, _, bucket in GAP_BUCKETS:
            for direction in ("up", "down"):
                row = summarize_bucket(all_gaps_by_kind.get(kind, []), kind, bucket, direction)
                if row:
                    bucket_rows.append(row)

    aggregate = {}
    for kind in ("equity", "future"):
        rows = all_gaps_by_kind.get(kind, [])
        if not rows:
            continue
        filled = [r for r in rows if r["filled"]]
        big = [r for r in rows if r["abs_gap_atr"] >= 1.0]
        big_filled = [r for r in big if r["filled"]]
        aggregate[kind] = {
            "sessions_with_gap": len(rows),
            "fill_rate_all": round(len(filled) / len(rows), 6),
            "fill_rate_ge_1_atr": round(len(big_filled) / len(big), 6) if big else None,
            "sessions_with_gap_ge_1_atr": len(big),
            "median_abs_gap_atr": median_or_none([r["abs_gap_atr"] for r in rows]),
            "median_abs_gap_atr_ge_1": median_or_none([r["abs_gap_atr"] for r in big]),
            "median_bars_to_fill": median_or_none([r["bars_to_fill"] for r in filled]),
            "share_closed_through": round(sum(1 for r in rows if r["closed_through"]) / len(rows), 6),
        }

    latency_rows = []
    for (kind, interval), series in sorted(latency_by_kind_interval.items()):
        row = {"kind": kind, "interval": interval}
        for name in ("same_session_next_open", "session_boundary_next_open",
                     *(f"delay_{s}_bar_close_delta" for s in LATENCY_STEPS)):
            row[name] = latency_summary(series.get(name, []))
        latency_rows.append(row)

    doc = {
        "_meta": {
            "kind": "intraday_study",
            "description": (
                "Deterministic measurement of (1) intra-session gap fills and (2) execution "
                "latency cost, computed only from the committed canonical vendor captures under "
                "data/intraday/. Yahoo Finance is a market_data_vendor tier source: these are "
                "vendor bars, not exchange prints, and no claim is made that any participant "
                "could have transacted at these prices."
            ),
            "engine": "intraday-study-1",
            "generated_utc": stamp,
            "script": "scripts/run_intraday_study.py",
            "price_source": "data/intraday_index.json + data/intraday/*.json",
            "intervals_studied": [i for i in ("15m", "1h") if any(
                c["interval"] == i for c in coverage)],
            "gap_buckets": [name for _, _, name in GAP_BUCKETS],
            "latency_steps_bars": list(LATENCY_STEPS),
            "methodology": [
                "Session = UTC calendar date of the bar timestamp. For US equities the regular "
                "session (13:30-20:00 UTC) never crosses a UTC date, so this equals the trading "
                "session. For futures a UTC date splits the CME session at the vendor's daily "
                "break; futures numbers here are therefore 'UTC-day boundary' numbers and are "
                "labelled that way, not exchange sessions.",
                "Gap = session_open - prior_session_close, both read from stored bars.",
                "Gap scale = ATR(14) of session-aggregated bars (open first bar, high/low of the "
                "session, close of the last bar) at the prior session; gap_atr = gap / ATR.",
                "Filled = the session traded back through the prior session close (gap up: "
                "session low <= prior close; gap down: session high >= prior close).",
                "Latency = price change from the decision bar's close to the fill bar's open "
                "(default engine semantics) or to a later bar's close, in basis points of the "
                "decision close. Positive = the fill is above the decision close.",
            ],
            "assumptions": [
                "Vendor intraday series are not adjusted for splits or dividends inside the "
                "capture window; a split inside the window would appear as a large gap.",
                "Yahoo intraday bars may include extended-hours prints depending on the "
                "instrument; the capture stores what the vendor returned.",
                "15-minute captures cover roughly the last 60 days, hourly captures roughly the "
                "last 730 days (vendor retention); sample sizes differ by interval.",
                "No transaction costs, borrow costs or liquidity limits are applied to the "
                "latency measurement; it is a price-distance measurement only.",
            ],
            "not_a_forecast": True,
        },
        "coverage": coverage,
        "gap_fill": {
            "aggregate_by_kind": aggregate,
            "buckets": bucket_rows,
            "per_symbol": per_symbol,
        },
        "execution_latency": {
            "by_kind_interval": latency_rows,
        },
    }

    out_path = os.path.join(ROOT, args.out)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"intraday study: {len(coverage)} captured series studied, "
          f"{sum(len(v) for v in all_gaps_by_kind.values())} session-boundary gaps")
    for kind, row in aggregate.items():
        print(f"  {kind}: fill_rate_all={row['fill_rate_all']} "
              f"fill_rate_ge_1_atr={row['fill_rate_ge_1_atr']} "
              f"median_abs_gap_atr={row['median_abs_gap_atr']}")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
