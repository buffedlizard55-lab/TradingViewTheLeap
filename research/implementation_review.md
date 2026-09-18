# Three-pass implementation and evidence review

Review date: 2026-09-18. This is an engineering audit, not a certification of every historical price or a promise of contest returns.

## Executive decision

**No current paper orders are released from this page.** Historical candidates are shown for research, but current official-provider coverage and authenticated TradingView comparisons are missing. We did not place trades, create accounts, buy data, obtain another person's API keys, or fabricate exports.

## Official sources checked in this session

| Official source | What it establishes | What it does not establish |
|---|---|---|
| [TradingView The Leap](https://www.tradingview.com/the-leap/) | Current listed edition: AMP Futures, September 1–30, 2026. | That the project's 20 equities are eligible for this futures contest. |
| [Alpaca data plans and authentication](https://docs.alpaca.markets/us/docs/about-market-data-api) | Basic is free; IEX equities coverage; API keys required for equities; key/secret go in request headers. | Full consolidated real-time coverage on Basic, or credentials available in this environment. |
| [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbars) | 15Min, 1Hour, 1Day; pagination; explicit feed/adjustment; inclusive dates. | Live test success without credentials or unrestricted public redistribution rights. |
| [TradingView CSV export](https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/) | Download from Strategy Report; each tab exported separately. | An anonymous export API, CSV cryptographic authenticity, or access to a signed-in account here. |

Existing Yahoo captures are retained as **legacy vendor evidence**, not upgraded to exchange-verified pricing. SHA-256 proves local consistency against a recorded hash, not provider authenticity. Existing relay-based collectors are not used by the new official-provider route.

## Pass 1 — implementation and initial verification

- Added `scripts/fetch_official_bars.py`: direct Alpaca HTTPS only, free IEX feed, explicit split adjustment, complete pagination, per-response SHA-256, local raw payload retention, canonical OHLC validation, no credential logging.
- `make official-bars` chains capture → gap/latency study → paper stock competition using a separate official index. A missing key pair fails closed with exit 2. Actual invocation here produced `data/official_bars/availability.json`: **blocked**. No official pricing results are claimed.
- Added 15-minute stock competition division alongside daily/hourly; shared rules engine and username roster remain in use. Missing symbols are explicit, never replaced with synthetic data.
- Corrected both competition engines: scheduled exits/reversals use the fill bar's open; only terminal liquidation uses its close. Terminal slippage no longer reads future decisions.
- Reran the existing futures season and available stock subset. Results changed following the execution correction; old rankings should not be reused.
- Put a prominent execution-blocked notice at the very top of the existing GitHub Pages executive summary.

## Pass 2 — bugs and assumptions

- Corrected the prior test that expected a scheduled exit at the close instead of the documented open.
- Removed the claim that a one-holding-period arithmetic scenario bounds all competition returns. Repeated trades, shorts and compounding invalidate that claim.
- Reject nonfinite values, Boolean prices, fractional epochs/volume, negative latency and nonintegral latency.
- TradingView imports now explicitly declare unverified origin. Failed imports cannot make the aggregate benchmark “measured.” A plausible filename cannot authenticate a CSV.
- Reject ambiguous intraday timestamp matching and multiple bar intervals instead of choosing the first same-day bar or first available series.
- Refreshed previously stale intelligence artifacts; added futures competition regeneration to the refresh pipeline.

## Pass 3 — requirement recheck

- Added synthetic-only regressions for next-open exits, final-close liquidation, future-decision isolation, bar latency/expiration, timestamp ambiguity, pagination and invalid numbers.
- Corrected study documentation: UTC calendar grouping is not an official exchange-session calendar; DST/overnight coverage matters. Bar-delay sensitivity is not measured network/broker execution latency.
- Kept source metadata on official-index study/competition output rather than falsely labelling all data Yahoo.
- All 65 unit tests pass. Offline verification: 385 checks pass, zero failures; five warnings remain (below). These checks prove configured invariants and reproducibility, not independent price truth.

## Strategy experiment and return objectives

The existing frozen, username-tracked C6–C10 strategies are hypotheses, not known winning edges: blow-off fade, capitulation pyramiding, opening gap-trap reversal, parabolic exhaustion short, and volume-climax reversal. B1 plus S1–S3 are controls. Originality relative to all published strategies is not established.

The corrected legacy futures simulation records some 5x and 10x participant-editions; those are model results on continuous vendor history, **not verified contestant returns or executable fills**. No 20x/50x/100x result is established. The stock run currently contains only ENPH daily history, so it is not a full-pool strategy comparison. Hourly and 15-minute divisions have no captured series. Rankings of a retrospectively selected volatile pool are subject to selection and survivorship bias.

Next experimental pass should freeze usernames/parameters before collecting a disjoint forward season; compare realized return, target-hit frequency and leaderboard percentile versus controls. Keep daily/hourly/15-minute results separate. High deployment is a paper experiment, not permission to ignore sizing, short availability, corporate actions or execution feasibility.

## Remaining blockers / next-session priorities

1. **Official-provider access:** no Alpaca credentials exist in this environment. An authorized Basic account key pair must become available through secure environment/secrets provisioning; never paste keys in chat or commit them. Account registration cannot honestly be completed unattended without the required account-holder authorization. The new adapter has mocked transport tests, not a successful live authenticated integration test.
2. **Full pool:** capture and validate all 20 names at each interval. Verify corporate actions, listing dates, feed omissions and symbol mapping; obtain a second authorized source for spot checks. Split-adjusted historical prices are research-normalized values, not literal historical execution prints.
3. **Official futures intraday data:** the new adapter covers equities only. Existing futures simulation uses continuous daily vendor history; obtain a legitimately free, authorized futures intraday source before claiming intraday futures results.
4. **TradingView benchmark:** no signed-in session or real Strategy Report exports are present. Authentic acquisition cannot be manufactured. When authorized exports become available, record symbol, interval, chart timezone, Pine revision, strategy settings, costs and export provenance. Current importer is diagnostic; full timezone/interval manifest enforcement and one-to-one strategy trade reconciliation remain work.
5. **Session/execution realism:** use an official exchange holiday/early-close calendar, preserve exact fill timestamps, handle simultaneous-symbol buying power consistently, model actual contract rolls/corporate actions, and reconcile tranche-level mark-to-market. Current simulator has simplified margin/accounting, no short-borrow availability model and no sub-bar execution observations.
6. **Warnings:** COMEX:SIC1! capture differs 2.09% from the TradingView snapshot; legacy intraday index lacks vendor source ID and ENPH granularity metadata; 14 stock usernames have no eligible leaderboard coverage; hourly executive division has no captured series.
7. **Publication:** GitHub Pages was already configured from main/root at [the project site](https://buffedlizard55-lab.github.io/TradingViewTheLeap/). This change improves that site, not a newly provisioned Pages service. Preserve provider licensing review before publishing newly acquired raw datasets.

## Reproduce

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/verify.py
python3 scripts/verify.py --self-test
python3 scripts/refresh_artifacts.py
# Only when authorized free-provider credentials exist securely:
make official-bars
```

No claim is made that all original requirements are complete: unavailable official bar coverage and authenticated TradingView exports are material blockers, displayed rather than hidden.
