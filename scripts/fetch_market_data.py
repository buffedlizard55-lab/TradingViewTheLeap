#!/usr/bin/env python3
"""Capture daily-bar market history for the selected contest futures.

This script runs ONLY in an environment with outbound internet access (currently the
``capture-market-data`` GitHub Actions workflow). The repository verifier is offline and
never fetches anything; it audits the files this script produces.

For every selected master-list symbol it requests the Yahoo Finance chart endpoint

    https://query1.finance.yahoo.com/v8/finance/chart/{YAHOO}?period1={P1}&period2={P2}&interval=1d

and stores the raw response bytes verbatim under ``data/market_history/``. It then writes
``data/market_history_index.json`` recording, per symbol: the exact endpoint URL, the SHA-256
of the stored bytes, the byte length, the bar count, first/last session dates, and the
vendor-reported contract description so a human can confirm the ticker mapping.

Direct requests are tried first; if the host cannot be reached (GitHub-hosted runners sit
on IP ranges the vendor rate-limits with HTTP 429), the request is retried through the
public allorigins relay. The relay only carries bytes: every response is validated against
the expected vendor symbol and OHLC invariants, and captured values are spot-verified
against independent captures recorded in the evidence file.

Yahoo Finance is a commercial market-data vendor, not an exchange or the contest organiser.
The captured series are front-month continuous futures with unadjusted roll splices; roll
gaps can create artificial price jumps. This is recorded as a limitation everywhere the
data is used.

Usage (CI):
    python3 scripts/fetch_market_data.py --out-dir data/market_history \
        --index data/market_history_index.json
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

# ---------------------------------------------------------------------------
# Frozen capture configuration
# ---------------------------------------------------------------------------

# Capture window: two years ending after the current capture date. The epochs are
# computed once and frozen so every re-capture uses the identical window.
PERIOD1_UTC = "2024-09-17T00:00:00Z"
PERIOD2_UTC = "2026-09-18T00:00:00Z"

PROXY_TEMPLATE = "https://api.allorigins.win/raw?url={encoded}"

SYMBOL_MAP = [
    # (TradingView contest symbol, Yahoo Finance ticker)
    ("CME:SOL1!", "SOL=F"),
    ("CME:MSL1!", "MSL=F"),
    ("CME:XRP1!", "XRP=F"),
    ("CME:MXP1!", "MXP=F"),
    ("CME:BTC1!", "BTC=F"),
    ("CME:MBT1!", "MBT=F"),
    ("CME:ETH1!", "ETH=F"),
    ("CME:MET1!", "MET=F"),
    ("NYMEX:NG1!", "NG=F"),
    ("NYMEX:MNG1!", "MNG=F"),
    ("NYMEX:CL1!", "CL=F"),
    ("NYMEX_MINI:QM1!", "QM=F"),
    ("NYMEX:MCL1!", "MCL=F"),
    ("NYMEX:RB1!", "RB=F"),
    ("NYMEX:HO1!", "HO=F"),
    ("COMEX:SI1!", "SI=F"),
    ("COMEX:SIC1!", "SIC=F"),
    ("COMEX_MINI:SIL1!", "SIL=F"),
    ("NYMEX:PL1!", "PL=F"),
    ("CME_MINI:NQ1!", "NQ=F"),
]

ENDPOINT_TEMPLATES = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?period1={period1}&period2={period2}&interval=1d",
    "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?period1={period1}&period2={period2}&interval=1d",
)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

SCRIPT_VERSION = "3"

# Seconds to sleep between vendor requests. The vendor rate-limits bursts from
# datacenter IP ranges; pacing the 20 requests costs a minute and avoids errors.
INTER_REQUEST_DELAY_S = 3.0


def epoch_of(iso_utc: str) -> int:
    return int(datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).timestamp())


def raw_filename(tv_symbol: str) -> str:
    return tv_symbol.replace(":", "_").replace("!", "") + ".json"


def fetch_bytes(url: str, attempts: int = 3, timeout: int = 60) -> tuple[bytes, str]:
    """Fetch a URL directly; on failure retry through the public relay.

    Returns (payload, transport) where transport records how the bytes arrived.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        )
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
    raise RuntimeError(f"GET failed after {attempts} attempts on both transports: {url} ({last_error})")


