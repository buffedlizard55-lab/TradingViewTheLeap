# Intraday capture evidence — Yahoo Finance v8 chart API (15-minute, hourly, long daily)

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1757635200&period2=1758240000&interval=15m — one of three registered endpoints under the `YAHOO-INTRADAY-CHART` source; the full endpoint list is in `research/sources/sources.json` (`endpoint_urls`) and every per-chunk endpoint actually requested is reproduced verbatim in `data/intraday_index.json`.
- **Accessed (UTC):** 2026-09-18
- **Tier:** market_data_vendor — Yahoo is a commercial data vendor, NOT an exchange, regulator, or the contest organiser. `official_source: false`; every number drawn from these endpoints is vendor-tier and labelled as such everywhere it is used.
- **Capture channel:** `scripts/fetch_intraday.py`, executed by the `capture-intraday` GitHub Actions workflow (run URL recorded in `data/intraday_index.json` → `_meta.workflow_run_url`).

## Why this vendor

The Leap's official pages publish rules, leaderboards and prize tiers, but **no** price history.
The repository therefore needs a price feed to test execution questions (intra-session gap fills,
execution latency) on bars, and the only feed that is reachable from this project's tooling at
intraday granularity and without a paid plan is the public Yahoo Finance v8 chart endpoint:

```
https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?period1=<epoch>&period2=<epoch>&interval=<15m|1h|1d>
```

Everything captured through it is stored under `data/intraday/` and indexed — with the raw
response digests of every request chunk — in `data/intraday_index.json`. The offline verifier
(`scripts/verify.py`) re-hashes each stored file and re-validates every OHLC invariant through
`intel/intraday.py`; nothing in this repository is trusted merely because the vendor returned it.

## Endpoint contract observed by this project

* `period1` / `period2` are honoured literally: a request whose window contains no trading hours
  returns fewer bars (or none), never a silently widened window.
* The response meta block reports `symbol`, `fullExchangeName`/`exchangeName`,
  `exchangeTimezoneName`, `gmtoffset`, `dataGranularity` and `regularMarketTime`. The capture
  script stores those vendor-reported fields verbatim in each capture file and refuses to store a
  payload whose `dataGranularity` does not match the requested interval.
* Bars arrive as parallel arrays (`timestamp[]`, `indicators.quote[0].open/high/low/close/volume`).
  Rows with a null open/high/low/close are dropped by the capture script and the drop count is
  recorded (`dropped_null_bars`) — never silently.
* Prices are rounded to 5 decimals on storage (`ROUNDING_DECIMALS = 5`); rounding is the only
  transformation applied to the vendor numbers, and every chunk's raw-response SHA-256 and byte
  length are recorded so a reviewer can re-fetch and compare.

### Point-in-time probe observations (2026-09-18, sandbox `fetch_page` tool)

These were read directly off the endpoint during this session, before the full capture was run
through GitHub Actions (the sandbox shell cannot reach `query1.finance.yahoo.com`; see
"Irregularities" below):

> AAPL, `interval=15m`, `range=5d`: 26 bars in the most recent session; meta reported
> `dataGranularity: "15m"`, `exchangeTimezoneName: "America/New_York"`, `gmtoffset: -14400`.

> NVDA, `interval=1h` over an explicit `period1`/`period2` window: 21 bars returned, meta
> reported `dataGranularity: "1h"`.

> MARA, `interval=15m` over an explicit `period1`/`period2` window: 52 bars returned, meta
> reported `dataGranularity: "15m"`.

The regular session (13:30–20:00 UTC) never crossed a UTC calendar date in any probe — which is
why `intel/intraday.py` can define a "session" as the UTC date of the bar timestamp for equities,
and why futures numbers in the same study must be labelled UTC-day-boundary numbers instead.

## Irregularities and limitations (recorded, not hidden)

1. **Vendor, not exchange.** These are vendor prints. Nothing here is an official price, and no
   claim is made that a participant could transact at these prices. Every page that shows a
   number derived from these bars carries the vendor label and this source id.
2. **Rate limiting.** GitHub-hosted runner IP ranges receive HTTP 429 from this endpoint. The
   capture script chunks each request window, disables direct calls after repeated 429s (recorded
   in the index as `direct_rate_limited` / `direct_429_count`), and falls back to public relays;
   when every path is exhausted the affected series is recorded with `status: "failed"` or
   `status: "not_attempted"` plus the error text, and a later `--only-failed` run tops it up.
   A partial capture is therefore visible in the index rather than being hidden.
3. **Retention windows.** Intraday history is limited by the vendor (roughly the last 60 days for
   15-minute bars, roughly two years for hourly bars). The capture scripts chunk their windows to
   those limits; series that begin no earlier than the vendor holds are not an error.
4. **No splits/dividends adjustment inside the intraday window.** A corporate action inside a
   capture window would appear as a large gap. `scripts/run_intraday_study.py` records this in its
   `assumptions` block and the study reports it alongside the gap statistics.
5. **Sandbox egress.** This repository's own sandbox can reach only `pypi.org`,
   `files.pythonhosted.org` and `api.github.com`; the market-data vendor is reachable only from
   the GitHub Actions runner (or the agent's page-fetch tool, which cannot stream large payloads
   into the repository). That is why the capture is a workflow (`.github/workflows/capture-intraday.yml`)
   whose committed output the offline verifier audits.
