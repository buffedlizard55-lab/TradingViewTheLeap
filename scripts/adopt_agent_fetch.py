#!/usr/bin/env python3
"""Adopt agent-fetched Yahoo chart responses into the canonical intraday capture format.

Why this exists
---------------
The research sandbox has no direct network egress; the GitHub-hosted capture lanes are the
primary route for vendor bars. When a lane repeatedly fails one series (vendor HTTP 429 /
relay timeouts on the oversized response) and the platform's page-fetch proxy CAN reach the
vendor, this script turns cached page-fetch responses into the exact same canonical capture
documents that scripts/fetch_intraday.py writes, so the offline verifier can audit them the
same way.

Honesty boundary (recorded in every document and index record this script writes):

* the transport is labelled ``arena-fetch-page`` - the bytes travelled through the agent
  platform's page-fetch proxy, not directly from this repository's network;
* ``raw_response_bytes`` / ``raw_response_sha256`` digest the exact response text received
  through that proxy (the markdown fence the proxy wraps JSON bodies in is stripped; nothing
  else is altered), so the recorded digest covers what was actually received;
* every bar still passes ``scripts.fetch_intraday.parse_chunk`` - vendor symbol, reported
  granularity, array alignment and OHLC invariants are checked with the SAME code the CI lane
  uses; a mangled or wrong-instrument response fails here exactly as it would in CI;
* bars are rounded to the same 5 decimals, merged, de-duplicated by epoch and sorted exactly
  like capture_series does; the series window must stay inside the frozen INTERVAL_SPEC.

Usage::

    python3 scripts/adopt_agent_fetch.py --symbol PLUG --interval 1d \
        --responses scratch/agent_fetch/PLUG_1d/   # one .json file per sub-window

The response files are named ``<period1>_<period2>.json`` (epoch bounds of the sub-window the
request used). The script writes data/intraday/<SYMBOL>_<interval>.json, replaces the series'
index record and recomputes the index tallies. It never touches any other series.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TRANSPORT = "arena-fetch-page"


def load_fetch_module():
    spec = importlib.util.spec_from_file_location(
        "fetch_intraday_host", os.path.join(ROOT, "scripts", "fetch_intraday.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_fence(text: str) -> str:
    """Remove the ```json fence the page-fetch proxy wraps JSON bodies in (nothing else)."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--interval", required=True, choices=("15m", "1h", "1d"))
    parser.add_argument("--responses", required=True,
                        help="directory holding <period1>_<period2>.json response files")
    parser.add_argument("--index", default="data/intraday_index.json")
    parser.add_argument("--out-dir", default="data/intraday")
    args = parser.parse_args()

    host = load_fetch_module()
    yahoo = None
    for sym, tick in host.stock_symbols():
        if sym == args.symbol:
            yahoo = tick
    if yahoo is None:
        raise SystemExit(f"{args.symbol} is not in the volatile-stock pool")

    spec = host.INTERVAL_SPEC[args.interval]
    window_start = host.epoch_of(spec["period1"])
    window_end = host.epoch_of(spec["period2"])

    files = sorted(
        f for f in os.listdir(os.path.join(ROOT, args.responses)) if f.endswith(".json"))
    if not files:
        raise SystemExit(f"no response files under {args.responses}")

    merged: dict[int, list] = {}
    chunk_records = []
    facts: dict = {}
    dropped_null = 0
    for name in files:
        m = re.match(r"^(\d+)_(\d+)\.json$", name)
        if not m:
            raise SystemExit(f"unexpected response filename {name!r} (want <p1>_<p2>.json)")
        chunk_start, chunk_end = int(m.group(1)), int(m.group(2))
        if not (window_start <= chunk_start < chunk_end <= window_end):
            raise SystemExit(
                f"{name}: sub-window outside the frozen {args.interval} window "
                f"[{window_start}, {window_end}]")
        with open(os.path.join(ROOT, args.responses, name), encoding="utf-8") as fh:
            raw_text = strip_fence(fh.read())
        payload = raw_text.encode("utf-8")
        endpoint = (f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo}"
                    f"?period1={chunk_start}&period2={chunk_end}&interval={args.interval}")
        bars, info = host.parse_chunk(payload, args.symbol, yahoo, args.interval,
                                      chunk_start, chunk_end)
        facts = info["facts"] or facts
        dropped_null += info["dropped_null"]
        for bar in bars:
            merged[bar[0]] = bar
        chunk_records.append({
            "period1": chunk_start,
            "period2": chunk_end,
            "period1_utc": host.iso_of(chunk_start),
            "period2_utc": host.iso_of(chunk_end),
            "endpoint": endpoint,
            "transport": TRANSPORT,
            "raw_response_bytes": len(payload),
            "raw_response_sha256": hashlib.sha256(payload).hexdigest(),
            "bars_returned": len(bars),
            "bars_dropped_null": info["dropped_null"],
            "bars_dropped_out_of_window": info["dropped_out_of_window"],
        })
        print(f"  chunk {chunk_start}..{chunk_end}: {len(bars)} bars", flush=True)

    bars = [merged[ts] for ts in sorted(merged)]
    if not bars:
        raise SystemExit("no usable bars in any response file")
    if bars[0][0] < window_start or bars[-1][0] > window_end:
        raise SystemExit("merged bars escape the frozen window")

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    document = {
        "_meta": {
            "kind": "intraday_vendor_capture",
            "description": (
                "Canonicalised Yahoo Finance chart capture: bars are validated and stored as "
                "[epoch_seconds, open, high, low, close, volume] with prices rounded to "
                f"{host.ROUNDING_DECIMALS} decimals. Per-chunk raw-response SHA-256 and byte "
                "lengths are recorded in data/intraday_index.json; rounding is the only "
                "transformation applied. The transport was the agent platform's page-fetch "
                "proxy (arena-fetch-page), so the recorded chunk digests cover the exact "
                "response text received through that proxy."
            ),
            "script": "scripts/fetch_intraday.py",
            "script_version": host.SCRIPT_VERSION,
            "interval": args.interval,
            "rounding_decimals": host.ROUNDING_DECIMALS,
            "vendor_retention_note": host.VENDOR_RETENTION_NOTE,
        },
        "symbol": args.symbol,
        "yahoo_ticker": yahoo,
        "kind": "equity",
        "interval": args.interval,
        "captured_at_utc": fetched_at,
        **facts,
        "dropped_null_bars": dropped_null,
        "chunks": chunk_records,
        "bar_count": len(bars),
        "bars": bars,
    }
    chunk_digests = "".join(c["raw_response_sha256"] for c in chunk_records)
    document["raw_response_sha256"] = hashlib.sha256(chunk_digests.encode("ascii")).hexdigest()
    document["raw_response_note"] = (
        "SHA-256 over the ordered concatenation of every chunk's raw-response SHA-256; "
        "multi-chunk series have no single raw vendor response. Chunk bodies were received "
        "through the agent page-fetch proxy (arena-fetch-page)."
    )
    stored_text = json.dumps(document, separators=(",", ":"))
    filename = host.stored_filename(args.symbol, args.interval)
    os.makedirs(os.path.join(ROOT, args.out_dir), exist_ok=True)
    with open(os.path.join(ROOT, args.out_dir, filename), "w", encoding="utf-8") as fh:
        fh.write(stored_text)

    record = {
        "symbol": args.symbol,
        "yahoo_ticker": yahoo,
        "kind": "equity",
        "interval": args.interval,
        "endpoint": chunk_records[0]["endpoint"],
        "endpoint_note": "first chunk; every chunk's exact endpoint is under 'chunks'",
        "file": f"{args.out_dir}/{filename}".replace("\\", "/"),
        "bar_count": len(bars),
        "dropped_null_bars": dropped_null,
        "first_epoch": bars[0][0],
        "last_epoch": bars[-1][0],
        "first_utc": host.iso_of(bars[0][0]),
        "last_utc": host.iso_of(bars[-1][0]),
        "first_close": bars[0][4],
        "last_close": bars[-1][4],
        "chunks": len(chunk_records),
        "chunk_provenance": chunk_records,
        "raw_response_bytes_total": sum(c["raw_response_bytes"] for c in chunk_records),
        "raw_response_sha256": document["raw_response_sha256"],
        "stored_bytes": len(stored_text.encode("utf-8")),
        "stored_sha256": hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
        "rounding_decimals": host.ROUNDING_DECIMALS,
        "max_abs_rounding_delta": 0.5 * 10 ** -host.ROUNDING_DECIMALS,
        "vendor_data_granularity": facts.get("vendor_data_granularity"),
        "vendor_reported_exchange": facts.get("vendor_reported_exchange"),
        "vendor_reported_instrument_type": facts.get("vendor_reported_instrument_type"),
        "vendor_currency": facts.get("vendor_currency"),
        "vendor_exchange_timezone": facts.get("vendor_exchange_timezone"),
        "transport": TRANSPORT,
        "transport_note": (
            "Captured through the agent platform's page-fetch proxy because the research "
            "sandbox has no direct egress and the CI lane repeatedly failed this series; the "
            "bars passed the identical parse_chunk validation the CI lane applies."
        ),
        "status": "captured",
        "captured_at_utc": fetched_at,
    }

    index_path = os.path.join(ROOT, args.index)
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)
    kept = [c for c in index["captures"]
            if not (c["symbol"] == args.symbol and c["interval"] == args.interval)]
    kept.append(record)
    index["captures"] = sorted(kept, key=lambda r: (r.get("kind", ""), r["symbol"], r["interval"]))

    captured = [r for r in index["captures"] if r.get("status") == "captured"]
    by_interval: dict[str, int] = {}
    for r in captured:
        by_interval[r["interval"]] = by_interval.get(r["interval"], 0) + 1
    meta = index["_meta"]
    meta.update({
        "symbol_count": len(index["captures"]),
        "captured_count": len(captured),
        "failed_count": sum(1 for r in index["captures"] if r.get("status") == "failed"),
        "not_attempted_count": sum(
            1 for r in index["captures"] if r.get("status") == "not_attempted"),
        "captured_by_interval": by_interval,
        "futures_symbols": sorted({r["symbol"] for r in captured if r.get("kind") == "future"}),
        "agent_proxy_note": (
            f"{args.symbol}[{args.interval}] was adopted on {fetched_at} via "
            "scripts/adopt_agent_fetch.py from page-fetch-proxy responses (transport "
            "arena-fetch-page); every other record is untouched."
        ),
        "merged_at_utc": fetched_at,
    })
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
        fh.write("\n")
    print(f"adopted {args.symbol}[{args.interval}]: {len(bars)} bars "
          f"({record['first_utc']} -> {record['last_utc']}), "
          f"index now captured={meta['captured_count']}/{meta['symbol_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