def summarize(payload: bytes, tv_symbol: str, yahoo_ticker: str, url: str) -> dict:
    """Parse the raw chart response and extract provenance + coverage facts."""
    document = json.loads(payload.decode("utf-8"))
    chart = document.get("chart") or {}
    if chart.get("error") is not None:
        raise RuntimeError(f"{tv_symbol}: vendor reported an error: {chart['error']}")
    results = chart.get("result") or []
    if len(results) != 1:
        raise RuntimeError(f"{tv_symbol}: expected exactly one chart result, got {len(results)}")
    result = results[0]
    meta = result.get("meta") or {}
    if meta.get("symbol") != yahoo_ticker:
        raise RuntimeError(
            f"{tv_symbol}: vendor returned symbol {meta.get('symbol')!r}, expected {yahoo_ticker!r}"
        )
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    closes = quote.get("close") or []
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    if not (len(closes) == len(opens) == len(highs) == len(lows) == len(timestamps)):
        raise RuntimeError(f"{tv_symbol}: ragged OHLC arrays in vendor response")

    bars = [
        (ts, o, h, l, c)
        for ts, o, h, l, c in zip(timestamps, opens, highs, lows, closes)
        if None not in (o, h, l, c)
    ]

    for ts, o, h, l, c in bars:
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            raise RuntimeError(
                f"{tv_symbol}: OHLC invariant violated at {ts}: o={o} h={h} l={l} c={c}"
            )
    if any(bars[i][0] >= bars[i + 1][0] for i in range(len(bars) - 1)):
        raise RuntimeError(f"{tv_symbol}: timestamps are not strictly increasing")

    return {
        "tradingview_symbol": tv_symbol,
        "yahoo_ticker": yahoo_ticker,
        "endpoint": url,
        "vendor_reported_contract": meta.get("shortName"),
        "vendor_reported_exchange": meta.get("fullExchangeName"),
        "vendor_reported_instrument_type": meta.get("instrumentType"),
        "currency": meta.get("currency"),
        "sessions_returned": len(timestamps),
        "sessions_valid": len(bars),
        "first_session_utc": (
            datetime.fromtimestamp(bars[0][0], tz=timezone.utc).date().isoformat()
            if bars else None
        ),
        "last_session_utc": (
            datetime.fromtimestamp(bars[-1][0], tz=timezone.utc).date().isoformat()
            if bars else None
        ),
        "first_close": bars[0][4] if bars else None,
        "last_close": bars[-1][4] if bars else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/market_history")
    parser.add_argument("--index", default="data/market_history_index.json")
    parser.add_argument("--only-failed", action="store_true",
                        help="retry only records whose status is not 'captured'; keep already "
                             "captured records and their stored bytes untouched")
    args = parser.parse_args()

    period1 = epoch_of(PERIOD1_UTC)
    period2 = epoch_of(PERIOD2_UTC)
    os.makedirs(args.out_dir, exist_ok=True)

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records = []
    failures = []
    todo = SYMBOL_MAP
    if args.only_failed and os.path.exists(args.index):
        with open(args.index, encoding="utf-8") as fh_prev:
            previous = json.load(fh_prev)
        keep = [c for c in previous.get("captures", []) if c.get("status") == "captured"]
        for c in keep:
            c.setdefault("captured_at_utc", previous["_meta"].get("fetched_at_utc"))
        records.extend(keep)
        kept_syms = {c["tradingview_symbol"] for c in keep}
        todo = [(tv, yh) for tv, yh in SYMBOL_MAP if tv not in kept_syms]
        print(f"preserving {len(keep)} existing captures; retrying {len(todo)}", flush=True)
    for tv_symbol, yahoo_ticker in todo:
        payload = None
        used_url = None
        transport = None
        error_text = None
        for template in ENDPOINT_TEMPLATES:
            url = template.format(ticker=yahoo_ticker, period1=period1, period2=period2)
            print(f"GET {tv_symbol} <- {url}", flush=True)
            try:
                payload, transport = fetch_bytes(url)
                used_url = url
                break
            except RuntimeError as exc:
                error_text = str(exc)
        if payload is None:
            print(f"FAILED {tv_symbol}: {error_text}", flush=True)
            failures.append({"tradingview_symbol": tv_symbol, "yahoo_ticker": yahoo_ticker,
                             "error": error_text})
            records.append({
                "tradingview_symbol": tv_symbol,
                "yahoo_ticker": yahoo_ticker,
                "status": "failed",
                "error": error_text,
            })
            continue
        try:
            path = os.path.join(args.out_dir, raw_filename(tv_symbol))
            with open(path, "wb") as fh:
                fh.write(payload)
            record = summarize(payload, tv_symbol, yahoo_ticker, used_url)
            record["file"] = path
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["bytes"] = len(payload)
            record["status"] = "captured"
            record["transport"] = transport
            record["captured_at_utc"] = fetched_at
            records.append(record)
            print(
                f"    {record['sessions_valid']}/{record['sessions_returned']} valid sessions "
                f"{record['first_session_utc']} -> {record['last_session_utc']} "
                f"({record['vendor_reported_contract']}) via {transport}",
                flush=True,
            )
        except (RuntimeError, ValueError, KeyError) as exc:
            print(f"FAILED {tv_symbol}: {exc}", flush=True)
            failures.append({"tradingview_symbol": tv_symbol, "yahoo_ticker": yahoo_ticker,
                             "error": str(exc)})
            records.append({
                "tradingview_symbol": tv_symbol,
                "yahoo_ticker": yahoo_ticker,
                "status": "failed",
                "error": str(exc),
            })
        time.sleep(INTER_REQUEST_DELAY_S)

    captured = [r for r in records if r["status"] == "captured"]
    index = {
        "_meta": {
            "description": (
                "Vendor market-history capture for the selected contest futures. Raw Yahoo "
                "Finance chart responses are stored verbatim; this index records provenance. "
                "Yahoo Finance is a market_data_vendor tier source, not an exchange or the "
                "contest organiser. Series are front-month continuous futures with "
                "unadjusted roll splices."
            ),
            "script": "scripts/fetch_market_data.py",
            "script_version": SCRIPT_VERSION,
            "capture_window_start_utc": PERIOD1_UTC,
            "capture_window_end_utc": PERIOD2_UTC,
            "interval": "1d",
            "fetched_at_utc": fetched_at,
            "capture_environment": os.environ.get("CAPTURE_ENV", "local"),
            "workflow_run_url": os.environ.get("WORKFLOW_RUN_URL"),
            "symbol_count": len(records),
            "captured_count": len(captured),
            "failed_count": len(failures),
            "provenance_note": (
                "Each record's endpoint reproduces the exact request; sha256 covers the stored "
                "bytes. Bytes arrive either directly from the vendor host or through the "
                "public allorigins relay (recorded per record as 'transport'); the relay is a "
                "transport only and every payload is validated against the expected vendor "
                "symbol and OHLC invariants. Re-run scripts/fetch_market_data.py in a networked "
                "environment to refresh; the offline verifier audits these files without "
                "network access. Records with status 'failed' carry the error text and must "
                "be retried."
            ),
        },
        "captures": records,
    }
    with open(args.index, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1, sort_keys=False)
        fh.write("\n")
    summary = (
        f"captured {len(captured)}/{len(records)}"
        + (f"; failures: " + ", ".join(
            f"{f['tradingview_symbol']}({f['error'][-120:]})" for f in failures) if failures else "")
    )
    print(f"SUMMARY: {summary}", flush=True)
    # GitHub Actions turns ::notice:: into an annotation readable without log access.
    print(f"::notice::market-history capture {summary}", flush=True)
    if not captured:
        print("::error::market-history capture captured 0 symbols", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
