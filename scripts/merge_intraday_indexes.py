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


def merge(base: dict | None, partials: list[dict]) -> tuple[dict, list[str]]:
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

    records = sorted(merged.values(), key=lambda r: (r.get("kind", ""), r["symbol"], r["interval"]))
    captured = [r for r in records if r.get("status") == "captured"]
    by_interval: dict[str, int] = {}
    for r in captured:
        by_interval[r["interval"]] = by_interval.get(r["interval"], 0) + 1

    # _meta: take the structural fields from the newest partial (they all share the frozen
    # spec), recompute tallies, sum transport counters, and record the merge itself.
    template = None
    stamps = []
    direct_429 = 0
    rate_limited = False
    elapsed = 0.0
    run_urls: list[str] = []
    for part in sorted(partials, key=lambda p: (p.get("_meta") or {}).get("fetched_at_utc") or ""):
        meta = part.get("_meta") or {}
        template = meta or template
        if meta.get("fetched_at_utc"):
            stamps.append(meta["fetched_at_utc"])
        direct_429 += int(meta.get("direct_429_count") or 0)
        rate_limited = rate_limited or bool(meta.get("direct_rate_limited"))
        elapsed += float(meta.get("elapsed_seconds") or 0.0)
        if meta.get("workflow_run_url") and meta["workflow_run_url"] not in run_urls:
            run_urls.append(meta["workflow_run_url"])
    if template is None:
        template = (base or {}).get("_meta") or {}
    meta_out = dict(template)
    meta_out.setdefault("vendor_source_id", "YAHOO-INTRADAY-CHART")
    meta_out.update({
        "fetched_at_utc": max(stamps) if stamps else meta_out.get("fetched_at_utc"),
        "capture_environment": meta_out.get("capture_environment", "github-actions"),
        "workflow_run_url": run_urls[-1] if run_urls else meta_out.get("workflow_run_url"),
        "workflow_run_urls": run_urls or meta_out.get("workflow_run_urls") or
                             ([meta_out["workflow_run_url"]] if meta_out.get("workflow_run_url") else []),
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
            "records; direct_429_count and elapsed_seconds are summed across the jobs."
        ),
        "merged_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "merged_partial_count": len(partials),
    })
    return {"_meta": meta_out, "captures": records}, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default="data/intraday_index.json")
    parser.add_argument("--partials-dir", required=True,
                        help="directory holding <SYMBOL>/intraday_index.json partials")
    args = parser.parse_args()

    base = load(os.path.join(ROOT, args.index))
    partial_paths = sorted(glob.glob(os.path.join(args.partials_dir, "*", "intraday_index.json")))
    partials = [p for p in (load(path) for path in partial_paths) if p]
    print(f"merging {len(partials)} partial index(es) into {args.index} "
          f"(base has {len((base or {}).get('captures', []))} records)")
    if not partials:
        print("::warning::no partial indexes found - index left untouched")
        return 0
    merged, notes = merge(base, partials)
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
