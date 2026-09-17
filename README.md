# TradingView The Leap — evidence-first research lab

A reproducible research layer for TradingView's **The Leap** paper-trading competition. The project
separates official contest facts, historical champion outcomes, vendor-sourced stock market moves,
capacity arithmetic, and untested strategy hypotheses. It does not present a backtest as a fact or
mix real historical stock returns with simulated competition returns.

**GitHub Pages:** https://buffedlizard55-lab.github.io/TradingViewTheLeap/

## September 17 review and return-target lab

Fresh official rules and champion-page review: [claim-by-claim audit, source quotations,
limitations and prioritized next-session work](research/evidence/AUDIT-2026-09-17.md).
This review does **not** refresh the September 16 leaderboard or price inputs below.

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

The live page displayed **93,527 participants**. Captured public frontiers were rank 1
**+$2,303,725.00 (+921.49%)**, rank 50 **+$1,144,096.25 (+457.64%)**, rank 100
**+$960,203.50 (+384.08%)**, and rank 250 **+$623,689.00 (+249.48%)**. These are moving snapshots,
not final thresholds and not prize guarantees. See [`data/live_contest_snapshot.json`](data/live_contest_snapshot.json).

## What the evidence says

1. **Explosive simulated outcomes have occurred.** The captured official completed-champion sample
   includes a maximum of **53.2072x** and at least one completed futures outcome above 10x.
2. **No captured official contest result reaches 100x.** This means 100x is unattested in this
   sample, not impossible and not beyond a proven ceiling.
3. **The live edition has no single stocks.** The 20-stock module is historical reference for a
   future stock edition, not a live tradable list.
4. **Volatility alone cannot rank instruments.** Dollar P/L also depends on price, multiplier,
   contracts, the rules cap, and buying power. The repository does not claim that caps or any one
   market are the binding cause of winning returns.
5. **Realizing a position does not create profit.** It moves open P/L into the realized ranking
   metric. The official rules automatically close remaining positions at the end.
6. **Edition parameters are not stable.** Balance, leverage, symbols, caps, and prize ranks differ
   between captured editions; every strategy must be revalidated against the current rules.

All verdicts and evidence lines are in
[`research/hypotheses/hypotheses.json`](research/hypotheses/hypotheses.json).

## Strategy research

Three long/short candidate models are pre-registered and implemented in Pine Script:

- Donchian trend breakout with EMA direction and ATR expansion;
- EMA impulse continuation with ATR expansion;
- Bollinger squeeze release.

Files:

- [`research/strategy/models.json`](research/strategy/models.json) — exact hypotheses and
  falsification rules.
- [`research/strategy/the-leap-hypothesis-lab.pine`](research/strategy/the-leap-hypothesis-lab.pine)
  — Pine Script v6 implementation.
- [`research/strategy/testing-plan.md`](research/strategy/testing-plan.md) — walk-forward,
  cost/fill sensitivity, holdout, and forward-test protocol.
- [`data/initial_capacity.json`](data/initial_capacity.json) — verified cap × multiplier × price ×
  buying-power arithmetic for the 20 selected live futures.

**No strategy result is claimed.** This repository environment has no authenticated TradingView
chart, Pine compiler, realtime entitlement, Strategy Report export, or competition account. Official
TradingView documentation also states that Pine strategies cannot directly place orders in the
built-in Paper Trading account. Publishing invented returns would violate the project's evidence
standard.

The capacity screen is not alpha. At the captured values, CL, SI, HO, and NQ had the lowest modeled
favorable percentage moves needed to equal the displayed rank-250 P/L among the 20 selected rows.
That comparison assumes whole contracts, initial 20:1 buying power, and no spread, slippage,
commission, liquidity effect, rejection, or margin-call path. It does not predict direction or
volatility.

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
| `data/initial_capacity.json` | Derived initial-balance capacity screen |
| `data/master_list.json` / `.csv` | 20 selected futures with official multipliers and rule caps |
| `data/verified_explosive_returns.json` | Official historical champion results plus one live snapshot |
| `data/volatile_stocks.json` | Vendor-tier, recomputable, window-bounded stock moves |
| `research/hypotheses/hypotheses.json` | Falsifiable research claims, tests, verdicts, and evidence |
| `research/strategy/` | Candidate models, Pine implementation, and test protocol |
| `research/irregularities.json` | Open, confirmed, and resolved source/data issues |
| `research/sources/sources.json` | Source registry with allowed uses and manual-review links |
| `research/evidence/` | Captured quotations and endpoint records |
| `scripts/verify.py` | Offline provenance, arithmetic, endpoint, strategy-state, and mutation checks |
| `scripts/build_site.py` | Deterministic root `index.html` generator for legacy GitHub Pages |

## Verify and build

```bash
python3 scripts/verify.py
python3 scripts/verify.py --self-test
python3 scripts/build_site.py
python3 -m py_compile scripts/verify.py scripts/build_site.py
```

Current audit result:

```text
verify:    303 passed, 0 failed, 0 warnings
self-test: 332 passed, 0 failed, 0 warnings
```

The mutation self-test proves checks fail when source endpoints, rule constants, leaderboard
arithmetic, capacity math, strategy result state, multipliers, return ratios, counts, or stock
windows are corrupted. CI rebuilds the site and fails if committed `index.html` is stale.

## Important limitations and remaining work

- The verifier is offline. Public pages were captured through the research environment and can
  change later; rerun the source-capture process for a new snapshot.
- Live leaderboard and quote values are asynchronous point-in-time displays, not executable prices.
- The public page does not show ranks 251–300, so the actual last-prize frontier is unavailable.
- Champion summaries contain no trade history; they cannot reveal a winning strategy.
- No consistent licensed intraday history for all 94 eligible futures is stored here. CME's official
  settlement-based continuous series is a licensed option for part of the universe.
- Continuous contracts can introduce roll effects. Strategy tests must record contract/roll settings.
- TradingView Paper Trading and Pine's broker emulator are distinct simulations with different fill
  mechanics. No Pine result should be labeled a competition-account result.
- The live rules do not state a commission schedule. Backtests must test declared zero and nonzero
  cost scenarios rather than assume.
- The official Paper Trading help page's displayed short-futures formula omits point value even
  though its worked example uses it; this is flagged as `IR-14`.
- Strategy candidates remain untested until authenticated TradingView Strategy Report and forward
  test artifacts are captured.

This project concerns virtual competition money. It is not investment advice or a forecast, and
historical market moves or simulated contest results do not imply future performance.
