# TradingView official contest capture — AMP Futures September 2026, pass 11 (R11)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-19, approximately 19:30–19:40 UTC (re-read live; timestamp
  recorded as 19:35Z midpoint). Leaderboard updates no more than once per hour per §08.
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** point-in-time public leaderboard frontier and displayed participant count only
- **Status:** official primary capture; not a final cutoff and not a prize guarantee

The page displayed **the same four frontier rows as R10** (byte-identical trader / % / $) with a
higher participant count. Displayed participants: **99,727**.

Frontier quartet (ranks 1 / 50 / 100 / 250) for `data/frontier_history.json` capture 10 — identical
to capture 9 / R10:

> 1 — HappyLittleTrades — +994.30% — +$2,485,745.50
>
> 50 — ashutoshrajan6 — +583.87% — +$1,459,666.50
>
> 100 — aoe900620 — +472.56% — +$1,181,405.00
>
> 250 — maxeq — +303.03% — +$757,562.50

Landing-page hero at the same session (see `TV-THELEAP-LANDING-R11.md`):

> Take part with 99,727 traders

### %-vs-$ consistency (H11 protocol, $12.50 rounding bound at 250,000 base)

Unchanged vs R10 (same displayed %/$):

- Rank 1: 250,000 × 9.9430 = 2,485,750.00 vs displayed 2,485,745.50 → diff **$4.50** ✓
- Rank 50: 250,000 × 5.8387 = 1,459,675.00 vs displayed 1,459,666.50 → diff **$8.50** ✓
- Rank 100: 250,000 × 4.7256 = 1,181,400.00 vs displayed 1,181,405.00 → diff **$5.00** ✓
- Rank 250: 250,000 × 3.0303 = 757,575.00 vs displayed 757,562.50 → diff **$12.50** ✓ (at bound)

### Key observations (recorded as H44)

1. Displayed participants rose 99,663 (R10, ~18:30Z) → **99,727 (+64)** while registration remains
   open until 2026-09-23 08:00 UTC.
2. Ranks 1 / 50 / 100 / 250 are **byte-identical** to R10 (same traders, same percentages, same
   dollar figures). This is a same-day interval of complete frontier stasis with a rising
   participant count (H44).
3. Rank-1 holder remains HappyLittleTrades +994.30% / +$2,485,745.50 (no further turnover vs R10).
4. Landing hero and contest-board participant counts both read **99,727** at this session
   (IR-09 asynchronous-counter delta is 0 at this capture; not a new irregularity).
5. No IR-30 is raised: the participant rise is the expected open-registration behaviour already
   catalogued under IR-09 / H44, and the frontier values did not move.

### No-hallucination check

- Frontier trader names, percentages, and dollar values above are the R10 verbatim rows, re-confirmed
  unchanged on the live contest page at ~19:30Z. They were not re-invented.
- Participant count 99,727 was read live from both the contest page and the landing page.
- This capture does **not** re-enumerate ranks 2–249; only the tracked quartet and the displayed
  participant count are claimed.
