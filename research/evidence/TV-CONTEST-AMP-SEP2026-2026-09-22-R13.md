# TradingView official contest capture — AMP Futures September 2026, pass 13 (R13)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22 ~23:00, twenty-second-pass research session (fetched and transcribed)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** eleventh timestamped leaderboard frontier capture (ranks 1/50/100/250), displayed
  participant count, registration-deadline clock, and the visible top of the public board
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

> This is the top 250 out of 102,886 participants.

Public frontier rows (rank · trader · realized profit % · realized profit $):

> 1 — HappyLittleTrades — +1,193.11% — +$2,982,777.45
>
> 50 — TRAD_ERDO — +610.01% — +$1,525,023.75
>
> 100 — rishig90x — +494.67% — +$1,236,663.00
>
> 250 — kumarv3 — +346.64% — +$866,600.85

Further top-of-board rows observed (ranks 2–15) and carried into this evidence only (not into
frontier arithmetic):

> 2 — someshsingh5845 — +1,104.84% — +$2,762,088.00
>
> 3 — AlphaTradersHub — +1,097.33% — +$2,743,334.50
>
> 4 — vishansingh200308 — +1,072.18% — +$2,680,449.75
>
> 5 — yxiao8911 — +1,050.80% — +$2,627,000.00
>
> 6 — huliusalecsander — +1,026.78% — +$2,566,954.75
>
> 7 — rajgaurav009 — +1,043.52% — +$2,608,807.00
>
> 8 — alltlll800 — +995.87% — +$2,489,684.00
>
> 9 — youcanttrickme — +978.96% — +$2,447,408.00
>
> 10 — anishjinn10 — +965.49% — +$2,413,720.00
>
> 11 — leonardo22_romano — +934.05% — +$2,335,125.00
>
> 12 — bdhbdalghny264 — +912.86% — +$2,282,150.00
>
> 13 — okiibaba_79 — +907.05% — +$2,267,630.00
>
> 14 — leongoat — +883.26% — +$2,208,160.00
>
> 15 — lucky_suman_09 — +863.93% — +$2,159,822.00

## Line-by-line findings

1. **This is the eleventh frontier capture** (`data/frontier_history.json`, capture 11,
   `captured_at_utc = 2026-09-22T23:00:00Z`) and the first frontier capture since R11
   (2026-09-19T19:35:00Z). R12 earlier the same day was a clock/top-rows capture only.
2. **All four tracked frontiers rose since R11** (verified arithmetic, `scripts/verify.py`
   `frontier.*`): rank 1 +$497,031.95 ($2,485,745.50 → $2,982,777.45), rank 50 +$65,357.25
   ($1,459,666.50 → $1,525,023.75), rank 100 +$55,258.00 ($1,181,405.00 → $1,236,663.00),
   rank 250 +$109,038.35 ($757,562.50 → $866,600.85). Registered as **H58**.
3. **Participants rose 99,727 → 102,886 (+3,159)** across the same interval; registration
   closes `Sep 23, 2026 · 04:00 GMT-4` (UTC 2026-09-23T08:00:00Z), so this capture is taken
   in the edition's final registration day.
4. **Every frontier row's displayed % and $ reconcile within the ±$12.50 rounding bound**
   (H11): deltas are $2.45 (rank 1), $1.25 (rank 50), $12.00 (rank 100), $0.85 (rank 250)
   against `250,000 × pct/100`.
5. **Rank 1's displayed row is byte-identical to the R12 clock capture** (+1,193.11% /
   +$2,982,777.45) — same-day leader stasis while the mid-board moved (vishansingh200308
   rank 4 rose from +1,064.70% at R12 to +1,072.18% here; rajgaurav009 rose from +978.50%
   at R12 to +1,043.52% here).
6. **The displayed board order is non-monotonic between ranks 6 and 7 at this capture**:
   rank 6 huliusalecsander +1,026.78% / +$2,566,954.75 while rank 7 rajgaurav009
   +1,043.52% / +$2,608,807.00 — the lower rank displays MORE profit. Both rows reconcile
   individually. Recorded as **IR-37** and tested as **H59**; displayed order is transcribed
   as observed, never corrected.

## Irregularities flagged

- **IR-35 (continuing)** — the landing page displayed `102,883 traders` for this contest
  minutes apart from this page's `102,886 participants` (delta 3). Both official, recorded
  as observed.
- **IR-37 (new)** — displayed rank 7 shows more realized profit than rank 6 (see finding 6).
