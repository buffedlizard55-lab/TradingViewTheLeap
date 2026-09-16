# High-Volatility Stocks — Verified Trough→Peak Close Multiples (daily adjclose)

- **Publisher:** Yahoo Finance chart API (market data vendor — **NOT an official exchange or regulator**; see honesty note below)
- **Tier:** market_data_vendor
- **Accessed (UTC):** 2026-09-16
- **Endpoint pattern:** `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?period1={epoch}&period2={epoch}&interval=1d`
- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/GME?period1=1583020800&period2=1588291200&interval=1d — first of 17 fetched endpoints; every other endpoint is quoted per ticker below
- **Series used:** `indicators.adjclose[0].adjclose` (split- and dividend-adjusted daily closes).
  Timestamps are Unix epoch seconds at the US regular-session open (13:30 UTC in EDT periods).

## Verbatim archived endpoint values (captured 2026-09-16)

> GME trough window: adjclose min 0.699999988079071 @ ts 1585920600; peak window: adjclose max 86.87750244140625 @ ts 1611757800
> AMC trough window: adjclose min 20.799999237060547 @ ts 1586784600; peak window: adjclose max 625.5 @ ts 1622640600
> SMCI trough window: adjclose min 5.242000102996826 @ ts 1665581400; peak window: adjclose max 118.80699920654297 @ ts 1710336600
> MSTR trough window: adjclose min 9.220000267028809 @ ts 1584538200; peak window: adjclose max 455.8999938964844 @ ts 1752672600
> NVDA trough window: adjclose min 11.186728477478027 @ ts 1665754200; peak window: adjclose max 135.20559692382812 @ ts 1718717400
> TSLA trough window: adjclose min 24.08133316040039 @ ts 1584538200; peak window: adjclose max 409.9700012207031 @ ts 1636032600
> PLTR trough window: adjclose min 6.0 @ ts 1672151400; peak window: adjclose max 207.17999267578125 @ ts 1762180200
> COIN trough window: adjclose min 32.529998779296875 @ ts 1672237800; peak window: adjclose max 325.4100036621094 @ ts 1731940200

## Honesty note

Yahoo Finance is a **commercial market-data vendor**, not a primary listing venue. These records
are the strongest verifiable evidence available in this session for equity price history (the
sandbox cannot reach exchange or SEC price archives directly), and every number below is
recomputable from the archived endpoint values. They are deliberately kept in a separate module
(`data/volatile_stocks.json`) from the official-source claims about the futures contest.

## Method

1. A monthly locator scan (see `VOLATILE-STOCKS-YAHOO-MONTHLY.md`) identified candidate trough
   and peak regions per ticker.
2. Each region was then fetched at daily resolution. Within each daily window the exact minimum
   (trough) and maximum (peak) adjusted close were taken, with their timestamps.
3. Multiple = peak_adjclose ÷ trough_adjclose. All claims are **window-bounded**: they state the
   lowest/highest close inside the fetched window. Where a window was extended and re-checked
   (SMCI trough, PLTR peak, MSTR peak), the final window is the one listed.

## Records

### GME — GameStop Corp. (NYSE)

- Trough window: `period1=1583020800&period2=1588291200` (2020-03-01 → 2020-05-01), 43 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/GME?period1=1583020800&period2=1588291200&interval=1d
- **Trough: adjclose 0.699999988079071 @ ts 1585920600 = 2020-04-03.** Guards (next lowest): 0.7124999761581421 (2020-04-02), 0.7725 (2020-04-06). Window max close 1.51 (2020-04-29).
- Peak window: `period1=1609459200&period2=1612137600` (2021-01-01 → 2021-02-01), 19 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/GME?period1=1609459200&period2=1612137600&interval=1d
- **Peak: adjclose 86.87750244140625 @ ts 1611757800 = 2021-01-27.** Guards (next highest): 81.25 (2021-01-29), 48.40 (2021-01-28). Window intraday high 120.75 (2021-01-28).
- **Multiple: 86.87750244140625 ÷ 0.699999988079071 = 124.11x** (close-to-close, 299 calendar days).
- Adjustment note: adjclose carries GME's June-2024 4-for-1 split (raw 2021-01-27 close $347.51 ÷ 4 = $86.8775 — exact match).

### AMC — AMC Entertainment Holdings, Inc. (NYSE)

