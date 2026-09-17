# Leaderboard capture 4 — The Leap by AMP Futures, September 2026

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Accessed (UTC):** 2026-09-17, between roughly 18:58 and 19:08; recorded midpoint **2026-09-17T19:04:00Z**
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Method:** same public page re-read through the research retrieval tool (chunked markdown, same
  mechanism as captures 1–3). The leaderboard self-reports updating "no more than once an hour"
  (official rules §08), so intra-hour chunk timing does not distort cross-chunk comparisons.

## Verbatim quotations (manual review against the live URL)

> This is the top 250 out of 96,095 participants.

Rank 1 (holder unchanged since capture 1):

> leonardo22_romano … +934.05% … +$2,335,125.00

Ranks 49–50 (both transcribed because the frontier row moved between them):

> 49 … rajgaurav009 … +499.16% … +$1,247,897.00

> 50 … Nikola_Ng … +497.73% … +$1,244,313.50

Rank 100 (new holder):

> 100 … JeremyTradezzz … +404.88% … +$1,012,202.50

Rank 250 (new holder; the row immediately above it reads johndu38 +264.14% / +$660,352.75 —
its rank number fell exactly on a retrieval chunk boundary and is therefore quoted without a rank label):

> 250 … NxSChadha … +262.92% … +$657,305.00

Prize block (unchanged from captures 1–3):

> Prizes up for grabs … The top 300 participants by the highest income will be the winners. …
> 1st place $10,000 · 2nd place $7,000 · 3rd place $6,000 · 4th place $3,500 · 5th place $2,500 ·
> 6th to 25th place $550 · 26th to 50th place $400 · 51st to 300th place 3-month TradingView subscription

## Cross-checks confirmed on the spot (row-level identity with prior captures)

| Row value | Rank at capture 2 (00:30Z) | Rank at capture 3 (16:56Z) | Rank at capture 4 (19:04Z) |
|---|---:|---:|---:|
| rajgaurav009 +$1,247,897.00 (+499.16%) | — (not yet on board at this value) | 50 | **49** |
| wowlass63 +$999,892.85 (+399.96%) | — | 100 | **103** |
| msm223034 +$971,231.00 (+388.49%) | 100 | ~114 | **116** |

Each value pair (percentage and dollar) is identical to the cent/digit across captures; the trader
names match. These are the same rows sliding down the board as new entrants insert above them,
except the capture-3 rank-50 row, which moved **up** one place — see the decrease note below.

## Deltas versus capture 3 (2026-09-17T16:56:00Z), ~2.13 hours later

| Rank | Capture 3 | Capture 4 | Δ USD | Δ pp | Holder |
|---|---:|---:|---:|---:|---|
| 1 | +$2,335,125.00 (+934.05%) | +$2,335,125.00 (+934.05%) | $0.00 | 0.00 | same |
| 50 | +$1,247,897.00 (+499.16%) | +$1,244,313.50 (+497.73%) | **−$3,583.50** | −1.43 | changed |
| 100 | +$999,892.85 (+399.96%) | +$1,012,202.50 (+404.88%) | +$12,309.65 | +4.92 | changed |
| 250 | +$655,069.50 (+262.03%) | +$657,305.00 (+262.92%) | +$2,235.50 | +0.89 | changed |
| Participants | 95,709 | 96,095 | +386 | — | — |

Every percentage/dollar pair in capture 4 satisfies the displayed-rounding identity against the
250,000 virtual-USD balance (maximum deviation $11.50 at rank 50, bound $12.50) — recomputed by the
offline verifier (`frontier.math`).

## Headline finding — the displayed frontier decreased

Realized profit/loss "is considered to be profit/loss on closed positions" (official rules §08); a
single participant's realized P/L cannot shrink when positions stay closed. Yet the displayed
rank-50 value fell by $3,583.50 while the capture-3 rank-50 row appeared verbatim at rank 49.
The net effect is **exactly one fewer row ahead of that tracked row**; the most parsimonious
reading is that one row ranked 1–48 at capture 3 was removed from the public board between 16:56
and ~19:04 UTC (disqualification or board correction; the rules reserve at-any-time
disqualification rights at §05, §09 and especially §16, and the official pages publish no
board-change log). Ranks 100 and 250 rose over the same window, so this is not a whole-board
recalculation artifact. Recorded as IR-23 and tested as hypothesis H20.

## Limitations

- Point-in-time public display; values update at most once per hour; not executable prices.
- Retrieval returns markdown, not raw bytes; the raw-HTML archive for this capture is
  `artifact_pages/the-leap-amp-futures-september-2026.html` (capture 1). Captures 2–4 are
  preserved as the verbatim quotations above plus recomputed deltas in
  `data/frontier_history.json`.
- The landing page counter read 96,089 at the same minute vs 96,095 on the contest page
  (evidence TV-THELEAP-LANDING-R4.md): two official counters disagreeing by 6, consistent with
  asynchronous caching — same pattern already logged as IR-09.
