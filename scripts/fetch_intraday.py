#!/usr/bin/env python3
"""Capture intraday (15-minute, hourly) and long daily bars for the volatile-stock pool.

This script runs ONLY in an environment with outbound internet access (the
``capture-intraday`` GitHub Actions workflow; GitHub-hosted runner IP ranges are rate
limited by the vendor, so requests are chunked and relayed — see TRANSPORT below). The
repository verifier is offline and never fetches anything; it audits the files this
script produces.

Symbol sets:

1. The 20-stock volatile equity pool in ``data/volatile_stocks.json`` (15m, 1h, 1d).
2. Optionally the 20 futures already captured daily in ``data/market_history_index.json``
   (1h only), so intraday gap-fill and execution-latency arithmetic runs on the futures
   the daily shadow competition trades too.

Requests are CHUNKED. Each (symbol, interval) window is split into sub-windows of
``chunk_days`` and each sub-window is one request:

    https://{host}/v8/finance/chart/{YAHOO}
        ?period1={chunk_start}&period2={chunk_end}&interval={INTERVAL}

Chunking exists for three reasons: the vendor rate-limits large/rapid requests from
datacenter IPs (HTTP 429), public relays time out on multi-hundred-kilobyte responses, and
a failed chunk loses only that chunk instead of the whole series. Every chunk's provenance
(request URL, raw response SHA-256, byte length, transport) is recorded in the index.

TRANSPORT. Direct requests are tried first. A single direct probe decides whether the host
answers the runner IP at all: if the first two direct attempts return HTTP 429, direct is
disabled for the rest of the run (recorded in the index as ``direct_rate_limited``) and all
remaining chunks go through the public relays, tried in order:

    allorigins  https://api.allorigins.win/raw?url={encoded}
    codetabs    https://api.codetabs.com/v1/proxy?quest={encoded}

A relay is a transport only. Every payload is validated against the expected vendor symbol,
the vendor's reported granularity and every OHLC invariant before a single bar is stored, so
a relay that returned the wrong instrument or a mangled body fails loudly.

STORED FORM. Canonicalised capture, not the verbatim response: bars are written as
``[[epoch_seconds, open, high, low, close, volume], ...]`` with prices rounded to
``ROUNDING_DECIMALS`` decimals, and the index keeps the raw-response SHA-256 and byte length
per chunk. Rounding is the only transformation; the bound is recorded in the index.

Yahoo Finance is a commercial market-data vendor, not an exchange, a regulator, or the
contest organiser. Intraday bars from this endpoint are unadjusted for splits and dividends
and may include pre/post-market prints.

Usage (CI):
    python3 scripts/fetch_intraday.py --interval all --futures-hourly \
        --out-dir data/intraday --index data/intraday_index.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Frozen capture configuration.
#
# Epoch windows are computed once from these ISO constants and frozen so that every
# re-capture requests the identical window. Yahoo Finance serves 15-minute bars for
# roughly the last 60 days and hourly bars for roughly the last 730 days; both windows
# below stay inside those limits at the capture date (2026-09-18).
# ---------------------------------------------------------------------------

INTERVAL_SPEC = {
    "15m": {"period1": "2026-07-21T00:00:00Z", "period2": "2026-09-19T00:00:00Z",
            "chunk_days": 10},
    "1h": {"period1": "2024-09-21T00:00:00Z", "period2": "2026-09-18T00:00:00Z",
           "chunk_days": 120},
    "1d": {"period1": "2016-01-01T00:00:00Z", "period2": "2026-09-19T00:00:00Z",
           "chunk_days": 1825},
}

INTERVAL_ORDER = ("15m", "1h", "1d")

VENDOR_RETENTION_NOTE = (
    "Yahoo Finance chart API retention, as published by the vendor: 1m ~7 days, "
    "2m/5m/15m/30m/90m ~60 days, 1h ~730 days. The frozen windows above sit inside those "
    "limits at the capture date 2026-09-18; a later re-capture of the 15m window would fall "
    "outside vendor retention and must be re-frozen deliberately."
)

ENDPOINT_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
RELAY_TEMPLATES = (
    ("allorigins", "https://api.allorigins.win/raw?url={encoded}"),
    ("codetabs", "https://api.codetabs.com/v1/proxy?quest={encoded}"),
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

SCRIPT_VERSION = "2"
ROUNDING_DECIMALS = 5


def epoch_of(iso_utc: str) -> int:
    return int(datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).timestamp())


def iso_of(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def stock_symbols() -> list[tuple[str, str]]:
    """(symbol, yahoo_ticker) for the 20-stock volatile pool.

    Read from data/volatile_stocks.json so the capture set can never drift from the pool
    the rest of the project analyses.
    """
    with open(os.path.join(ROOT, "data", "volatile_stocks.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    return [(record["symbol"], record.get("yahoo_ticker") or record["symbol"])
            for record in doc["records"]]


def futures_symbols() -> list[tuple[str, str]]:
    """(tradingview_symbol, yahoo_ticker) for futures previously captured daily."""
    path = os.path.join(ROOT, "data", "market_history_index.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return [(record["tradingview_symbol"], record["yahoo_ticker"])
            for record in doc.get("captures", [])
            if record.get("status") == "captured"]


def stored_filename(key: str, interval: str) -> str:
    safe = key.replace(":", "_").replace("!", "").replace("/", "_")
    return f"{safe}_{interval}.json"


def chunks_for(interval: str) -> list[tuple[int, int]]:
    spec = INTERVAL_SPEC[interval]
    start = epoch_of(spec["period1"])
    end = epoch_of(spec["period2"])
    step = spec["chunk_days"] * 86_400
    out = []
    cursor = start
    while cursor < end:
        out.append((cursor, min(cursor + step, end)))
        cursor += step
    return out


class Transport:
    """Direct + relay HTTP transport with a per-run direct decision."""

    def __init__(self, relay_attempts: int = 3, direct_attempts: int = 1,
                 timeout: int = 60, log=print):
        self.relay_attempts = relay_attempts
        self.direct_attempts = direct_attempts
        self.timeout = timeout
        self.direct_disabled = False
        self.direct_429s = 0
        self.attempts_log: list[str] = []
        self.log = log

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read()

    def fetch(self, url: str) -> tuple[bytes, str]:
        last_error: Exception | None = None
        if not self.direct_disabled:
            for attempt in range(1, self.direct_attempts + 1):
                try:
                    payload = self._get(url)
                    self.attempts_log.append("direct-ok")
                    return payload, "direct"
                except urllib.error.HTTPError as exc:
                    last_error = exc
                    if exc.code == 429:
                        self.direct_429s += 1
                        # The runner IP range is rate limited: stop wasting the run's
                        # budget on direct calls and go straight to the relays.
                        if self.direct_429s >= 2:
                            self.direct_disabled = True
                            self.log("    direct disabled for this run after repeated HTTP 429")
                    self.log(f"    direct attempt {attempt} failed: HTTP {exc.code}")
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last_error = exc
                    self.log(f"    direct attempt {attempt} failed: {exc}")
                time.sleep(2 * attempt)
        for name, template in RELAY_TEMPLATES:
            relay_url = template.format(encoded=urllib.parse.quote(url, safe=""))
            for attempt in range(1, self.relay_attempts + 1):
                try:
                    payload = self._get(relay_url)
                    self.attempts_log.append(f"{name}-ok")
                    return payload, f"{name}-relay"
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                    last_error = exc
                    self.log(f"    {name} relay attempt {attempt}/{self.relay_attempts} "
                             f"failed: {exc}")
                    time.sleep(min(20, 3 * attempt))
        raise RuntimeError(f"GET failed on every transport: {url} ({last_error})")


def parse_chunk(payload: bytes, key: str, yahoo_ticker: str, interval: str,
                chunk_start: int, chunk_end: int) -> tuple[list[list], dict]:
    """Validate one chunk's payload and return its bars plus vendor facts."""
    document = json.loads(payload.decode("utf-8"))
    chart = document.get("chart") or {}
    if chart.get("error") is not None:
        raise RuntimeError(f"{key}: vendor reported an error: {chart['error']}")
    results = chart.get("result") or []
    if len(results) != 1:
        raise RuntimeError(f"{key}: expected exactly one chart result, got {len(results)}")
    result = results[0]
    meta = result.get("meta") or {}
    if meta.get("symbol") != yahoo_ticker:
        raise RuntimeError(
            f"{key}: vendor returned symbol {meta.get('symbol')!r}, expected {yahoo_ticker!r}"
        )
    if meta.get("dataGranularity") != interval:
        raise RuntimeError(
            f"{key}: vendor reported granularity {meta.get('dataGranularity')!r}, "
            f"expected {interval!r}"
        )
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    for name, series in (("open", opens), ("high", highs), ("low", lows),
                         ("close", closes), ("volume", volumes)):
        if len(series) != len(timestamps):
            raise RuntimeError(
                f"{key}: ragged arrays: {name}={len(series)} timestamps={len(timestamps)}"
            )
    bars: list[list] = []
    dropped_null = 0
    for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if ts < chunk_start or ts > chunk_end:
            raise RuntimeError(
                f"{key}: bar at {ts} outside the requested chunk "
                f"[{chunk_start}, {chunk_end}]"
            )
        if None in (o, h, l, c):
            dropped_null += 1
            continue
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            raise RuntimeError(
                f"{key}: OHLC invariant violated at {ts}: o={o} h={h} l={l} c={c}"
            )
        if v is not None and v < 0:
            raise RuntimeError(f"{key}: negative volume at {ts}: {v}")
        bars.append([
            int(ts),
            round(float(o), ROUNDING_DECIMALS),
            round(float(h), ROUNDING_DECIMALS),
            round(float(l), ROUNDING_DECIMALS),
            round(float(c), ROUNDING_DECIMALS),
            0 if v is None else int(v),
        ])
    facts = {
        "vendor_reported_symbol": meta.get("symbol"),
        "vendor_reported_name": meta.get("shortName") or meta.get("longName"),
        "vendor_reported_exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "vendor_reported_instrument_type": meta.get("instrumentType"),
        "vendor_currency": meta.get("currency"),
        "vendor_exchange_timezone": meta.get("exchangeTimezoneName"),
        "vendor_gmtoffset_seconds": meta.get("gmtoffset"),
        "vendor_data_granularity": meta.get("dataGranularity"),
        "vendor_first_trade_epoch": meta.get("firstTradeDate"),
    }
    return bars, {"facts": facts, "dropped_null": dropped_null, "bars": len(bars)}