- Trough window: `period1=1583020800&period2=1588291200` (2020-03-01 → 2020-05-01), 43 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/AMC?period1=1583020800&period2=1588291200&interval=1d
- **Trough: adjclose 20.799999237060547 @ ts 1586784600 = 2020-04-13.** Guards: 20.8 is unique minimum; next 21.799999237060547 (2020-04-14), 22.399999237060547 (2020-03-30). Window max close 60.73 (2020-03-02).
- Peak window: `period1=1621036800&period2=1623715200` (2021-05-15 → 2021-06-15), 20 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/AMC?period1=1621036800&period2=1623715200&interval=1d
- **Peak: adjclose 625.5 @ ts 1622640600 = 2021-06-02.** Guards: 570.0 (2021-06-14), 550.5 (2021-05-28). Window intraday high 726.20 (2021-05-28).
- **Multiple: 625.5 ÷ 20.799999237060547 = 30.07x** (close-to-close, 415 calendar days).
- Adjustment note: series carries AMC's August-2025 1-for-10 reverse split; 10 pre-split shares
  held at the peak become 1 share worth 10× as much, so this is genuine per-holder value growth.

### SMCI — Super Micro Computer, Inc. (NasdaqGS)

- Trough window: `period1=1664582400&period2=1669852800` (2022-10-01 → 2022-12-01), 42 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/SMCI?period1=1664582400&period2=1669852800&interval=1d
- **Trough: adjclose 5.242000102996826 @ ts 1665581400 = 2022-10-12.** Guards: 5.4019999504089355 (2022-10-14), 5.514999866485596 (2022-10-13). Window max close 9.387 (2022-11-29).
- Peak window: `period1=1707955200&period2=1711929600` (2024-02-15 → 2024-04-01), 30 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/SMCI?period1=1707955200&period2=1711929600&interval=1d
- **Peak: adjclose 118.80699920654297 @ ts 1710336600 = 2024-03-13.** Guards: 116.30 (2024-03-12), 115.976 (2024-03-11). Window intraday high 122.90 (2024-03-12).
- **Multiple: 118.80699920654297 ÷ 5.242000102996826 = 22.66x** (close-to-close, 518 calendar days).
- Adjustment note: series carries SMCI's October-2024 10-for-1 split (raw peak close $1,188.07 ÷ 10 = $118.807 — exact match).

### MSTR — Strategy Inc (NasdaqGS)

- Trough window: `period1=1583020800&period2=1586908800` (2020-03-01 → 2020-04-15), 31 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/MSTR?period1=1583020800&period2=1586908800&interval=1d
- **Trough: adjclose 9.220000267028809 @ ts 1584538200 = 2020-03-18.** Guards: 10.074 (2020-03-20), 10.247 (2020-03-23). Window intraday low 9.0 (2020-03-19).
- Peak window: `period1=1749945600&period2=1753920000` (2025-06-15 → 2025-08-01), 31 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/MSTR?period1=1749945600&period2=1753920000&interval=1d
- **Peak: adjclose 455.8999938964844 @ ts 1752672600 = 2025-07-16.** Guards: 451.34 (2025-07-17), 451.02 (2025-07-15).
- Peak confirmation window: `period1=1752672600&period2=1764547200` (2025-07-16 → 2025-12-01).
  URL: https://query1.finance.yahoo.com/v8/finance/chart/MSTR?period1=1752672600&period2=1764547200&interval=1d
  Every daily close from 2025-07-17 through 2025-12-01 is below 455.9 (declining to ~175 by
  December; current regularMarketPrice at fetch time: 129.6), so 2025-07-16 stands as the peak.
- **Multiple: 455.8999938964844 ÷ 9.220000267028809 = 49.45x** (close-to-close, 1,946 calendar days).
- Adjustment note: series carries MSTR's August-2024 10-for-1 split.

### NVDA — NVIDIA Corporation (NasdaqGS)

- Trough window: `period1=1664582400&period2=1668470400` (2022-10-01 → 2022-11-15), 31 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/NVDA?period1=1664582400&period2=1668470400&interval=1d
- **Trough: adjclose 11.186728477478027 @ ts 1665754200 = 2022-10-14.** Guards: 11.458746910095215 (2022-10-12), 11.544440269470215 (2022-10-11).
- Peak window: `period1=1717200000&period2=1719792000` (2024-06-01 → 2024-07-01), 19 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/NVDA?period1=1717200000&period2=1719792000&interval=1d
- **Peak: adjclose 135.20559692382812 @ ts 1718717400 = 2024-06-18.** Guards: 131.516 (2024-06-14), 130.618 (2024-06-17). Window intraday high 140.76 (2024-06-20).
- **Multiple: 135.20559692382812 ÷ 11.186728477478027 = 12.09x** (close-to-close, 613 calendar days).
- Adjustment note: series carries NVDA's June-2024 10-for-1 split (raw peak close $1,352.06 ÷ 10 = $135.206 — exact match).

### TSLA — Tesla, Inc. (NasdaqGS)

