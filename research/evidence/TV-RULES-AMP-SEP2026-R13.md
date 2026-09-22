# TradingView official rules capture — AMP Futures September 2026, pass 13 (R13)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22 ~23:00, twenty-second-pass research session (all five page
  chunks fetched and read line by line)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** thirteenth re-verification of rule constants, the section-08 94-instrument universe
  and per-instrument caps, and the section-09 prize ladder
- **Status:** official primary capture; point-in-time text, may change upstream

## Verbatim quotations (line-by-line verified against the page text)

Section 04 — competition period and registration:

> begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC

> Registration for the Competition opens at Aug 17, 2026, 13:00 UTC and is open until Sep 23,
> 2026, 08:00 UTC.

Section 05 — eligibility (free-plan clause as displayed):

> or users on a free plan (other than Essential, Plus, Premium, or Ultimate subscription types)

Section 08 — account presets, activity, ranking:

> The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD.
> Leverage for futures: 20:1.

> A prerequisite that a Competition participant must fulfill in order to qualify for a prize is
> trading activity for at least 5 days of the Competition.

> Access to Paper Trading is prohibited if 60 or more transactions with orders and positions
> are performed per minute.

> A participant's place during the Competition and at the end of the Competition is determined
> based on the realized profit/loss on the Competition account.

> All open positions of the Competition participants will be automatically closed at the end of
> the Competition Period.

Section 09 — prize ladder and payment rail:

> Prizes are distributed among the first 300 participants in the Competition

> - 1 Place: 10,000 USD
> - 2 Place: 7,000 USD
> - 3 Place: 6,000 USD
> - 4 Place: 3,500 USD
> - 5 Place: 2,500 USD
> - From 6 to 25 Place: 550 USD
> - From 26 to 50 Place: 400 USD
> - From 51 to 300 Place: 3-month subscription

> The total approximate retail value (" **ARV**") of the cash prizes is: 50,000 USD. Prizes
> equal to, or more than Six hundred (600) USD will be awarded only via Wire Transfer

> In the event an Entrant qualifies for more than one (1) prize (i.e. the Top Trader Prize, MPT
> Prize or Flawless Run Prize), such Entrant shall be awarded only the single prize with the
> highest monetary value among the prizes for which they are eligible to receive.

> Prizes must be claimed within fourteen (14) days after the close of the Competition,
> otherwise, they will be forfeited.

## Section-08 universe transcription (94 instruments, page listing order)

Diff protocol: parse the block below (symbol = cap) and compare (symbol, cap, order) against
`data/contest_universe.json`. Expected: 94/94 symbols, 94/94 caps, identical order, 0 equities.
Executed in this session: **94/94 symbols + 94/94 caps + identical order, 0 equities — MATCH.**

