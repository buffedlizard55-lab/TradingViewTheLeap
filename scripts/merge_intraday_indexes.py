#!/usr/bin/env python3
"""Merge per-symbol partial intraday indexes into data/intraday_index.json.

The matrix capture workflow (.github/workflows/capture-intraday-matrix.yml) runs one job
per symbol, each writing its own partial index (``<dir>/<SYMBOL>/intraday_index.json``)
plus the canonical capture files it stored. This script folds those partials into the
committed index without ever discarding an existing captured series:

* a ``captured`` record from a partial replaces whatever the committed index held for
  that (symbol, interval);
* a ``failed`` / ``not_attempted`` record from a partial is kept only when the committed
  index has no ``captured`` record for that key (a retry must not downgrade a capture);
* every capture file referenced by a kept record is re-hashed and must match its
  ``stored_sha256`` - a record whose file is missing or corrupt is dropped with a
  printed reason rather than committed;
* ``_meta`` tallies are recomputed from the merged records; transport counters are
  summed across the partials; ``fetched_at_utc`` is the latest partial stamp.

``--salvage-orphans`` additionally reconstructs an index record from any canonical
capture file that already sits under ``data/intraday/`` but is not yet marked
``captured``. Reconstruction reads the file (bars, chunks, vendor facts, stored SHA-256);
it never invents a bar. This is how a complete capture that missed the merge (the
MARA 1h file of 2026-09-19) is adopted without a re-fetch.

No network access, no bar is modified, and nothing is invented: the output is exactly
the union of what the capture jobs stored, audited for integrity.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED_STATES = ("failed", "not_attempted")
ROUNDING_DECIMALS = 5


def load(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def file_ok(record: dict) -> tuple[bool, str]:
    rel = record.get("file")
    if not rel:
        return False, "record has no file"
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return False, f"{rel} missing"
    with open(path, "rb") as fh:
        payload = fh.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != record.get("stored_sha256"):
        return False, f"{rel} SHA-256 {digest[:12]}... != index {str(record.get('stored_sha256'))[:12]}..."
    if record.get("stored_bytes") not in (None, len(payload)):
        return False, f"{rel} length {len(payload)} != stored_bytes {record.get('stored_bytes')}"
    return True, "ok"


def iso_of(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def record_from_capture_file(rel: str) -> tuple[dict | None, str]:
    """Rebuild an index record from a canonical capture file. Never invents bars.

    The file is the source of truth: bars, per-chunk provenance, vendor facts and the
    stored SHA-256 are read from disk. A file that is not a capture document, has no
    bars, or fails the OHLC invariants is refused.
    """
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None, f"{rel} missing"
    with open(path, "rb") as fh:
        payload = fh.read()
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"{rel} is not JSON: {exc}"
    if not isinstance(document, dict) or document.get("_meta", {}).get("kind") != "intraday_vendor_capture":
        return None, f"{rel} is not an intraday_vendor_capture document"
    bars = document.get("bars") or []
    if not bars:
        return None, f"{rel} has no bars"
    chunks = document.get("chunks") or []
    if not chunks:
        return None, f"{rel} has no chunk provenance"
    symbol = document.get("symbol")
    interval = document.get("interval")
    if not symbol or not interval:
        return None, f"{rel} missing symbol/interval"
    # OHLC invariants — same checks the fetcher applied before storage.
    for i, bar in enumerate(bars):
        if not isinstance(bar, list) or len(bar) < 6:
            return None, f"{rel} bar {i} is not [ts, o, h, l, c, v]"
        ts, o, h, l, c, v = bar[:6]
        if None in (o, h, l, c):
            return None, f"{rel} bar {i} has a null OHLC field"
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            return None, f"{rel} bar {i} violates OHLC invariants"
        if v is not None and v < 0:
            return None, f"{rel} bar {i} has negative volume"
    if document.get("bar_count") not in (None, len(bars)):
        return None, f"{rel} bar_count {document.get('bar_count')} != {len(bars)} bars"
    digest = hashlib.sha256(payload).hexdigest()
    first, last = bars[0], bars[-1]
    record = {
        "symbol": symbol,
        "yahoo_ticker": document.get("yahoo_ticker") or symbol,
        "kind": document.get("kind") or "equity",
        "interval": interval,
        "endpoint": chunks[0].get("endpoint"),
        "endpoint_note": "first chunk; every chunk's exact endpoint is under 'chunks'",
        "file": rel.replace("\\", "/"),
        "bar_count": len(bars),
        "dropped_null_bars": document.get("dropped_null_bars", 0),
        "first_epoch": first[0],
        "last_epoch": last[0],
        "first_utc": iso_of(first[0]),
        "last_utc": iso_of(last[0]),
        "first_close": first[4],
        "last_close": last[4],
        "chunks": len(chunks),
        "chunk_provenance": chunks,
        "raw_response_bytes_total": sum(int(c.get("raw_response_bytes") or 0) for c in chunks),
        "raw_response_sha256": document.get("raw_response_sha256"),
        "stored_bytes": len(payload),
        "stored_sha256": digest,
        "rounding_decimals": document.get("_meta", {}).get("rounding_decimals", ROUNDING_DECIMALS),
        "max_abs_rounding_delta": 0.5 * 10 ** -ROUNDING_DECIMALS,
        "vendor_data_granularity": document.get("vendor_data_granularity") or interval,
        "vendor_reported_exchange": document.get("vendor_reported_exchange"),
        "vendor_reported_instrument_type": document.get("vendor_reported_instrument_type"),
        "vendor_currency": document.get("vendor_currency"),
        "vendor_exchange_timezone": document.get("vendor_exchange_timezone"),
        "status": "captured",
        "captured_at_utc": document.get("captured_at_utc"),
        "salvaged_from_orphan_file": True,
    }
    return record, "ok"


def salvage_orphans(merged: dict[tuple[str, str], dict], capture_dir: str) -> list[str]:
    """Promote on-disk capture files that the index has not yet marked captured."""
    notes: list[str] = []
    abs_dir = os.path.join(ROOT, capture_dir)
    if not os.path.isdir(abs_dir):
        return [f"salvage: {capture_dir} is not a directory"]
    for name in sorted(os.listdir(abs_dir)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        rel = f"{capture_dir.rstrip('/')}/{name}"
        record, why = record_from_capture_file(rel)
        if record is None:
            notes.append(f"salvage skipped {name}: {why}")
            continue
        key = (record["symbol"], record["interval"])
        current = merged.get(key)
        if current is not None and current.get("status") == "captured":
            continue
        merged[key] = record
        prior = current.get("status") if current else "absent"
        notes.append(
            f"{key[0]}[{key[1]}]: salvaged orphan capture file "
            f"({record['bar_count']} bars, prior status {prior})"
        )
    return notes


def rebuild_document(merged: dict[tuple[str, str], dict], base: dict | None,
                     partials: list[dict]) -> dict:
    records = sorted(merged.values(), key=lambda r: (r.get("kind", ""), r["symbol"], r["interval"]))
    captured = [r for r in records if r.get("status") == "captured"]
    by_interval: dict[str, int] = {}
    for r in captured:
        by_interval[r["interval"]] = by_interval.get(r["interval"], 0) + 1

    template = (base or {}).get("_meta") or {}
    stamps = []
    direct_429 = int(template.get("direct_429_count") or 0) if not partials else 0
    rate_limited = bool(template.get("direct_rate_limited")) if not partials else False
    elapsed = float(template.get("elapsed_seconds") or 0.0) if not partials else 0.0
    run_urls: list[str] = list(template.get("workflow_run_urls") or (
        [template["workflow_run_url"]] if template.get("workflow_run_url") else []))
    for part in sorted(partials, key=lambda p: (p.get("_meta") or {}).get("fetched_at_utc") or ""):
        meta = part.get("_meta") or {}
        if meta.get("fetched_at_utc"):
            stamps.append(meta["fetched_at_utc"])
        direct_429 += int(meta.get("direct_429_count") or 0)
        rate_limited = rate_limited or bool(meta.get("direct_rate_limited"))
        elapsed += float(meta.get("elapsed_seconds") or 0.0)
        if meta.get("workflow_run_url") and meta["workflow_run_url"] not in run_urls:
            run_urls.append(meta["workflow_run_url"])
    meta_out = dict(template)
    meta_out.setdefault("kind", "intraday_capture_index")
    meta_out.setdefault("script", "scripts/fetch_intraday.py")
    meta_out.setdefault("vendor_source_id", "YAHOO-INTRADAY-CHART")
    meta_out.update({
        "fetched_at_utc": max(stamps) if stamps else meta_out.get("fetched_at_utc"),
        "capture_environment": meta_out.get("capture_environment", "github-actions"),
        "workflow_run_url": run_urls[-1] if run_urls else meta_out.get("workflow_run_url"),
        "workflow_run_urls": run_urls,
        "direct_rate_limited": rate_limited,
        "direct_429_count": direct_429,
        "symbol_count": len(records),
        "captured_count": len(captured),
        "failed_count": sum(1 for r in records if r.get("status") == "failed"),
        "not_attempted_count": sum(1 for r in records if r.get("status") == "not_attempted"),
        "elapsed_seconds": round(elapsed, 1),
        "captured_by_interval": by_interval,
        "futures_symbols": sorted({r["symbol"] for r in captured if r.get("kind") == "future"}),
        "merge_note": (
            "Merged from per-symbol partial indexes written by parallel capture jobs "
            "(scripts/merge_intraday_indexes.py). Tallies are recomputed from the merged "
            "records; when partials are present, direct_429_count and elapsed_seconds are "
            "summed across the jobs. Orphan capture files already on disk are salvaged "
            "into captured records (re-hashed, never invented)."
        ),
        "merged_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "merged_partial_count": len(partials),
    })
    return {"_meta": meta_out, "captures": records}


def merge(base: dict | None, partials: list[dict],
          salvage_dir: str | None = None) -> tuple[dict, list[str]]:
    notes: list[str] = []
    merged: dict[tuple[str, str], dict] = {}
    if base:
        for rec in base.get("captures", []):
            merged[(rec["symbol"], rec["interval"])] = rec
    for part in partials:
        for rec in part.get("captures", []):
            key = (rec["symbol"], rec["interval"])
            current = merged.get(key)
            if rec.get("status") == "captured":
                merged[key] = rec
            elif current is None or current.get("status") != "captured":
                merged[key] = rec
            else:
                notes.append(f"{key[0]}[{key[1]}]: kept existing capture over a {rec.get('status')} retry")

    if salvage_dir:
        notes.extend(salvage_orphans(merged, salvage_dir))

    # Integrity: every captured record must be backed by a file that hashes to its digest.
    for key, rec in list(merged.items()):
        if rec.get("status") != "captured":
            continue
        ok, why = file_ok(rec)
        if not ok:
            notes.append(f"{key[0]}[{key[1]}]: DROPPED captured record - {why}")
            del merged[key]
            continue
        # The vendor granularity is stored in the capture document; records written by a
        # fetch build that omitted it from the index are back-filled from the file, never guessed.
        if rec.get("vendor_data_granularity") is None:
            with open(os.path.join(ROOT, rec["file"]), encoding="utf-8") as fh:
                rec["vendor_data_granularity"] = json.load(fh).get("vendor_data_granularity")

    return rebuild_document(merged, base, partials), notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="data/intraday_index.json")
    parser.add_argument("--partials-dir", default=None,
                        help="directory holding <SYMBOL>/intraday_index.json partials")
    parser.add_argument("--salvage-orphans", action="store_true",
                        help="adopt canonical capture files on disk that the index has not "
                             "yet marked captured (re-hash only; never invent bars)")
    parser.add_argument("--capture-dir", default="data/intraday",
                        help="directory of canonical capture files for --salvage-orphans")
    args = parser.parse_args()

    if not args.partials_dir and not args.salvage_orphans:
        print("::error::need --partials-dir and/or --salvage-orphans")
        return 2

    base = load(os.path.join(ROOT, args.index))
    partials: list[dict] = []
    if args.partials_dir:
        partial_paths = sorted(glob.glob(os.path.join(args.partials_dir, "*", "intraday_index.json")))
        partials = [p for p in (load(path) for path in partial_paths) if p]
        print(f"merging {len(partials)} partial index(es) into {args.index} "
              f"(base has {len((base or {}).get('captures', []))} records)")
        if not partials and not args.salvage_orphans:
            print("::warning::no partial indexes found - index left untouched")
            return 0
    salvage_dir = args.capture_dir if args.salvage_orphans else None
    merged, notes = merge(base, partials, salvage_dir=salvage_dir)
    for note in notes:
        print(f"  {note}")
    if merged["_meta"]["captured_count"] <= 0:
        print("::warning::merged index holds 0 captured series - not written "
              "(a zero-capture index must never be committed)")
        return 0
    with open(os.path.join(ROOT, args.index), "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=1)
        fh.write("\n")
    m = merged["_meta"]
    print(f"wrote {args.index}: captured={m['captured_count']} failed={m['failed_count']} "
          f"not_attempted={m['not_attempted_count']} by_interval={m['captured_by_interval']}")
    print(f"::notice::merged intraday index captured={m['captured_count']} "
          f"by_interval={m['captured_by_interval']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