- Trough window: `period1=1583020800&period2=1586908800` (2020-03-01 → 2020-04-15), 31 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/TSLA?period1=1583020800&period2=1586908800&interval=1d
- **Trough: adjclose 24.08133316040039 @ ts 1584538200 = 2020-03-18.** Guards: 28.502 (2020-03-20), 28.509 (2020-03-19).
- Peak window: `period1=1634256000&period2=1636934400` (2021-10-15 → 2021-11-15), 21 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/TSLA?period1=1634256000&period2=1636934400&interval=1d
- **Peak: adjclose 409.9700012207031 @ ts 1636032600 = 2021-11-04.** Guards: 407.363 (2021-11-05), 404.62 (2021-11-03).
- **Multiple: 409.9700012207031 ÷ 24.08133316040039 = 17.02x** (close-to-close, 596 calendar days).
- Adjustment note: series carries TSLA's Aug-2020 5-for-1 and Aug-2022 3-for-1 splits (raw peak close $1,229.91 ÷ 3 = $409.97 — exact match; 2020 trough raw $361.22 ÷ 15 = $24.08 — exact match).

### PLTR — Palantir Technologies Inc. (NasdaqGS)

- Trough window: `period1=1669852800&period2=1673740800` (2022-12-01 → 2023-01-15), 30 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/PLTR?period1=1669852800&period2=1673740800&interval=1d
- **Trough: adjclose 6.0 @ ts 1672151400 = 2022-12-27.** Guards: 6.07 (2022-12-28), 6.29 (2022-12-23).
- Peak window: `period1=1760486400&period2=1765756800` (2025-10-15 → 2025-12-15), 42 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/PLTR?period1=1760486400&period2=1765756800&interval=1d
- **Peak: adjclose 207.17999267578125 @ ts 1762180200 = 2025-11-03.** Guards: 200.47 (2025-10-31), 198.81 (2025-10-29). Window intraday high 207.52 (2025-11-03, matches the 52-week high shown in meta).
- **Multiple: 207.17999267578125 ÷ 6.0 = 34.53x** (close-to-close, 1,042 calendar days).
- Adjustment note: no stock splits since IPO, adjclose = raw close.

### COIN — Coinbase Global, Inc. (NasdaqGS)

- Trough window: `period1=1669852800&period2=1673740800` (2022-12-01 → 2023-01-15), 30 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/COIN?period1=1669852800&period2=1673740800&interval=1d
- **Trough: adjclose 32.529998779296875 @ ts 1672237800 = 2022-12-28.** Guards: 32.65 (2022-12-27), 33.26 (2023-01-03).
- Peak window: `period1=1730419200&period2=1733011200` (2024-11-01 → 2024-12-01), 20 sessions.
  URL: https://query1.finance.yahoo.com/v8/finance/chart/COIN?period1=1730419200&period2=1733011200&interval=1d
- **Peak: adjclose 325.4100036621094 @ ts 1731940200 = 2024-11-18.** Guards: 324.57 (2024-11-19), 324.24 (2024-11-08). Window intraday high 341.75 (2024-11-20).
- **Multiple: 325.4100036621094 ÷ 32.529998779296875 = 10.00x** (close-to-close, 691 calendar days).
- Adjustment note: no stock splits since IPO, adjclose = raw close.

## Thresholds met (verified, window-bounded)

| Threshold | Tickers verified this session |
|---|---|
| ≥ 5x | all 8 |
| ≥ 10x | GME, MSTR, PLTR, AMC, SMCI, TSLA, NVDA, COIN |
| ≥ 20x | GME, MSTR, PLTR, AMC, SMCI |
| ≥ 50x | GME |
| ≥ 100x | GME (124.11x, April 2020 → January 2021 close-to-close) |

## Caveats (recorded, not hidden)

1. **Window-bounded, not all-time claims.** Each trough/peak is the extremum inside its fetched
   window. Windows were chosen from full-history monthly locator scans and, for SMCI (trough) and
   PLTR/MSTR (peak), extended and re-fetched until the extremum stopped improving.
2. **These are price returns over multi-year holding windows**, not returns achievable inside a
   30-day contest, and they are stock-market returns — The Leap (September 2026 edition) is a
   futures-only contest (0 equities in the verified universe; see `data/contest_universe.json`).
3. Realized returns of this magnitude required holding through drawdowns of 50–90%; they are
   evidence of *what these assets have done*, not a strategy the contest allows or the project
   recommends.
4. Yahoo Finance data may differ from exchange official prints in edge cases; the endpoint values
   above are archived verbatim in `data/volatile_stocks.json` for re-computation.


## Re-verification pass — 2026-09-16 (second pass)

All 16 endpoint windows (8 symbols × trough/peak) were re-fetched from the Yahoo v8 chart API on
2026-09-16 and re-derived:

- GME, MSTR, PLTR, AMC, SMCI, TSLA, COIN: endpoint values bit-identical to the original capture;
  dates and rounded multiples unchanged.
- NVDA: Yahoo re-adjusted historical adjclose. Currently served: trough 2022-10-14 =
  11.186724662780762 (was 11.186728477478027); peak 2024-06-18 = 135.20562744140625 (was
  135.20559692382812). Both generations recompute 12.09x. The archive in
  data/volatile_stocks.json was updated to the currently-served values (IR-13).
