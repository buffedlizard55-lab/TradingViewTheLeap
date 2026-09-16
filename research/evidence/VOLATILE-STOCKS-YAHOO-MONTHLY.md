# High-Volatility Stocks — Monthly Locator Scans (window selection)

- **Publisher:** Yahoo Finance chart API (market data vendor — **NOT an official exchange or regulator**)
- **Tier:** market_data_vendor
- **Accessed (UTC):** 2026-09-16
- **Purpose:** full-history (or long-history) monthly scans used to select the daily-resolution
  windows documented in `VOLATILE-STOCKS-YAHOO-DAILY.md`. The daily windows carry the verified
  numbers; this file records how those windows were located and what the long view adds.

## Verbatim meta values captured from the three monthly fetches (2026-09-16)

> MSTR scan meta: "longName":"Strategy Inc", "regularMarketPrice":129.6, "fiftyTwoWeekHigh":365.21, "fiftyTwoWeekLow":81.81
> GME scan meta: "firstTradeDate":1013610600 (= 2002-02-13), "longName":"GameStop Corp.", "exchangeName":"NYQ"
> SMCI scan meta: "firstTradeDate":1175175000 (= 2007-03-29), "longName":"Super Micro Computer, Inc.", "exchangeName":"NMS"

## MSTR — monthly scan 2018-01-01 → 2026-09-14

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/MSTR?period1=1514764800&period2=1789516800&interval=1mo
- Observations captured from the response meta and series:
  - `longName` "Strategy Inc"; currency USD; exchange NasdaqGS.
  - Lowest monthly close in range: 11.81 (March 2020). Lowest monthly intraday value: 9.0 (March 2020).
  - Highest monthly close in range: 404.23 (June 2025); July 2025 monthly close 401.86.
  - At fetch time: `regularMarketPrice` 129.6; `fiftyTwoWeekHigh` 365.21; `fiftyTwoWeekLow` 81.81.
- Locator conclusion: trough region = March 2020, peak region = June–July 2025. Daily resolution
  refined these to 2020-03-18 (adjclose 9.22) and 2025-07-16 (adjclose 455.9). The monthly-close
  ratio 404.23 ÷ 11.81 ≈ 34.2x is the conservative monthly-close view; the verified close-to-close
  daily multiple is 49.45x.

## GME — monthly scan 2002-02-01 → 2026-09-14 (full listed history)

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/GME?period1=1009843200&period2=1789516800&interval=1mo
- Response meta: `firstTradeDate` 1013610600 (2002-02-13); `longName` "GameStop Corp.";
  currency USD; exchange NYSE.
- Observation captured from the monthly `low` series (2002 through late 2019): every monthly low
  in 2002–2019 is ≥ 1.1775 (adjusted).
- Locator conclusion: the April 2020 daily adjclose trough of 0.70 sits below every monthly low
  recorded in 2002–2019, i.e. the 2020-04-03 trough is the global adjusted low of the fetched
  history up to that point. Peak region (January 2021) confirmed at daily resolution.

## SMCI — monthly scan 2007-01-01 → 2026-09-14 (full listed history)

- **URL:** https://query1.finance.yahoo.com/v8/finance/chart/SMCI?period1=1167609600&period2=1789516800&interval=1mo
- Response meta: `firstTradeDate` 1175175000 (2007-03-29); `longName` "Super Micro Computer, Inc.";
  exchange NasdaqGS.
- Observation captured from the monthly series (2007–2011 portion): monthly open/low values in the
  2008–2009 financial-crisis months ran as low as ≈ 0.44–0.51 (adjusted), i.e. SMCI traded far
  lower in 2008–2009 than in the 2018–2022 region.
- **Irregularity/correction:** a partial 2018–onward locator scan suggested the 2022 trough
  (adjclose 5.242, 2022-10-12) was the all-time trough; the full-history scan disproves that —
  the all-time adjusted lows date to 2008–2009. The verified SMCI multiple in
  `data/volatile_stocks.json` is therefore kept **window-bounded** (2022-10-01 → 2022-12-01 trough
  window; 2024-02-15 → 2024-04-01 peak window): 22.66x. No 2008→2024 multiple is asserted because
  2008 daily resolution was not fetched this session (no number without a source).

## Cross-reference

The locator scans for AMC, NVDA, TSLA, PLTR and COIN used the same endpoint pattern at
`interval=1mo` over candidate regions; the daily windows documented in
`VOLATILE-STOCKS-YAHOO-DAILY.md` are the authoritative, fully-fetched records.
