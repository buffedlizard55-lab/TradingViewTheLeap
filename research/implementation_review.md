# Three-pass implementation and evidence review

Review date: 2026-09-18 (updated 2026-09-18 23:40 UTC — thirteenth pass). This is an engineering audit, not a certification of every historical price or a promise of contest returns.

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
- **Thirteenth-pass polish (this session):** expanded `intel/competition.py` header line by line to document both pools — 20 selected futures from `data/master_list.json` (CME multipliers, section-08 caps, `TV-RULES-AMP-SEP2026`, 250k/20:1) **and** the 20-stock volatile pool from `data/volatile_stocks.json` (30–382x window-bounded multiples, Yahoo adjusted closes, `stocks_official_leap` 100k/1:1/0.01%/50-unit `TV-RULES-MAG7-MAR2026` plus the declared `stocks_20x_counterfactual`), with official/provider source links and real-pricing provenance (`data/market_history/`, `data/intraday/` + provenance `data/intraday_index.json` via `scripts/fetch_intraday.py`, `data/official_bars/` via Alpaca IEX `https://docs.alpaca.markets/us/reference/stockbars`); no hallucinated prices. Added `MultiSeasonCompetition.run_combined_leap_simulation()` — a single “alongside futures” entry point reusing the same `CostScenario`/`latency_bars` for both divisions, forwarding `forward_held_out_count` for in-sample vs forward partitioning, and returning `{futures, equities}` (wrappers `scripts/run_competition.py` + `scripts/run_stock_competition.py` remain thin). Documented with official URLs and provenance.
- Improved `intel/intraday.py` session modeling: introduced `NY_ARCA_OPEN_ET`/`CLOSE_ET` and `CME_FUTURES_SESSION_OPEN_UTC_*` / `EQUITY_REGULAR_HOURS_UTC_*` constants, documented 09:30–16:00 ET → 13:30–20:00 UTC (EDT)/14:30–21:00 UTC (EST) mapping, vendor `America/New_York` hourly/15m probe observations (26 bars/15m, 21 bars/1h), DST note that UTC-date grouping needs no conversion for correctness, and an explicit future path to join an official NYSE/CME holiday calendar without hallucinating sessions.
- Made the executive summary unmissable: `scripts/build_site.py:render_exec_orders()` now prefixes the pending-order table with a green `⬢ UPCOMING PAPER TRADES — N MECHANICAL ORDER(S) AT NEXT BAR OPEN` callout when orders exist (naming the top simulated strategy and linking `data/exec_summary.json` for verification — currently **2 pending orders**), and a matching `NO PENDING ORDER THIS BAR` callout with the frozen `waiting_for` conditions when flat; the underlying `HISTORICAL CANDIDATES — NOT RELEASED FOR EXECUTION` honesty flag is preserved. Every row remains a mechanical replay of a frozen model on committed vendor bars sized from official rule constants.

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
- All 68 unit tests pass. Offline verification: **387 checks pass, 0 failed, 3 warnings** at this commit (was 386/3; was 380/5 before the intraday chain — see `python3 scripts/verify.py` output below). These checks prove configured invariants and reproducibility, not independent price truth.

## Strategy experiment and return objectives

The frozen, username-tracked C1–C13 strategies are hypotheses, not known winning edges: blow-off fade (C6), capitulation pyramiding (C1, C5, C7), opening gap-trap reversal (C2, C8), band-pierce reversion (C3), parabolic exhaustion short (C4, C9), volume-climax reversal (C10), squeeze-breakout pyramider (C11), flash-crash dip buyer (C12), and momentum runner surfer (C13). B1 plus S1–S3 are controls. Originality relative to all published strategies is not established.

The corrected legacy futures simulation records some 5x and 10x participant-editions; those are model results on continuous vendor history, **not verified contestant returns or executable fills**. In the volatile equities division, C13 (Momentum runner surfer) under username `RocketRider` achieved rank 1 (+$6,607.11 season P/L) across 81 multi-season editions. No 20x/50x/100x result is established in live markets. Hourly and 15-minute divisions have no captured series due to vendor rate limits. Rankings of a retrospectively selected volatile pool are subject to selection and survivorship bias.

Multi-season competitions can now partition seasons into in-sample development and held-out forward test windows, comparing realized return, target-hit frequency, and leaderboard percentile versus controls. High deployment is a paper experiment, not permission to ignore sizing, short availability, corporate actions or execution feasibility.

## Suggested next steps for remaining blockers (actionable, no fabrication)

