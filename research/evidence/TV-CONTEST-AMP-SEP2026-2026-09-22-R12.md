# TradingView official contest capture — AMP Futures September 2026, pass 12 (R12)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22, twenty-first-pass research session (fetched and transcribed)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** registration deadline clock (`data/live_contest_clock.json`), trading window, prize
  display, displayed participant count, and the visible top of the public leaderboard
- **Status:** official primary capture; point-in-time snapshot, not a live feed and not a final cutoff

## Verbatim quotations (line-by-line verified against the page text)

The binding upcoming date — the registration deadline rendered in the site's live clock:

> Join until Sep 23, 2026 · 04:00 GMT-4

Trading window and minimum activity:

> Paper trade from September 1 to September 30, and for at least 5 days.

Prize display and asset class:

> $50 K + 250 plans

> Futures

Leaderboard scope and displayed participants:

> This is the top 250 out of 102,747 participants.

Public leaderboard top 3 rows (rank · trader · realized profit % · realized profit $):

> 1 — HappyLittleTrades — +1,193.11% — +$2,982,777.45
>
> 2 — someshsingh5845 — +1,104.84% — +$2,762,088.00
>
> 3 — AlphaTradersHub — +1,097.33% — +$2,743,334.50

Further rows observed (ranks 4-10) but not carried into downstream arithmetic:

> 4 — vishansingh200308 — +1,064.70% — +$2,661,749.75
>
> 5 — yxiao8911 — +1,050.80% — +$2,627,000.00
>
> 6 — huliusalecsander — +1,026.78% — +$2,566,954.75
>
> 7 — youcanttrickme — +978.96% — +$2,447,408.00
>
> 8 — rajgaurav009 — +978.50% — +$2,446,262.00
>
> 9 — leonardo22_romano — +934.05% — +$2,335,125.00
>
> 10 — bdhbdalghny264 — +912.86% — +$2,282,150.00

## Line-by-line findings

1. **Registration closes `Sep 23, 2026 · 04:00 GMT-4`** (UTC `2026-09-23T08:00:00Z`) — the most
   time-critical upcoming action for entering the live contest at all. Recorded verbatim in
   `data/live_contest_clock.json` (`registration_close_display`) and rendered at the top of the
   site's executive summary.
2. The board ranks by **realized profit** (`Realized profit %` / `Realized profit $` columns),
   consistent with `data/contest_config.json`'s `ranking_metric`.
3. The visible board is **top 250 of 102,747**; ranks below 250 are never published
   (`public_leaderboard_last_visible_rank`).
4. The frontier moved materially since R11 (2026-09-19): rank 1 then HappyLittleTrades
   +$2,485,745.50 / +994.30%, now +$2,982,777.45 / +1,193.11%; participants then 99,727, now
   102,747 (+3,020). The R11 "frontier stasis" observation is expired; no stasis claim is
   carried forward.

## Irregularities flagged

- **IR-35** — the landing page displayed `102,729 traders` for this contest minutes apart from
  this page's `102,747 participants` (delta 18). Both official, recorded as observed.
