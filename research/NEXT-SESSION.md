# Next session — remaining work, suggestions, and limitations

**Last updated:** 2026-09-22 (twenty-first pass). Every claim below is cross-referenced to a
committed artifact or an official source URL for manual review. Nothing here is a forecast.

---

## 1. What this session added (for continuity)

- **Four new unique contrarian strategies**, frozen before any run and registered as
  hypotheses **H52–H55**: C31 failed-breakout upthrust short (Wyckoff bull-trap twin of C20),
  C32 hammer-rejection sniper (volume-free bar-shape trigger), C33 thin melt-up fade short
  (fires when volume is ABSENT — structurally opposite to C6), C34 gap-exhaustion engulfing
  fade (failure twin of the C14/C29 gap-hold longs). Eight new usernames
  (UpthrustUrsula, CeilingTrapCal, RejectionRocco, WickWizardWilla, ThinMeltTina, MeltupMaven,
  ExhaustionEzra, IslandIzzy) — the stock roster is now **70 usernames (66 daily, 4 hourly)**.
- **Forward-test PnL ledger** (`data/forward_test_ledger.json`, `intel/forward_ledger.py`):
  every username replayed on the latest window of each division with every closed tranche
  recorded (dates, fill prices, size, side, net P/L, running cumulative P/L). 210 usernames,
  2,978 closed tranches, each sum cross-checked against the season artifact's
  `latest_edition` aggregate within one cent per tranche. The verifier re-runs the builder
  field-for-field at its stored stamp.
- **Executive summary restructured**: the UPCOMING PAPER TRADES orders are now the first
  content of the page — the answer before the caveats — with the forward-window PnL of the
  recommending usernames rendered as the mechanical "why these" basis.
