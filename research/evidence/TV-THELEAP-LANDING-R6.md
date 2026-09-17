# The Leap landing page — sixth re-verification (2026-09-17 ~21:27 UTC)

- **URL:** https://www.tradingview.com/the-leap/
- **Accessed (UTC):** 2026-09-17 between roughly 21:25 and 21:30
- **Tier:** official_primary (TradingView, Inc. — the competition landing page)
- **Result:** **zero changes vs the five earlier passes.** The 15 completed-edition champion records in `data/verified_explosive_returns.json` are unchanged in name, net-profit percentage and participant count. The maximum remains **BenBernanke1: +5,220.72% (53.2072x)**, 59,187 participants; **no sampled record at or above 100x** (IR-03).

## Live-edition hero (the edition currently in its competition window)

> The Leap by AMP Futures — September, 2026 … Trade with virtual money … $250,000 … Futures … 20:1

Participant counter printed during this capture:

> 96,263 participants

This is the landing-page hero counter. It sits **5 participants below** the contest page's 96,268 printed in the same minute (see TV-CONTEST-AMP-SEP2026-2026-09-17-R6.md, IR-09 asynchronous counters). It rose from 96,230 at capture 5 to 96,263 at capture 6 (+33), tracking the contest page's rise of +32 over the same window; the +1 difference between the two pages' rises is within the async-snapshot jitter already documented.

## Completed-edition champions (verbatim snapshot, identical to passes 1–5)

The landing page lists the same 15 champions in the same order; spot-checked rows:

> BenBernanke1 — Net profit +5,220.72% — Profitable trades 94% — Leap by CME — 59,187 participants

> Me-tis — Net profit +155.95% — 1st out of 107,677 — Futures trading contest — July 2026

> Minitrader91 — Net profit +91.87% — 1st out of 60,141 — Forex trading contest — June 2026

> Manishh_jain92 — Net profit +271.78% — 1st out of 39,363 — Crypto trading contest — May 2026

> hoy8886 — Net profit +8.36% — 1st out of 59,127 — Multi-asset — August 2024

And the remaining historical rows (Investox_Solutions +10.01%, Melissa2018 +11.11%, StihlBtChainSaw +87.25%) are byte-identical to the first pass. The full comparison set underlying `data/verified_explosive_returns.json` is machine-diffed by `scripts/verify.py::check_verified_returns` on every build.

## Checks performed this pass

1. **Champion table diff:** every hero-card percentage, trader handle and participant count was re-read and compared with the committed `data/verified_explosive_returns.json` — zero changes.
2. **Live-edition identity:** the live hero still points at AMP Futures September 2026 with the same August 17 → September 23 registration window and the same September 1 08:00 UTC → September 30 12:00 UTC competition window quoted in the rules; no edition switch.
3. **Counter consistency:** landing hero 96,263 vs contest page 96,268 at ~21:27 UTC; both rose vs their capture-5 values (96,230 vs 96,236), confirming the IR-09 async pattern persists but is bounded to a few-count difference (here 5 participants, 0.005%).
