# Evidence: CME-SOL-GUIDE

- **Publisher:** CME Group Inc.
- **URL:** https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html
- **Title as served:** "The essential guide to Solana futures - CME Group"
- **Accessed (UTC):** 2026-09-16
- **Tier:** official_primary (listing exchange)

## Q1 — Contract sizes

> Solana futures are available in both larger micro-sized versions; SOL (SOL) futures with a
> contract multiplier of 500 SOL and Micro SOL (MSL) futures with a contract multiplier of
> 25 SOL.

Contract specification table, verbatim rows:

| Field | SOL futures | Micro SOL futures |
|---|---|---|
| Rulebook Chapter | CME 439 | CME 440 |
| CME Globex/CME ClearPort Code | SOL | MSL |
| Contract Size | 500 SOL as defined by the CME CF Solana-Dollar Reference Rate (SOLUSD_RR) | 25 SOL as defined by the CME CF Solana-Dollar Reference Rate (SOLUSD_RR) |
| Trading Unit | USD per SOL | (same) |
| Settlement Method | Financial | (same) |
| Minimum Price Fluctuation | Outright: $0.05 per SOL = $25 per contract | Outright: $0.05 per SOL = $1.25 per contract |
| Last Trade Date | 4:00 p.m. London time on the last Friday of the contract month | (same) |
| Final Settlement | cash settlement by reference to the final settlement price, equal to the CME CF Solana-Dollar Reference Rate on the LTD | (same) |

## Q2 — Trading hours

> Globex pre-open: 4:45 p.m. Central Time (CT) - 5:00 p.m. CT
> Globex: Sunday - Friday 5:00 p.m. - 4:00 p.m. CT with a 60-minute break each day beginning at
> 4:00 p.m. CT

## Q3 — Listing schedule

> Monthly contracts listed for six (6) consecutive months, quarterly contracts (Mar, Jun, Sept,
> Dec) listed for four (4) additional quarters and a second Dec contract if only one is listed

## Mapping to the contest universe

TradingView symbols `CME:SOL1!` and `CME:MSL1!` both appear in the live contest's permitted
instrument list (`data/contest_universe.json`), and the Globex codes published here are `SOL` and
`MSL` respectively. That code match is the basis for treating these CME specifications as
authoritative for those two contest instruments.


## Re-verification pass — 2026-09-16 (second pass)

The guide article was not re-fetched this pass; instead the underlying contract spec pages were
captured directly and registered as CME-SPEC-SOL1! (500 SOL, rule CME 439) and CME-SPEC-MSL1!
(25 SOL, rule CME 440), both confirmed live 2026-09-16 (see CME-CONTRACT-SPECS-BATCH2.md).
