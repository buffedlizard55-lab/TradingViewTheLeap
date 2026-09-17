# TradingView The Leap — evidence-first research lab

A reproducible research layer for TradingView's **The Leap** paper-trading competition. The project
separates official contest facts, historical champion outcomes, vendor-sourced market moves,
capacity arithmetic, and independently simulated strategy verdicts. It does not present a backtest
as a platform result, and it never mixes real historical market returns with simulated competition
returns.

**GitHub Pages:** https://buffedlizard55-lab.github.io/TradingViewTheLeap/

## Live-edition facts

Snapshot: **2026-09-16T21:39:34Z**. The official edition is **The Leap by AMP Futures — September
2026**.

| Fact | Verified value | Manual review |
|---|---:|---|
| Competition | Sep 1 08:00 UTC → Sep 30 12:00 UTC | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Registration closes | Sep 23 08:00 UTC | [Official rules](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Starting balance | 250,000 virtual USD | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Futures leverage | 20:1 | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Eligible instruments | 94 futures; 0 single-stock equities | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Ranking | Realized P/L on closed positions; end-of-contest auto-close counts | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Qualification | Activity on at least 5 UTC days | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| Prizes | Up to 300 recipients; public leaderboard exposes only ranks 1–250 | [Rules §09](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) · [contest](https://www.tradingview.com/the-leap/amp-futures-september-2026/) |

The live page displayed **93,527 participants**. Captured public frontiers were rank 1
**+$2,303,725.00 (+921.49%)**, rank 50 **+$1,144,096.25 (+457.64%)**, rank 100
**+$960,203.50 (+384.08%)**, and rank 250 **+$623,689.00 (+249.48%)**. These are moving snapshots,
not final thresholds and not prize guarantees. See [`data/live_contest_snapshot.json`](data/live_contest_snapshot.json).

### Frontier tracker

A second official capture on **2026-09-17 ~00:30 UTC** (93,702 participants) moved the mid-board
frontier: rank 50 **+$1,172,236.00 (+468.89%)**, rank 100 **+$971,231.00 (+388.49%)**, while rank 1
and rank 250 were unchanged. Every capture is stored with its official URL in
[`data/frontier_history.json`](data/frontier_history.json); the verifier re-derives all deltas and
percentage arithmetic and requires each capture's values to be internally consistent
(`frontier.*` checks). The raw leaderboard HTML of each capture is archived under
`artifact_pages/` for manual review.

## What the evidence says

1. **Explosive simulated outcomes have occurred.** The captured official completed-champion sample
   includes a maximum of **53.2072x** and at least one completed futures outcome above 10x.
2. **No captured official contest result reaches 100x.** This means 100x is unattested in this
   sample, not impossible and not beyond a proven ceiling.
3. **The live edition has no single stocks.** The 20-stock module is historical reference for a
   future stock edition, not a live tradable list.
4. **All three pre-registered strategies are refuted on daily bars.** The independent walk-forward
   simulation (below) produced a **$0.0 pooled median net profit** for S1, S2 and S3 across 210
   windows, with concentration and sensitivity failures on top (H14–H16).
5. **Volatility alone cannot rank instruments.** Dollar P/L also depends on price, multiplier,
   contracts, the rules cap, and buying power. The volatility screen (below) ranks captured symbols
   by historical 30-day moves versus the move each needs to reach the captured rank-250 frontier
   (H17).
6. **Realizing a position does not create profit.** It moves open P/L into the realized ranking
   metric. The official rules automatically close remaining positions at the end.
7. **Edition parameters are not stable.** Balance, leverage, symbols, caps, and prize ranks differ
   between captured editions; every strategy must be revalidated against the current rules.

All verdicts and evidence lines are in
[`research/hypotheses/hypotheses.json`](research/hypotheses/hypotheses.json).

## Intelligence layer

An offline, pure-stdlib Python engine (`intel/`) plus two orchestrators turn committed vendor data
into reproducible, verifiable artifacts. Nothing is trusted until `scripts/verify.py` re-derives it.

### Market-data pipeline

`scripts/fetch_market_data.py` (run in GitHub Actions, `.github/workflows/capture-market-data.yml`)
fetches 2 years of daily bars (2024-09-17 → 2026-09-18) for the 20 selected futures from the Yahoo
Finance chart endpoint, with a relay-transport fallback for datacenter-IP blocks (IR-15). It writes
raw vendor bytes per symbol plus [`data/market_history_index.json`](data/market_history_index.json)
(SHA-256, endpoint, transport, session counts per record). Captured 2026-09-17 over four automated
passes: **10 symbols with 503 sessions** (CL1!, QM1!, RB1!, HO1!, NG1!, SI1!, SIL1!, PL1!, NQ1!,
ETH1!), **8 newly listed single-session symbols** (excluded, IR-16), and **2 persistent relay
failures** (BTC1!, MXP1!, IR-19). Captures are `market_data_vendor` tier, spot-verified in-session and
cross-checked against the official TradingView quote snapshot (warn >2%, fail >15%); see
[`research/evidence/YAHOO-FUTURES-CAPTURE-2026-09-17.md`](research/evidence/YAHOO-FUTURES-CAPTURE-2026-09-17.md).

### Independent strategy simulation

`scripts/run_backtests.py` simulates the three pre-registered models per
[`research/strategy/testing-plan.md`](research/strategy/testing-plan.md): non-overlapping 30-day
walk-forward windows with a fresh $250,000 account each, 20:1 leverage, whole contracts,
next-open fills, three cost scenarios (zero / $1.50+5% ATR / $2.50+10% ATR), a frozen sensitivity
grid, bootstrap confidence intervals (seed 1729), and pre-registered concentration checks.
Results: [`data/backtest_results.json`](data/backtest_results.json).

| Model | Verdict | Zero-cost median | Windows | Trades | ≥5x windows |
|---|---|---:|---:|---:|---:|
| S1 Donchian trend breakout | **refuted** | $0.0 | 210 | 70 | 3 (best 7.39x, single trade) |
| S2 EMA impulse continuation | **refuted** | $0.0 | 210 | 28 | 0 (best 1.87x) |
| S3 Bollinger squeeze release | **refuted** | $0.0 | 210 | 4 | 0 (best 1.16x) |

Every per-symbol median is $0.0; means are outlier-driven (S1's three ≥5x windows are single-trade
Donchian breakouts in silver and crude); S2's mean is negative in all cost scenarios; S3 fires too
rarely on daily bars for any confidence statement. These are **independent daily-bar simulations,
not TradingView Strategy Reports** — platform validation remains `not_run` because this environment
has no authenticated TradingView chart session or Pine compiler.

### Volatility screen

`data/volatility_intelligence.json` ranks each captured symbol by annualized volatility, ATR(14),
best 30-day up/down moves, largest overnight gap, and — the key ratio — the favorable move needed
to reach the captured rank-250 frontier ($623,689) from each symbol's modeled initial notional,
versus the best 30-day move actually delivered in the 2-year window. Full-size CL1!/HO1!/SI1!
needed only ~12.7–12.9% and delivered 58–78%; NG1! (87.5% annualized, best 30-day +140.4%) needed
86.3% because its margin-limited notional is small; QM1! and ETH1! are structurally priced out
(needed +121.8% / +517.7%). This is simulation arithmetic on vendor data, not a prediction.

## Return datasets: keep these separate

### Simulated contest-account returns

[`data/verified_explosive_returns.json`](data/verified_explosive_returns.json) contains 15 completed
#1 records from TradingView's official landing page plus one timestamped in-progress row. The
multiple is recomputed as:

```text
competition return multiple = 1 + published net-profit percentage / 100
```

### Historical stock market moves

[`data/volatile_stocks.json`](data/volatile_stocks.json) contains 20 trough-to-later-peak
**adjusted-close** ratios from exact Yahoo Finance API windows. Yahoo is a commercial market-data
vendor, not an exchange, regulator, or contest organiser. Every record is explicitly
window-bounded, and the verifier recomputes:

```text
historical market multiple = archived peak adjusted close / archived trough adjusted close
```

Both exact trough and peak endpoint URLs are available in each data row, the source registry, and
the Pages table. The data does not claim all-time extrema or a realizable strategy return.

## Repository map

| Path | Purpose |
|---|---|
| `data/contest_config.json` | Central rulebook transcription: dates, balance, leverage, ranking, limits, prizes |
| `data/contest_universe.json` | All 94 permitted symbols and position caps |
| `data/live_contest_snapshot.json` | Timestamped leaderboard rows and official TradingView display-price inputs |
| `data/frontier_history.json` | Timestamped rank-1/50/100/250 frontier captures with deltas |
| `data/initial_capacity.json` | Derived initial-balance capacity screen |
| `data/master_list.json` / `.csv` | 20 selected futures with official multipliers and rule caps |
| `data/market_history/` + `data/market_history_index.json` | Raw vendor daily-bar captures (SHA-256 indexed, relay transport documented) |
| `data/backtest_results.json` | Independent walk-forward simulation results for S1/S2/S3 (verdicts, costs, sensitivity, bootstrap) |
| `data/volatility_intelligence.json` | Per-symbol volatility and rank-250 requirement screen |
| `data/verified_explosive_returns.json` | Official historical champion results plus one live snapshot |
| `data/volatile_stocks.json` | Vendor-tier, recomputable, window-bounded stock moves |
| `intel/` | Pure-stdlib simulation engine: data loading, Pine-faithful indicators, strategy signals, backtest, walk-forward |
| `research/hypotheses/hypotheses.json` | Falsifiable research claims, tests, verdicts, and evidence |
| `research/strategy/` | Candidate models, Pine implementation, and test protocol |
| `research/irregularities.json` | Open, confirmed, and resolved source/data issues |
| `research/sources/sources.json` | Source registry with allowed uses and manual-review links |
| `research/evidence/` | Captured quotations and endpoint records |
| `artifact_pages/` | Raw archived official pages (leaderboard HTML per capture) |
| `scripts/verify.py` | Offline provenance, arithmetic, endpoint, backtest-audit, and mutation checks |
| `scripts/run_backtests.py` | Deterministic backtest/volatility orchestrator (`--stamp` for byte reproducibility) |
| `scripts/fetch_market_data.py` | CI-side vendor capture with integrity checks and relay fallback |
| `scripts/build_site.py` | Deterministic root `index.html` generator for legacy GitHub Pages |

## Verify and build

```bash
python3 scripts/verify.py
python3 scripts/verify.py --self-test
python3 scripts/build_site.py
python3 -m py_compile scripts/verify.py scripts/build_site.py scripts/run_backtests.py
```

Current audit result:

```text
verify:    311 passed, 0 failed, 2 warnings
self-test: 347 passed, 0 failed, 0 warnings
```

The two verify warnings are recorded for review: a 2.09% vendor-vs-quote delta on the newly listed
COMEX:SIC1!, and the three symbols excluded by persistent relay failures (IR-19).

The mutation self-test proves checks fail when source endpoints, rule constants, leaderboard
arithmetic, capacity math, strategy result state, multipliers, return ratios, counts, stock
windows, capture digests, backtest constants, verdict/status sync, or determinism are corrupted.
The verifier also re-runs the backtest orchestrator with a pinned stamp and requires byte-identical
artifacts. CI rebuilds the site and fails if committed `index.html` is stale.

## Important limitations and remaining work

- **TradingView platform validation is still `not_run`.** The daily-bar simulation is independent
  arithmetic, not a TradingView Strategy Report; the platform requires an authenticated chart
  session this environment does not have.
- **S1/S2/S3 are refuted on daily bars only.** Intraday bars could change signal frequency
  (S3 in particular fires too rarely on daily bars); no licensed intraday history is stored here.
- **BTC1! and MXP1! have no captured history** (persistent relay failures across four passes, IR-19); the panel is
  10 of 20 selected symbols. Eight more symbols are newly listed on the vendor with a single
  session (IR-16).
- The verifier is offline. Public pages were captured through the research environment and can
  change later; rerun the source-capture process for a new snapshot.
- Live leaderboard and quote values are asynchronous point-in-time displays, not executable prices;
  rank 1/250 were frozen between the two captures while the mid-board moved (IR-18).
- The public page does not show ranks 251–300, so the actual last-prize frontier is unavailable.
- Champion summaries contain no trade history; they cannot reveal a winning strategy.
- Continuous front-month vendor series are unadjusted for rolls; roll gaps can create artificial
  signals (see the assumptions list in `data/backtest_results.json`). A licensed CME
  settlement-based continuous series is a stronger basis for strategy tests.
- The official Paper Trading help page's displayed short-futures formula omits point value even
  though its worked example uses it; this is flagged as `IR-14`.
- Forward-test window before contest end (2026-09-30 12:00 UTC) is unused; registration closes
  2026-09-23 08:00 UTC and qualification needs 5 active UTC days.

This project concerns virtual competition money. It is not investment advice or a forecast, and
historical market moves or simulated contest results do not imply future performance.
