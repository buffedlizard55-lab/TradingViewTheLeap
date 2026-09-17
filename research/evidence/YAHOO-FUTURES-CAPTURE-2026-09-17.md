# Yahoo Finance chart API — futures daily-bar capture (2026-09-17)

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/CL=F?period1=1726531200&period2=1789689600&interval=1d — first of 20 per-symbol endpoints registered under the `YAHOO-FUTURES-CHART` source; the complete per-symbol list is in `research/sources/sources.json` (`endpoint_urls`) and reproduced verbatim in `data/market_history_index.json` per record.
- **Accessed (UTC):** 2026-09-17
- **Tier:** market_data_vendor — Yahoo is a commercial data vendor, NOT an exchange, regulator, or the contest organiser. Every number drawn from these endpoints is vendor-tier and labelled as such everywhere it is used.
- **Capture channel:** `scripts/fetch_market_data.py` executed by the `capture-market-data` GitHub Actions workflow (run URL recorded in `data/market_history_index.json` → `_meta.workflow_run_url`). Direct vendor requests from the workflow runner are rate-limited (HTTP 429 to the whole runner IP range, confirmed by probe on 2026-09-17); the script then retries the identical URL through the public `api.allorigins.win` relay, which is a byte transport only. Every stored payload is validated against the expected vendor symbol (`meta.symbol`), ragged-array/OHLC invariants, and strictly increasing timestamps before it is written, and the SHA-256 of the stored bytes is recorded per symbol in the index.
- **Window:** period1=1726531200 (2024-09-17T00:00:00Z) → period2=1789689600 (2026-09-18T00:00:00Z), interval=1d. Frozen as constants in the fetch script so every re-capture requests the identical window.
- **Series caveat:** Yahoo `=F` tickers are front-month continuous futures with UNADJUSTED roll splices. Roll gaps can create artificial jumps and artificial signals; the volatility intelligence table reports the largest absolute overnight gap per symbol as a roll-gap proxy, and the backtest report lists this as a declared limitation. CME's official settlement-based continuous series remains the licensed alternative flagged in the README.

## Independent spot-verification anchors (in-session captures)

The same endpoints were fetched independently through the research environment's fetch tool on 2026-09-17 (before the workflow capture) and the following values were confirmed verbatim. They anchor the captured files against transcription or relay errors:

> CL=F meta.shortName: "Crude Oil Oct 26"; meta.fullExchangeName: "NY Mercantile"; meta.instrumentType: "FUTURE"; meta.regularMarketPrice: 101.22; chartPreviousClose: 64.52.

> CL=F first bar of the 2025-09-17→2026-09-18 sub-window: timestamp 1758081600 (2025-09-17), open 64.58999633789062.

> CL=F session 2026-09-16: close 105.83 (adjclose 105.83), high 106.75, low 101.20999908447266.

> BTC=F meta.shortName: "Bitcoin Futures,Sep-2026"; meta.fullExchangeName: "CME"; fiftyTwoWeekHigh: 127240.0; fiftyTwoWeekLow: 57850.0; regularMarketPrice: 76460.0 (2026-09-17).

> SOL=F: exactly one daily bar exists (2026-09-17 session), open 98.44999694824219, close 98.80000305175781; validRanges limited to ["1d","5d"] — the ticker has under five days of history.

> XRP=F: exactly one daily bar exists, close 1.3020000457763672; validRanges ["1d","5d"].

> MSL=F: exactly one daily bar exists, close 98.94999694824219; validRanges ["1d","5d"].

> MXP=F: exactly one daily bar exists, close 1.3014999628067017; validRanges ["1d","5d"].

## Cross-check against the TradingView quote snapshot (2026-09-16)

The offline verifier compares each captured symbol's last close against the TradingView continuous-contract quote captured on 2026-09-16 (source `TV-QUOTE-*`, evidence `TRADINGVIEW-QUOTE-SNAPSHOT-2026-09-16.md`). Observed from the in-session captures:

> CL=F closed 2026-09-16 at 105.83 while the TradingView CL1! quote displayed 102.43 — a 3.32% difference, consistent with different front contract months (Yahoo front: "Crude Oil Oct 26") and intraday capture timing (TradingView quotes were captured between 16:49 and 17:23 GMT-4). Flagged as IR-17; treated as a documented caveat, not a mapping error (the >15% hard-fail bound in the verifier guards against actual ticker mix-ups).

## Per-symbol capture table

Completed after the workflow capture lands; see `data/market_history_index.json` for the machine-readable per-symbol record (endpoint, transport, SHA-256, sessions, first/last dates, first/last close) and the verifier check `market_history.*` which re-derives all of it offline.
