# TradingView official rules capture — The Leap: Magnificent Seven (stocks edition), 2026-09-22

- **URL:** https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22, twenty-first-pass research session (fetched and read in full, 4 pages)
- **Tier:** official_primary (TradingView, Inc., contest organiser — Official Competition Rules)
- **Use:** source of record for the stocks-edition rule constants used across this repository
  (`intel/competition.py` RULE_PROFILES["stocks_official_leap"], `data/contest_config.json`
  lineage, the 50-unit cap in `run_participant_window` sizing, and the min-3-active-days rule)
- **Status:** official primary capture; the edition ran Mar 16 – Apr 3, 2026 and its results are final

## Verbatim quotations (line-by-line verified against the page text)

Balance, leverage, commission and the position cap (the four constants every stocks-edition
figure in this repository is derived from):

> The preset balance size for the Paper Trading Competition Account is 100,000 virtual USD. Leverage for stocks: 1:1. The commission is 0.01%.

> The maximum size of an open position per instrument is limited to 50.0 units. One unit represents one share of the underlying instrument.

Eligible instruments (exactly seven NASDAQ names — NOT the repository's 20-stock experiment pool):

> NASDAQ:NVDA
>
> NASDAQ:AAPL
>
> NASDAQ:MSFT
>
> NASDAQ:GOOGL
>
> NASDAQ:AMZN
>
> NASDAQ:META
>
> NASDAQ:TSLA

Ranking and end-of-competition auto-close (the metric every leaderboard in this repo mirrors):

> A participant’s place during the Competition and at the end of the Competition is determined based on the realized profit/loss on the Competition account. Realized profit/loss for the purposes of the Competition is considered to be profit/loss on closed positions.

> All open positions of the Competition participants will be automatically closed at the end of the Competition Period. The realized profit/loss of the automatically closed positions will be taken into account in the final calculation of the places of the participants of the Competition.

Minimum activity and prize structure (placement arithmetic in `data/leaderboard_lab.json` reads these):

> A prerequisite that a Competition participant must fulfill in order to qualify for a prize is trading activity for at least 3 days of the Competition

> Prizes are distributed among the first 500 participants in the Competition who received the greatest profit in the Paper Trading Competition Account as of the end date of the Competition, taking into account the results of automatically closed positions.

> From 1 to 10 Place: 12-month subscription
>
> From 11 to 50 Place: 6-month subscription
>
> From 51 to 250 Place: 3-month subscription
>
> From 251 to 500 Place: 1-month subscription

No-reset rule (why ruin is terminal in every simulation here):

> The preset parameters of the Paper Trading Competition Account cannot be changed, and the account cannot be reset to its initial state.

Paper-only scope and rate limit (relevant to high-frequency paper strategies):

> Only simulated trading is allowed in the Competition. **No real money or cryptocurrency will be used for trading during the Competition.**

> Access to Paper Trading is prohibited if 60 or more transactions with orders and positions are performed per minute.

## Line-by-line findings

1. **The four constants in `RULE_PROFILES["stocks_official_leap"]` match the page exactly** —
   100,000 virtual USD / 1:1 / 0.01% / 50.0 units per instrument. No transcription drift found.
2. **Min active days = 3** matches `min_active_days: 3` in the profile (the AMP futures edition's
   5-day rule is separately sourced to TV-RULES-AMP-SEP2026).
3. **Prizes run 500 deep** for this edition (subscription months, one prize per entrant), with
   tiers 1-10 / 11-50 / 51-250 / 251-500. The repository's `maximum_prize_recipients: 50`
   belongs to the live AMP futures edition's cash-prize structure, not this one.
4. **Short selling is not addressed anywhere in the rules text.** The rules restrict instruments,
   size, leverage and commission but never prohibit short positions; the actual Paper Trading
   engine's short mechanics are therefore unverified rather than forbidden. This is recorded as
   the standing caveat for the short-side strategy families (C18, C31, C33, C34, C6, C9).
5. **Irregularity IR-36:** the Prize Limitation clause names prizes that the rules never define.

## Irregularities flagged

- **IR-36** — the clause "In the event an Entrant qualifies for more than one (1) prize (i.e. the
  Top Trader Prize, MPT Prize or Flawless Run Prize)" references an "MPT Prize" and a "Flawless
  Run Prize" that do not appear anywhere else in the four-page rules text; only "Top Trader
  Prizes" are defined. Official-document inconsistency; flagged for human review.
