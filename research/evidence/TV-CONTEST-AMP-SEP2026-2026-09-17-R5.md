# Leaderboard capture 5 — The Leap by AMP Futures, September 2026

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Accessed (UTC):** 2026-09-17, between roughly 20:55 and 21:01; recorded midpoint **2026-09-17T20:58:00Z**
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Method:** the same public page re-read through the research retrieval tool (chunked markdown, same
  mechanism as captures 1–4). The leaderboard self-reports updating "no more than once an hour"
  (official rules §08), so intra-chunk timing cannot create a sub-hour discrepancy inside one capture.

## Verbatim quotations (manual review against the live URL)

Participant counter and board header:

> This is the top 250 out of 96,236 participants.

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

Prize block (identical wording to captures 1–4):

> Prizes up for grabs … The top 300 participants by the highest income will be the winners. …
> 1st place $10,000 · 2nd place $7,000 · 3rd place $6,000 · 4th place $3,500 · 5th place $2,500 ·
> 6th to 25th place $550 · 26th to 50th place $400 · 51st to 300th place 3-month TradingView subscription

Eligible-instrument block on the same page (12 named, count completed by the collapsed remainder):

> Paper trade the symbols below during the contest. … MES1! … MNQ1! … MYM1! … M2K1! … ES1! … NQ1! …
> YM1! … RTY1! … EMD1! … MNK1! … NKD1! … BTC1! and 82 more

## Cross-checks confirmed on the spot

1. **Rank-1, rank-49 and rank-50 rows are byte-identical to capture 4** (2026-09-17T19:04:00Z,
   ~1.90 hours earlier): leonardo22_romano +934.05% / +$2,335,125.00; rajgaurav009 +499.16% /
   +$1,247,897.00; Nikola_Ng +497.73% / +$1,244,313.50. The board refreshed at ranks 100 and 250 but
   not at the top or at the cash-prize edge during that window.
2. **Row identity across captures** — capture-3's rank-100 row (`wowlass63`, +$999,892.85) now sits at
   rank 105 and capture-4's rank-100 row (`JeremyTradezzz`, +$1,012,202.50) now sits at rank 101, so
   between captures 4 and 5 the rank-100 boundary was pushed down by exactly one new row while the
   rank-50 boundary did not move at all. Board drift is rank-heterogeneous, not uniform (H22).
3. **Arithmetic re-derived:** $ / 250,000 → displayed %: rank 1 934.05% exact; rank 50 497.73%
   (re-derived $1,244,325.00 vs displayed $1,244,313.50 — $11.50 inside the ±$12.50 two-decimal
   rounding bound); rank 100 405.98% exact; rank 250 264.30% (re-derived $660,750.00 vs displayed
   $660,759.50 — $9.50 inside the same bound). Both residues are consistent with the page rounding a
   longer internal P/L to a two-decimal percentage; they are recorded rather than smoothed.
4. **Counters:** the contest page printed 96,236 participants during this capture while the landing
   page printed 96,230 for the same edition about a minute earlier (IR-09, asynchronous counters).
5. **Universe count:** the page lists 12 instruments and collapses the remainder as "and 82 more",
   i.e. 12 + 82 = 94, matching the 94 instruments in the official rules §08 and in
   `data/contest_universe.json`.

## Frontier movement, captures 4 → 5 (2026-09-17T19:04:00Z → 2026-09-17T20:58:00Z, 1.90 h)

| Rank | Capture 4 | Capture 5 | Change |
|---|---|---:|---:|
| 1 | +$2,335,125.00 | +$2,335,125.00 | $0.00 |
| 50 | +$1,244,313.50 | +$1,244,313.50 | $0.00 |
| 100 | +$1,012,202.50 | +$1,014,950.00 | +$2,747.50 |
| 250 | +$657,305.00 | +$660,759.50 | +$3,454.50 |
| Participants | 96,095 | 96,236 | +141 |

All values are point-in-time displays of a board that the organiser may correct (IR-23); none of them
is a threshold, a floor, or a final prize level. The 4 → 5 window is the first observed interval in
which the cash-prize edge (rank 50) did not move while lower tracked frontiers did.
