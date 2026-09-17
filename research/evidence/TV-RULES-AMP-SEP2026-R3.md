# Evidence: TV-RULES-AMP-SEP2026-R3

- **Publisher:** TradingView, Inc.
- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- **Title as served:** "The Leap by AMP Futures — Terms and Conditions — TradingView"
- **Accessed (UTC):** 2026-09-17 (re-verification pass, ~16:55 UTC)
- **Tier:** official_primary

Line-by-line re-verification of every rule constant in `data/contest_config.json` and
`data/contest_universe.json` against the page as served on 2026-09-17. All 21 sections were
re-read. Result: **no rule constant changed** between the 2026-09-16 transcription and this
re-read. Quotations below are verbatim.

## Q1 — Competition period and registration (section 04)

> The TradingView Paper Trading Competition by AMP Global Clearing, LLC ("Competition") sponsored by Sponsor begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC ("Competition Period"). Registration for the Competition opens at Aug 17, 2026, 13:00 UTC and is open until Sep 23, 2026, 08:00 UTC.

> TradingView's computer will be the official clock for the Competition.

## Q2 — Nature (preamble)

> NO PURCHASE OR PAYMENT OF ANY KIND NECESSARY TO PARTICIPATE OR WIN. THIS IS A COMPETITION OF SKILL. A PURCHASE WILL NOT INCREASE YOUR CHANCES OF WINNING. NO ACTUAL CASH WILL BE TRADED.

> INSTRUMENTS AVAILABLE IN THE COMPETITION ARE FOR SIMULATION PURPOSES ONLY AND MAY NOT REFLECT THE ACTUAL INSTRUMENTS AVAILABLE ON A SPONSOR'S ACCOUNT.

## Q3 — Account parameters, ranking, auto-close (section 08)

> The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD. Leverage for futures: 20:1.

> A prerequisite that a Competition participant must fulfill in order to qualify for a prize is trading activity for at least 5 days of the Competition. Trading activity within one day is considered to be actions that resulted in the opening or closing of positions from 00:00:00 to 23:59:59 UTC.

> A participant's place during the Competition and at the end of the Competition is determined based on the realized profit/loss on the Competition account. Realized profit/loss for the purposes of the Competition is considered to be profit/loss on closed positions. During the Competition, the places in the leaderboard are updated no more than once an hour. All open positions of the Competition participants will be automatically closed at the end of the Competition Period. The realized profit/loss of the automatically closed positions will be taken into account in the final calculation of the places of the participants of the Competition.

> The preset parameters of the Paper Trading Competition Account cannot be changed, and the account cannot be reset to its initial state. The Competition accounts will be automatically deleted after 30 days from the date of the end of the Competition, without notifying the participants.

> TradingView warns that excessively high activity of transactions in Paper Trading, including using various scripts, will lead to a ban on access to Paper Trading for one hour or longer. Access to Paper Trading is prohibited if 60 or more transactions with orders and positions are performed per minute.

> The results of the Competition will be announced no later than up to five working days from the end date of the Competition.

## Q4 — Instrument universe (section 08)

> Only the following instruments are available for trading within the Competition:

The 94 listed symbols were re-read in order on 2026-09-17 and diffed programmatically, line by
line, against `data/contest_universe.json`: **94/94 symbols identical, all 94 per-instrument
position limits identical, zero equity (single-stock) symbols present** (no NASDAQ/NYSE/AMEX
contracts in the list). Per-instrument caps were re-read from the matching "maximum amount for an
open position is N" lines (e.g. "for CME_MINI:MES1! maximum amount for an open position is 500.0",
"for CME:BTC1! maximum amount for an open position is 1.0").

## Q5 — Real-time data gating (section 06)

> Participants on a free plan (other than Essential, Plus, Premium, or Ultimate subscription types) who were not previously active users of TradingView's paid services will not be provided with the Competition Real-Time Data by reason of their participation in the Competition.

> access to the Competition Real-Time Data will then be granted within twenty-four (24) hours of such subscription or trial activation.

## Q6 — Prize ladder (section 09)

> 1 Place: 10,000 USD · 2 Place: 7,000 USD · 3 Place: 6,000 USD · 4 Place: 3,500 USD · 5 Place: 2,500 USD
> From 6 to 25 Place: 550 USD · From 26 to 50 Place: 400 USD · From 51 to 300 Place: 3-month subscription

> The total approximate retail value ("ARV") of the cash prizes is: 50,000 USD. Prizes equal to, or more than One thousand (1,000) USD will be awarded only via Wire Transfer or PayPal. Prizes less than One thousand (1,000) USD will be awarded via PayPal only.

> A maximum of 300 Entrants will be awarded prizes.

## Q7 — Irregularity note (unchanged since 2026-09-16, re-observed today)

The prize-limitation boilerplate references prize categories that the live prize ladder does not
define (tracked as IR-07):

> In the event an Entrant qualifies for more than one (1) prize (i.e. the Top Trader Prize, MPT Prize or Flawless Run Prize), such Entrant shall be awarded only the single prize with the highest monetary value among the prizes for which they are eligible to receive.

## Manual review

Open https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/ and compare each
section against `data/contest_config.json` (machine-readable transcription) and
`data/contest_universe.json` (full instrument list with caps).
