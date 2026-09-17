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

Captured 2026-09-17 in automated passes (GitHub Actions runs on this branch; the latest run URL is in `data/market_history_index.json` `_meta.workflow_run_url`). Later passes used `--only-failed`, so each full-history record's bytes and digest are frozen at its first successful pass.
The 10 full-history symbols are the backtest panel; the 8 single-session symbols are newly listed on the vendor and are excluded (IR-16). CME:BTC1! and CME:MXP1! failed every relay pass attempted (IR-19).

| Symbol | Vendor ticker | Sessions | Window | Transport | SHA-256 (prefix) |
|---|---|---|---|---|---|
| CME:SOL1! | SOL=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `8041212f270a87b9…` |
| CME:MSL1! | MSL=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `6726cceec27dfedb…` |
| CME:ETH1! | ETH=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `910afd0e1268c58e…` |
| NYMEX:NG1! | NG=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `d276cad7ae1c1668…` |
| NYMEX:CL1! | CL=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `670efca637d6cee5…` |
| NYMEX_MINI:QM1! | QM=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `525a7ca43e72ff88…` |
| NYMEX:RB1! | RB=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `0666f37f2a652749…` |
| NYMEX:HO1! | HO=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `dfba9916d180b86d…` |
| COMEX:SI1! | SI=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `98eda3b2a5fc7d79…` |
| COMEX:SIC1! | SIC=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `e889ba3236f281e2…` |
| NYMEX:PL1! | PL=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `b518e95510ed2b40…` |
| CME:MBT1! | MBT=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `20bfef2924b62c3c…` |
| CME:MET1! | MET=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `3cd5b80bf539a225…` |
| NYMEX:MNG1! | MNG=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `e00443160cbd2a98…` |
| NYMEX:MCL1! | MCL=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `b5f08e878406d3ff…` |
| COMEX_MINI:SIL1! | SIL=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `4321c5a56fc15e79…` |
| CME_MINI:NQ1! | NQ=F | 503 | 2024-09-17 → 2026-09-17 | allorigins-relay | `9ba48cdfc0509eee…` |
| CME:XRP1! | XRP=F | 1 | 2026-09-17 → 2026-09-17 | allorigins-relay | `913e498daef0a361…` |
| CME:MXP1! | MXP=F | — | — | failed | GET failed after 3 attempts on both transports: https://quer |
| CME:BTC1! | BTC=F | — | — | failed | GET failed after 3 attempts on both transports: https://quer |

Full SHA-256 digests, byte counts, endpoints and per-record capture timestamps live in `data/market_history_index.json`; `scripts/verify.py` (`check_market_history`) re-derives every digest and re-validates OHLC invariants offline. Captures are `market_data_vendor` tier: raw vendor bytes, spot-verified against independent in-session fetches (above) and the TradingView quote snapshot (warn >2%, fail >15%).
