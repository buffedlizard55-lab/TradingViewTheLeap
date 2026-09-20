#!/usr/bin/env python3
"""Adopt agent-fetched CME contract-spec pages into the official transcription lane.

Why this exists
---------------
The GitHub-hosted capture lane (``capture-cme-specs.yml`` -> ``scripts/fetch_cme_specs.py``)
answers HTTP 403 from cmegroup.com on every runner (irregularity IR-33), so the
machine-transcribed product hours were stuck at 3 of 20 pooled products. The research
sandbox has no direct network egress either, but the agent platform's page-fetch proxy CAN
reach the official contractSpecs pages. When the proxy delivers a page, this script adopts
the delivered text into the same audited pipeline the CI lane uses - the pattern already
established for vendor bars by ``scripts/adopt_agent_fetch.py``.

Honesty boundary (recorded on every record this script writes)
--------------------------------------------------------------
* the transport is labelled ``arena-fetch-page`` - the text travelled through the agent
  platform's page-fetch proxy, which renders the official HTML page to markdown; it is not
  the raw HTML response and is never presented as one (``body_format: "markdown"``);
* the stored body under ``data/cme_specs/<PRODUCT>.agentfetch.md`` is the exact text of the
  contract-spec table section as delivered by the proxy - no rewrite, no reordering - with
  its SHA-256 and byte length recorded; the manifest of fetched chunk indices is recorded
  on the index record (``agent_fetch_chunks`` / ``agent_fetch_total_chunks``) so the
  capture scope is explicit (a section of the page, not the whole page);
* the transcription is extracted from that stored body by
  ``fetch_cme_specs.extract_spec_fields_markdown`` - the SAME label matching the CI lane
  applies to HTML - and ``scripts/verify.py`` re-extracts from the stored body and fails on
  any divergence, so a hand-edited hour cannot survive a build;
* a page whose stored body yields no 'Trading Hours' row is NOT adopted; nothing is filled
  from another product or from memory.

What this script does NOT do
-----------------------------
It does not fetch anything itself (the agent fetched the pages out-of-band), it does not
touch records that are already ``captured``, and it does not invent a chunk map. After
adoption it recomputes the index tallies and rebuilds ``data/cme_product_hours.json``
through ``fetch_cme_specs.write_hours_artifact`` - the same pure function the CI lane uses -
so the offline audit stays meaningful.

Usage
-----
    python3 scripts/adopt_cme_specs_fetch.py --manifest scratch/cme_agent_fetch.json

The manifest records, per product, the page-fetch chunk indices that carried the spec
table and the page's total chunk count, plus the UTC access timestamp::

    {
      "accessed_utc": "2026-09-20T00:17:00Z",
      "products": {
        "CL":  {"chunks": [1], "total_chunks": 3},
        "PL":  {"chunks": [0, 1], "total_chunks": 2}
      }
    }
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRANSPORT = "arena-fetch-page"
CAPTURE_SCOPE = (
    "contract-spec table section as delivered by the agent page-fetch proxy (markdown: "
    "section heading + pipe-table rows); the full page was not stored"
)


def load_fetch_module():
    spec = importlib.util.spec_from_file_location(
        "fetch_cme_specs_host", os.path.join(ROOT, "scripts", "fetch_cme_specs.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", required=True,
                        help="JSON manifest of fetched chunk indices per product")
    args = parser.parse_args()

    module = load_fetch_module()
    with open(args.manifest, encoding="utf-8") as fh:
        manifest = json.load(fh)
    accessed_utc = manifest.get("accessed_utc")
    if not accessed_utc:
        raise SystemExit("manifest must carry accessed_utc")

    products = {p["product"]: p for p in module.pooled_products()}
    index_path = module.INDEX_PATH
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)
    records = {r["product"]: r for r in index.get("records", [])}

    adopted, skipped, refused = [], [], []
    for product in sorted(manifest.get("products", {})):
        info = manifest["products"][product]
        body_path = module.SPECS_DIR / f"{product}.agentfetch.md"
        rec = records.get(product)
        if rec is None:
            raise SystemExit(f"{product}: not a pooled product in data/cme_specs_index.json")
        if rec.get("status") == "captured":
            skipped.append(f"{product} (already captured via {rec.get('transport')})")
            continue
        if not body_path.exists():
            raise SystemExit(f"{product}: {body_path.name} is not stored under data/cme_specs/")
        if product not in products:
            raise SystemExit(f"{product}: no registered official spec URL")

        body = body_path.read_bytes()
        fields, missing = module.extract_spec_fields_markdown(body.decode("utf-8", "replace"))
        if not fields.get("trading_hours"):
            refused.append(f"{product} (no 'Trading Hours' row in the stored body; not adopted)")
            continue

        rec.update({
            "status": "captured",
            "accessed_utc": accessed_utc,
            "http_status": None,  # proxy delivery; no raw HTTP status is claimed
            "transport": TRANSPORT,
            "body_format": "markdown",
            "capture_scope": CAPTURE_SCOPE,
            "agent_fetch_chunks": list(info.get("chunks") or []),
            "agent_fetch_total_chunks": info.get("total_chunks"),
            "raw_bytes": len(body),
            "raw_sha256": hashlib.sha256(body).hexdigest(),
            "file": f"data/cme_specs/{product}.agentfetch.md",
            "fields": fields,
            "missing_fields": missing,
            # A previously retained hand-audited row must not masquerade as this run's
            # transcription once the machine transcription replaces it.
            "retained_row": None,
            "retained_reason": None,
        })
        adopted.append(product)

    index["_meta"]["captured_count"] = len([r for r in records.values() if r["status"] == "captured"])
    index["_meta"]["failed_count"] = len([r for r in records.values() if r["status"] == "failed"])
    index["_meta"]["kept_previous_count"] = len(
        [r for r in records.values() if r["status"] == "kept_previous"])
    index["_meta"]["product_count"] = len(records)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    if adopted:
        module.write_hours_artifact(index)
        print(f"adopted {len(adopted)} products: {', '.join(adopted)}")
        print("data/cme_product_hours.json rebuilt through fetch_cme_specs.write_hours_artifact")
    else:
        print("nothing adopted; data/cme_product_hours.json left untouched")
    for line in skipped:
        print(f"  skipped   {line}")
    for line in refused:
        print(f"  REFUSED   {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
