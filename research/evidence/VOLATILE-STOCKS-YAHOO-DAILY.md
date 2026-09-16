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

---

## Batch 2 — 2026-09-16 (12 additional symbols, same methodology)

Captured the same way as batch 1: a daily window around each extremum, plus monthly locator scans that
bound the neighbouring months (a month whose intraday high is below the archived peak close cannot
contain a higher close). Windows were extended and re-fetched whenever the extremum sat at a window edge.
Every extremum date was cross-checked against an independent anchor (the monthly-close bar of the
corresponding month, where available). Split events for CVNA and SHOP were verified from the API's
`events=splits` response. All values below are window-bounded extremum claims, not all-time claims; the
archived endpoint values live in `data/volatile_stocks.json` and every multiple is re-derived by
`scripts/verify.py`. Note: the vendor series occasionally omits individual sessions inside an otherwise
continuous window (e.g. no bar for 2023-01-02 in the Dec-2022 trough windows); session counts below are
as returned by the endpoint.

### ENPH — Enphase Energy, Inc. (382.49x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/ENPH?period1=1492204800&period2=1497484800&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/ENPH?period1=1634256000&period2=1637366400&interval=1d
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/ENPH?period1=1636934400&period2=1642204800&interval=1d — peak follow-up window 2021-11-15 to 2022-01-14: max close 261.12 on 2021-11-22, below the 2021-11-19 peak
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/ENPH?period1=1483228800&period2=1527811200&interval=1mo — monthly locator 2017-01-01 to 2018-06-01: lowest monthly close 0.76 (May 2017), monthly low 0.65 (May 2017)
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/ENPH?period1=1609459200&period2=1635724800&interval=1mo — monthly scan Jan-Oct 2021: highest monthly high 229.04 (Feb 2021) < 267.74, so no 2021 close exceeds the archived peak
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "regularMarketPrice":35.3,...,"fiftyTwoWeekHigh":73.74,"fiftyTwoWeekLow":25.78
> trough window adjclose slice (2017-05-17, 2017-05-18, 2017-05-19): "adjclose":[...,0.7099999785423279,0.699999988079071,0.7200000286102295,...]
> peak window adjclose slice (2021-11-17, 2021-11-18, 2021-11-19): "adjclose":[...,254.86000061035156,254.47999572753906,267.739990234375]

Bounded-extremum derivation: trough 0.699999988079071 on 2017-05-18 is the minimum adjclose in the
2017-04-15→2017-06-15 window (adjacent closes 0.7099999785423279 (2017-05-17) and 0.7200000286102295 (2017-05-19); intraday low 0.6499999761581421 on the trough day). Peak 267.739990234375 on 2021-11-19 is the maximum
adjclose in the 2021-10-15→2021-11-20 window (adjacent closes 254.86000061035156 (2021-11-17) and 254.47999572753906 (2021-11-18); intraday high 272.0 on the peak day). The rounded multiple 382.49x
recomputes as peak ÷ trough and spans 1646 calendar days.
Split/basis note: close equals adjclose at both endpoints (no split or dividend adjustments inside the archived windows).

### AMD — Advanced Micro Devices, Inc. (322.73x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/AMD?period1=1452816000&period2=1456790400&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/AMD?period1=1779235200&period2=1782864000&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/AMD?period1=1717200000&period2=1789344000&interval=1mo — monthly locator Jun 2024 to Sep 2026: Jun 2026 is the highest monthly close (580.9099731445312) and highest monthly high (584.72998046875); Jul-Sep 2026 highs stay below 575
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/AMD?period1=1782221400&period2=1782864000&interval=1d — peak sub-window 2026-06-23 to 2026-07-01 (second fetch, pins the 2026-06-30 close)
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"AMD","fullExchangeName":"NasdaqGS",...,"fiftyTwoWeekHigh":584.73,"fiftyTwoWeekLow":149.85
> trough window adjclose slice (2016-01-19, 2016-01-20, 2016-01-21): "adjclose":[...,1.9500000476837312,1.7999999523162842,2.0899999141693115,...]
> peak sub-window closes (2026-06-25, 2026-06-26, 2026-06-29, 2026-06-30): "close":[...,532.5700073242188,521.5800170898438,539.489990234375,580.9099731445312]

