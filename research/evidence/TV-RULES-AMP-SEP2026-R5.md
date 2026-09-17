# Rules re-verification, fifth pass — The Leap by AMP Futures, September 2026

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- **Accessed (UTC):** 2026-09-17, between roughly 20:58 and 21:02
- **Tier:** official_primary (TradingView, Inc. — the organiser's binding rules text)
- **Result:** **zero rule changes since the 2026-09-16 capture and the three earlier 2026-09-17
  passes.** Every constant in `data/contest_config.json` and every entry of the 94-instrument
  universe in `data/contest_universe.json` was re-read from this page and re-diffed.

## Competition window, registration, eligibility (verbatim)

> begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC

> Registration for the Competition opens at Aug 17, 2026, 13:00 UTC and is open until Sep 23, 2026, 08:00 UTC.

> A user has the right to register for the Competition only once. Registering multiple accounts will lead to disqualification from the Competition.

> are legal residents of a jurisdiction other than the following: Iran, North Korea, Russia, Belarus, Cuba, Crimean, Donetsk, and Luhansk Regions of Ukraine

## Account parameters, ranking, qualification (verbatim)

> The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD. Leverage for futures: 20:1.

> A prerequisite that a Competition participant must fulfill in order to qualify for a prize is trading activity for at least 5 days of the Competition. Trading activity within one day is considered to be actions that resulted in the opening or closing of positions from 00:00:00 to 23:59:59 UTC.

> Access to Paper Trading is prohibited if 60 or more transactions with orders and positions are performed per minute.

> Realized profit/loss for the purposes of the Competition is considered to be profit/loss on closed positions.

> the places in the leaderboard are updated no more than once an hour

> All open positions of the Competition participants will be automatically closed at the end of the Competition Period.

> the account cannot be reset to its initial state

## Prize section (verbatim)

> Prizes are distributed among the first 300 participants in the Competition who received the greatest profit

> 1 Place: 10,000 USD / 2 Place: 7,000 USD / 3 Place: 6,000 USD / 4 Place: 3,500 USD / 5 Place: 2,500 USD / From 6 to 25 Place: 550 USD / From 26 to 50 Place: 400 USD / From 51 to 300 Place: 3-month subscription

> The total approximate retail value ("ARV") of the cash prizes is: 50,000 USD.

> Prizes equal to, or more than One thousand (1,000) USD will be awarded only via Wire Trans

> Prizes must be claimed within fourteen (14) days after the close of the Competition

## §08 instrument list and caps, transcribed in page order

Parsed mechanically by `scripts/verify.py::check_universe_transcription`, which re-reads this block
and requires an exact match (symbol strings and numeric caps, same order, same count) with
`data/contest_universe.json`. Any drift between this transcription and the committed data fails the
build.

> - for CME_MINI:MES1! maximum amount for an open position is 500.0
> - for CME_MINI:MNQ1! maximum amount for an open position is 500.0
> - for CBOT_MINI:MYM1! maximum amount for an open position is 500.0
> - for CME_MINI:M2K1! maximum amount for an open position is 500.0
> - for CME_MINI:ES1! maximum amount for an open position is 100.0
> - for CME_MINI:NQ1! maximum amount for an open position is 100.0
> - for CBOT_MINI:YM1! maximum amount for an open position is 100.0
> - for CME_MINI:RTY1! maximum amount for an open position is 100.0
> - for CME_MINI:EMD1! maximum amount for an open position is 25.0
> - for CME:MNK1! maximum amount for an open position is 5.0
> - for CME:NKD1! maximum amount for an open position is 10.0
> - for CME:BTC1! maximum amount for an open position is 1.0
> - for CME:MBT1! maximum amount for an open position is 25.0
> - for CME:ETH1! maximum amount for an open position is 1.0
> - for CME:MET1! maximum amount for an open position is 25.0
> - for CME:SOL1! maximum amount for an open position is 1.0
> - for CME:MSL1! maximum amount for an open position is 5.0
> - for CME:XRP1! maximum amount for an open position is 1.0
> - for CME:MXP1! maximum amount for an open position is 5.0
> - for CME:6A1! maximum amount for an open position is 25.0
> - for CME:6B1! maximum amount for an open position is 25.0
> - for CME:6C1! maximum amount for an open position is 25.0
> - for CME:6E1! maximum amount for an open position is 25.0
> - for CME:6J1! maximum amount for an open position is 25.0
> - for CME:6N1! maximum amount for an open position is 25.0
> - for CME:6S1! maximum amount for an open position is 25.0
> - for CME_MINI:NES1! maximum amount for an open position is 10.0
> - for CME_MINI:NNQ1! maximum amount for an open position is 10.0
> - for CME_MINI:N2K1! maximum amount for an open position is 10.0
> - for CBOT_MINI:NDOW1! maximum amount for an open position is 10.0
> - for CME_MINI:E71! maximum amount for an open position is 10.0
> - for CME_MINI:J71! maximum amount for an open position is 5.0
> - for CME_MINI:M6A1! maximum amount for an open position is 25.0
> - for CME_MINI:M6B1! maximum amount for an open position is 10.0
> - for CME_MINI:MCD1! maximum amount for an open position is 10.0
> - for CME_MINI:M6E1! maximum amount for an open position is 25.0
> - for CME_MINI:MJY1! maximum amount for an open position is 5.0
> - for CME_MINI:MSF1! maximum amount for an open position is 5.0
> - for NYMEX:CL1! maximum amount for an open position is 100.0
> - for NYMEX_MINI:QM1! maximum amount for an open position is 10.0
> - for NYMEX:MCL1! maximum amount for an open position is 100.0
> - for NYMEX:NG1! maximum amount for an open position is 25.0
> - for NYMEX_MINI:QG1! maximum amount for an open position is 5.0
> - for NYMEX:MNG1! maximum amount for an open position is 10.0
> - for NYMEX:RB1! maximum amount for an open position is 25.0
> - for NYMEX:HO1! maximum amount for an open position is 25.0
> - for COMEX:GC1! maximum amount for an open position is 100.0
> - for COMEX_MINI:QO1! maximum amount for an open position is 10.0
> - for COMEX_MINI:MGC1! maximum amount for an open position is 100.0
> - for COMEX:1OZ1! maximum amount for an open position is 25.0
> - for COMEX:HG1! maximum amount for an open position is 25.0
> - for COMEX_MINI:QC1! maximum amount for an open position is 5.0
> - for COMEX_MINI:MHG1! maximum amount for an open position is 25.0
> - for COMEX:SI1! maximum amount for an open position is 25.0
> - for COMEX_MINI:QI1! maximum amount for an open position is 5.0
> - for COMEX_MINI:SIL1! maximum amount for an open position is 10.0
> - for COMEX:SIC1! maximum amount for an open position is 10.0
> - for NYMEX:PL1! maximum amount for an open position is 25.0
> - for CBOT:UB1! maximum amount for an open position is 100.0
> - for CBOT:MWN1! maximum amount for an open position is 5.0
> - for CBOT:TN1! maximum amount for an open position is 100.0
> - for CBOT:MTN1! maximum amount for an open position is 5.0
> - for CBOT:Z3N1! maximum amount for an open position is 10.0
> - for CBOT:ZB1! maximum amount for an open position is 100.0
> - for CBOT_MINI:30Y1! maximum amount for an open position is 1.0
> - for CBOT:ZF1! maximum amount for an open position is 100.0
> - for CBOT_MINI:5YY1! maximum amount for an open position is 1.0
> - for CBOT:ZN1! maximum amount for an open position is 100.0
> - for CBOT_MINI:10Y1! maximum amount for an open position is 5.0
> - for CBOT:ZQ1! maximum amount for an open position is 25.0
> - for CBOT:ZT1! maximum amount for an open position is 100.0
> - for CBOT_MINI:2YY1! maximum amount for an open position is 1.0
> - for CME:SR11! maximum amount for an open position is 25.0
> - for CME:SR31! maximum amount for an open position is 100.0
> - for CBOT:ZC1! maximum amount for an open position is 25.0
> - for CBOT_MINI:XC1! maximum amount for an open position is 5.0
> - for CBOT_MINI:MZC1! maximum amount for an open position is 5.0
> - for CBOT:ZW1! maximum amount for an open position is 25.0
> - for CBOT_MINI:XW1! maximum amount for an open position is 5.0
> - for CBOT_MINI:MZW1! maximum amount for an open position is 5.0
> - for CBOT:ZS1! maximum amount for an open position is 25.0
> - for CBOT_MINI:XK1! maximum amount for an open position is 5.0
> - for CBOT_MINI:MZS1! maximum amount for an open position is 5.0
> - for CBOT:ZL1! maximum amount for an open position is 25.0
> - for CBOT_MINI:MZL1! maximum amount for an open position is 5.0
> - for CBOT:ZM1! maximum amount for an open position is 25.0
> - for CBOT_MINI:MZM1! maximum amount for an open position is 5.0
> - for CBOT:ZO1! maximum amount for an open position is 5.0
> - for CBOT:ZR1! maximum amount for an open position is 5.0
> - for CME:DC1! maximum amount for an open position is 5.0
> - for CME:LBR1! maximum amount for an open position is 5.0
> - for CME:GF1! maximum amount for an open position is 10.0
> - for CME:HE1! maximum amount for an open position is 25.0
> - for CME:LE1! maximum amount for an open position is 25.0

## Claim-by-claim result

| Claim | Exact excerpt (§) | Result |
|---|---|---|
| Competition window | §04: "begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC" | matches |
| Registration window | §04: "opens at Aug 17, 2026, 13:00 UTC and is open until Sep 23, 2026, 08:00 UTC" | matches |
| Balance / leverage | §08: "250,000 virtual USD. Leverage for futures: 20:1." | matches |
| Qualification | §08: "at least 5 days … 00:00:00 to 23:59:59 UTC" | matches |
| Rate limit | §08: "prohibited if 60 or more transactions … per minute" | matches |
| Ranking metric | §08: "profit/loss on closed positions" | matches |
| Board refresh | §08: "no more than once an hour" | matches |
| No reset | §08: "the account cannot be reset to its initial state" | matches |
| Auto-close | §08: "automatically closed at the end of the Competition Period" | matches |
| Winners | §09: "first 300 participants" | matches |
| Prize ladder | §09: 10,000 / 7,000 / 6,000 / 3,500 / 2,500 / 550 (6–25) / 400 (26–50) / 3-month subscription (51–300) | matches |
| Cash ARV | §09: "50,000 USD" | matches |
| Payment rails | §09: "≥ 1,000 USD … via Wire Trans[fer]" | matches the transcription (wire; the page continues with the PayPal condition below the fold of this capture) |
| Claim deadline | §09: "claimed within fourteen (14) days" | matches |
| Cross-clock check | contest page FAQ: "September 1 at 04:00 EDT to September 30 at 08:00 EDT" vs §04 UTC times | equal (EDT = UTC−4: 04:00 EDT = 08:00 UTC, 08:00 EDT = 12:00 UTC) |
| Universe size | §08 list count vs `data/contest_universe.json` | 94 = 94, caps identical (checked by the verifier) |

Residual uncertainty carried forward (unchanged): the rules state a 5-day qualification but do not
state a commission schedule for the competition account (IR-08), and the prize section refers to
prize categories ("MPT Prize", "Flawless Run Prize") that the published ladder does not define
(IR-07). Neither affects the arithmetic in this repository.
