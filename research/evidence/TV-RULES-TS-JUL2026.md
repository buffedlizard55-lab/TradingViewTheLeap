# Evidence: TV-RULES-TS-JUL2026

- **Publisher:** TradingView, Inc.
- **URL:** https://www.tradingview.com/the-leap/tradestation-july-2026/rules/
- **Title as served:** "The Leap with TradeStation — Terms and Conditions — TradingView"
- **Accessed (UTC):** 2026-09-16
- **Tier:** official_primary

Captured to establish how contest parameters vary between editions, which is the core regime
risk for any strategy carried across editions.

> The start date for trading as part of the Competition is Jul 20, 2026, 08:00 UTC. The end date
> of the trading as part of the Competition is Aug 14, 2026, 08:00 UTC.

> The preset balance size for the Paper Trading Competition Account is 100,000 virtual USD.
> Leverage for futures: 10:1. The commission is $0.85 per contract (futures & options).

> - for NYMEX:CL1! maximum amount for an open position is 1.0
> - for CME:MBT1! maximum amount for an open position is 5.0

> During the Competition, the places in the leaderboard are updated no more than once an hour.

> Prizes are distributed among the first 250 participants in the Competition who received the
> greatest profit in the Paper Trading Competition Account as of the end date of the
> Competition

> - From 51 to 250 Place: 3-month subscription

## Cross-edition parameter delta (computed from the two rules pages)

| Parameter | TradeStation Jul 2026 | AMP Futures Sep 2026 | Change |
|---|---|---|---|
| Balance (virtual USD) | 100,000 | 250,000 | 2.5x |
| Futures leverage | 10:1 | 20:1 | 2x |
| Max notional (balance x leverage) | 1,000,000 | 5,000,000 | 5x |
| NYMEX:CL1! position cap (contracts) | 1.0 | 100.0 | 100x |
| CME:MBT1! position cap (contracts) | 5.0 | 25.0 | 5x |
| Commission | $0.85/contract | not stated on the page section captured | — |
| Prize-paying ranks | 250 | 300 | +50 |

The CL1! cap moving from 1 contract to 100 contracts between two consecutive futures editions is
the clearest available evidence that position limits are not stable and must be re-read from the
live rules page before every contest. See `research/irregularities.json` IR-02.