Bounded-extremum derivation: trough 1.7999999523162842 on 2016-01-20 is the minimum adjclose in the
2016-01-15→2016-03-01 window (adjacent closes 1.8300000429153442 (2016-02-12 and 2016-02-16) and 1.840000033378601 (2016-02-10)). Peak 580.9099731445312 on 2026-06-30 is the maximum
adjclose in the 2026-05-20→2026-07-01 window (adjacent closes 539.489990234375 (2026-06-29) and 551.6300048828125 (2026-06-22); intraday high 584.72998046875 on the peak day equals the 52-week high in effect at fetch time). The rounded multiple 322.73x
recomputes as peak ÷ trough and spans 3814 calendar days.
Split/basis note: close equals adjclose at both endpoints (AMD's post-2024 dividend is not reflected as an adjustment inside either archived window).

### MARA — MARA Holdings, Inc. (190.22x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1583020800&period2=1585699200&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1635120000&period2=1638316800&interval=1d
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1636727400&period2=1638316800&interval=1d — peak follow-up window 2021-11-12 to 2021-12-01: max close 75.91999816894531 (2021-11-12), below the 2021-11-09 peak; the 2021-11-30 close 51.06999969482422 matches the November monthly-close anchor
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1564617600&period2=1590969600&interval=1mo — monthly locator Aug 2019 to May 2020: lowest monthly close 0.44999998807907104 (Mar 2020), monthly low 0.3499999940395355
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/MARA?period1=1590969600&period2=1654041600&interval=1mo — monthly scan Jun 2020 to May 2022: every month except Nov 2021 has an intraday high below 76.09, and the Nov 2021 daily window pins the max close at 76.08999633789062
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"MARA","fullExchangeName":"NasdaqCM",...,"regularMarketPrice":11.03,...,"fiftyTwoWeekHigh":23.45,"fiftyTwoWeekLow":6.66
> trough window adjclose slice (2020-03-17, 2020-03-18, 2020-03-19): "adjclose":[...,0.47999998927116394,0.4000000059604645,0.47999998927116394,...]
> peak window adjclose slice (2021-11-08, 2021-11-09, 2021-11-10): "adjclose":[...,75.30000305175781,76.08999633789062,64.83999633789062,...]

Bounded-extremum derivation: trough 0.4000000059604645 on 2020-03-18 is the minimum adjclose in the
2020-03-01→2020-04-01 window (adjacent closes 0.44999998807907104 (2020-03-23 and 2020-03-31); intraday low 0.3499999940395355 on the trough day). Peak 76.08999633789062 on 2021-11-09 is the maximum
adjclose in the 2021-10-25→2021-12-01 window (adjacent closes 75.30000305175781 (2021-11-08) and 75.91999816894531 (2021-11-12); intraday high 83.44999694824219 on the peak day). The rounded multiple 190.22x
recomputes as peak ÷ trough and spans 601 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### CVNA — Carvana Co. (128.62x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1669852800&period2=1673308800&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1764547200&period2=1772323200&interval=1d
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1673308800&period2=1676419200&interval=1d — trough follow-up window 2023-01-10 to 2023-02-15: min close 0.8840000033378601 (2023-01-10), above the 2022-12-27 trough
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1675209600&period2=1685577600&interval=1mo — monthly scan Feb-May 2023: lowest monthly low 1.2899999618530273 (Mar 2023), above the archived trough
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1685577600&period2=1789344000&interval=1mo — monthly locator Jun 2023 to Sep 2026: highest monthly close before Dec 2025 is 78.03 (Aug 2025); Dec 2025 close 84.40; Jan 2026 high 97.37799835205078 is the 2026-01-22 intraday peak captured in the daily window; Feb-Aug 2026 highs stay below 84
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/CVNA?period1=1669852800&period2=1789344000&interval=1mo — events=splits fetch 2022-12-01 to 2026-09-14: "events":{"splits":{"1777608000":{"date":1778247000,"numerator":5.0,"denominator":1.0,"splitRatio":"5:1"}}}
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"CVNA","fullExchangeName":"NYSE",...,"regularMarketPrice":65.41,...,"fiftyTwoWeekHigh":97.378,"fiftyTwoWeekLow":54.464
> trough window adjclose slice (2022-12-27, 2022-12-28, 2022-12-29): "adjclose":[...,0.7440000176429749,0.765999972820282,0.7440000176429749,...]
> peak window adjclose slice (2026-01-22, 2026-01-23, 2026-01-26): "adjclose":[...,95.69000244140625,94.66200256347656,94.74199676513672,...]

Bounded-extremum derivation: trough 0.7440000176429749 on 2022-12-27 is the minimum adjclose in the
2022-12-01→2023-01-10 window (adjacent closes 0.765999972820282 (2022-12-07 and 2022-12-28) and 0.8100000023841858 (2022-12-23); intraday low 0.7099999785423279 (2022-12-07)). Peak 95.69000244140625 on 2026-01-22 is the maximum
adjclose in the 2025-12-01→2026-03-01 window (adjacent closes 94.66200256347656 (2026-01-23) and 94.74199676513672 (2026-01-26); next-highest in window 95.54399871826172 (2026-01-27); intraday high 97.37799835205078 on the peak day equals the 52-week high in effect at fetch time). The rounded multiple 128.62x
recomputes as peak ÷ trough and spans 1122 calendar days.
Split/basis note: VERIFIED split event: the API events=splits response records a 5:1 forward split with date 1778247000 (2026-05-08), so pre-split adjclose values are one-fifth of contemporaneous unadjusted closes; both endpoints use the same vendor-adjusted series, so the multiple is unaffected.

### RIOT — Riot Platforms, Inc. (119.85x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/RIOT?period1=1583020800&period2=1585699200&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/RIOT?period1=1612137600&period2=1615766400&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/RIOT?period1=1546300800&period2=1590969600&interval=1mo — monthly locator Jan 2019 to May 2020: lowest monthly close 0.8330000042915344 (Mar 2020), monthly low 0.5109999775886536
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/RIOT?period1=1590969600&period2=1654041600&interval=1mo — monthly scan Jun 2020 to May 2022: every month except Feb 2021 has an intraday high below 77.90; Mar 2021 high 67.85 and Apr 2021 high 61.55 bound all later closes below the archived peak; the 2021-02-26 close 43.7400016784668 matches the February monthly-close anchor
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"RIOT","fullExchangeName":"NasdaqCM",...,"regularMarketPrice":20.235,...,"fiftyTwoWeekHigh":30.32,"fiftyTwoWeekLow":11.5
> trough window adjclose slice (2020-03-16, 2020-03-17, 2020-03-18): "adjclose":[...,0.6579999923706055,0.7480000257492065,0.6499999761581421,...]
> peak window adjclose slice (2021-02-17, 2021-02-18, 2021-02-19): "adjclose":[...,77.9000015258789,62.029998779296875,71.33000183105469,...]

Bounded-extremum derivation: trough 0.6499999761581421 on 2020-03-18 is the minimum adjclose in the
2020-03-01→2020-04-01 window (adjacent closes 0.6579999923706055 (2020-03-16) and 0.6690000295639038 (2020-03-23); intraday low 0.5109999775886536 on the trough day). Peak 77.9000015258789 on 2021-02-17 is the maximum
adjclose in the 2021-02-01→2021-03-15 window (adjacent closes 62.029998779296875 (2021-02-18) and 71.33000183105469 (2021-02-19); intraday high 79.5 on the peak day is the all-time intraday high in the scanned history). The rounded multiple 119.85x
recomputes as peak ÷ trough and spans 336 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### NVAX — Novavax, Inc. (81.41x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/NVAX?period1=1575158400&period2=1579046400&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/NVAX?period1=1612137600&period2=1614556800&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/NVAX?period1=1527811200&period2=1577836800&interval=1mo — monthly locator Jun 2018 to Dec 2019: lowest monthly close 3.9800000190734863 (Dec 2019), monthly low 3.8499999046325684
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/NVAX?period1=1577836800&period2=1593561600&interval=1mo — monthly scan Jan-Jun 2020: lowest monthly low 3.6500000953674316 (Jan 2020); Feb 2020 low 6.26 excludes a lower close after the archived trough
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/NVAX?period1=1593561600&period2=1638316800&interval=1mo — monthly scan Jul 2020 to Nov 2021: every month except Feb 2021 has an intraday high below 319.93 (max Aug 2021 high 260.0), so no other month can contain a higher close; the 2021-02-26 close 231.22999572753906 matches the February monthly-close anchor
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"NVAX","fullExchangeName":"NasdaqGS",...,"regularMarketPrice":9.35,...,"fiftyTwoWeekHigh":11.97,"fiftyTwoWeekLow":6.2
> trough window adjclose slice (2020-01-09, 2020-01-10, 2020-01-13): "adjclose":[...,4.010000228881836,3.930000066757202,3.950000047683716,...]
> peak window adjclose slice (2021-02-08, 2021-02-09, 2021-02-10): "adjclose":[...,319.92999267578125,315.8699951171875,298.3599853515625,...]

Bounded-extremum derivation: trough 3.930000066757202 on 2020-01-10 is the minimum adjclose in the
2019-12-01→2020-01-15 window (adjacent closes 3.950000047683716 (2020-01-13) and 3.9600000381469727 (2019-12-18); intraday low 3.6500000953674316 on the trough day). Peak 319.92999267578125 on 2021-02-08 is the maximum
adjclose in the 2021-02-01→2021-02-27 window (adjacent closes 315.8699951171875 (2021-02-09) and 298.3599853515625 (2021-02-10); intraday high 331.67999267578125 on 2021-02-10 is the all-time intraday high in the scanned history). The rounded multiple 81.41x
recomputes as peak ÷ trough and spans 395 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### APP — AppLovin Corporation (78.88x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/APP?period1=1669852800&period2=1673740800&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/APP?period1=1756684800&period2=1767225600&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/APP?period1=1717200000&period2=1789344000&interval=1mo — monthly locator Jun 2024 to Sep 2026: highest monthly close before the daily window is 718.5399780273438 (Sep 2025); Jan-Aug 2026 highs stay below 684, bounding all later closes below the archived peak
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/APP?period1=1648771200&period2=1669852800&interval=1mo — monthly scan Apr-Nov 2022: lowest monthly low 13.0 (Nov 2022), above the archived Dec 2022 trough
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"APP","fullExchangeName":"NasdaqGS",...,"regularMarketPrice":326.56,...,"fiftyTwoWeekHigh":745.61,"fiftyTwoWeekLow":297.5
> trough window adjclose slice (2022-12-23, 2022-12-27, 2022-12-28): "adjclose":[...,9.84000015258789,9.300000190734863,9.399999618530273,...]
> peak window adjclose slice (2025-12-19, 2025-12-22, 2025-12-23): "adjclose":[...,724.6199951171875,733.5999755859375,728.4500122070312,...]

Bounded-extremum derivation: trough 9.300000190734863 on 2022-12-27 is the minimum adjclose in the
2022-12-01→2023-01-15 window (adjacent closes 9.399999618530273 (2022-12-28) and 9.479999542236328 (2022-12-19); intraday low 9.140000343322754 (2022-12-28)). Peak 733.5999755859375 on 2025-12-22 is the maximum
adjclose in the 2025-09-01→2026-01-01 window (adjacent closes 728.4500122070312 (2025-12-23) and 727.5 (2025-12-24); next-highest in window 724.6199951171875 (2025-12-19); intraday high 745.6099853515625 (2025-09-29) equals the 52-week high in effect at fetch time; 2025-12-22 intraday high 738.010009765625). The rounded multiple 78.88x
recomputes as peak ÷ trough and spans 1091 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### SHOP — Shopify Inc. (92.61x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1451606400&period2=1455926400&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1759276800&period2=1762041600&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1443657600&period2=1464739200&interval=1mo — monthly locator Oct 2015 to Apr 2016: lowest monthly close 2.23799991607666 (Jan 2016), monthly low 1.8480000495910645
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1546300800&period2=1638316800&interval=1mo — monthly scan Jan 2019 to Nov 2021: only Nov 2021 has an intraday high (176.2917938232422) above the Nov-2021 interim daily peak close 169.05999755859375 (2021-11-19)
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1635724800&period2=1638316800&interval=1d — interim peak window Nov 2021: max close 169.05999755859375 on 2021-11-19 (last session of the window)
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/SHOP?period1=1717200000&period2=1789344000&interval=1mo — monthly locator Jun 2024 to Sep 2026: Oct 2025 is the highest-close month (173.86000061035156, matching the 2025-10-31 daily close anchor); Dec 2025 high 178.375 and all later monthly highs stay below the archived peak close
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"SHOP","fullExchangeName":"NasdaqGS",...,"regularMarketPrice":129.96,...,"fiftyTwoWeekHigh":182.19,"fiftyTwoWeekLow":94.0
> trough window adjclose slice (2016-02-11, 2016-02-12, 2016-02-16): "adjclose":[...,1.937000036239624,1.9329999685287476,2.049999952316284,...]
> peak window adjclose slice (2025-10-28, 2025-10-29, 2025-10-30): "adjclose":[...,178.96000671386719,179.00999450683594,173.61000061035156,...]

Bounded-extremum derivation: trough 1.9329999685287476 on 2016-02-12 is the minimum adjclose in the
2016-01-01→2016-02-20 window (adjacent closes 1.937000036239624 (2016-02-11) and 1.9850000143051147 (2016-02-09); intraday low 1.8480000495910645 on 2016-01-20). Peak 179.00999450683594 on 2025-10-29 is the maximum
adjclose in the 2025-10-01→2025-11-01 window (adjacent closes 178.96000671386719 (2025-10-28) and 173.61000061035156 (2025-10-30); next-highest in window 175.05999755859375 (2025-10-27); intraday high 182.19000244140625 on the peak day equals the 52-week high in effect at fetch time). The rounded multiple 92.61x
recomputes as peak ÷ trough and spans 3547 calendar days.
Split/basis note: VERIFIED split event: the API events=splits response records a 10:1 forward split with date 1656509400 (2022-06-29), so pre-split adjclose values are one-tenth of contemporaneous unadjusted closes (the Nov-2021 interim peak adjclose 169.05999755859375 corresponds to a $1690.60 unadjusted close); both endpoints use the same vendor-adjusted series, so the multiple is unaffected.

### PLUG — Plug Power, Inc. (72.46x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/PLUG?period1=1543622400&period2=1548979200&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/PLUG?period1=1609459200&period2=1612137600&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/PLUG?period1=1546300800&period2=1622505600&interval=1mo — monthly locator Jan 2019 to Apr 2021: Feb 2021 high 70.51000213623047 and all later monthly highs stay below the archived peak close; the 2021-01-29 close 63.16999816894531 matches the January monthly-close anchor
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/PLUG?period1=1527811200&period2=1546300800&interval=1mo — monthly scan Jun-Dec 2018: lowest monthly low outside Dec 2018 is 1.7100000381469727 (Nov 2018); Dec 2018 monthly low 0.9900000095367432 is inside the daily trough window
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/PLUG?period1=1583020800&period2=1586908800&interval=1d — alternate 2020 COVID trough window: min close 2.759999990463257 (2020-03-16), superseded by the deeper 2018-12-20 trough
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"PLUG","fullExchangeName":"NasdaqCM",...,"regularMarketPrice":2.03,...,"fiftyTwoWeekHigh":4.58,"fiftyTwoWeekLow":1.69
> trough window adjclose slice (2018-12-20, 2018-12-21, 2018-12-24): "adjclose":[...,1.0099999904632568,1.0199999809265137,1.0199999809265137,...]
> peak window adjclose slice (2021-01-25, 2021-01-26, 2021-01-27): "adjclose":[...,65.72000122070312,73.18000030517578,64.41999816894531,...]

Bounded-extremum derivation: trough 1.0099999904632568 on 2018-12-20 is the minimum adjclose in the
2018-12-01→2019-02-01 window (adjacent closes 1.0199999809265137 (2018-12-21 and 2018-12-24); intraday low 0.9900000095367432 on those days). Peak 73.18000030517578 on 2021-01-26 is the maximum
adjclose in the 2021-01-01→2021-02-01 window (adjacent closes 65.72000122070312 (2021-01-25) and 64.41999816894531 (2021-01-27); next-highest in window 69.5 (2021-01-13); intraday high 75.48999786376953 on the peak day is the all-time intraday high in the scanned history). The rounded multiple 72.46x
recomputes as peak ÷ trough and spans 768 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### NIO — NIO Inc. (47.61x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/NIO?period1=1569369600&period2=1571097600&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/NIO?period1=1609718400&period2=1614556800&interval=1d
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/NIO?period1=1567296000&period2=1569369600&interval=1d — trough guard window 2019-09-03 to 2019-09-24: min close 2.5999999046325684 (2019-09-03), above the archived trough
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/NIO?period1=1535760000&period2=1612137600&interval=1mo — monthly locator Sep 2018 to Jan 2021: only the Oct 2019 bar has a monthly low (1.190000057220459) below 1.32; the Oct 2019 daily window pins the min close at 1.3200000524520874
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/NIO?period1=1609459200&period2=1640995200&interval=1mo — monthly scan 2021: Jan 2021 high 66.99 and Feb 2021 high 64.60 are the only months above 62.85; both are covered by the daily peak windows; Mar-Dec 2021 highs stay below 55.14; the 2021-02-26 close 45.779998779296875 matches the February monthly-close anchor
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"NIO","fullExchangeName":"NYSE",...,"regularMarketPrice":3.59,...,"fiftyTwoWeekHigh":8.02,"fiftyTwoWeekLow":3.55
> trough window adjclose slice (2019-09-30, 2019-10-01, 2019-10-02): "adjclose":[...,1.559999942779541,1.3200000524520874,1.590000033378601,...]
> peak window adjclose slice (2021-02-08, 2021-02-09, 2021-02-10): "adjclose":[...,59.06999969482422,62.84000015258789,61.2599983215332,...]

Bounded-extremum derivation: trough 1.3200000524520874 on 2019-10-01 is the minimum adjclose in the
2019-09-25→2019-10-15 window (adjacent closes 1.5499999523162842 (2019-10-08) and 1.5299999713897705 (2019-10-10 and 2019-10-14); intraday low 1.190000057220459 on the trough day). Peak 62.84000015258789 on 2021-02-09 is the maximum
adjclose in the 2021-01-01→2021-02-26 window (adjacent closes 59.06999969482422 (2021-02-08) and 61.2599983215332 (2021-02-10); intraday high 66.98999786376953 on 2021-01-11 is the all-time intraday high in the scanned history). The rounded multiple 47.61x
recomputes as peak ÷ trough and spans 497 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### PTON — Peloton Interactive, Inc. (8.58x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/PTON?period1=1583020800&period2=1586908800&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/PTON?period1=1608009600&period2=1612137600&interval=1d
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/PTON?period1=1577836800&period2=1612137600&interval=1mo — monthly scan Jan 2020 to Jan 2021: every month before Dec 2020 has an intraday high below 139.76, and the Dec 2020 high 167.3699951171875 is below the archived peak close
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/PTON?period1=1609459200&period2=1640995200&interval=1mo — monthly scan 2021: Feb-Dec 2021 highs stay below 157.84, bounding all later closes below the archived peak; the 2020-12-31 close 151.72000122070312 and 2021-01-29 close 146.1300048828125 match the December and January monthly-close anchors
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"PTON","fullExchangeName":"NasdaqGS",...,"regularMarketPrice":4.835,...,"fiftyTwoWeekHigh":9.2,"fiftyTwoWeekLow":3.65
> trough window adjclose slice (2020-03-11, 2020-03-12, 2020-03-13): "adjclose":[...,22.0,19.510000228881836,19.719999313354492,...]
> peak window adjclose slice (2021-01-13, 2021-01-14, 2021-01-15): "adjclose":[...,156.0399932861328,167.4199981689453,165.25,...]

Bounded-extremum derivation: trough 19.510000228881836 on 2020-03-12 is the minimum adjclose in the
2020-03-01→2020-04-15 window (adjacent closes 22.0 (2020-03-11) and 19.719999313354492 (2020-03-13); intraday low 17.829999923706055 (2020-03-13)). Peak 167.4199981689453 on 2021-01-14 is the maximum
adjclose in the 2020-12-15→2021-02-01 window (adjacent closes 156.0399932861328 (2021-01-13) and 165.25 (2021-01-15); intraday high 171.08999633789062 (2021-01-15) is the all-time intraday high in the scanned history). The rounded multiple 8.58x
recomputes as peak ÷ trough and spans 308 calendar days.
Split/basis note: close equals adjclose in both archived windows.

### HOOD — Robinhood Markets, Inc. (19.8x)

- **URL (trough window):** https://query1.finance.yahoo.com/v8/finance/chart/HOOD?period1=1669852800&period2=1673740800&interval=1d
- **URL (peak window):** https://query1.finance.yahoo.com/v8/finance/chart/HOOD?period1=1759276800&period2=1763164800&interval=1d
- **URL (bounding fetch, 1d):** https://query1.finance.yahoo.com/v8/finance/chart/HOOD?period1=1668470400&period2=1669852800&interval=1d — trough guard window 2022-11-15 to 2022-11-30: min close 8.850000381469727 (2022-11-21), above the archived trough
- **URL (bounding fetch, 1mo):** https://query1.finance.yahoo.com/v8/finance/chart/HOOD?period1=1735689600&period2=1789344000&interval=1mo — monthly locator Jan 2025 to Sep 2026: Oct 2025 is the highest-close month (146.77999877929688, matching the 2025-10-31 daily close anchor); Nov 2025 high 149.41 is below the archived peak close; Dec 2025 onward monthly highs stay below 139.76
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor — Yahoo Finance chart API (NOT an official exchange, contest
  organiser, or regulator)

Archived endpoint values (verbatim fragments from the responses):

> "symbol":"HOOD","fullExchangeName":"NasdaqGS",...,"regularMarketPrice":104.42,...,"fiftyTwoWeekHigh":153.86,"fiftyTwoWeekLow":63.515
> trough window adjclose slice (2022-12-27, 2022-12-28, 2022-12-29): "adjclose":[...,7.699999809265137,7.699999809265137,8.050000190734863,...]
> peak window adjclose slice (2025-10-08, 2025-10-09, 2025-10-10): "adjclose":[...,150.8699951171875,152.4600061035156,138.9600067138672,...]

Bounded-extremum derivation: trough 7.699999809265137 on 2022-12-28 is the minimum adjclose in the
2022-12-01→2023-01-15 window (the trough close 7.699999809265137 occurs on both 2022-12-27 (epoch 1672151400) and 2022-12-28 (epoch 1672237800); next-higher closes 8.050000190734863 (2022-12-29) and 8.079999923706055 (2023-01-03); intraday low 7.565000057220459 on the trough day). Peak 152.4600061035156 on 2025-10-09 is the maximum
adjclose in the 2025-10-01→2025-11-15 window (adjacent closes 150.8699951171875 (2025-10-08) and 138.9600067138672 (2025-10-10); next-highest in window 148.6699981689453 (2025-10-03); intraday high 153.86000061035156 (2025-10-06) equals the 52-week high in effect at fetch time). The rounded multiple 19.8x
recomputes as peak ÷ trough and spans 1016 calendar days.
Split/basis note: close equals adjclose in both archived windows.

