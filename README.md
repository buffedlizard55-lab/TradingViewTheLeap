# TradingView The Leap — evidence-first research lab

A reproducible research layer for TradingView's **The Leap** paper-trading competition. The project
separates official contest facts, historical champion outcomes, vendor-sourced market moves,
capacity arithmetic, and independently simulated strategy verdicts. It does not present a backtest
as a platform result, and it never mixes real historical market returns with simulated competition
returns.

**GitHub Pages:** https://buffedlizard55-lab.github.io/TradingViewTheLeap/

## September 17 fourth pass: board-correction finding + fourth frontier capture

On 2026-09-17 (~19:04 UTC) all three official pages were fetched again (~2.1 hours after the
16:56 UTC pass) and verified line by line ([evidence: contest](research/evidence/TV-CONTEST-AMP-SEP2026-2026-09-17-R4.md) ·
[rules](research/evidence/TV-RULES-AMP-SEP2026-R4.md) · [landing](research/evidence/TV-THELEAP-LANDING-R4.md)):

- **The displayed frontier can fall.** Rank 50 moved from +$1,247,897.00 (16:56 UTC) to
  **+$1,244,313.50** (~19:04 UTC), while the exact capture-3 rank-50 row re-appeared verbatim at
  rank 49 and ranks 100/250 rose ($12,309.65 / $2,235.50). Realized P/L on closed positions cannot
  shrink for a still-registered account; the net effect is exactly one fewer row ahead of the
  tracked row, and the most parsimonious reading is one removal among rows ranked 1–48
  (disqualification or correction — the rules reserve at-any-time disqualification rights at
  §05/§09/§16 and the official pages publish no board-change log). Recorded as **IR-23** and
  tested as hypothesis **H20**
  (supported). Practical consequence: no captured frontier value is a ratchet floor, in either
  direction.
- **New hypothesis H21 (supported):** full-window frontier accumulation rates are quantified —
  $141,857.07/day (rank 1), $75,591.10/day (rank 50), $61,490.53/day (rank 100) and
  $39,930.78/day (rank 250) over the 16.4611 elapsed days. Constant-rate end-of-contest scenarios
  are pure arithmetic, **not forecasts** (e.g. rank 250 ≈ $1,164,647.74 at the 2026-09-30 12:00
  UTC deadline if its average rate persisted, which H18/H20 show it will not do smoothly).
- **Rules re-verified for the fourth time, zero changes:** all rule constants and the 94-symbol
  universe re-diffed programmatically — 94/94 symbols, caps and listing order identical,
  0 equities.
- **Champions re-verified for the fourth time:** the 15 completed-edition records are unchanged;
  maximum completed outcome remains 53.2072x, no completed edition at/above 100x.
- Participants displayed: 95,709 → **96,095** (the landing counter read 96,089 at the same
  minute; asynchronous counters, IR-09).

## September 17 second pass: full official re-verification + third frontier capture

On 2026-09-17 (~16:55 UTC) all three official pages were re-fetched and verified line by line:

- **Rules re-verified, zero changes:** every rule constant in
  [data/contest_config.json](data/contest_config.json) re-read from the
  [official rules](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) —
  dates, 250,000 balance, 20:1 leverage, 5 active days, 60/min rate limit, auto-close, prize
  ladder, 50,000 ARV, payment methods. The 94-symbol universe was diffed programmatically,
  line by line: **94/94 symbols and all 94 position caps identical, 0 equity symbols**
  ([evidence](research/evidence/TV-RULES-AMP-SEP2026-R3.md)).
- **Third frontier capture (16:56 UTC, 95,709 participants):** all four public frontiers rose
  during the US trading day — rank 1 +934.05% / +$2,335,125.00, rank 50 +499.16% /
  +$1,247,897.00, rank 100 +399.96% / +$999,892.85, rank 250 +262.03% / +$655,069.50.
  New hypotheses **H18** (frontier non-stationarity) and **H19** (cash-frontier gap) are
  supported ([evidence](research/evidence/TV-CONTEST-AMP-SEP2026-2026-09-17-R3.md)).
