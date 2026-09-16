# Testing plan — how to place (and win) The Leap: AMP Futures September 2026 edition

Status: every number in this plan cites a verified source (see `research/sources/sources.json`).
Re-verified live 2026-09-16 (second pass). This is a **test protocol**, not financial advice, and
it deliberately respects one rule from the brief: **risk management is not the goal** — the goal
is leaderboard placement. Where the rules make unbounded aggression self-defeating, this plan says
so with the rule text, because the goal is to *place*, not to die fast.

## 0. What "placing" actually requires (verified arithmetic)

Fact base (all re-verified live 2026-09-16):

| Fact | Value | Source |
|---|---|---|
| Starting balance | 250,000 virtual USD | [TV-RULES-AMP-SEP2026](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) §04 |
| Max leverage | 20:1 → max notional 5,000,000 | §04 |
| Ranking basis | **Absolute realized P/L in USD** on closed positions | §06, §07 |
| Leaderboard refresh | Hourly | §06 |
| Auto-close | All open positions closed at end (12:00 UTC Sep 30) | §07 |
| Activity requirement | Trades on ≥ 5 different trading days | §08 |
| Instrument universe | 94 futures, **zero stocks**, per-instrument position caps | §08 |
| Rate limit | ≥60 transactions/min ⇒ 1-hour+ paper-trading ban | §08 (IR-12) |
| Current rank 1 (day 16) | +$2,303,725.00 (+921.49%) | [TV-CONTEST-AMP-SEP2026](https://www.tradingview.com/the-leap/amp-futures-september-2026/) |
| Prize ladder | 1st $10,000 … 51st–300th 3-month plan; ARV $50,000 | §15 |

Key structural facts this plan exploits:

1. **Ranking is absolute USD, not percent.** A +921% account at rank 1 holds $2,303,725 —
   but so would any account that *realizes* $2.3M. Percentages only matter through the current
   balance: each 1% realized move on a $B balance is worth $B/100. Compounding your winning
   balance is therefore a direct multiplier on every future point (H3, H5).
2. **Only realized P/L counts.** Unrealized gains are invisible to the leaderboard. The
   leaderboard is an *hourly* snapshot of your closed-position history.
3. **Full leverage self-destructs at a 5% adverse tick move** on notional: 5% × $5M = $250k =
   the whole balance. There is no reset (§04) and a blown account cannot trade (balance floor).
   The only officially recorded 100x-class results in The Leap history come from **futures
   editions** (max #1 = 53.21x, BenBernanke1 Feb 2025) — the mechanism is high-volatility
   futures with realized compounding, not a single lucky 100x.
4. **Position caps bind the biggest levers.** E.g. SOL1! max 2.0 contracts × 500 SOL ≈
   96.05 × 1,000 SOL ≈ $96k notional/contract pair — ~1.9% of max notional. To express $5M
   notional you need many instruments (that is why the universe lists 94).

## 1. Testable hypotheses (with the exact test for each)

These are the "how to place" hypotheses H1–H12 in `research/hypotheses/hypotheses.json`
(distilled), plus the operational tests to run **inside the paper account** from today
(day 16 of 30 — registration is closed, but a paper trading account can still be opened and
used as a dry-run harness; the live leaderboard only counts registered accounts, so dry-run
results calibrate the *next* edition and any still-open registration window).

### T1 — Volatility-per-dollar test (which instruments to trade)
- Hypothesis: the fastest path to rank 1 is a basket of the highest-volatility-per-dollar
  instruments **whose caps do not bind before the notional target does**.
- Test: for each of the 20 master-list instruments, record the realized $ P/L per 1% adverse/
  favorable move on the cap-limited notional (multiplier × cap × price). Rank by that ratio.
  Expected ordering (to confirm live): crypto (SOL/XRP family — 4-digit daily ranges) >
  energy (NG, CL, RB, HO) > index (NQ) > metals (SI, PL).
- Instrumentation: 1-day paper positions at 25% of cap each morning; compare vs the daily
  realized P/L of the actual leaderboard top 10 (visible hourly).
- Decision rule: concentrate ≥70% of notional in the top-3 instruments of this test.

### T2 — Realization cadence test (when to close)
- Hypothesis: hourly leaderboard refresh ⇒ closing at least every trading session locks in
  more *counted* P/L than letting positions ride, and it also caps drawdown on the counted
  number (realized P/L never walks back — §07 counts realized only).
- Test: A/B within one day — morning positions closed at 12:00 UTC, afternoon positions closed
  at 18:00 UTC; compare counted leaderboard-equivalent $ vs a counterfactual "held to auto-close".
- Decision rule: adopt the cadence that maximizes realized $ per session with zero margin events.

### T3 — Compounding test (reinvest vs fixed stake)
- Hypothesis: with ranking = absolute $, reinvesting every realized profit maximizes d$/dt
  (each point of % return buys back a larger $ base). Fixed-stake is strictly dominated **as
  long as** the strategy's win rate per session is > 50% of its gross exposure — the test
  measures whether that holds.
- Test: track realized $ after each session; compute the "compounding multiplier" =
  (balance_today / 250,000) × session_%_return vs session_%_return on fixed 250k base.
- Decision rule: compound while T1's selected instruments are trending; revert to fixed stake
  in chop (measured by intraday range < 1% on 4h bars of the instrument).

### T4 — Threshold tracking (how much is enough)
- Hypothesis: the prize frontier moves *down* through the contest as late joiners compress
  the field; you only need to track and clear the current rank-300 line, not rank 1.
- Data (day-16, verified): top-50 ≈ +441.00%, top-100 ≈ +352.71%, top-250 ≈ +228.85%
  (H10, [TV-CONTEST-AMP-SEP2026](https://www.tradingview.com/the-leap/amp-futures-september-2026/)).
  In $ at the 250k base those lines ≈ $952k / $882k / $572k — but lines in **%** only convert
  at *your* balance, so the actionable metric is "my realized $ vs the $ shown at rank 300".
- Test: snapshot ranks 50/100/250/300 daily; regress the frontier against days-remaining.
- Decision rule: when your realized $ exceeds the rank-300 line with ≥ 5 trading days of
  activity banked (§08 minimum), stop taking marginal risk — you have a guaranteed prize.

### T5 — Activity-day banking (§08)
- Fact: you must trade on ≥ 5 different trading days. The contest has 22 trading days left
  (≈ 22 US sessions through Sep 30).
- Test/protocol: from day 1 of any future edition, book at least one small realized round-trip
  per session for the first 5 sessions (cost: a few dollars of P/L; benefit: the
  disqualification trigger of §12 "failed to make 5 days of trading activity" is eliminated).

### T6 — Automation guardrails (IR-12 — critical)
- Fact: ≥60 transactions/min ⇒ 1-hour+ ban; "using various scripts" is named in the warning;
  repeated violation risks disqualification (§12/§16).
- Protocol: order rate capped at ≤ 1 order per 5 seconds (12/min, 83% headroom), all orders
  batched through one manual-confirmation step (human-in-the-loop), no EAs/websockets polling
  faster than the hourly leaderboard cycle. This is the only configuration of "no manual
  input" that survives the rules text; anything faster is a documented ban risk.

## 2. Daily operating checklist (the "test run")

1. 00:00 UTC — snapshot leaderboard top 50/100/250/300 + rank-1 $; record to
   `research/strategy/snapshots/` (create on first run).
2. 08:00 UTC (open) — run T1's $-per-1%-move table on live prices; pick the top-3 instruments.
3. 08:05–16:00 UTC — trade T1 basket at ≤ 25% of cap per instrument, T2 cadence, T3 staking.
4. 16:05 UTC — close everything (auto-close parity); bank T5 activity-day.
5. 17:00 UTC — T4 frontier check: if rank-300 line cleared → switch to minimal-risk session.
6. End of edition — §07 auto-close; results within 5 working days (§15).

## 3. What this plan does NOT claim

- It does not claim a 100x is possible in 30 days: the only officially recorded #1 results cap
  at 53.21x (Feb 2025) and most editions' #1 are single-digit multiples (IR-03, IR-02).
- It does not claim the 8 volatile **stocks** (GME 124.11x … COIN 10.00x,
  [stocks section](../../index.html#stocks)) are tradable here: the AMP universe has **zero
  single-stock instruments** (IR-01). They are the verified reference set for the next
  stock edition of The Leap.
- It does not ignore the brief's "no risk management" instruction; it treats ruin-prevention
  only as the *rule arithmetic* that determines which aggressive paths actually finish the
  contest (a blown paper account scores $0 — IR-04 stands).
