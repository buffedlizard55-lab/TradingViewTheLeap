# Rules re-verification, fourth pass — The Leap by AMP Futures, September 2026

- **URL:** https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- **Accessed (UTC):** 2026-09-17 (~19:02–19:07)
- **Tier:** official_primary
- **Result:** **zero rule changes since the 2026-09-16 and earlier 2026-09-17 passes.** All
  constants in `data/contest_config.json` and the universe in `data/contest_universe.json`
  re-verified line by line.

## Selected verbatim excerpts (manual review against the live URL)

> begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC

> The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD. Leverage for futures: 20:1.

> A user has the right to register for the Competition only once. Registering multiple accounts will lead to disqualification from the Competition.

> From 26 to 50 Place: 400 USD

> From 51 to 300 Place: 3-month subscription

> Realized profit/loss for the purposes of the Competition is considered to be profit/loss on closed positions.

## Programmatic diff of §08 (instrument list and caps)

The §08 list was transcribed from the live page during this pass and diffed in-process against
`data/contest_universe.json`:

- 94 instruments fetched == 94 instruments stored; **0 differences**; **0 equity instruments**
  (futures only — IR-01 still stands for the "volatile stocks" brief).
- All 94 `max_open_position_contracts` values identical.
- Order of listing identical (COS orders the pairs the same way the rules list them).

## Claim-by-claim (selected verbatim excerpts)

| Claim | Exact excerpt (§) | Result |
|---|---|---|
| Competition window | §04: “begins at Sep 1, 2026, 08:00 UTC and ends at Sep 30, 2026, 12:00 UTC” | matches |
| Registration closes | §04: “Registration for the Competition opens at Aug 17, 2026, 13:00 UTC and is open until Sep 23, 2026, 08:00 UTC” | matches |
| Multiple accounts | §05: “Registering multiple accounts will lead to disqualification from the Competition.” | matches |
| Balance / leverage | §08: “The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD. Leverage for futures: 20:1.” | matches |
| Qualification | §08: “trading activity for at least 5 days of the Competition … actions that resulted in the opening or closing of positions from 00:00:00 to 23:59:59 UTC” | matches |
| Rate limit | §08: “Access to Paper Trading is prohibited if 60 or more transactions with orders and positions are performed per minute.” | matches |
| Ranking metric | §08: “determined based on the realized profit/loss … Realized profit/loss … is considered to be profit/loss on closed positions” | matches |
| Board refresh | §08: “the places in the leaderboard are updated no more than once an hour” | matches |
| Auto-close | §08: “All open positions of the Competition participants will be automatically closed at the end of the Competition Period.” and counted in final places | matches |
| Winners | §09: “Prizes are distributed among the first 300 participants … taking into account the results of automatically closed positions” | matches |
| Prize ladder | §09: “1 Place: 10,000 USD … 2 Place: 7,000 … 3 Place: 6,000 … 4 Place: 3,500 … 5 Place: 2,500 … From 6 to 25 Place: 550 … From 26 to 50 Place: 400 … From 51 to 300 Place: 3-month subscription” | matches |
| ARV | §09: ‘The total approximate retail value (“ARV”) of the cash prizes is: 50,000 USD’ | matches |
| Payment rails | §09: “Prizes equal to, or more than One thousand (1,000) USD … Wire Transfer or PayPal. Prizes less than One thousand (1,000) USD … via PayPal only.” | matches |
| Tie rule | §09: equal profit ⇒ adjacent prizes “combined and divided in equal shares … A maximum of 300 Entrants will be awarded prizes.” | matches |
| Identity checks | §09: “TradingView may withhold delivery of a Prize until it has received such evidence from a winner” | matches (IR-16 stands: unattended prize collection cannot be promised) |
| Disqualification | §09: “TradingView reserves the right to disqualify and prosecute … any Entrant or winner who it suspects has tampered” | matches — relevant to the capture-4 board decrease (IR-23/H20) |

## Boilerplate sections (chunk 4) — verified this pass, two clauses are strategy-relevant

> 16. DISQUALIFICATION/FORCE MAJEURE: TradingView reserves the right, at any time and in its sole discretion, to disqualify and/or deem ineligible to participate in this Competition, any individual who TradingView believes to be: (A) tampering with the entry process … (C) acting in bad faith, an unsportsmanlike or disruptive manner

§16 is the explicit at-any-time disqualification clause — consistent with the capture-4 board
decrease recorded in IR-23/H20. §17 is equally binding on every projection this project makes:

> 17. GENERAL CONDITIONS: TradingView reserves the right to shorten, extend, modify, or cancel the Competition, in its sole discretion, at any time and without notice, even though such action may affect your ability to win a prize.

Remaining chunk-4 sections were read and carry no rule constants: §18 severability, §19 disputes
(confidential binding JAMS arbitration in New York, California law, 1-year limitation), §20
results location, §21 no social-media affiliation.

## Notes

- Retrieval produced 5 page chunks; §§01–07 in chunk 0, §08 in chunks 1–2, §09–15 in chunks 2–3,
  §§16–21 in chunk 4. Every chunk was re-read during this pass.
- No new sections, no edits to dates/caps/prizes versus the 16:55 UTC pass on the same day.
- The one-prize-per-Entrant clause and prize-limitation clause are restated; they constrain
  multi-account strategies to exactly zero benefit and full disqualification risk (§05, §16).
