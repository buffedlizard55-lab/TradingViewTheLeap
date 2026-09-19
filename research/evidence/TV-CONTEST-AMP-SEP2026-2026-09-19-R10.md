# TradingView official contest capture — AMP Futures September 2026, pass 10 (R10)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-19, approximately 18:15–18:45 UTC (read window; leaderboard
  updates no more than once per hour per §08)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** point-in-time public leaderboard frontier and displayed participant count only
- **Status:** official primary capture; not a final cutoff and not a prize guarantee

The page displayed **"This is the top 250 out of 99,663 participants."** The following rows
were read verbatim from the official page at this pass:

> 1 — HappyLittleTrades — +994.30% — +$2,485,745.50
>
> 2 — huliusalecsander — +958.47% — +$2,396,183.75
>
> 3 — leonardo22_romano — +934.05% — +$2,335,125.00
>
> 4 — youcanttrickme — +908.01% — +$2,270,023.00
>
> 5 — AlphaTradersHub — +869.09% — +$2,172,714.50

Frontier quartet (ranks 1 / 50 / 100 / 250) for `data/frontier_history.json` capture 9:

> 1 — HappyLittleTrades — +994.30% — +$2,485,745.50
>
> 50 — ashutoshrajan6 — +583.87% — +$1,459,666.50
>
> 100 — aoe900620 — +472.56% — +$1,181,405.00
>
> 250 — maxeq — +303.03% — +$757,562.50

Adjacent boundary rows (prize-tier edges), read verbatim:

> 51 — hazem2mahmoud6 — +579.59% — +$1,448,980.00

Prize ladder (§09 restatement on the contest page), read verbatim and unchanged:

> 2nd place $7,000; 1st place $10,000; 3rd place $6,000; 4th place $3,500; 5th place $2,500;
> 6th to 25th place $550; 26th to 50th place $400; 51st to 300th place 3-month TradingView
> subscription. "The top 300 participants by the highest income will be the winners."

Essentials (§08 restatement on the contest page), read verbatim and unchanged:

> "At the start of the contest, every participant will have $250,000 in paper trading money
> to take part. Remember, you'll need to trade for 5 days or more to qualify."
> "Participants with paid and trial plans get real-time data for this competition. Free users
> can still compete with a delay or start a trial subscription."
> Header facts: "$50 K + 250 plans Prizes; 30 days Duration; Futures Assets to trade."
> Registration note: "Join until Sep 23, 2026 · 04:00 GMT-4" (= 08:00 UTC, matches §04).

### %-vs-$ consistency (H11 protocol, $12.50 rounding bound at 250,000 base)

- Rank 1: 250,000 × 9.9430 = 2,485,750.00 vs displayed 2,485,745.50 → diff **$4.50** ✓
- Rank 50: 250,000 × 5.8387 = 1,459,675.00 vs displayed 1,459,666.50 → diff **$8.50** ✓
- Rank 100: 250,000 × 4.7256 = 1,181,400.00 vs displayed 1,181,405.00 → diff **$5.00** ✓
- Rank 250: 250,000 × 3.0303 = 757,575.00 vs displayed 757,562.50 → diff **$12.50** ✓ (at bound)

### Key observations (recorded as H40; all values above are the evidence)

1. Participants rose 96,707 (R9, Sep 18) → **99,663 (+2,956)**; landing hero read 99,658
   at the same session (IR-09 async delta +5, same signature as captures 5–6).
2. **First rank-1 turnover since captures began:** HappyLittleTrades +994.30%
   (+$2,485,745.50) takes the lead, up from rank 3 / +826.37% / +$2,065,935.50 at R9
   (+$419,810.00 of newly realised profit). Prior holder leonardo22_romano is
   byte-identical at +$2,335,125.00 and slides to rank 3.
3. huliusalecsander rises rank 4 → rank 2 (+786.78% → +958.47%, +$429,243.75 realised).
4. youcanttrickme's displayed realised profit FELL (+929.89% → +908.01%, −$54,700.00)
   while sliding rank 2 → rank 4: realised P/L moves down only when net losers are
   closed, re-confirming H20 (frontier values are not ratchet floors).
5. Cash-prize edge (rank 50) rose vs capture 8 (+$1,380,404.00 → +$1,459,666.50,
   +$79,262.50); rank 100 rose (+$1,123,096.25 → +$1,181,405.00); rank 250 rose
   (+$715,045.00 → +$757,562.50). Registration still open until Sep 23, 2026 08:00 UTC.

### No-hallucination check

- Every rank, trader, percentage, and dollar value above is copied verbatim from the
  fetched official page (16 chunks, ranks 1–250 fully enumerated in-session).
- Participant count 99,663 matches the "top 250 out of 99,663 participants" display.
- Prize ladder and essentials quotes match the contest page sections exactly.
- URL for rules: https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- URL for contest: https://www.tradingview.com/the-leap/amp-futures-september-2026/
- URL for landing: https://www.tradingview.com/the-leap/
