# TradingView official landing-page capture — The Leap, pass 13 (R13)

- **URL:** https://www.tradingview.com/the-leap/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22 ~23:00, twenty-second-pass research session (fetched and transcribed)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** live-edition hero counter, re-verification of the completed-champion sample
  (`data/verified_explosive_returns.json`), official results-post links
- **Status:** official primary capture; point-in-time snapshot

## Verbatim quotations (line-by-line verified against the page text)

Live-edition block:

> September 1 – 30, 2026

> The Leap by AMP Futures

> Take part with 102,883 traders

> Compete for $50 K prize pool and 250 plans

Completed-champion cards as displayed (edition · winner · net profit · official results link):

> Futures trading contest — July 2026 — Me-tis — Net profit +155.95% —
> https://www.tradingview.com/blog/en/the-leap-tradestation-july-2026-60266/

> Forex trading contest — June 2026 — Minitrader91 — Net profit +91.87% —
> https://www.tradingview.com/blog/en/the-leap-forex-edition-59492/

> Crypto trading contest — May 2026 — Manishh_jain92 — Net profit +271.78% —
> https://www.tradingview.com/blog/en/winners-of-the-leap-crypto-series-58603/

> Stocks trading contest — March 2026 — prodigy5284 — Net profit +17.58% —
> https://www.tradingview.com/blog/en/the-leap-magnificent-seven-results-57868/

> Crypto trading contest — February 2026 — vasu_adiraju — Net profit +114.61% —
> https://www.tradingview.com/blog/en/the-leap-crypto-edition-results-57323/

> Futures trading contest — February 2026 — JoshTrades_ICT — Net profit +124.24% —
> https://www.tradingview.com/blog/en/the-leap-by-eurex-has-come-to-a-close-56951/

> Stocks trading contest — December 2025 — kgougakis — Net profit +29.90% —
> https://www.tradingview.com/blog/en/the-leap-christmas-edition-is-over-55806/

> Futures trading contest — November 2025 — apsudnay — Net profit +148.51% —
> https://www.tradingview.com/blog/en/the-leap-co-marketed-with-tradestation-comes-to-an-end-55603/

> Futures trading contest — June 2025 — BitK77 — Net profit +111.92% —
> https://www.tradingview.com/blog/en/tradingview-leap-by-tradestation-results-52831/

> Multi-asset trading contest — April 2025 — ICT_Hispanohablantes — Net profit +308.07% —
> https://www.tradingview.com/blog/en/tradingview-leap-by-pepperstone-winners-52062/

> Futures trading contest — February 2025 — BenBernanke1 — Net profit +5,220.72% —
> https://www.tradingview.com/blog/en/leap-by-cme-winners-announced-50889/

> Multi-asset trading contest — November 2024 — hoy8886 — Net profit +8.36% —
> https://www.tradingview.com/blog/en/the-leap-4-winners-48745/

> Multi-asset trading contest — August 2024 — Investox_Solutions — Net profit +10.01% —
> https://www.tradingview.com/blog/en/the-leap-3-paper-trading-competition-results-46445/

> Multi-asset trading contest — May 2024 — Melissa2018 — Net profit +11.11% —
> https://www.tradingview.com/blog/en/the-leap-2-paper-trading-competition-results-44828/

> Multi-asset trading contest — March 2024 — StihlBtChainSaw — Net profit +87.25% —
> https://www.tradingview.com/blog/en/leap-paper-trading-competition-results-43788/

## Line-by-line findings

1. **Champion sample re-verified: all 15 completed #1 records on the landing page match
   `data/verified_explosive_returns.json` field for field** (edition label, winner, published
   net-profit %, official results URL). No new completed edition has been published since
   R12; no row was added, removed, or changed. The maximum completed value remains
   **+5,220.72% (53.2072×, BenBernanke1)** — no 100× completed outcome exists on this page.
2. **The stocks-edition ceiling is unchanged**: the two completed stock champions display
   +17.58% (March 2026) and +29.90% (December 2025) — neither approaches 5×, consistent
   with the recorded arithmetic ceiling for official stocks-edition rules.
3. **Landing hero counter (102,883) trails the contest-page counter (102,886) by 3** in the
   same session — the asynchronous-counter pattern already logged as **IR-35 / IR-09**;
   recorded as observed, no arithmetic downstream depends on the counter.
4. Every champion figure above is TradingView's own published net-profit percentage; the
   only transformation applied anywhere in the project is
   `return_multiple = 1 + published_pct / 100`.
