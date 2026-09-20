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
import http.client
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
# below stay inside those limits at the capture date (2026-09-19).
# ---------------------------------------------------------------------------

INTERVAL_SPEC = {
    # Re-frozen 2026-09-19 (was 2026-07-21..2026-09-19): the earlier window's start sat exactly
    # 60 days before the capture date, at the edge of the vendor's 15m retention, and the run
    # that was meant to land it failed for an unrelated reason (see SCRIPT_VERSION 4). A
    # 2026-07-28 start keeps the window inside retention for the next several days of retries.
    "15m": {"period1": "2026-07-28T00:00:00Z", "period2": "2026-09-19T00:00:00Z",
            "chunk_days": 14},
    "1h": {"period1": "2024-09-21T00:00:00Z", "period2": "2026-09-18T00:00:00Z",
           "chunk_days": 180},
    "1d": {"period1": "2016-01-01T00:00:00Z", "period2": "2026-09-19T00:00:00Z",
           "chunk_days": 730},
}

INTERVAL_ORDER = ("15m", "1h", "1d")

VENDOR_RETENTION_NOTE = (
    "Yahoo Finance chart API retention, as published by the vendor: 1m ~7 days, "
    "2m/5m/15m/30m/90m ~60 days, 1h ~730 days. The frozen windows above sit inside those "
    "limits at the capture date 2026-09-19; a later re-capture of the 15m window would fall "
    "outside vendor retention and must be re-frozen deliberately (the window was re-frozen "
    "once, on 2026-09-19, from a 2026-07-21 start to a 2026-07-28 start)."
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

# 1 -> first intraday capture path.
# 2 -> chunked requests, relay fallback with a sticky preference, per-chunk provenance,
#      explicit not_attempted records, --time-budget-seconds / --max-series.
# 3 -> stored bytes are EXACTLY the digested bytes (no trailing newline): the offline loader
#      re-hashes the file on disk, so a writer that appends a newline makes every capture fail
#      its own integrity check. Found by the eleventh-pass audit before any capture was adopted.
# 4 -> bars the vendor returns OUTSIDE the requested [period1, period2] window are dropped and
#      counted per chunk (bars_dropped_out_of_window) instead of failing the series. Observed on
#      run 35398650536 (2026-09-18): Yahoo appended the live bar at epoch 1789761600
#      (2026-09-18T20:00Z) to every historical 15m chunk, so 18/20 symbols failed with
#      "bar at 1789761600 outside the requested chunk" even when the transport succeeded.
#      Direct transport is also re-enabled after a cooldown instead of staying disabled for
#      the whole run, because the public relays answered HTTP 5xx for long stretches.
# 5 -> daily chunking tightened from 3650 to 730 days. The series window is UNCHANGED
#      (2016-01-01..2026-09-19); only the request size shrinks. The 10-year single chunk was
#      a several-hundred-kilobyte response that the public relays repeatedly timed out or
#      truncated (PLUG[1d] chunk 1451606400 failed every one of four retry passes on run
#      35479263003 after RIOT's identical window succeeded, i.e. the window is fetchable but
#      the oversized body is not reliably relayable). Two-year chunks are ~500 bars each.
#      Existing captures keep their own recorded chunk provenance; only new (re-)captures
#      use the tighter chunking, and the merged index's _meta.interval_spec is updated by
#      scripts/merge_intraday_indexes.py from the newest partial.
SCRIPT_VERSION = "5"
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

    def __init__(self, relay_attempts: int = 2, direct_attempts: int = 1,
                 timeout: int = 75, log=print):
        self.relay_attempts = relay_attempts
        self.direct_attempts = direct_attempts
        self.timeout = timeout
        self.direct_disabled = False
        self.direct_disabled_at: float | None = None
        self.direct_cooldown_seconds = 300.0
        self.direct_429s = 0
        self.attempts_log: list[str] = []
        self.preferred_relay: str | None = None
        self.log = log

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            try:
                return response.read()
            except (http.client.IncompleteRead, http.client.HTTPException) as exc:
                # Public relays routinely close a chunked body early ("IncompleteRead: 82203
                # bytes read" was observed on a GitHub runner). That is a transport failure and
                # must be retried or handed to the next relay, never allowed to escape: an
                # escaping read error used to end the whole run before the index was written.
                raise urllib.error.URLError(f"truncated response body: {exc}") from exc

    def fetch(self, url: str) -> tuple[bytes, str]:
        last_error: Exception | None = None
        if (self.direct_disabled and self.direct_disabled_at is not None
                and time.time() - self.direct_disabled_at >= self.direct_cooldown_seconds):
            # The vendor's per-IP limit recovers within minutes; give direct one more chance
            # rather than depending on the relays for the rest of a two-hour run.
            self.direct_disabled = False
            self.direct_429s = 0
            self.log("    direct re-enabled after cooldown")
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
                            self.direct_disabled_at = time.time()
                            self.log("    direct disabled after repeated HTTP 429 "
                                     f"(cooldown {int(self.direct_cooldown_seconds)}s)")
                    self.log(f"    direct attempt {attempt} failed: HTTP {exc.code}")
                except (urllib.error.URLError, TimeoutError, OSError,
                        http.client.HTTPException) as exc:
                    last_error = exc
                    self.log(f"    direct attempt {attempt} failed: {exc}")
                time.sleep(2 * attempt)
        ordered = sorted(RELAY_TEMPLATES,
                         key=lambda item: 0 if item[0] == self.preferred_relay else 1)
        for name, template in ordered:
            relay_url = template.format(encoded=urllib.parse.quote(url, safe=""))
            for attempt in range(1, self.relay_attempts + 1):
                try:
                    payload = self._get(relay_url)
                    self.attempts_log.append(f"{name}-ok")
                    if self.preferred_relay != name:
                        self.preferred_relay = name
                        self.log(f"    relay preference set to {name}")
                    return payload, f"{name}-relay"
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                        http.client.HTTPException) as exc:
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
    dropped_out_of_window = 0
    for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if ts < chunk_start or ts > chunk_end:
            # The vendor appends the most recent (possibly still-forming) bar to every chart
            # response whatever window was requested. It is not part of the requested
            # history, so it is never stored; the count is recorded in the chunk provenance.
            dropped_out_of_window += 1
            continue
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
    return bars, {"facts": facts, "dropped_null": dropped_null,
                  "dropped_out_of_window": dropped_out_of_window, "bars": len(bars)}


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
            "bars_dropped_out_of_window": info["dropped_out_of_window"],
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
    parser.add_argument("--previous-index", default=None,
                        help="index to read already-captured series from for --only-failed "
                             "(defaults to --index); lets a per-symbol matrix job skip series the "
                             "committed index already holds while writing its own partial index")
    parser.add_argument("--symbols", default=None,
                        help="comma-separated subset of pool symbols / futures TradingView symbols "
                             "to capture (matrix jobs pass exactly one)")
    parser.add_argument("--pacing-seconds", type=float, default=1.0)
    parser.add_argument("--relay-attempts", type=int, default=2)
    parser.add_argument("--time-budget-seconds", type=float, default=0.0,
                        help="stop after roughly this long and mark the rest not_attempted "
                             "(0 = no limit); a later --only-failed run resumes them")
    parser.add_argument("--max-series", type=int, default=0,
                        help="stop after this many series (0 = all); for smoke tests")
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

    if args.symbols:
        wanted = {s.strip() for s in args.symbols.split(",") if s.strip()}
        known = {j[0] for j in jobs}
        unknown = sorted(wanted - known)
        if unknown:
            raise SystemExit(f"--symbols contains symbols outside the capture plan: {unknown}")
        jobs = [j for j in jobs if j[0] in wanted]

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[dict] = []
    failures: list[dict] = []
    index_path = os.path.join(ROOT, args.index)
    previous_path = os.path.join(ROOT, args.previous_index) if args.previous_index else index_path
    if args.only_failed and os.path.exists(previous_path):
        with open(previous_path, encoding="utf-8") as fh:
            previous = json.load(fh)
        keep = [c for c in previous.get("captures", []) if c.get("status") == "captured"]
        if args.symbols:
            # A matrix job's partial index holds only its own symbols; the merge step
            # re-attaches everything else from the committed index.
            keep = [c for c in keep if c["symbol"] in wanted]
        records.extend(keep)
        done = {(c["symbol"], c["interval"]) for c in keep}
        jobs = [j for j in jobs if (j[0], j[3]) not in done]
        print(f"preserving {len(keep)} existing captures; retrying {len(jobs)}", flush=True)

    transport = Transport(relay_attempts=args.relay_attempts)
    started_at = time.time()
    attempted = 0
    deferred: list[tuple[str, str, str, str]] = []

    pending = list(jobs)
    for pass_number in (1, 2):
        failed_this_pass: list[tuple[str, str, str, str]] = []
        for key, yahoo, kind, interval in pending:
            if args.time_budget_seconds and (time.time() - started_at) > args.time_budget_seconds:
                if pass_number == 1:
                    deferred.append((key, yahoo, kind, interval))
                continue
            if args.max_series and attempted >= args.max_series:
                if pass_number == 1:
                    deferred.append((key, yahoo, kind, interval))
                continue
            attempted += 1
            print(f"GET {key} [{interval}] across {len(chunks_for(interval))} chunk(s)", flush=True)
            try:
                result = capture_series(transport, key, yahoo, interval, args.pacing_seconds)
            except Exception as exc:                      # noqa: BLE001 - see the note below
                # Deliberately broad. A rate-limited vendor or a relay that answers with an HTML
                # error page raises types that are not worth enumerating (JSONDecodeError,
                # UnicodeDecodeError, HTTPError, socket timeouts, ...), and an escaping exception
                # kills the whole run BEFORE the index is written: the workflow then commits
                # nothing and reports a green step, which is exactly how two capture runs were lost
                # on 2026-09-18. One series failing must never cost the other nineteen.
                detail = f"{type(exc).__name__}: {exc}"
                print(f"FAILED {key} [{interval}]: {detail}", flush=True)
                # Exactly one record per series however it ends: a series that fails on both
                # passes must not be reported twice, or the index tallies would double-count it.
                records[:] = [r for r in records
                              if (r.get("symbol"), r.get("interval")) != (key, interval)
                              or r.get("status") == "captured"]
                failures[:] = [f for f in failures
                               if (f["symbol"], f["interval"]) != (key, interval)]
                failures.append({"symbol": key, "interval": interval, "error": detail})
                records.append({
                    "symbol": key, "yahoo_ticker": yahoo, "kind": kind, "interval": interval,
                    "status": "failed", "error": detail,
                })
                failed_this_pass.append((key, yahoo, kind, interval))
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
            # A series that failed earlier in this run and succeeds on the retry pass replaces
            # its own failure record instead of appearing twice in the index.
            records[:] = [r for r in records
                          if (r.get("symbol"), r.get("interval")) != (key, interval)
                          or r.get("status") == "captured"]
            failures[:] = [f for f in failures
                           if (f["symbol"], f["interval"]) != (key, interval)]
            # The stored file must be EXACTLY the bytes that stored_sha256 digests: the offline
            # loader (intel/intraday.py) re-hashes the file on disk and refuses a mismatch, so no
            # trailing newline is appended here.
            # A multi-chunk series has no single raw vendor response, so the series-level digest is
            # defined as SHA-256 over the ordered concatenation of every chunk's raw-response digest.
            # It is written to BOTH the capture document and the index record, and the offline loader
            # requires the two to agree (or both to be absent, for captures written before this field).
            chunk_digests = "".join(c["raw_response_sha256"] for c in result["chunks"])
            document["raw_response_sha256"] = hashlib.sha256(chunk_digests.encode("ascii")).hexdigest()
            document["raw_response_note"] = (
                "SHA-256 over the ordered concatenation of every chunk's raw-response SHA-256; "
                "multi-chunk series have no single raw vendor response."
            )
            stored_text = json.dumps(document, separators=(",", ":"))
            filename = stored_filename(key, interval)
            with open(os.path.join(ROOT, args.out_dir, filename), "w", encoding="utf-8") as fh:
                fh.write(stored_text)
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
                "raw_response_sha256": document["raw_response_sha256"],
                "stored_bytes": len(stored_text.encode("utf-8")),
                "stored_sha256": hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
                "rounding_decimals": ROUNDING_DECIMALS,
                "max_abs_rounding_delta": 0.5 * 10 ** -ROUNDING_DECIMALS,
                "vendor_data_granularity": result["facts"].get("vendor_data_granularity"),
                "vendor_reported_exchange": result["facts"].get("vendor_reported_exchange"),
                "vendor_reported_instrument_type": result["facts"].get(
                    "vendor_reported_instrument_type"),
                "vendor_currency": result["facts"].get("vendor_currency"),
                "vendor_exchange_timezone": result["facts"].get("vendor_exchange_timezone"),
                "status": "captured",
                "captured_at_utc": fetched_at,
            })
            print(f"    {len(bars)} bars {iso_of(bars[0][0])} -> {iso_of(bars[-1][0])}", flush=True)

        if pass_number == 1 and failed_this_pass:
            # The vendor's per-IP limit and the public relays both recover within seconds to
            # minutes, so every failed series gets exactly one more chance before the run ends.
            # Observed on a GitHub runner: direct HTTP 429 everywhere plus HTTP 522 from both
            # relays, and truncated relay bodies, before chunks started succeeding again.
            print(f"RETRY pass: {len(failed_this_pass)} series failed on pass 1 "
                  f"({len(deferred)} deferred so far)", flush=True)
        pending = failed_this_pass

    for key, yahoo, kind, interval in deferred:
        records.append({
            "symbol": key, "yahoo_ticker": yahoo, "kind": kind, "interval": interval,
            "status": "not_attempted",
            "error": "deferred by --time-budget-seconds/--max-series; rerun with --only-failed",
        })
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
            "vendor_source_id": "YAHOO-INTRADAY-CHART",
            "fetched_at_utc": fetched_at,
            "capture_environment": os.environ.get("CAPTURE_ENV", "local"),
            "workflow_run_url": os.environ.get("WORKFLOW_RUN_URL"),
            "direct_rate_limited": transport.direct_disabled,
            "direct_429_count": transport.direct_429s,
            "symbol_count": len(records),
            "captured_count": len(captured),
            "failed_count": len(failures),
            "not_attempted_count": len(deferred),
            "elapsed_seconds": round(time.time() - started_at, 1),
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
    print(f"wrote {args.index} ({len(records)} records, {len(captured)} captured)", flush=True)

    summary = f"captured {len(captured)}/{len(records)} series; by interval {by_interval}"
    if failures:
        summary += "; failures: " + ", ".join(
            f"{f['symbol']}[{f['interval']}]({f['error'][-90:]})" for f in failures)
    print(f"SUMMARY: {summary}", flush=True)
    print(f"::notice::intraday capture {summary}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
