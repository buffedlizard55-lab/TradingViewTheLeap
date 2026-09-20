# C19 follow-up gate: two-stage absorption variant

**Status: proposal only — implemented and frozen as model `C19A`, not rostered, not
backtested on the live pool, and not a recommendation.**

## Why this exists

Frozen C19 (`intel/stock_strategies.py`) requires two consecutive closes each down by at least
1.5 ATR, with the second bar closing in the top half of its own range and volume confirmation.
Coverage history: 38/60 when this gate was written (2026-09-19), 58/60 on 2026-09-20 (daily
19/20 — PLUG[1d] and SMCI[1h] outstanding), and the gate fires only at 60/60 with daily 20/20.
The recorded zero-fire result on the partial pool cannot establish
that the hypothesis is false. A full-pool run must happen first.

If C19 still has zero fires after the matrix reaches 60/60 and the competition is re-derived, this
is a **new model**, not a parameter change to frozen C19:

## C19-A — delayed two-stage absorption (`C19A`)

- **Stage 1:** detect the first liquidation bar: close-to-close decline at least 1.5 ATR and volume
  at least 2 times the rolling volume baseline.
- **Stage 2:** within the next three sessions, accept a second liquidation bar at least 1.0 ATR
  down whose low is not more than 0.25 ATR below the first liquidation low, and whose close is in
  the top 40% of its own range.
- **Entry:** long at the next bar open after Stage 2; pyramid only on a close at least 1 ATR above
  the entry close, with a maximum of three adds.
- **Exit:** the frozen holding-period rule for the new model's pre-registration, plus terminal
  liquidation at the edition boundary.

The wider three-session confirmation is intended to test whether the strict adjacent-bar cascade is
simply too rare for a monthly edition while preserving the same contrarian/absorption idea. It is
not a tuned rescue: the rules above are frozen in `intel/stock_strategies.py` (`C19A` /
`GATED_STOCK_MODEL_IDS`) and must not be rostered until the evidence list below is complete.
`scripts/verify.py` fails if a gated model appears on `data/competition/stock_roster.json`.

## Required evidence before registration

1. Matrix index reports 60/60 captured stock series, including 20/20 daily series.
2. `scripts/run_stock_competition.py` is run unchanged for C17–C19 and B1 on the full daily pool.
3. H39 is assigned a verdict from the pre-registered comparison, with fire count and coverage in the
   evidence file; a zero-fire result remains `inconclusive` rather than `refuted`.
4. If C19-A is registered, it receives new usernames, a new model ID, a frozen parameter record,
   the same costs and forward-held-out split, and an untouched forward window.
5. Official-provider bars remain preferred. Until Alpaca credentials are available, Yahoo captures
   stay vendor-tier and must not be described as exchange-verified prices.
