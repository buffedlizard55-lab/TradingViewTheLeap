#!/usr/bin/env python3
"""Fetch the official CME Group contract-specification page of every pooled future.

Why this exists
---------------
`data/cme_product_hours.json` used to hold the verbatim Globex hours of exactly three
products (SI, ETH, BTC); the other seventeen carried an explicit "omitted" note because a
previous offline pass refused to guess. This script closes that gap the only honest way
available: read each product's own official contract-spec page over HTTPS and transcribe
what it says, byte for byte, keeping the raw HTML so the transcription can be re-audited
offline.

Official pages (one per pooled product) are taken from `research/sources/sources.json`,
which already registers every URL with publisher "CME Group" and tier
``official_primary``. Nothing here builds a URL from a product code.

What is stored
--------------
* ``data/cme_specs/<PRODUCT>.html`` - the exact response body (no rewrite, no minify).
* ``data/cme_specs_index.json``   - per product: resolved URL, HTTP status, byte length,
  SHA-256 of the response body, transport, access timestamp, and the extracted fields
  with their verbatim text. Fields the page does not expose are ``null`` and are listed
  under ``missing_fields`` - they are never filled from another product or from memory.
* ``data/cme_product_hours.json`` - rebuilt from the index: verbatim trading hours,
  termination rule, listed-contract rule and contract unit for every product whose page
  answered, preserving the previous schema's keys.

What this script does NOT do
----------------------------
It never derives hours, expiries or roll dates by analogy, it never falls back to a
third-party mirror, and it never leaves a partially extracted product looking complete.
A product whose page returns a non-200 status or whose table is absent is recorded as
``failed`` with the reason, and the exit code is non-zero when any product failed so a
CI lane cannot silently commit a short table.

Offline auditability: `scripts/verify.py` re-runs `extract_spec_fields()` against the
stored HTML and requires field-for-field equality with the committed JSON, so a
hand-edited transcription fails the build.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "data" / "cme_specs"
INDEX_PATH = ROOT / "data" / "cme_specs_index.json"
HOURS_PATH = ROOT / "data" / "cme_product_hours.json"
SOURCES_PATH = ROOT / "research" / "sources" / "sources.json"
HISTORY_INDEX_PATH = ROOT / "data" / "market_history_index.json"

USER_AGENT = (
    "TradingViewTheLeap-research/1.0 (+https://github.com/buffedlizard55-lab/"
    "TradingViewTheLeap) python-urllib"
)

#: Contract-spec table row labels this project transcribes. The label is matched after
#: whitespace normalisation and a trailing-colon strip, so cosmetic page changes that do
#: not rename the row do not silently drop a field.
FIELD_LABELS = {
    "contract_unit": ("contract unit",),
    "price_quotation": ("price quotation",),
    "trading_hours": ("trading hours",),
    "minimum_price_fluctuation": ("minimum price fluctuation", "minimum tick", "tick size"),
    "product_code": ("product code",),
    "listed_contracts": ("listed contracts", "contract months", "contract month"),
    "settlement_method": ("settlement method",),
    "termination_of_trading": (
        "termination of trading",
        "last trading day",
        "termination",
    ),
}

#: Row labels that are product-specific hours but sit in a different table on some pages.
EXTRA_HOURS_LABELS = ("globex", "clearport", "tas")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pooled_products() -> list[dict]:
    """Every captured future in the pool, paired with its registered official spec URL."""
    history = load_json(HISTORY_INDEX_PATH)
    sources = {s["source_id"]: s for s in load_json(SOURCES_PATH)["sources"]}
    out: list[dict] = []
    for rec in history["captures"]:
        tv_symbol = rec["tradingview_symbol"]
        product = tv_symbol.split(":")[-1].split("1!")[0]
        source_id = f"CME-SPEC-{tv_symbol.split(':')[-1]}"
        src = sources.get(source_id)
        out.append(
            {
                "product": product,
                "tradingview_symbol": tv_symbol,
                "source_id": source_id,
                "url": src["url"] if src else None,
                "publisher": src.get("publisher") if src else None,
                "tier": src.get("tier") if src else None,
            }
        )
    out.sort(key=lambda r: r["product"])
    return out


_BREAK = "\x00"  # sentinel: only an explicit <br>/</p> may become a newline


def _clean_text(raw: str) -> str:
    """Normalise an HTML cell to a layout-independent string.

    Only an explicit ``<br>`` or ``</p>`` produces a newline. Every other whitespace
    character - including the source newlines and indentation a pretty-printed page
    carries inside a ``<td>`` - collapses to a single space, so the transcription is
    identical whether CME serves the table minified or wrapped. Entities are decoded and
    a non-breaking space becomes a normal one.
    """
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", _BREAK, raw)
    text = re.sub(r"(?i)</\s*p\s*>", _BREAK, text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_module.unescape(text)
    text = text.replace("\u00a0", " ").replace("\u2011", "-").replace("\u2013", "-")
    # Source wrapping must not survive: everything that is not a sentinel break is a space.
    text = re.sub(r"[^\S\x00]+", " ", text)
    lines = []
    for line in text.split(_BREAK):
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _rows(document: str) -> list[tuple[str, str]]:
    """Yield (label, value) for every two-cell table row in the document."""
    pairs: list[tuple[str, str]] = []
    for table in re.findall(r"(?is)<table[^>]*>(.*?)</table>", document):
        for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table):
            cells = re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", row)
            if len(cells) < 2:
                continue
            label = _clean_text(cells[0]).strip().rstrip(":").lower()
            value = _clean_text(cells[1]).strip()
            if label:
                pairs.append((label, value))
    return pairs


def extract_spec_fields(document: str) -> tuple[dict, list[str]]:
    """Extract the transcribed contract-spec fields from a spec page.

    Returns ``(fields, missing)``. A field is taken from the first table row whose label
    matches; a label that never appears yields ``None`` and lands in ``missing``. The
    extraction is deterministic and reads only the given document.
    """
    pairs = _rows(document)
    fields: dict[str, str | None] = {}
    missing: list[str] = []
    for key, labels in FIELD_LABELS.items():
        value = None
        for label, cell in pairs:
            if label in labels:
                value = cell or None
                break
        fields[key] = value
        if value is None:
            missing.append(key)

    # Some pages split TAS / ClearPort / Globex hours into their own rows.
    extra: dict[str, str] = {}
    for label, cell in pairs:
        if not cell:
            continue
        for token in EXTRA_HOURS_LABELS:
            if token in label and ("hour" in label or "trading" in label):
                extra[label] = cell
                break
    fields["additional_hours_rows"] = extra or None
    return fields, missing


#: Header sets tried in order. CME's edge has been observed to hold a connection open
#: rather than reject a bare client, so the second attempt presents a full browser profile.
#: Both are ordinary GETs of a public page; neither spoofs a login or a signed-in session.
HEADER_SETS = (
    {"User-Agent": USER_AGENT, "Accept": "text/html"},
    {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "image/avif,image/webp,*/*;q=0.8"),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    },
)


def fetch(url: str, timeout: int = 25) -> tuple[int, bytes]:
    """GET a public page, trying each header set once. Raises the last transport error."""
    last: Exception | None = None
    for headers in HEADER_SETS:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
            if body:
                return int(getattr(response, "status", 200) or 200), body
            last = ValueError("empty response body")
        except Exception as exc:                      # noqa: BLE001 - transport-level only
            last = exc
    raise RuntimeError(f"GET failed with every header set: {url} ({last})")


def build(args: argparse.Namespace) -> int:
    products = pooled_products()
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    previous = {}
    if INDEX_PATH.exists():
        previous = {r["product"]: r for r in load_json(INDEX_PATH).get("records", [])}

    for item in products:
        product = item["product"]
        record: dict = {
            "product": product,
            "tradingview_symbol": item["tradingview_symbol"],
            "source_id": item["source_id"],
            "publisher": item["publisher"] or "CME Group Inc.",
            "tier": item["tier"] or "official_primary",
            "url": item["url"],
            "status": "not_attempted",
            "reason": None,
        }
        if not item["url"]:
            record["status"] = "failed"
            record["reason"] = (
                f"no registered official spec URL for {item['source_id']} "
                "in research/sources/sources.json; not guessed"
            )
            records.append(record)
            continue

        if args.offline:
            # Re-extract from the stored HTML only (used by the offline verifier lane).
            stored = SPECS_DIR / f"{product}.html"
            if not stored.exists():
                record["status"] = "failed"
                record["reason"] = f"{stored.name} not stored yet; run without --offline"
                records.append(record)
                continue
            body = stored.read_bytes()
            prior = previous.get(product, {})
            record.update(
                {
                    "accessed_utc": prior.get("accessed_utc"),
                    "http_status": prior.get("http_status"),
                    "transport": "stored_html",
                    "raw_bytes": len(body),
                    "raw_sha256": hashlib.sha256(body).hexdigest(),
                    "file": f"data/cme_specs/{product}.html",
                }
            )
            fields, missing = extract_spec_fields(body.decode("utf-8", "replace"))
            record["fields"] = fields
            record["missing_fields"] = missing
            record["status"] = "captured"
            records.append(record)
            continue

        print(f"GET {product} <- {item['url']}", flush=True)
        try:
            status, body = fetch(item["url"], timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001 - fetch() normalises every transport error
            # fetch() folds URLError/HTTPError/OSError/ValueError into one RuntimeError, and a
            # product whose page will not answer must be *recorded*, never allowed to abort the
            # lane: a crash here would exit 1 with no index written and lose every product
            # already transcribed in this run.
            record["status"] = "failed"
            record["reason"] = f"{type(exc).__name__}: {exc}"
            # Keep the previous successful extraction so a transient network failure does
            # not erase an audited transcription.
            if previous.get(product, {}).get("status") == "captured":
                record["status"] = "kept_previous"
                record["reason"] = (
                    f"fetch failed ({type(exc).__name__}); previous stored extraction kept: {exc}"
                )
                record.update({k: previous[product].get(k) for k in
                               ("accessed_utc", "http_status", "transport", "raw_bytes",
                                "raw_sha256", "file", "fields", "missing_fields")})
            records.append(record)
            continue

        if status != 200:
            record["status"] = "failed"
            record["reason"] = f"HTTP {status}"
            record["http_status"] = status
            records.append(record)
            continue

        (SPECS_DIR / f"{product}.html").write_bytes(body)
        fields, missing = extract_spec_fields(body.decode("utf-8", "replace"))
        if fields.get("trading_hours") is None:
            record["status"] = "failed"
            record["reason"] = "page fetched but no 'Trading Hours' row found; not guessed"
            record["http_status"] = status
            record["raw_bytes"] = len(body)
            record["raw_sha256"] = hashlib.sha256(body).hexdigest()
            record["file"] = f"data/cme_specs/{product}.html"
            records.append(record)
            continue

        record.update(
            {
                "status": "captured",
                "accessed_utc": utc_now_iso(),
                "http_status": status,
                "transport": "direct_https",
                "raw_bytes": len(body),
                "raw_sha256": hashlib.sha256(body).hexdigest(),
                "file": f"data/cme_specs/{product}.html",
                "fields": fields,
                "missing_fields": missing,
            }
        )
        records.append(record)

    captured = [r for r in records if r["status"] == "captured"]

    # Provenance keys that describe a historical fact about this index rather than this run.
    # _meta is rebuilt from scratch every run, so without carrying these forward the record
    # that an earlier offline pass destroyed the per-record failure reasons would silently
    # disappear on the next capture, and the carried rows would start quoting the overwritten
    # "<file> not stored yet" text as if it were the finding.
    prior_meta: dict = {}
    if INDEX_PATH.exists():
        try:
            prior_meta = json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("_meta") or {}
        except (json.JSONDecodeError, OSError):
            prior_meta = {}

    index = {
        "_meta": {
            "kind": "cme_contract_spec_capture_index",
            "description": (
                "Provenance for the official CME Group contract-specification page of every "
                "future in this repository's pool. Each record stores the exact response body "
                "under data/cme_specs/ with its SHA-256 and byte length; the transcribed "
                "fields are re-extractable from that body offline. A missing field is null "
                "and listed in missing_fields - it is never inferred from another product."
            ),
            "script": "scripts/fetch_cme_specs.py",
            "script_version": "1",
            "generated_utc": utc_now_iso(),
            "capture_environment": os.environ.get("CAPTURE_ENV", "local"),
            "workflow_run_url": os.environ.get("WORKFLOW_RUN_URL"),
            "product_count": len(records),
            "captured_count": len(captured),
            "failed_count": len([r for r in records if r["status"] == "failed"]),
            "kept_previous_count": len([r for r in records if r["status"] == "kept_previous"]),
            "not_a_forecast": True,
            "engine_applies_hours": False,
        },
        "records": records,
    }
    for carried_key in ("provenance_note", "reasons_overwritten_by_offline_pass"):
        if carried_key in prior_meta:
            index["_meta"][carried_key] = prior_meta[carried_key]

    # Carry forward, onto the index record itself, any row a previous run already audited for
    # a product this run could not transcribe. Storing it here (rather than merging from the
    # artifact at write time) keeps write_hours_artifact() a pure function of the index, which
    # is what makes the offline audit meaningful.
    previous_hours_rows: dict[str, dict] = {}
    if HOURS_PATH.exists():
        try:
            previous_hours_rows = {
                r["product"]: r
                for r in json.loads(HOURS_PATH.read_text(encoding="utf-8")).get("products") or []
            }
        except (json.JSONDecodeError, OSError):
            previous_hours_rows = {}
    for rec in records:
        if rec["status"] == "captured":
            continue
        kept = previous_hours_rows.get(rec["product"])
        if not kept:
            continue
        row = dict(kept)
        row["retained_from_previous"] = True
        row["retained_reason"] = retained_reason(rec["product"], rec.get("reason"),
                                                 index["_meta"])
        rec["retained_row"] = row

    INDEX_PATH.write_text(json.dumps(index, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    if captured:
        write_hours_artifact(index)
    else:
        # A run that transcribed nothing must not overwrite a transcription that a previous
        # run (or a careful hand reading of the official page) already audited. The first run
        # of this lane did exactly that: 20/20 fetches failed and data/cme_product_hours.json
        # lost all three of its hand-transcribed products (commit 4f5604f).
        print("no product transcribed this run; data/cme_product_hours.json left untouched so "
              "the existing audited transcription is not destroyed")

    print(
        f"cme specs: {len(captured)}/{len(records)} products transcribed "
        f"(failed={index['_meta']['failed_count']}, "
        f"kept_previous={index['_meta']['kept_previous_count']})"
    )
    for rec in records:
        if rec["status"] != "captured":
            print(f"  {rec['status']:>14}  {rec['product']:<5} {rec['reason']}")
    if index["_meta"]["failed_count"] and not args.allow_failures:
        return 2
    return 0


# Keys that describe *how* a page was reached rather than *what it said*. The offline
# re-extraction audit re-derives the transcription from stored HTML, so these legitimately
# differ between the network pass and the offline pass - a product that failed live carries
# the transport error, and offline it carries "<file> not stored yet". Comparing them would
# fail the audit on every partial capture for a reason that has nothing to do with whether the
# stored bytes still say what was transcribed. That comparison lived inline in the workflow
# and never fired, because every run so far captured zero products and the step was skipped.
def retained_reason(product: str, reason: str | None, index_meta: dict) -> str:
    """Explain why a previously audited row is being carried, without inventing a cause.

    The reason is embedded only when it is one this run actually produced. The first offline
    pass of this lane overwrote every record's reason with "<PRODUCT>.html not stored yet;
    run without --offline" and the commit step saved that (clobber bug #2), so the index's
    ``_meta`` now records the loss. Embedding that string verbatim would launder a destroyed
    transport error into the hours artifact as if it were the finding, so when the index says
    the reasons were overwritten this says so instead.
    """
    if index_meta.get("reasons_overwritten_by_offline_pass"):
        return (
            f"this run could not transcribe {product}; the failure reason recorded in "
            "data/cme_specs_index.json was destroyed by an earlier offline re-extraction pass "
            "and is not recoverable (see that index's _meta.provenance_note); the previously "
            "audited row is kept unchanged"
        )
    cause = f" ({reason})" if reason else ""
    return (
        f"this run could not transcribe {product}{cause}; "
        "the previously audited row is kept unchanged"
    )


TRANSPORT_KEYS = frozenset({
    "accessed_utc",
    "http_status",
    "transport",
    "status",
    "reason",
    "retained_row",  # carries the reason text of the run that failed, so it differs too
})


def substantive_records(index: dict) -> dict:
    """Project an index down to the transcription itself, dropping transport metadata."""
    return {
        rec["product"]: {k: v for k, v in rec.items() if k not in TRANSPORT_KEYS}
        for rec in index["records"]
    }


def offline_divergences(network_index: dict, offline_index: dict) -> list[str]:
    """Return human-readable differences between a network pass and its offline replay.

    Empty means the stored HTML reproduces the committed transcription exactly.
    """
    a = substantive_records(network_index)
    b = substantive_records(offline_index)
    out: list[str] = []
    for product in sorted(set(a) | set(b)):
        if product not in a:
            out.append(f"{product}: only present in the offline pass")
            continue
        if product not in b:
            out.append(f"{product}: only present in the network pass")
            continue
        for key in sorted(set(a[product]) | set(b[product])):
            if a[product].get(key) != b[product].get(key):
                out.append(f"{product}.{key}: network={a[product].get(key)!r} "
                           f"offline={b[product].get(key)!r}")
    return out


def write_hours_artifact(index: dict) -> None:
    """Rebuild data/cme_product_hours.json from the capture index alone.

    This is deliberately a pure function of ``index``: a product this run transcribed becomes a
    new row, and a product it could *not* transcribe carries the row a previous run (or a hand
    reading of the official page) already audited, stored on the index record as
    ``retained_row`` and marked ``retained_from_previous``. Nothing is read from the artifact
    being rebuilt, so the verifier can regenerate the file and compare it byte for byte - a
    hand-edited hour therefore always diverges, instead of being fed back in as its own
    "previous" value and reproducing itself.
    """
    products = []
    omitted = []
    for rec in index["records"]:
        fields = rec.get("fields") or {}
        if rec["status"] != "captured" or not fields.get("trading_hours"):
            kept = rec.get("retained_row")
            if kept:
                products.append(dict(kept))
            else:
                omitted.append({"product": rec["product"], "reason": rec.get("reason")})
            continue
        extra = fields.get("additional_hours_rows") or {}
        products.append(
            {
                "product": rec["product"],
                "tradingview_symbol": rec["tradingview_symbol"],
                "source_id": rec["source_id"],
                "spec_url": rec["url"],
                "accessed_utc": rec.get("accessed_utc"),
                "raw_sha256": rec.get("raw_sha256"),
                "globex_hours": fields.get("trading_hours"),
                "contract_unit": fields.get("contract_unit"),
                "product_code": fields.get("product_code"),
                "listed_contracts": fields.get("listed_contracts"),
                "termination": fields.get("termination_of_trading"),
                "minimum_price_fluctuation": fields.get("minimum_price_fluctuation"),
                "settlement_method": fields.get("settlement_method"),
                "additional_hours_rows": extra,
                "missing_fields": rec.get("missing_fields") or [],
                "roll_dates": [],
            }
        )
    products.sort(key=lambda p: p["product"])
    artifact = {
        "_meta": {
            "kind": "cme_product_hours_transcription",
            "description": (
                "Verbatim CME contract-spec transcription for the pooled futures: trading "
                "hours, termination rule, listed-contract rule and contract unit exactly as "
                "published on each product's official contractSpecs page. Machine-generated "
                "by scripts/fetch_cme_specs.py from the raw HTML stored under "
                "data/cme_specs/; scripts/verify.py re-extracts from that HTML and fails on "
                "any divergence. The simulation engine does not drop sessions from these "
                "hours. Dated roll calendars are not transcribed here."
            ),
            "generated_utc": index["_meta"]["generated_utc"],
            "not_a_forecast": True,
            "engine_applies_hours": False,
            "roll_dates_transcribed": False,
            "source_ids": sorted({r["source_id"] for r in index["records"]
                                  if r["status"] == "captured"}),
            "capture_index": "data/cme_specs_index.json",
            "raw_html_dir": "data/cme_specs",
            "product_count": len(products),
            "machine_transcribed_count": len([r for r in products
                                              if not r.get("retained_from_previous")]),
            "retained_from_previous_count": len([r for r in products
                                                 if r.get("retained_from_previous")]),
            "omitted": omitted,
        },
        "products": products,
    }
    HOURS_PATH.write_text(json.dumps(artifact, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true",
                        help="re-extract from the stored HTML instead of fetching")
    parser.add_argument("--timeout", type=int, default=25,
                        help="per-request socket timeout in seconds")
    parser.add_argument("--allow-failures", action="store_true",
                        help="exit 0 even when some products could not be transcribed")
    args = parser.parse_args()
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
