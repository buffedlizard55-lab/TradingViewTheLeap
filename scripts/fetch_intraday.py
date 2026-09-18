#!/usr/bin/env python3
"""Capture intraday (15-minute, hourly) and long daily bars for the volatile-stock pool.

This script runs ONLY in an environment with outbound internet access (the
``capture-intraday`` GitHub Actions workflow). The repository verifier is offline and never
fetches anything; it audits the files this script produces.

Two symbol sets are captured:

1. The 20-stock volatile equity pool listed in ``data/volatile_stocks.json`` (the pool the
   project selected from the Yahoo Finance chart API with recomputable trough/peak windows).
2. Optionally, the futures already captured in ``data/market_history_index.json`` (hourly),
   so intraday gap-fill and execution-latency arithmetic can be run on the same futures the
   daily shadow competition trades.

For every symbol and interval the script requests

    https://query1.finance.yahoo.com/v8/finance/chart/{YAHOO}
        ?period1={P1}&period2={P2}&interval={INTERVAL}

Direct requests are tried first; if the host is unreachable or rate-limits the runner IP
(HTTP 429), the request is retried through the public allorigins relay. The relay is a
transport only: every payload is validated against the expected vendor symbol, the vendor
instrument type, and OHLC invariants before anything is stored.

Stored form is a CANONICALISED capture, not the verbatim response: the vendor's response body
is parsed, every bar is validated, and the bars are written as a compact array

    "bars": [[epoch_seconds, open, high, low, close, volume], ...]

with prices rounded to ``ROUNDING_DECIMALS`` decimals. The index records the SHA-256 of the
raw response bytes, the raw byte length, and the SHA-256 of the stored canonical file, so a
reviewer can (a) audit the stored bars directly and (b) re-run the identical request to
confirm the raw payload is unchanged. Rounding is the only transformation applied; the bound
is 0.5 x 10**-ROUNDING_DECIMALS per price field and is recorded in the index.

Yahoo Finance is a commercial market-data vendor, not an exchange, not a regulator, and not
the contest organiser. Intraday bars from this endpoint are unadjusted for splits and
dividends inside the window and may contain pre/post-market prints; they are used here as
vendor history and nothing is claimed about exchange prints.

Usage (CI):
    python3 scripts/fetch_intraday.py --interval all --out-dir data/intraday \
        --index data/intraday_index.json --futures-hourly
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
# The epoch windows are computed once from these ISO constants and frozen so that
# every re-capture requests the identical window. Yahoo Finance serves 15-minute
# bars for roughly the last 60 days and hourly bars for roughly the last 730 days;
# both windows below stay inside those limits at the capture date (2026-09-18).
# ---------------------------------------------------------------------------

INTERVAL_WINDOWS = {
    "15m": {"period1": "2026-07-21T00:00:00Z", "period2": "2026-09-19T00:00:00Z"},
    "1h": {"period1": "2024-09-21T00:00:00Z", "period2": "2026-09-18T00:00:00Z"},
    "1d": {"period1": "2016-01-01T00:00:00Z", "period2": "2026-09-19T00:00:00Z"},
}

INTERVAL_ORDER = ("15m", "1h", "1d")

# Yahoo documents 15m for the last 60 days and 1h for the last 730 days. These mirrors
# are declared so a reviewer can see why the windows above stop where they stop.
VENDOR_RETENTION_NOTE = (
    "Yahoo Finance chart API retention: 1m ~7d, 2m/5m/15m/30m/90m ~60d, 1h ~730d "
    "(see research/evidence/INTRADAY-VENDOR-CAPTURE.md). Windows are frozen inside those "
    "limits at the capture date."
)

ENDPOINT_TEMPLATE = (
    "https://{host}/v8/finance/chart/{ticker}"
    "?period1={period1}&period2={period2}&interval={interval}"
)
ENDPOINT_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
PROXY_TEMPLATE = "https://api.allorigins.win/raw?url={encoded}"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

SCRIPT_VERSION = "1"
ROUNDING_DECIMALS = 5
INTER_REQUEST_DELAY_S = 2.5


def epoch_of(iso_utc: str) -> int:
    return int(datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).timestamp())


def iso_of(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def stock_symbols() -> list[tuple[str, str]]:
    """(symbol, yahoo_ticker) for the 20-stock volatile pool.

    Read from data/volatile_stocks.json so the capture set can never drift from
    the pool the rest of the project analyses.
    """
    with open(os.path.join(ROOT, "data", "volatile_stocks.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    out = []
    for record in doc["records"]:
        symbol = record["symbol"]
        out.append((symbol, record.get("yahoo_ticker") or symbol))
    return out


def futures_symbols() -> list[tuple[str, str]]:
    """(tradingview_symbol, yahoo_ticker) for futures previously captured daily."""
    path = os.path.join(ROOT, "data", "market_history_index.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = []
    for record in doc.get("captures", []):
        if record.get("status") != "captured":
            continue
        out.append((record["tradingview_symbol"], record["yahoo_ticker"]))
    return out


def stored_filename(key: str, interval: str) -> str:
    safe = key.replace(":", "_").replace("!", "").replace("/", "_")
    return f"{safe}_{interval}.json"


def fetch_bytes(url: str, attempts: int = 2, timeout: int = 60) -> tuple[bytes, str]:
    """Fetch a URL directly; on failure retry through the public relay.

    Returns (payload, transport) where transport records how the bytes arrived.
    """
    last_error: Exception | None = None
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), "direct"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            print(f"    direct attempt {attempt}/{attempts} failed: {exc}", flush=True)
            time.sleep(2 * attempt)
    relay_url = PROXY_TEMPLATE.format(encoded=urllib.parse.quote(url, safe=""))
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            relay_url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), "allorigins-relay"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            print(f"    relay attempt {attempt}/{attempts} failed: {exc}", flush=True)
            time.sleep(4 * attempt)
    raise RuntimeError(
        f"GET failed after {attempts} attempts on both transports: {url} ({last_error})"
    )


def parse_bars(payload: bytes, key: str, yahoo_ticker: str, interval: str) -> dict:
    """Validate the vendor payload and return canonical bars + provenance."""
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
    prior_ts = None
    for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if None in (o, h, l, c):
            dropped_null += 1
            continue
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            raise RuntimeError(
                f"{key}: OHLC invariant violated at {ts}: o={o} h={h} l={l} c={c}"
            )
        if v is not None and v < 0:
            raise RuntimeError(f"{key}: negative volume at {ts}: {v}")
        if prior_ts is not None and ts <= prior_ts:
            raise RuntimeError(f"{key}: timestamps not strictly increasing at {ts}")
        prior_ts = ts
        bars.append([
            int(ts),
            round(float(o), ROUNDING_DECIMALS),
            round(float(h), ROUNDING_DECIMALS),
            round(float(l), ROUNDING_DECIMALS),
            round(float(c), ROUNDING_DECIMALS),
            0 if v is None else int(v),
        ])
    if not bars:
        raise RuntimeError(f"{key}: vendor returned no usable bars for interval {interval}")

    return {
        "bars": bars,
        "dropped_null_bars": dropped_null,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/intraday")
    parser.add_argument("--index", default="data/intraday_index.json")
    parser.add_argument("--interval", default="all",
                        choices=("all",) + INTERVAL_ORDER,
                        help="which interval to capture")
    parser.add_argument("--futures-hourly", action="store_true",
                        help="also capture the hourly futures series already in the daily index")
    parser.add_argument("--only-failed", action="store_true",
                        help="retry only records whose status is not 'captured'")
    parser.add_argument("--pacing-seconds", type=float, default=INTER_REQUEST_DELAY_S)
    args = parser.parse_args()

    intervals = INTERVAL_ORDER if args.interval == "all" else (args.interval,)
    os.makedirs(os.path.join(ROOT, args.out_dir), exist_ok=True)

    jobs: list[tuple[str, str, str, str]] = []   # (key, yahoo, kind, interval)
    for symbol, yahoo in stock_symbols():
        for interval in intervals:
            jobs.append((symbol, yahoo, "equity", interval))
    if args.futures_hourly:
        for tv_symbol, yahoo in futures_symbols():
            if "1h" in intervals:
                jobs.append((tv_symbol, yahoo, "future", "1h"))

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[dict] = []
    failures: list[dict] = []
    if args.only_failed and os.path.exists(os.path.join(ROOT, args.index)):
        with open(os.path.join(ROOT, args.index), encoding="utf-8") as fh:
            previous = json.load(fh)
        keep = [c for c in previous.get("captures", []) if c.get("status") == "captured"]
        records.extend(keep)
        done = {(c["symbol"], c["interval"]) for c in keep}
        jobs = [j for j in jobs if (j[0], j[3]) not in done]
        print(f"preserving {len(keep)} existing captures; retrying {len(jobs)}", flush=True)

    for key, yahoo, kind, interval in jobs:
        window = INTERVAL_WINDOWS[interval]
        p1, p2 = epoch_of(window["period1"]), epoch_of(window["period2"])
        payload = None
        transport = None
        used_url = None
        error_text = None
        for host in ENDPOINT_HOSTS:
            url = ENDPOINT_TEMPLATE.format(host=host, ticker=urllib.parse.quote(yahoo, safe=""),
                                           period1=p1, period2=p2, interval=interval)
            print(f"GET {key} [{interval}] <- {url}", flush=True)
            try:
                payload, transport = fetch_bytes(url)
                used_url = url
                break
            except RuntimeError as exc:
                error_text = str(exc)
        if payload is None:
            print(f"FAILED {key} [{interval}]: {error_text}", flush=True)
            failures.append({"symbol": key, "interval": interval, "error": error_text})
            records.append({
                "symbol": key, "yahoo_ticker": yahoo, "kind": kind, "interval": interval,
                "status": "failed", "error": error_text,
            })
            time.sleep(args.pacing_seconds)
            continue
        try:
            parsed = parse_bars(payload, key, yahoo, interval)
        except (RuntimeError, ValueError, KeyError) as exc:
            print(f"FAILED {key} [{interval}]: {exc}", flush=True)
            failures.append({"symbol": key, "interval": interval, "error": str(exc)})
            records.append({
                "symbol": key, "yahoo_ticker": yahoo, "kind": kind, "interval": interval,
                "status": "failed", "error": str(exc),
            })
            time.sleep(args.pacing_seconds)
            continue

        bars = parsed.pop("bars")
        document = {
            "_meta": {
                "kind": "intraday_vendor_capture",
                "description": (
                    "Canonicalised Yahoo Finance chart capture: bars are validated and stored "
                    "as [epoch_seconds, open, high, low, close, volume] with prices rounded to "
                    f"{ROUNDING_DECIMALS} decimals. The raw response SHA-256 and byte length are "
                    "recorded in data/intraday_index.json; rounding is the only transformation."
                ),
                "script": "scripts/fetch_intraday.py",
                "script_version": SCRIPT_VERSION,
                "interval": interval,
                "rounding_decimals": ROUNDING_DECIMALS,
            },
            "symbol": key,
            "yahoo_ticker": yahoo,
            "kind": kind,
            "interval": interval,
            "endpoint": used_url,
            "requests_epoch": {"period1": p1, "period2": p2,
                               "period1_utc": window["period1"], "period2_utc": window["period2"]},
            "captured_at_utc": fetched_at,
            "transport": transport,
            "raw_response_bytes": len(payload),
            "raw_response_sha256": hashlib.sha256(payload).hexdigest(),
            "bar_count": len(bars),
            **parsed,
            "bars": bars,
        }
        stored_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
        filename = stored_filename(key, interval)
        path = os.path.join(ROOT, args.out_dir, filename)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(document, separators=(",", ":")))
            fh.write("\n")
        record = {
            "symbol": key,
            "yahoo_ticker": yahoo,
            "kind": kind,
            "interval": interval,
            "endpoint": used_url,
            "requests_epoch": {"period1": p1, "period2": p2},
            "file": f"{args.out_dir}/{filename}".replace("\\", "/"),
            "bar_count": len(bars),
            "dropped_null_bars": document["dropped_null_bars"],
            "first_epoch": bars[0][0],
            "last_epoch": bars[-1][0],
            "first_utc": iso_of(bars[0][0]),
            "last_utc": iso_of(bars[-1][0]),
            "first_close": bars[0][4],
            "last_close": bars[-1][4],
            "raw_response_bytes": len(payload),
            "raw_response_sha256": document["raw_response_sha256"],
            "stored_bytes": len(stored_bytes),
            "stored_sha256": hashlib.sha256(stored_bytes).hexdigest(),
            "rounding_decimals": ROUNDING_DECIMALS,
            "max_abs_rounding_delta": 0.5 * 10 ** -ROUNDING_DECIMALS,
            "vendor_reported_symbol": document["vendor_reported_symbol"],
            "vendor_reported_exchange": document["vendor_reported_exchange"],
            "vendor_reported_instrument_type": document["vendor_reported_instrument_type"],
            "vendor_currency": document["vendor_currency"],
            "vendor_exchange_timezone": document["vendor_exchange_timezone"],
            "status": "captured",
            "transport": transport,
            "captured_at_utc": fetched_at,
        }
        records.append(record)
        print(
            f"    {len(bars)} bars {record['first_utc']} -> {record['last_utc']} "
            f"({document['vendor_reported_exchange']}) via {transport}",
            flush=True,
        )
        time.sleep(args.pacing_seconds)

    captured = [r for r in records if r["status"] == "captured"]
    by_interval: dict[str, int] = {}
    for record in captured:
        by_interval[record["interval"]] = by_interval.get(record["interval"], 0) + 1
    index = {
        "_meta": {
            "kind": "intraday_capture_index",
            "description": (
                "Provenance index for the canonicalised intraday and long daily captures under "
                "data/intraday/. Each record reproduces the exact vendor request, records the "
                "raw response SHA-256 and byte length, and the SHA-256 of the stored canonical "
                "file. Yahoo Finance is a market-data vendor tier source, not an exchange, a "
                "regulator, or the contest organiser."
            ),
            "script": "scripts/fetch_intraday.py",
            "script_version": SCRIPT_VERSION,
            "interval_windows": INTERVAL_WINDOWS,
            "vendor_retention_note": VENDOR_RETENTION_NOTE,
            "rounding_decimals": ROUNDING_DECIMALS,
            "fetched_at_utc": fetched_at,
            "capture_environment": os.environ.get("CAPTURE_ENV", "local"),
            "workflow_run_url": os.environ.get("WORKFLOW_RUN_URL"),
            "symbol_count": len(records),
            "captured_count": len(captured),
            "failed_count": len(failures),
            "captured_by_interval": by_interval,
            "equity_symbols": [s for s, _ in stock_symbols()],
            "futures_symbols": sorted({r["symbol"] for r in captured if r["kind"] == "future"}),
            "provenance_note": (
                "Re-run scripts/fetch_intraday.py in a networked environment (the "
                "capture-intraday workflow) to refresh. The offline verifier audits these files "
                "without network access: it re-validates every OHLC invariant, re-checks the "
                "stored SHA-256, and re-derives the intraday study. Records with status 'failed' "
                "carry the error text and must be retried."
            ),
        },
        "captures": sorted(records, key=lambda r: (r["kind"], r["symbol"], r["interval"])),
    }
    with open(os.path.join(ROOT, args.index), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
        fh.write("\n")

    summary = f"captured {len(captured)}/{len(records)} capture requests; by interval {by_interval}"
    if failures:
        summary += "; failures: " + ", ".join(
            f"{f['symbol']}[{f['interval']}]({f['error'][-100:]})" for f in failures)
    print(f"SUMMARY: {summary}", flush=True)
    print(f"::notice::intraday capture {summary}", flush=True)
    if not captured:
        print("::error::intraday capture stored 0 records", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
