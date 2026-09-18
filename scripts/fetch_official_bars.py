#!/usr/bin/env python3
"""Direct Alpaca Basic/IEX stock bars; no relays, paid feeds, or invented fallback.

Official contract: https://docs.alpaca.markets/us/reference/stockbars
Free plan/auth: https://docs.alpaca.markets/us/docs/about-market-data-api
IEX is one exchange, NOT consolidated US pricing or guaranteed executable fills.
Raw responses are kept locally (ignored by Git); redistribution requires license review.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from intel.intraday import _validate_bars

BASE = "https://data.alpaca.markets/v2/stocks/bars"
TIMEFRAMES = {"15m": "15Min", "1h": "1Hour", "1d": "1Day"}


def fetch(symbol, interval, start, end, headers, raw_dir, opener=urllib.request.urlopen):
    rows, provenance, seen = [], [], set()
    params = dict(symbols=symbol, timeframe=TIMEFRAMES[interval], start=start, end=end,
                  feed="iex", adjustment="split", sort="asc", limit=10000, asof="-")
    while True:
        url = BASE + "?" + urllib.parse.urlencode(params)
        with opener(urllib.request.Request(url, headers=headers), timeout=45) as response:
            raw = response.read()
        digest = hashlib.sha256(raw).hexdigest()
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / (digest + ".json")).write_bytes(raw)
        doc = json.loads(raw)
        if not isinstance(doc.get("bars"), dict) or set(doc["bars"]) - {symbol}:
            raise ValueError("Unexpected symbols or missing bars in provider response")
        for bar in doc["bars"].get(symbol, []):
            stamp = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Provider timestamp lacks timezone")
            rows.append([stamp.timestamp(), bar["o"], bar["h"], bar["l"], bar["c"], bar["v"]])
        provenance.append({"endpoint": url, "raw_response_sha256": digest,
                           "raw_response_bytes": len(raw), "transport": "direct_https"})
        token = doc.get("next_page_token")
        if not token:
            break
        if token in seen:
            raise ValueError("Repeated pagination token")
        seen.add(token)
        params["page_token"] = token
    _validate_bars(rows, symbol, interval)
    lower = datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp()
    upper = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp()
    if any(not lower <= b[0] <= upper for b in rows):
        raise ValueError("Provider returned bars outside requested dates")
    return rows, provenance


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2024-10-01T00:00:00Z")
    ap.add_argument("--end", default="2026-09-18T00:00:00Z", help="Inclusive; use completed sessions only")
    ap.add_argument("--intervals", nargs="+", choices=TIMEFRAMES, default=list(TIMEFRAMES))
    ap.add_argument("--out-dir", default="data/official_bars")
    args = ap.parse_args()
    start, end = [datetime.fromisoformat(v.replace("Z", "+00:00")) for v in (args.start, args.end)]
    if start.tzinfo is None or end.tzinfo is None or not start < end <= datetime.now(timezone.utc):
        ap.error("Require timezone-aware start < end <= now")
    output = ROOT / args.out_dir
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    meta = {"fetched_at_utc": stamp, "provider": "Alpaca", "feed": "iex",
            "adjustment": "split", "source_tier": "official_provider_api",
            "limitation": "IEX-only, split-adjusted research prices; not consolidated executable quotes",
            "documentation": "https://docs.alpaca.markets/us/reference/stockbars"}
    key, secret = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
    report = {"_meta": meta, "captures": []}
    if not key or not secret:
        meta.update(status="blocked", reason="Alpaca Basic API credentials unavailable; no network request or fabricated bars")
    else:
        headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        pool = json.loads((ROOT / "data/volatile_stocks.json").read_text())["records"]
        for item in pool:
            symbol = item["symbol"]
            for interval in args.intervals:
                record = {"symbol": symbol, "interval": interval, "kind": "equity"}
                try:
                    bars, chunks = fetch(symbol, interval, args.start, args.end, headers, output / "raw")
                    digest = hashlib.sha256("".join(c["raw_response_sha256"] for c in chunks).encode()).hexdigest()
                    document = {"symbol": symbol, "interval": interval, "bars": bars,
                                "raw_response_sha256": digest, "chunks": chunks, "_meta": meta.copy()}
                    payload = json.dumps(document, allow_nan=False).encode()
                    path = output / f"{symbol}_{interval}.json"
                    path.write_bytes(payload)
                    record.update(status="captured", file=str(path.relative_to(ROOT)),
                                  endpoint=chunks[0]["endpoint"], raw_response_sha256=digest,
                                  stored_sha256=hashlib.sha256(payload).hexdigest(), bar_count=len(bars),
                                  first_utc=datetime.fromtimestamp(bars[0][0], timezone.utc).isoformat(),
                                  last_utc=datetime.fromtimestamp(bars[-1][0], timezone.utc).isoformat(),
                                  vendor_exchange_timezone="America/New_York", rounding_decimals=None)
                except Exception as exc:
                    # Never serialize request headers or server bodies into a public artifact.
                    record.update(status="failed", error_type=type(exc).__name__)
                report["captures"].append(record)
        meta["status"] = "captured" if all(r["status"] == "captured" for r in report["captures"]) else "partial"
    # Never replace successful prior captures with a blocked credential check.
    path = output / ("availability.json" if meta["status"] == "blocked" else "index.json")
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"{meta['status']}: {path.relative_to(ROOT)}")
    return 0 if meta["status"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