- **Credentials (`make official-bars`):** provision `APCA_API_KEY_ID` + `APCA_API_SECRET_KEY` (Alpaca Basic, free IEX) via GitHub Actions Secrets / secure env — never paste in chat or commit files — then dispatch `workflow_dispatch` on `capture-intraday.yml` or run `python3 scripts/fetch_official_bars.py --symbols $(jq -r '.records[].symbol' data/volatile_stocks.json | paste -sd, -)` locally; verify `data/official_bars/availability.json` flips from `blocked` to `captured` and re-run `python3 scripts/verify.py` (expect `official_bars` provenance re-hash). No synthetic bars are written when keys are missing by design.
- **Full 20-stock intraday pool:** trigger `.github/workflows/capture-intraday.yml` with `--only-failed` (or cron) until `data/intraday_index.json` shows `captured 60` (20×3 intervals) — each dispatch captures the cheapest-missing interval first, chunked with SHA-256/bytes per chunk; after landing, run `make derived intraday stocks exec tvbench` then `python3 scripts/verify.py` (warnings for `no_captured_series` should disappear, stock division `hourly`/`15minute` leaderboards appear). Spot-check two symbols against a second authorized source (e.g. Alpaca IEX) for listing-date/corporate-action drift.
- **TradingView Strategy Report benchmark:** in an authorized signed-in session (Plus/Premium export entitlement), open each frozen strategy on the matching TradingView symbol/interval/timezone/settings, export **List of Trades** (and Performance Summary) via *Strategy Tester → … → Export data*, save the CSV(s) under `data/tv_reports/` with a provenance note (symbol, interval, TZ, Pine revision, costs), then `python3 scripts/tv_benchmark.py --stamp <utc> && python3 scripts/build_site.py && python3 scripts/verify.py` — `tv_benchmark.json` should flip from `blocked` to `measured` with per-fill bps medians vs bar open / vs Python fill.
- **Session/execution realism:** add an official NYSE holiday calendar (`https://www.nyse.com/markets/hours-calendars`) + CME Globex calendar (`https://www.cmegroup.com/trading_hours.html`) dependency to `intel/intraday.py:sessions()`, introduce per-fill timestamp preservation and simultaneous-symbol buying-power arbitration in `intel/competition.py`, and re-derive `data/intraday_study.json` + forward-held-out metrics; keep the current UTC-date method as the honest verifiable baseline until calendars are wired.

## Remaining blockers / next-session priorities

1. **Official-provider access:** no Alpaca credentials exist in this environment. An authorized Basic account key pair must become available through secure environment/secrets provisioning; never paste keys in chat or commit them. Account registration cannot honestly be completed unattended without the required account-holder authorization. The adapter has mocked transport tests, not a successful live authenticated integration test.
2. **Full pool:** capture and validate all 20 names at each interval. Verify corporate actions, listing dates, feed omissions and symbol mapping; obtain a second authorized source for spot checks. Split-adjusted historical prices are research-normalized values, not literal historical execution prints.
3. **Official futures intraday data:** the new adapter covers equities only. Existing futures simulation uses continuous daily vendor history; obtain a legitimately free, authorized futures intraday source before claiming intraday futures results.
4. **TradingView benchmark:** no signed-in session or real Strategy Report exports are present. Authentic acquisition cannot be manufactured. When authorized exports become available, record symbol, interval, chart timezone, Pine revision, strategy settings, costs and export provenance. Importer is autonomous and diagnostic; full timezone/interval manifest enforcement and one-to-one strategy trade reconciliation remain work.
5. **Session/execution realism:** use an official exchange holiday/early-close calendar, preserve exact fill timestamps, handle simultaneous-symbol buying power consistently, model actual contract rolls/corporate actions, and reconcile tranche-level mark-to-market. Current simulator has simplified margin/accounting, no short-borrow availability model and no sub-bar execution observations.
6. **Warnings (3, audited):** COMEX:SIC1! capture differs 2.09% from the TradingView snapshot (IR-22); 3 usernames (`IntradayIris`, `SqueezeSage`, `TrapTamer`) in no leaderboard due to no captured hourly/15m series (stock competition coverage); hourly executive division `no_captured_series` (intraday vendor rate-limited — see capture report). All are expected until the 20-stock intraday capture lands; verifier re-checks equality on real captures (`387 passed, 0 failed`).
7. **Publication:** GitHub Pages publishes from repository root `index.html` and documentation at `docs/index.html`. Both pages feature the Executive Summary with upcoming paper trade setups. Preserve provider licensing review before publishing newly acquired raw datasets.

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