def capture_series(transport: Transport, key: str, yahoo: str, interval: str,
                   pacing: float) -> dict:
    """Fetch every chunk of one (symbol, interval) and return the merged capture."""
    merged: dict[int, list] = {}
    chunk_records = []
    facts: dict = {}
    dropped_null = 0
    for chunk_start, chunk_end in chunks_for(interval):
        url = None
        error_text = None
        payload = None
        transport_name = None
        for host in ENDPOINT_HOSTS:
            url = (f"https://{host}/v8/finance/chart/{urllib.parse.quote(yahoo, safe='')}"
                   f"?period1={chunk_start}&period2={chunk_end}&interval={interval}")
            try:
                payload, transport_name = transport.fetch(url)
                break
            except RuntimeError as exc:
                error_text = str(exc)
        if payload is None:
            raise RuntimeError(f"{key}[{interval}] chunk {chunk_start}: {error_text}")
        bars, info = parse_chunk(payload, key, yahoo, interval, chunk_start, chunk_end)
        facts = info["facts"] or facts
        dropped_null += info["dropped_null"]
        for bar in bars:
            merged[bar[0]] = bar
        chunk_records.append({
            "period1": chunk_start,
            "period2": chunk_end,
            "period1_utc": iso_of(chunk_start),
            "period2_utc": iso_of(chunk_end),
            "endpoint": url,
            "transport": transport_name,
            "raw_response_bytes": len(payload),
            "raw_response_sha256": hashlib.sha256(payload).hexdigest(),
            "bars_returned": len(bars),
            "bars_dropped_null": info["dropped_null"],
        })
        print(f"    chunk {chunk_start}..{chunk_end}: {len(bars)} bars via {transport_name}",
              flush=True)
        time.sleep(pacing)
    bars = [merged[ts] for ts in sorted(merged)]
    if not bars:
        raise RuntimeError(f"{key}[{interval}]: no usable bars in any chunk")
    return {"bars": bars, "chunks": chunk_records, "facts": facts,
            "dropped_null": dropped_null}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/intraday")
    parser.add_argument("--index", default="data/intraday_index.json")
    parser.add_argument("--interval", default="all", choices=("all",) + INTERVAL_ORDER)
    parser.add_argument("--futures-hourly", action="store_true")
    parser.add_argument("--only-failed", action="store_true")
    parser.add_argument("--pacing-seconds", type=float, default=1.0)
    parser.add_argument("--relay-attempts", type=int, default=3)
    args = parser.parse_args()

    intervals = INTERVAL_ORDER if args.interval == "all" else (args.interval,)
    os.makedirs(os.path.join(ROOT, args.out_dir), exist_ok=True)

    jobs: list[tuple[str, str, str, str]] = []
    for symbol, yahoo in stock_symbols():
        for interval in intervals:
            jobs.append((symbol, yahoo, "equity", interval))
    if args.futures_hourly and "1h" in intervals:
        for tv_symbol, yahoo in futures_symbols():
            jobs.append((tv_symbol, yahoo, "future", "1h"))

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[dict] = []
    failures: list[dict] = []
    index_path = os.path.join(ROOT, args.index)
    if args.only_failed and os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as fh:
            previous = json.load(fh)
        keep = [c for c in previous.get("captures", []) if c.get("status") == "captured"]
        records.extend(keep)
        done = {(c["symbol"], c["interval"]) for c in keep}
        jobs = [j for j in jobs if (j[0], j[3]) not in done]
        print(f"preserving {len(keep)} existing captures; retrying {len(jobs)}", flush=True)

    transport = Transport(relay_attempts=args.relay_attempts)

    for key, yahoo, kind, interval in jobs:
        print(f"GET {key} [{interval}] across {len(chunks_for(interval))} chunk(s)", flush=True)
        try:
            result = capture_series(transport, key, yahoo, interval, args.pacing_seconds)
        except (RuntimeError, ValueError, KeyError) as exc:
            print(f"FAILED {key} [{interval}]: {exc}", flush=True)
            failures.append({"symbol": key, "interval": interval, "error": str(exc)})
            records.append({
                "symbol": key, "yahoo_ticker": yahoo, "kind": kind, "interval": interval,
                "status": "failed", "error": str(exc),
            })
            continue

        bars = result["bars"]
        document = {
            "_meta": {
                "kind": "intraday_vendor_capture",
                "description": (
                    "Canonicalised Yahoo Finance chart capture: bars are validated and stored as "
                    "[epoch_seconds, open, high, low, close, volume] with prices rounded to "
                    f"{ROUNDING_DECIMALS} decimals. Per-chunk raw-response SHA-256 and byte "
                    "lengths are recorded in data/intraday_index.json; rounding is the only "
                    "transformation applied."
                ),
                "script": "scripts/fetch_intraday.py",
                "script_version": SCRIPT_VERSION,
                "interval": interval,
                "rounding_decimals": ROUNDING_DECIMALS,
                "vendor_retention_note": VENDOR_RETENTION_NOTE,
            },
            "symbol": key,
            "yahoo_ticker": yahoo,
            "kind": kind,
            "interval": interval,
            "captured_at_utc": fetched_at,
            **result["facts"],
            "dropped_null_bars": result["dropped_null"],
            "chunks": result["chunks"],
            "bar_count": len(bars),
            "bars": bars,
        }
        stored_text = json.dumps(document, separators=(",", ":"))
        filename = stored_filename(key, interval)
        with open(os.path.join(ROOT, args.out_dir, filename), "w", encoding="utf-8") as fh:
            fh.write(stored_text)
            fh.write("\n")
        records.append({
            "symbol": key,
            "yahoo_ticker": yahoo,
            "kind": kind,
            "interval": interval,
            "endpoint": result["chunks"][0]["endpoint"],
            "endpoint_note": "first chunk; every chunk's exact endpoint is under 'chunks'",
            "file": f"{args.out_dir}/{filename}".replace("\\", "/"),
            "bar_count": len(bars),
            "dropped_null_bars": result["dropped_null"],
            "first_epoch": bars[0][0],
            "last_epoch": bars[-1][0],
            "first_utc": iso_of(bars[0][0]),
            "last_utc": iso_of(bars[-1][0]),
            "first_close": bars[0][4],
            "last_close": bars[-1][4],
            "chunks": len(result["chunks"]),
            "chunk_provenance": result["chunks"],
            "raw_response_bytes_total": sum(c["raw_response_bytes"] for c in result["chunks"]),
            "stored_bytes": len(stored_text.encode("utf-8")),
            "stored_sha256": hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
            "rounding_decimals": ROUNDING_DECIMALS,
            "max_abs_rounding_delta": 0.5 * 10 ** -ROUNDING_DECIMALS,
            "vendor_reported_exchange": result["facts"].get("vendor_reported_exchange"),
            "vendor_reported_instrument_type": result["facts"].get(
                "vendor_reported_instrument_type"),
            "vendor_currency": result["facts"].get("vendor_currency"),
            "vendor_exchange_timezone": result["facts"].get("vendor_exchange_timezone"),
            "status": "captured",
            "captured_at_utc": fetched_at,
        })
        print(f"    {len(bars)} bars {iso_of(bars[0][0])} -> {iso_of(bars[-1][0])}", flush=True)

    captured = [r for r in records if r["status"] == "captured"]
    by_interval: dict[str, int] = {}
    for record in captured:
        by_interval[record["interval"]] = by_interval.get(record["interval"], 0) + 1
    index = {
        "_meta": {
            "kind": "intraday_capture_index",
            "description": (
                "Provenance index for the canonicalised intraday and long daily captures under "
                "data/intraday/. Each record lists every chunk's exact vendor request, the raw "
                "response SHA-256 and byte length, the transport that delivered it, and the "
                "SHA-256 of the stored canonical file. Yahoo Finance is a market_data_vendor "
                "tier source, not an exchange, a regulator, or the contest organiser."
            ),
            "script": "scripts/fetch_intraday.py",
            "script_version": SCRIPT_VERSION,
            "interval_spec": INTERVAL_SPEC,
            "vendor_retention_note": VENDOR_RETENTION_NOTE,
            "rounding_decimals": ROUNDING_DECIMALS,
            "fetched_at_utc": fetched_at,
            "capture_environment": os.environ.get("CAPTURE_ENV", "local"),
            "workflow_run_url": os.environ.get("WORKFLOW_RUN_URL"),
            "direct_rate_limited": transport.direct_disabled,
            "direct_429_count": transport.direct_429s,
            "symbol_count": len(records),
            "captured_count": len(captured),
            "failed_count": len(failures),
            "captured_by_interval": by_interval,
            "equity_symbols": [s for s, _ in stock_symbols()],
            "futures_symbols": sorted({r["symbol"] for r in captured if r["kind"] == "future"}),
            "provenance_note": (
                "Re-run scripts/fetch_intraday.py --only-failed in a networked environment to "
                "top up. The offline verifier audits these files without network access: it "
                "re-validates every OHLC invariant, re-checks each stored SHA-256 against the "
                "index, and re-derives the intraday study. Records with status 'failed' carry "
                "the error text and must be retried."
            ),
        },
        "captures": sorted(records, key=lambda r: (r["kind"], r["symbol"], r["interval"])),
    }
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
        fh.write("\n")

    summary = f"captured {len(captured)}/{len(records)} series; by interval {by_interval}"
    if failures:
        summary += "; failures: " + ", ".join(
            f"{f['symbol']}[{f['interval']}]({f['error'][-90:]})" for f in failures)
    print(f"SUMMARY: {summary}", flush=True)
    print(f"::notice::intraday capture {summary}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
