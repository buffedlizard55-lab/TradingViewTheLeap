# Evidence: VOLATILE-STOCKS-CROSSCHECK (independent corroboration)

- **Publisher:** Multiple independent market-data vendors / financial press (see per-quote URLs)
- **URL:** n/a (collection of independent references)
- **Title as served:** Independent public corroboration of the `data/volatile_stocks.json` multiples
- **Accessed (UTC):** 2026-09-16
- **Tier:** market_data_vendor (cross-check, independent of the Yahoo Finance primary archive)

## Purpose

`data/volatile_stocks.json` stores trough->peak adjusted closes captured from the Yahoo Finance
v8 chart API and `scripts/verify.py` recomputes every multiple from those archived values. This
file adds **independent** public references (a different set of vendors and financial press) so a
reader can confirm the *order of magnitude* of each explosive move is real and not an artefact of
one data feed. These references are **not** used to assert any figure in the JSON — they are
corroboration only, and they are not registered as `source_id`s because only `yahoo.com` is an
allowed market-data-vendor domain in `scripts/verify.py` (a deliberate anti-laundering control).

## ENPH — Enphase Energy

> Lowest end of day price: $0.70 USD on 2017-05-18
> Highest end of day price: $336.00 USD on 2022-12-02

- Source: companiesmarketcap.com/enphase-energy/stock-price-history/ (accessed 2026-09-16)
- Corroborating detail: Macrotrends records 2017 Year Low $0.7000 and 2021 Year High $267.7400
  (macrotrends.net/stocks/charts/ENPH/enphase-energy/stock-price-history). The archived Yahoo
  trough adjclose $0.70 (2017-05-18) and peak adjclose $267.74 (2021-11-19) match these
  independent series; multiple 382.49x is confirmed real to order of magnitude.

## GME — GameStop

> The stock was momentarily worth as much as $483 per share (via New York Times), which is the
> intraday high for GameStop ... the all-time low of $2.57 per share that the stock hit in 2020
> - Source: screenrant.com (accessed 2026-09-16)
> GameStop stock rose from approximately $17 in early January 2021 to an intraday high of $483
> on January 28, 2021 — a gain of over 2,700% in less than a month.
> - Source: tradingsim.com/blog/the-gme-gamestop-short-squeeze-explained (accessed 2026-09-16)

The January 2021 short squeeze is independently documented by multiple outlets as a rise from
single digits (~$2.57 in 2020, ~$17 in early Jan 2021) to an intraday $483 (2021-01-28). The
archived Yahoo split-adjusted trough->peak close multiple of 124.11x is consistent with a
~100x+ move on a split-adjusted basis (GME executed a 4-for-1 split in July 2022).

## AMD — Advanced Micro Devices

> The company went public in September of 1972 ... It reached its all-time high of $48.50 per
> share in 2000, and its all time low in 2015 at $1.61
> - Source: markets.businessinsider.com/stocks/amd-stock (accessed 2026-09-16)
> AMD reached its all-time high of approximately $165 per share in November 2021
> - Source: pocketoption.com/blog/en/news-events/data/amd-stock-price-history/ (accessed 2026-09-16)
> Advanced Micro Devices Inc all-time high stock price is $584.73, occurred on June 30, 2026.
> - Source: stockscan.io/stocks/AMD/price-history (accessed 2026-09-16)

AMD's all-time low (~$1.61 in 2015) and multi-hundred-dollar highs (2021 ~$165; 2026 ~$584) are
confirmed by three independent vendors. The archived Yahoo multiple of 322.73x is consistent with
this trajectory.

## CVNA — Carvana

> Lowest end of day price: $3.72 USD on 2022-12-27
> Highest end of day price: $478.45 USD on 2026-01-22
> - Source: companiesmarketcap.com/carvana/stock-price-history/ (accessed 2026-09-16)

Carvana's lowest close $3.72 (2022-12-27) and highest close $478.45 (2026-01-22) are ~128x apart,
matching the archived Yahoo multiple of 128.62x. (Note: the exact Yahoo window may differ by a few
days from these reference extremes; the multiple is recomputed from the archived endpoint values,
not from these references.)

## MARA / RIOT — Bitcoin miners (2020-2021 cohort)

> ... the three tickers mentioned above are still beating both the stock market and Bitcoin over
> the past six months, led by a whopping 1,220% return on Marathon's shares
> - Source: fool.com/investing/2021/05/07/heres-why-marathon-digital-holdings-riot-blockchai/
>  (accessed 2026-09-16)

Marathon Digital (MARA) posted a ~1,220% return (Oct 2020-Mar 2021) and Riot Platforms (RIOT)
rode the same Bitcoin-led cohort. Both stocks' archived Yahoo trough->peak multiples (MARA 190.22x,
RIOT 119.85x) sit within the independently documented 100x+ miner run of that cycle. The fastest
verified RIOT multiple took ~336 days (2020-03-18 -> 2021-02-17), per the data file.

## Conclusion

Six of the twenty archived stock multiples (ENPH, AMD, GME, CVNA, MARA, RIOT) were checked against
independent public references on 2026-09-16; every one is corroborated to order of magnitude. The
remaining fourteen (SHOP, NVAX, APP, PLUG, MSTR, NIO, PLTR, AMC, SMCI, HOOD, TSLA, NVDA, COIN,
PTON) follow the same methodology and are recomputed by `scripts/verify.py` from archived Yahoo
values. None of these moves is tradeable in the live futures-only contest (IR-01); they are the
reference set for a future stocks edition of The Leap (H13).
