# Landing page re-verification, fifth pass — The Leap champions

- **URL:** https://www.tradingview.com/the-leap/
- **Accessed (UTC):** 2026-09-17, between roughly 20:55 and 20:58
- **Tier:** official_primary (TradingView, Inc.)
- **Result:** all **15 completed-edition #1 records** in `data/verified_explosive_returns.json`
  are unchanged in identity, displayed net profit and participant count; **0 new champions** (the
  September edition is still live, so its leader is not a completed record).

## Selected verbatim excerpts (manual review against the live URL)

> Risk-free trading competitions with real-money prizes and real practice up for grabs.

> September 1 – 30, 2026 … The Leap by AMP Futures … Take part with 96,230 traders … Trade futures … Compete for $50 K prize pool and 250 plans

> Futures trading contest — February 2025 … BenBernanke1 … Net profit+5,220.72% … Profitable trades94%

> Futures trading contest — July 2026 … Me-tis … Net profit+155.95% … Profitable trades65%

> Stocks trading contest — March 2026 … prodigy5284 … Net profit+17.58% … Profitable trades95%

> Crypto trading contest — May 2026 … Manishh_jain92 … Net profit+271.78% … Profitable trades77%

> Show more champs

## Champion roll re-read this pass (verbatim profit strings, page order)

| Edition | Champion | Displayed net profit | Displayed #1 out of | Recomputed multiple |
|---|---|---:|---:|---:|
| Futures, Jul 2026 | Me-tis | +155.95% | 107,677 | 2.5595x |
| Forex, Jun 2026 | Minitrader91 | +91.87% | 60,141 | 1.9187x |
| Crypto, May 2026 | Manishh_jain92 | +271.78% | 39,363 | 3.7178x |
| Stocks, Mar 2026 | prodigy5284 | +17.58% | 41,301 | 1.1758x |
| Crypto, Feb 2026 | vasu_adiraju | +114.61% | 49,466 | 2.1461x |
| Futures, Feb 2026 | JoshTrades_ICT | +124.24% | 55,871 | 2.2424x |
| Stocks, Dec 2025 | kgougakis | +29.90% | 71,342 | 1.299x |
| Futures, Nov 2025 | apsudnay | +148.51% | 82,042 | 2.4851x |
| Futures, Jun 2025 | BitK77 | +111.92% | 54,870 | 2.1192x |
| Multi-asset, Apr 2025 | ICT_Hispanohablantes | +308.07% | 36,965 | 4.0807x |
| Futures, Feb 2025 | BenBernanke1 | +5,220.72% | 59,187 | **53.2072x** |
| Multi-asset, Nov 2024 | hoy8886 | +8.36% | 59,127 | 1.0836x |
| Multi-asset, Aug 2024 | Investox_Solutions | +10.01% | 59,105 | 1.1001x |
| Multi-asset, May 2024 | Melissa2018 | +11.11% | 78,243 | 1.1111x |
| Multi-asset, Mar 2024 | StihlBtChainSaw | +87.25% | 92,045 | 1.8725x |

Every row above was matched one-to-one, in page order, against the `records` array of
`data/verified_explosive_returns.json`: 15/15 trader names, 15/15 displayed percentages, 15/15
participant counts, 0 mismatches; the recomputed multiple uses the frozen project formula
`1 + published net-profit percentage / 100`. Maximum completed outcome remains **53.2072x**
(BenBernanke1, Futures February 2025); no completed edition at or above 100x (H6 remains refuted).
The in-progress AMP September row is tracked separately in `data/frontier_history.json`.

## Live-edition counter note

The landing hero read "Take part with 96,230 traders" at this pass versus "96,236" in the contest
page's leaderboard header at the same minute — a 6-unit gap between two official counters, the same
asynchronous-caching pattern registered as IR-09. The tracker always records the contest-page
number (96,236) and never mixes counters from two pages.

## Limitations

Champion cards disclose username, net profit, profitable-trade share and participant count only —
no trade history, no instrument attribution, no risk figures, and no statement that a strategy
generalizes. The page also renders a "Show more champs" control, so the visible 15 are the
*displayed* sample; this project makes no claim that it is every edition ever run.