```
CME_MINI:MES1!=500.0
CME_MINI:MNQ1!=500.0
CBOT_MINI:MYM1!=500.0
CME_MINI:M2K1!=500.0
CME_MINI:ES1!=100.0
CME_MINI:NQ1!=100.0
CBOT_MINI:YM1!=100.0
CME_MINI:RTY1!=100.0
CME_MINI:EMD1!=25.0
CME:MNK1!=5.0
CME:NKD1!=10.0
CME:BTC1!=1.0
CME:MBT1!=25.0
CME:ETH1!=1.0
CME:MET1!=25.0
CME:SOL1!=1.0
CME:MSL1!=5.0
CME:XRP1!=1.0
CME:MXP1!=5.0
CME:6A1!=25.0
CME:6B1!=25.0
CME:6C1!=25.0
CME:6E1!=25.0
CME:6J1!=25.0
CME:6N1!=25.0
CME:6S1!=25.0
CME_MINI:NES1!=10.0
CME_MINI:NNQ1!=10.0
CME_MINI:N2K1!=10.0
CBOT_MINI:NDOW1!=10.0
CME_MINI:E71!=10.0
CME_MINI:J71!=5.0
CME_MINI:M6A1!=25.0
CME_MINI:M6B1!=10.0
CME_MINI:MCD1!=10.0
CME_MINI:M6E1!=25.0
CME_MINI:MJY1!=5.0
CME_MINI:MSF1!=5.0
NYMEX:CL1!=100.0
NYMEX_MINI:QM1!=10.0
NYMEX:MCL1!=100.0
NYMEX:NG1!=25.0
NYMEX_MINI:QG1!=5.0
NYMEX:MNG1!=10.0
NYMEX:RB1!=25.0
NYMEX:HO1!=25.0
COMEX:GC1!=100.0
COMEX_MINI:QO1!=10.0
COMEX_MINI:MGC1!=100.0
COMEX:1OZ1!=25.0
COMEX:HG1!=25.0
COMEX_MINI:QC1!=5.0
COMEX_MINI:MHG1!=25.0
COMEX:SI1!=25.0
COMEX_MINI:QI1!=5.0
COMEX_MINI:SIL1!=10.0
COMEX:SIC1!=10.0
NYMEX:PL1!=25.0
CBOT:UB1!=100.0
CBOT:MWN1!=5.0
CBOT:TN1!=100.0
CBOT:MTN1!=5.0
CBOT:Z3N1!=10.0
CBOT:ZB1!=100.0
CBOT_MINI:30Y1!=1.0
CBOT:ZF1!=100.0
CBOT_MINI:5YY1!=1.0
CBOT:ZN1!=100.0
CBOT_MINI:10Y1!=5.0
CBOT:ZQ1!=25.0
CBOT:ZT1!=100.0
CBOT_MINI:2YY1!=1.0
CME:SR11!=25.0
CME:SR31!=100.0
CBOT:ZC1!=25.0
CBOT_MINI:XC1!=5.0
CBOT_MINI:MZC1!=5.0
CBOT:ZW1!=25.0
CBOT_MINI:XW1!=5.0
CBOT_MINI:MZW1!=5.0
CBOT:ZS1!=25.0
CBOT_MINI:XK1!=5.0
CBOT_MINI:MZS1!=5.0
CBOT:ZL1!=25.0
CBOT_MINI:MZL1!=5.0
CBOT:ZM1!=25.0
CBOT_MINI:MZM1!=5.0
CBOT:ZO1!=5.0
CBOT:ZR1!=5.0
CME:DC1!=5.0
CME:LBR1!=5.0
CME:GF1!=10.0
CME:HE1!=25.0
CME:LE1!=25.0
```

## Line-by-line findings (constant-by-constant)

| Rule constant | Observed at R13 | Repository transcription | Verdict |
|---|---|---|---|
| §04 competition window | Sep 1 08:00 UTC → Sep 30 12:00 UTC | `contest_config.json` same | MATCH |
| §04 registration close | Sep 23, 2026, 08:00 UTC | `contest_config.json` same | MATCH |
| §05 eligibility | 18+, paid/trial/former-paid/free-plan users, territory exclusions | unchanged vs R10 | MATCH (no change) |
| §08 balance | 250,000 virtual USD | same | MATCH |
| §08 leverage | futures 20:1 | same | MATCH |
| §08 minimum activity | 5 days (00:00:00–23:59:59 UTC) | same | MATCH |
| §08 rate limit | 60 transactions/minute | same | MATCH |
| §08 ranking | realized P/L on closed positions; auto-close at end | same | MATCH |
| §08 universe | 94 futures, 0 equities, caps above | `contest_universe.json` 94/94 | MATCH |
| §09 recipients | first 300 | `maximum_prize_recipients` 300 | MATCH |
| §09 cash ladder | 1:10,000 · 2:7,000 · 3:6,000 · 4:3,500 · 5:2,500 · 6–25:550 · 26–50:400 | `prize_tiers` same | MATCH |
| §09 subscriptions | 51–300: 3-month | same | MATCH |
| §09 cash ARV | 50,000 USD | `cash_prize_total_arv_usd` 50,000 | MATCH |
| §09 payment rail | ≥600 USD wire-only | frozen at the same R10 reading (IR-29 open) | unchanged vs R10; IR-29 stands |
| §09 claim window | 14 days | same | MATCH |

## Irregularities confirmed (not newly created)

- **IR-29 (open, flagged for manual review):** the payment-rails text remains "≥ Six hundred
  (600) USD … Wire Transfer" — `data/contest_config.json` stays frozen at this reading.
- **IR-36 (open):** this rules page also names an "MPT Prize" and "Flawless Run Prize" in the
  Prize Limitation clause that the document never defines — same undefined-prize pattern as
  the Magnificent Seven rules.

## No-hallucination check

- Every quotation above is copied verbatim from the five fetched rules chunks (Sep 22 session).
- The 94-line universe block preserves the page's listing order and was machine-diffed against
  `data/contest_universe.json` in this session (94/94 + caps + order, 0 equities).
- No repository transcription was modified by this capture; changes would be flagged, not
  silently applied.
