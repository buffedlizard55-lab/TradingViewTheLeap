# Landing page re-verification, fourth pass — The Leap champions

- **URL:** https://www.tradingview.com/the-leap/
- **Accessed (UTC):** 2026-09-17 (~19:03–19:06)
- **Tier:** official_primary
- **Result:** all **15 completed-edition #1 records** in `data/verified_explosive_returns.json`
  are unchanged; **0 new champions added** (the September edition is still live).

## Selected verbatim excerpts (manual review against the live URL)

> Risk-free trading competitions with real-money prizes and real practice up for grabs.

> September 1 – 30, 2026 … The Leap by AMP Futures … Take part with 96,089 traders … Trade futures … Compete for $50 K prize pool and 250 plans

> Futures trading contest — February 2025 … BenBernanke1 … Net profit+5,220.72%

> Futures trading contest — July 2026 … Me-tis … Net profit+155.95%

> Stocks trading contest — March 2026 … prodigy5284 … Net profit+17.58%

## Champion roll re-read this pass (verbatim profit strings)

| Edition | Champion | Displayed net profit | Recomputed multiple |
|---|---|---:|---:|
| Futures, Jul 2026 | Me-tis | +155.95% | 2.5595x |
| Forex, Jun 2026 | Minitrader91 | +91.87% | 1.9187x |
| Crypto, May 2026 | Manishh_jain92 | +271.78% | 3.7178x |
| Stocks, Mar 2026 | prodigy5284 | +17.58% | 1.1758x |
| Crypto, Feb 2026 | vasu_adiraju | +114.61% | 2.1461x |
| Futures, Feb 2026 | JoshTrades_ICT | +124.24% | 2.2424x |
| Stocks, Dec 2025 | kgougakis | +29.90% | 1.299x |
| Futures, Nov 2025 | apsudnay | +148.51% | 2.4851x |
| Futures, Jun 2025 | BitK77 | +111.92% | 2.1192x |
| Multi-asset, Apr 2025 | ICT_Hispanohablantes | +308.07% | 4.0807x |
| Futures, Feb 2025 | BenBernanke1 | +5,220.72% | **53.2072x** |
| Multi-asset, Nov 2024 | hoy8886 | +8.36% | 1.0836x |
| Multi-asset, Aug 2024 | Investox_Solutions | +10.01% | 1.1001x |
| Multi-asset, May 2024 | Melissa2018 | +11.11% | 1.1111x |
| Multi-asset, Mar 2024 | StihlBtChainSaw | +87.25% | 1.8725x |

Multiple formula (unchanged project convention): `1 + published net-profit percentage / 100`.
Maximum completed outcome remains **53.2072x** (BenBernanke1, Futures February 2025); no
completed edition at or above 100x (H6 stands as refuted). The live September row's frontier
progress is tracked separately in `data/frontier_history.json` (capture 4: rank 1 +934.05%).

## Live-edition counter note

The landing hero read “Take part with 96,089 traders” at this pass versus 96,095 on the contest
page at the same minute — a 6-unit gap between two official counters, same asynchronous-caching
pattern already registered as IR-09. No action; never overwrite a contest-page capture with a
landing-page counter.

## Limitations

Champion cards disclose username, net profit, profitable-trade share and participant count only —
no trade history, no instrument attribution, and no statement that a strategy generalizes.
