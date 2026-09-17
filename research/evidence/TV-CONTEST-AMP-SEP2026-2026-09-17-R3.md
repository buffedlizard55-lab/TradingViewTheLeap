# Evidence: TV-CONTEST-AMP-SEP2026-R3

- **Publisher:** TradingView, Inc.
- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Title as served:** "The Leap by AMP Futures — September, 2026 — TradingView"
- **Accessed (UTC):** 2026-09-17 (third capture; read between roughly 16:54 and 16:58 UTC, recorded midpoint 16:56:00Z)
- **Tier:** official_primary

Third timestamped capture of the public leaderboard. Quotations below are verbatim from the page
as served on the access date. This is a moving snapshot, not a final threshold and not a prize
guarantee. The raw page is archived by the CI workflow (`artifact_pages/`); this text capture is
the audited evidence of record for the frontier values in `data/frontier_history.json` (capture 3).

## Q1 — Participant count and board range

> This is the top 250 out of ‪95,709‬ participants.

## Q2 — Registration deadline as displayed

> LiveJoin until Sep 23, 2026 · 04:00 GMT-4

(04:00 GMT-4 = 08:00 UTC, consistent with rules §04: "open until Sep 23, 2026, 08:00 UTC".)

## Q3 — Frontier rows (rank / trader / realized profit % / realized profit $)

> 1 · leonardo22_romano · +934.05% · +$2,335,125.00

> 25 · hanglesmoof · +607.80% · +$1,519,493.75

> 26 · Bizcryptbay · +605.70% · +$1,514,252.50

> 50 · rajgaurav009 · +499.16% · +$1,247,897.00

> 51 · Nikola_Ng · +497.73% · +$1,244,313.50

> 100 · wowlass63 · +399.96% · +$999,892.85

> 250 · mrchrissmithl143 · +262.03% · +$655,069.50

Display-arithmetic check (recomputed by scripts/verify.py within the ±$12.50 rounding bound):
250,000 × 9.3405 = 2,335,125.00 (exact); 250,000 × 4.9916 = 1,247,900.00 vs 1,247,897.00 (Δ$3.00);
250,000 × 3.9996 = 999,900.00 vs 999,892.85 (Δ$7.15); 250,000 × 2.6203 = 655,075.00 vs 655,069.50 (Δ$5.50).

## Q4 — Drift against the two earlier captures (from data/frontier_history.json)

| Rank | Capture 1 (09-16 21:39) | Capture 2 (09-17 00:30) | Capture 3 (09-17 16:56) |
|---|---|---|---|
| 1 | +921.49% / +$2,303,725.00 | +921.49% / +$2,303,725.00 | +934.05% / +$2,335,125.00 |
| 50 | +457.64% / +$1,144,096.25 | +468.89% / +$1,172,236.00 | +499.16% / +$1,247,897.00 |
| 100 | +384.08% / +$960,203.50 | +388.49% / +$971,231.00 | +399.96% / +$999,892.85 |
| 250 | +249.48% / +$623,689.00 | +249.48% / +$623,689.00 | +262.03% / +$655,069.50 |
| Participants | 93,527 | 93,702 | 95,709 |

Between captures 2 and 3 (~16.4 hours, US trading day): rank 1 rose +12.56 pp (+$31,400.00) with
the same holder; rank 50 rose +30.27 pp (+$75,661.00) and changed holder again; rank 100 rose
+11.47 pp (+$28,661.85); rank 250 rose +12.55 pp (+$31,380.50) and changed holder. The value that
was rank 50 at capture 2 (RIA-JANGHU, +$1,172,236.00) had slid to rank 69 at capture 3; the value
that was rank 100 at capture 2 (msm223034, +$971,231.00) had slid to rank 114.

## Q5 — Prize ladder as displayed (unchanged vs 2026-09-16 capture)

> 1st place $10,000 · 2nd place $7,000 · 3rd place $6,000 · 4th place $3,500 · 5th place $2,500
> 6th to 25th place $550 · 26th to 50th place $400 · 51st to 300th place 3-month TradingView subscription

## Q6 — FAQ confirmations (verbatim)

> You can trade only during the official competition period — from September 1 at 04:00 EDT to September 30 at 08:00 EDT.

> Registration closes on September 23 at 04:00 EDT, so don't miss your chance to join.

> If you register after the start of the contest, you can begin trading immediately and stay in the game until the very end. You'll not receive any extra time if you've registered later.

## Manual review

Open https://www.tradingview.com/the-leap/amp-futures-september-2026/ and compare each Q3 value.
The leaderboard updates no more than once per hour and values can move between any two reads.