- **Live contest clock** (`data/live_contest_clock.json`): the verbatim official registration
  deadline `Join until Sep 23, 2026 · 04:00 GMT-4`, trading window, prize display and the
  top of the public board, captured 2026-09-22
  ([official page](https://www.tradingview.com/the-leap/amp-futures-september-2026/)).
- **Official-source re-captures (R12)** with verbatim evidence files for the contest page,
  the landing page and the Magnificent Seven results post; **IR-35** logged (landing counter
  102,729 vs contest counter 102,747 in one session).

---

## 2. What still needs to be done (suggestions, highest value first)

1. **Enter the live contest before the registration deadline (time-critical).**
   `Join until Sep 23, 2026 · 04:00 GMT-4` on the official contest page. The live edition is
   **futures-only** (Sep 1–30, 2026, $50K + 250 plans). The only officially attested 5x+
   champion returns in our sample are futures/crypto editions
   (BenBernanke1 +5,220.72%, [official results](https://www.tradingview.com/blog/en/leap-by-cme-winners-announced-50889/);
   ICT_Hispanohablantes +308.07%; Me-tis +155.95%). If the goal is winning a prize, the
   futures division strategies (ContrarianQueen / FadeThePanic / ClimaxCarla families in
   `data/competition_results.json`) are the ones aligned with the live contest's asset class.
   The 20:1 futures profile is the only profile in which our own placement arithmetic
   (`data/leaderboard_lab.json`) shows a fresh account reaching the rank-50 frontier at all.

2. **Replace vendor-tier pricing with an official/verified provider feed.**
   This is limitation #1 below and irregularity IR-32. Concretely: run
   `scripts/fetch_official_bars.py` in a CI environment with network egress and the
   documented free official-provider route (Alpaca IEX
   [docs](https://docs.alpaca.markets/us/reference/stockbars)), or import an authenticated
   TradingView export ([export docs](https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/)).
   Then `scripts/spot_check_official_vs_vendor.py` quantifies the gap and the captures can be
   re-labelled. Until then every price figure on the site says "vendor-tier".

3. **Roll the forward window on a schedule.** The forward ledger is frozen at the last
   capture (window ends 2026-09-18 daily / 2026-09-17 hourly). A weekly scheduled
   `capture-intraday` → `derive-intraday` cycle (already automated in `.github/workflows/`)
   plus `scripts/run_forward_test.py` extends true forward tracking. Consider a standing
   "forward PnL since 2026-09-22" accumulator so the ledger grows an out-of-sample record
   rather than only sliding windows.

4. **Extend the forward ledger to the futures division.** Today it covers the stock roster
   only (the brief's own competition). The futures season artifact has the same
   `latest_edition` machinery (`data/competition_results.json`), so
   `intel/forward_ledger.py` can be generalized with the futures series map
   (`scripts/build_exec_summary.py` shows how those Series objects are built with CME
   multipliers and section-08 caps).

5. **Short-side realism check for C31/C33/C34.** The three new short families borrow nothing
   and assume continuous shortability. The official stocks-edition rules
   ([rules](https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/)) should be
   re-read line by line for short-selling eligibility of the 20 pool names; if the real
   contest forbids or constrains shorting, the short families are research-only and the long
   families (C32, C26, C30) carry the executable thesis. Add a borrow-cost scenario to
   `intel/backtest.py`'s CostScenario set either way.

6. **Widen the official champion sample.** Each new edition's results post (linked from
   [the landing page](https://www.tradingview.com/the-leap/)) extends
   `data/verified_explosive_returns.json` and sharpens the H31 bound question. The
   stocks-edition ceiling (+17.58%, +29.90%) has never once reached 5x officially; every new
   stocks edition either confirms or refutes that observed ceiling.

7. **Options-flow features for C26's thesis.** The gamma-squeeze chaser currently proxies
   squeeze conditions with price/volume only (no options chain in any verified free official
   source we found). A verified free options dataset (e.g. the OCC's public volume data) would
   let H47's mechanism be tested properly instead of proxied.

8. **Estimate the hidden prize frontier (ranks 251+).** The board publishes only its top 250
   rows (`public_leaderboard_last_visible_rank`). Frontier-history captures near month-end
   (`data/frontier_history.json`) are the only way to estimate where rank 50 — the last cash
   prize — actually finishes. Capture the final board in the last hours of Sep 30.

9. **Re-run the mechanical verdict pipeline after each capture refresh:**
   `run_stock_competition.py` → `assign_full_pool_verdicts.py --write-hypotheses` →
   `run_forward_test.py` → `build_exec_summary.py` → `build_site.py`, then `verify.py`.
   H52–H55 are currently **refuted** on their first full-pool run; per
   `research/strategy/C19-VARIANT-GATE.md` a refuted model stays frozen — do not retune it.
   New variants need new pre-registered hypotheses (H56+).

10. **Crypto/forex shadow divisions.** Official crypto champions ran +114% to +272% and the
    multi-asset winner +308%; crypto trades 24/7 so the "5 active days" rule is easier to
    satisfy and compounding windows are longer. The same competition engine
    (`intel/competition.py`) accepts any bar series.

---

## 3. Limitations in the way of a successful project (ranked)

1. **No exchange-verified prices (IR-32).** All captured bars are Yahoo Finance vendor-tier.
   The sandbox has no egress to the official providers and no stored credentials, by policy.
   Every simulated dollar figure inherits this limitation. Missing prices are never
   synthesized — partial captures are recorded as `failed`/`not_attempted` instead.
2. **5x–100x is arithmetically out of reach under official stocks-edition rules.** 1:1
   leverage, a 50-unit-per-instrument cap, and 18–22 session editions bound the single-hold
   scenario at 4.74x maximum across all 81 editions and 20 volatile names
   (`data/stock_competition_results.json` → `official_rule_bound`), and no official stocks
   champion has ever exceeded +29.90%. The observed 5x+ outcomes are futures (20:1) and
   crypto editions. If the target remains 5x–100x, it must be pursued in the futures or
   crypto divisions, not the stocks division — this is measured, not a judgment.
3. **The live contest is futures-only.** The current live edition (Sep 1–30, 2026) trades
   futures; the volatile-stock competition in this repository is our own laboratory and its
   names are not the live eligible universe
   ([universe evidence](https://www.tradingview.com/the-leap/amp-futures-september-2026/)).
4. **Registration closes 2026-09-23 04:00 GMT-4** (official page, verbatim). After that the
   live September edition cannot be entered at all; the next edition's rules may differ.
5. **One forward window (~21–27 sessions) is a small sample.** Forward PnL on a single
   window cannot separate skill from luck; the multi-season leaderboards
   (`in_sample` vs `forward_held_out` splits) are the better evidence and they disagree
   often (see H34/H37 partially-supported vs their forward rows).
6. **Short-side models (C31/C33/C34) ignore borrow, locate and uptick constraints.** Paper
   engines fill shorts as easily as longs; real-world shortability of the 20 pool names is
   unverified (see suggestion #5).
7. **Fill model is ATR-fraction slippage + 0.01% commission** (`intel/backtest.py`
   CostScenario "moderate"); the latency study shows mean multiples are insensitive from 0 to
   5 bars of delay (`data/intraday_study.json`), but tail fills in a real flash move would
   differ from any model. Sizes in `data/exec_summary.json` are indicative at the last
   captured close; the actual fill would be at the next bar's open, which is unknown.
8. **Ranks below 250 are never published**, so the true rank-50 prize frontier can only be
   estimated from the visible rows (suggestion #8).
9. **Counter sources disagree (IR-35).** Landing page and contest page displayed participant
   counts 18 apart in one session; both are official text. Downstream arithmetic does not
   depend on the counter, but any screenshot-level claim should cite which page it came from.
10. **The TradingView Pine-vs-Python benchmark is blocked** (`data/tv_benchmark.json`,
    status `blocked`) until an authenticated Strategy Report export exists; the emulator
    agreement figures in `intel/pine_emulator.py` remain fixture-tested only.

---

## 4. Verification commands (run before trusting any figure)

```bash
python3 scripts/verify.py                        # full offline provenance + arithmetic suite
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/run_stock_competition.py         # regenerate the season (deterministic)
python3 scripts/assign_full_pool_verdicts.py --write-hypotheses
python3 scripts/run_forward_test.py              # regenerate the forward ledger
python3 scripts/build_exec_summary.py
python3 scripts/build_site.py                    # regenerate index.html + docs/ mirror
```

Official sources for manual review (the full registry is `research/sources/sources.json`):

- https://www.tradingview.com/the-leap/
- https://www.tradingview.com/the-leap/amp-futures-september-2026/
- https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
- https://www.tradingview.com/blog/en/the-leap-magnificent-seven-results-57868/
- https://www.cmegroup.com/ (contract specifications, per-symbol source ids `CME-SPEC-*`)
