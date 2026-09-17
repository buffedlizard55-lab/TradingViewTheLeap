# Leaderboard capture 6 — The Leap by AMP Futures, September 2026

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Accessed (UTC):** 2026-09-17, between roughly 21:15 and 21:30; recorded midpoint **2026-09-17T21:27:00Z**
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Method:** the same public page re-read through the research retrieval tool (chunked markdown, same mechanism as captures 1–5). The leaderboard self-reports updating "no more than once an hour" (official rules §08), so intra-chunk timing cannot create a sub-hour discrepancy inside one capture.
- **Result:** **top frontier unchanged to the cent vs capture 5**; participant counter rose **96,236 → 96,268 (+32)**. Landing page hero at same minute read **96,263** (IR-09 asynchronous counters).

## Verbatim quotations (manual review against the live URL)

Participant counter and board header:

> This is the top 250 out of 96,268 participants.

Top three rows (rank 1 holder unchanged since capture 1):

> 1 … leonardo22_romano … +934.05% … +$2,335,125.00

> 2 … youcanttrickme … +929.89% … +$2,324,723.00

> 3 … ashutoshrajan6 … +867.61% … +$2,169,031.50

Ranks 45–51 (the cash-prize cut-off sits between 50 and 51):

> 45 … dussadin … +505.50% … +$1,263,760.00

> 46 … nique316 … +503.95% … +$1,259,867.00

> 47 … asilturk … +501.54% … +$1,253,854.09

> 48 … GenesisRashelAguilar … +501.44% … +$1,253,588.00

> 49 … rajgaurav009 … +499.16% … +$1,247,897.00

> 50 … Nikola_Ng … +497.73% … +$1,244,313.50

> 51 … Schwimmente123 … +492.09% … +$1,230,221.65

Rank 100 and the rows it displaced (both were the displayed rank-100 holder in an earlier capture):

> 100 … nynyyynn54 … +405.98% … +$1,014,950.00

> 101 … JeremyTradezzz … +404.88% … +$1,012,202.50

> 105 … wowlass63 … +399.96% … +$999,892.85

Rank 250 and the two rows directly above it:

> 248 … josechuhdelb … +266.53% … +$666,314.12

> 249 … bayupanji836 … +266.46% … +$666,150.00

> 250 … mrchrissmithl143 … +264.30% … +$660,759.50

Prize block (identical wording to captures 1–5):

> Prizes up for grabs … The top 300 participants by the highest income will be the winners. …
> 1st place $10,000 · 2nd place $7,000 · 3rd place $6,000 · 4th place $3,500 · 5th place $2,500 ·
> 6th to 25th place $550 · 26th to 50th place $400 · 51st to 300th place 3-month TradingView subscription

Eligible-instrument block on the same page (12 named, count completed by the collapsed remainder):

> Paper trade the symbols below during the contest. … MES1! … MNQ1! … MYM1! … M2K1! … ES1! … NQ1! …
> YM1! … RTY1! … EMD1! … MNK1! … NKD1! … BTC1! and 82 more

## Cross-checks confirmed on the spot

1. **All four tracked ranks byte-identical to capture 5** (2026-09-17T20:58:00Z, ~29 minutes earlier): leonardo22_romano +934.05% / +$2,335,125.00; Nikola_Ng +497.73% / +$1,244,313.50; nynyyynn54 +405.98% / +$1,014,950.00; mrchrissmithl143 +264.30% / +$660,759.50. The board was static at the tracked frontier while the participant count grew.
2. **Participant counter:** the contest page printed 96,268 participants during this capture while the landing page printed 96,263 for the same edition about a minute earlier (IR-09, asynchronous counters, difference 5). The landing hero also rose from 96,230 (capture 5) to 96,263 (+33), tracking the contest page's rise.
3. **Arithmetic re-derived:** $ / 250,000 → displayed %: rank 1 934.05% exact; rank 50 497.73% (re-derived $1,244,325.00 vs displayed $1,244,313.50 — $11.50 inside the ±$12.50 two-decimal rounding bound); rank 100 405.98% exact; rank 250 264.30% (re-derived $660,750.00 vs displayed $660,759.50 — $9.50 inside the same bound). Both residues are consistent with the page rounding a longer internal P/L to a two-decimal percentage; they are recorded rather than smoothed (IR-24).
4. **Universe count:** the page lists 12 instruments and collapses the remainder as "and 82 more", i.e. 12 + 82 = 94, matching the 94 instruments in the official rules §08 and in `data/contest_universe.json`.

## Frontier movement, captures 5 → 6 (2026-09-17T20:58:00Z → 2026-09-17T21:27:00Z, 0.48 h)

| Rank | Capture 5 | Capture 6 | Change |
|---|---|---:|---:|
| 1 | +$2,335,125.00 | +$2,335,125.00 | $0.00 |
| 50 | +$1,244,313.50 | +$1,244,313.50 | $0.00 |
| 100 | +$1,014,950.00 | +$1,014,950.00 | $0.00 |
| 250 | +$660,759.50 | +$660,759.50 | $0.00 |
| Participants | 96,236 | 96,268 | +32 |

All values are point-in-time displays of a board that the organiser may correct (IR-23); none of them is a threshold, a floor, or a final prize level. The 5 → 6 window is the second observed interval in which **all four tracked frontiers were static** while the participant count rose, confirming that board quiescence can extend beyond the 1.90-hour window of capture 5 and that participant inflow does not mechanically move the tracked frontier every hour. Combined with H22 (rank-heterogeneous drift) and H20 (correction-driven fall), this establishes three distinct board behaviours in one day: heterogeneous rise, correction-driven fall, and uniform stasis.
