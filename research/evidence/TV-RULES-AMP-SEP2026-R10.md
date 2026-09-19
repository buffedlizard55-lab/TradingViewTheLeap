# TradingView official rules re-verification — AMP Futures September 2026, pass 10 (R10)

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-19, approximately 18:15–18:45 UTC (5 chunks re-read live)
- **Tier:** official_primary (TradingView, Inc., contest organiser)
- **Use:** re-verification of §08 instrument universe + caps, §09 prize ladder + ARV, and the
  transcribed constants in `data/contest_config.json` / `data/contest_universe.json`
- **Status:** official primary capture; see flagged payment-rails delta (IR-29) below

## Verdict

| Check | Result |
|---|---|
| §08 instrument universe (§08 list order) | 94/94 symbols, same listing order as `data/contest_universe.json` — MATCH |
| §08 per-instrument caps | 94/94 caps identical — MATCH (machine diff, 0 missing / 0 extra / 0 changed) |
| Equities in §08 universe | 0 — MATCH (futures-only edition) |
| §09 prize ladder | 1st $10,000 / 2nd $7,000 / 3rd $6,000 / 4th $3,500 / 5th $2,500 / 6–25 $550 / 26–50 $400 / 51–300 3-month subscription — MATCH |
| §09 cash ARV | $50,000 — MATCH |
| §09 prize-claim window | 14 days — MATCH |
| §08 balance / leverage | 250,000 virtual USD / 20:1 — MATCH |
| §08 activity / ranking / updates | 5 days (00:00–23:59 UTC open/close) / realised P/L on closed positions / ≤ once per hour — MATCH |
| §08 auto-close / announce / delete / reset | end-of-period auto-close / results ≤ 5 working days / accounts deleted after 30 days / no reset — MATCH |
| §08 script/rate clause | 60+ transactions per minute prohibited; 1-hour+ Paper Trading ban warning — MATCH |
| §04 dates | Sep 1 08:00 UTC → Sep 30 12:00 UTC; registration Aug 17 13:00 UTC → Sep 23 08:00 UTC — MATCH |
| §05 eligibility | 18+, paid/trial/former-paid/free-plan users, Eligible Territory exclusions — MATCH (no change observed) |
| §06 real-time data | paid/trial/former-paid get Competition Real-Time Data ≤1h after registration; other free users must subscribe/trial (granted ≤24h); terminated after competition — MATCH |
| §09 payment rails | **DELTA — see IR-29.** Page now reads “Six hundred (600) USD … only via Wire Transfer / … via PayPal” where R3–R6 read “One thousand (1,000) USD … Wire Transfer or PayPal / … via PayPal only”. `data/contest_config.json` is NOT changed pending manual review. |

## Verbatim §08 / §09 quotations (this pass)

> Only the following instruments are available for trading within the Competition:
> (94 symbols, listed in §08 order in the machine-readable block below)

> If the execution of orders can lead to the appearance of open positions with an amount
> exceeding the maximum set by the Terms and Conditions, then such orders will be rejected
> by the system.

> The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD.
> Leverage for futures: 20:1.

> A prerequisite that a Competition participant must fulfill in order to qualify for a prize
> is trading activity for at least 5 days of the Competition. Trading activity within one day
> is considered to be actions that resulted in the opening or closing of positions from
> 00:00:00 to 23:59:59 UTC.

> Access to Paper Trading is prohibited if 60 or more transactions with orders and positions
> are performed per minute.

> A participant's place during the Competition and at the end of the Competition is
> determined based on the realized profit/loss on the Competition account. Realized
> profit/loss for the purposes of the Competition is considered to be profit/loss on closed
> positions. During the Competition, the places in the leaderboard are updated no more than
> once an hour. All open positions of the Competition participants will be automatically
> closed at the end of the Competition Period.

> Prizes are distributed among the first 300 participants in the Competition who received the
> greatest profit in the Paper Trading Competition Account as of the end date of the
> Competition, taking into account the results of automatically closed positions.

> - 1 Place: 10,000 USD / - 2 Place: 7,000 USD / - 3 Place: 6,000 USD /
> - 4 Place: 3,500 USD / - 5 Place: 2,500 USD / - From 6 to 25 Place: 550 USD /
> - From 26 to 50 Place: 400 USD / - From 51 to 300 Place: 3-month subscription

> The total approximate retail value ("ARV") of the cash prizes is: 50,000 USD.

> Prizes equal to, or more than Six hundred (600) USD will be awarded only via Wire Transfer
> (chunk 2) … Prizes less than Six hundred (600) USD will be awarded via PayPal. No
> alternative payment methods will be accepted or offered. (chunk 3)

> Prizes must be claimed within fourteen (14) days after the close of the Competition,
> otherwise, they will be forfeited.

> The Competition accounts will be automatically deleted after 30 days from the date of the
> end of the Competition, without notifying the participants.

> The results of the Competition will be announced no later than up to five working days
> from the end date of the Competition.

## Machine-readable §08 universe + caps (this pass, §08 order)

```text
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

Diff protocol: parse the block above and compare (symbol, cap, order) against
`data/contest_universe.json`. Expected: 94/94 symbols, 94/94 caps, identical order,
0 equities. Any deviation fails the pass and is logged as an irregularity.

## No-hallucination check

- Every quotation above is copied verbatim from the 5 fetched rules chunks (Sep 19 session).
- The 94-line universe block preserves the page's listing order (equity/micro-FX/energy/
  metals/rates/ags/livestock grouping).
- The §09 payment-rails delta is quoted from both chunks (2 and 3) and flagged as IR-29
  instead of being silently transcribed into `data/contest_config.json`.
- URL for rules: https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