- **Champions re-verified:** all 15 completed-edition #1 records on the
  [landing page](https://www.tradingview.com/the-leap/) are unchanged
  ([evidence](research/evidence/TV-THELEAP-LANDING-R3.md)).
- **BTC1! history captured:** the fourth automated pass (03:15 UTC, run 35177491162) succeeded
  for BTC=F after three relay failures; the backtest panel is now **11 of 20** selected symbols
  (231 windows). IR-21 downgraded: MXP=F's single session is newly-listed vendor history (IR-18),
  not a relay failure.
- **Pipeline fix:** automated captures now re-derive the backtest/volatility artifacts, sync
  `models.json` stamps and rebuild the site before committing
  (`scripts/refresh_artifacts.py`), so the determinism check can no longer go stale after a
  capture pass.

## September 17 review and return-target lab

Fresh official rules and champion-page review: [claim-by-claim audit, source quotations,
limitations and prioritized next-session work](research/evidence/AUDIT-2026-09-17.md).

- **Cash prizes end at rank 50**; ranks 51–300 receive subscriptions. Rank 250 is not a cash frontier.
- New [target dataset](data/target_lab.json): 5×, 10×, 20×, 50× and 100× balance targets,
  official completed-champion occurrence counts, and 100 fixed-exposure arithmetic scenarios.
- A 5× balance means +400% net profit, not +500%. A 100× balance means +9,900%.
- These are numerical requirements, **not backtests or evidence of achievable future returns**.
- No complete officially verified explosive-stock opportunity list satisfies this futures-only edition.
  The 20 historical stocks remain vendor-tier reference; 74 of 94 futures lack full capacity coverage.
- Prize eligibility and possible identity/payment paperwork cannot be resolved by research automation.

Reproduce the new experiment and tests:

```bash
python3 scripts/target_lab.py
python3 scripts/build_site.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

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

The live page displayed **96,095 participants** at the 2026-09-17 ~19:04 UTC capture (fourth).
Captured public frontiers at that capture: rank 1 **+$2,335,125.00 (+934.05%)**, rank 50
**+$1,244,313.50 (+497.73%)**, rank 100 **+$1,012,202.50 (+404.88%)**, rank 250
**+$657,305.00 (+262.92%)**. These are moving snapshots, not final thresholds and not prize
guarantees. The first (2026-09-16) capture is the point-in-time record in
[`data/live_contest_snapshot.json`](data/live_contest_snapshot.json).

### Frontier tracker

Four official captures are stored with their official URLs in
[`data/frontier_history.json`](data/frontier_history.json); the verifier re-derives all deltas and
percentage arithmetic and requires each capture's values to be internally consistent
(`frontier.*` checks). The raw leaderboard HTML of the first capture is archived under
`artifact_pages/` for manual review; captures 2–4 are preserved as verbatim quotations in their
evidence files.

| Rank | Capture 1 (09-16 21:39) | Capture 2 (09-17 00:30) | Capture 3 (09-17 16:56) | Capture 4 (09-17 19:04) |
|---|---|---|---|---|
| 1 | +$2,303,725.00 (+921.49%) | +$2,303,725.00 (+921.49%) | +$2,335,125.00 (+934.05%) | +$2,335,125.00 (+934.05%) |
| 50 | +$1,144,096.25 (+457.64%) | +$1,172,236.00 (+468.89%) | +$1,247,897.00 (+499.16%) | **+$1,244,313.50 (+497.73%) ↓** |
| 100 | +$960,203.50 (+384.08%) | +$971,231.00 (+388.49%) | +$999,892.85 (+399.96%) | +$1,012,202.50 (+404.88%) |
| 250 | +$623,689.00 (+249.48%) | +$623,689.00 (+249.48%) | +$655,069.50 (+262.03%) | +$657,305.00 (+262.92%) |
| Participants | 93,527 | 93,702 | 95,709 | 96,095 |

The 3-hour window between captures 1 and 2 froze rank 1 and 250 while the mid-board moved; during
the US trading day before capture 3 **all four frontiers rose** and ranks 50/100/250 changed
holders (H18, supported). The P/L needed to hold a public rank is a rising moving target — but
capture 4 proved it is not a one-way ratchet: the rank-50 frontier **fell** $3,583.50 in just over
two hours while the former rank-50 row survived intact one place higher at rank 49 (H20, IR-23).

## What the evidence says

1. **Explosive simulated outcomes have occurred.** The captured official completed-champion sample
   includes a maximum of **53.2072x** and at least one completed futures outcome above 10x.
2. **No captured official contest result reaches 100x.** This means 100x is unattested in this
   sample, not impossible and not beyond a proven ceiling.
3. **The live edition has no single stocks.** The 20-stock module is historical reference for a
   future stock edition, not a live tradable list.
4. **All three pre-registered strategies are refuted on daily bars.** The independent walk-forward
   simulation (below) produced a **$0.0 pooled median net profit** for S1, S2 and S3 across 231
   windows (11 symbols), with concentration and sensitivity failures on top (H14–H16). Adding
   CME:BTC1! to the panel did not change any verdict.
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
Finance chart endpoint, with a relay-transport fallback for datacenter-IP blocks (IR-17). It writes
raw vendor bytes per symbol plus [`data/market_history_index.json`](data/market_history_index.json)
(SHA-256, endpoint, transport, session counts per record). Captured 2026-09-17 over four automated
passes; the fourth (03:15 UTC, run 35177491162) left **20/20 captured, 0 failed**: **11 symbols
with full history** (CL1!, QM1!, RB1!, HO1!, NG1!, SI1!, SIL1!, PL1!, NQ1!, ETH1! at 503 sessions
each; BTC1! at 504 — its three relay failures resolved on the fourth pass, IR-21) and **9 newly
listed single-session symbols** (SOL1!, MSL1!, SIC1!, MBT1!, MET1!, MNG1!, MCL1!, XRP1!, MXP1! —
excluded by the 150-bar minimum, IR-18). The workflow then re-derives all downstream artifacts via
`scripts/refresh_artifacts.py` before committing, so the backtest determinism check stays green
after every capture. Captures are `market_data_vendor` tier, spot-verified in-session and
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
| S1 Donchian trend breakout | **refuted** | $0.0 | 231 | 74 | 3 (best 7.39x, single trade) |
| S2 EMA impulse continuation | **refuted** | $0.0 | 231 | 30 | 0 (best 1.87x) |
| S3 Bollinger squeeze release | **refuted** | $0.0 | 231 | 5 | 0 (best 1.16x) |

(Run stamp 2026-09-17T03:15:40+00:00, 11 symbols; S1's three ≥5x windows are single-trade
Donchian breakouts in silver and crude.)

Every per-symbol median is $0.0; means are outlier-driven (S1's three ≥5x windows are single-trade
Donchian breakouts in silver and crude); S2's mean is negative in all cost scenarios; S3 fires too
rarely on daily bars for any confidence statement. These are **independent daily-bar simulations,
not TradingView Strategy Reports** — platform validation remains `not_run` because this environment
has no authenticated TradingView chart session or Pine compiler.

### Volatility screen

`data/volatility_intelligence.json` ranks each captured symbol by annualized volatility, ATR(14),
best 30-day up/down moves, largest overnight gap, and — the key ratio — the favorable move needed
to reach the captured rank-250 P/L ($623,689; the last publicly visible leaderboard rank — cash
prizes end at rank 50, see the target lab above) from each symbol's modeled initial notional,
versus the best 30-day move actually delivered in the 2-year window. Full-size CL1!/HO1!/SI1!
needed only ~12.7–12.9% and delivered 58–78%; NG1! (87.5% annualized, best 30-day +140.4%) needed
86.3% because its margin-limited notional is small; QM1! and ETH1! are structurally priced out
(needed +121.8% / +517.7%); BTC1! (now with full history) needed +163.9% against a best 30-day
up move of +48.8% because its 1-contract cap leaves a $380,425 modeled notional. This is
simulation arithmetic on vendor data, not a prediction.

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
| `data/target_lab.json` | Balance-multiple targets (5x–100x), champion occurrence counts, fixed-exposure scenarios |
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
| `scripts/refresh_artifacts.py` | One-step post-capture refresh: re-run backtests, sync `models.json`, rebuild the site (used by the CI capture workflow) |
| `scripts/fetch_market_data.py` | CI-side vendor capture with integrity checks and relay fallback |
| `scripts/build_site.py` | Deterministic root `index.html` generator for legacy GitHub Pages |

## Verify and build

```bash
python3 scripts/verify.py
python3 scripts/verify.py --self-test
python3 scripts/build_site.py
python3 scripts/target_lab.py
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 -m py_compile scripts/verify.py scripts/build_site.py scripts/run_backtests.py
```

After the raw captures change (CI or manual `scripts/fetch_market_data.py`), re-derive the
downstream artifacts in one step:

```bash
python3 scripts/refresh_artifacts.py   # re-run backtests, sync models.json, rebuild site
```

Current audit result:

```text
verify:    330 passed, 0 failed, 1 warning
self-test: 366 passed, 0 failed, 1 warning
```

The single verify warning is recorded for review: a 2.09% vendor-vs-quote delta on the newly
listed COMEX:SIC1! (front-contract month and capture time may differ; tracked as IR-22).

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
- **Nine selected symbols are newly listed on the vendor with a single session each**
  (SOL1!, MSL1!, SIC1!, MBT1!, MET1!, MNG1!, MCL1!, XRP1!, MXP1!; IR-18); the backtest panel is
  11 of 20 selected symbols. BTC1! now has full history (captured on the fourth automated pass,
  IR-21 resolved for BTC=F). Their capacity arithmetic (rules cap x multiplier x price) is
  verified from official sources and does not depend on vendor history.
- The verifier is offline. Public pages were captured through the research environment and can
  change later; rerun the source-capture process for a new snapshot.
- Live leaderboard and quote values are asynchronous point-in-time displays, not executable prices;
  rank 1/250 were frozen between the two captures while the mid-board moved (IR-20). Board
  membership itself is corrected over time — the displayed rank-50 frontier fell $3,583.50 between
  captures 3 and 4 with no public change log (IR-23), so no captured frontier is a floor in either
  direction.
- The constant-rate scenario values in H21 (e.g. rank 250 ≈ $1.16M at the deadline) are arithmetic
  extrapolations of captured displays, **not forecasts**; H18/H20 show the true path is irregular.
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
