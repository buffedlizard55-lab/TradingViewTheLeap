# Next session — remaining work, suggestions, and limitations

**Last updated:** 2026-09-22 (twenty-second pass). Every claim below is cross-referenced to a
committed artifact or an official source URL for manual review. Nothing here is a forecast.

---

## 1. What this session added (for continuity)

- **R13 final-week official captures** (contest page, landing page, rules — verbatim evidence
  files, capture #11 at 2026-09-22T23:00:00Z): frontier rank 1 **$2,982,777.45 (+1,193.11%)**,
  rank 50 **$1,525,023.75**, rank 100 **$1,236,663.00**, rank 250 **$866,600.85**, participants
  **102,886** (+3,159 vs R11); all four frontiers rose (**H58 supported**). Rules re-read line
  by line: §08 universe 94/94 match, constants unchanged; registration still `Join until
  Sep 23, 2026 · 04:00 GMT-4`. The displayed board showed rank 7's row $41,852.25 RICHER than
  rank 6's — non-monotonic ordering (**H59 supported**, **IR-37**); landing vs contest counters
  differ by 3 (IR-35 continuation).
- **Two new frozen contrarian futures families + 4 usernames** (roster 15 → **19**: 16
  contrarian, 3 baselines): **F1** compressed-streak fade (exact k=4 compressed up-streak marks
  momentum death; StreakStan default, CompressCleo slow5) and **F2** swing-failure reclaim
  (prior-20-bar low/high sweep + close reclaim; SpringSasha default, CreekCasey shallow),
  registered as **H56/H57**. Verdicts on the first full run (stamp
  2026-09-22T23:10:00Z, 456 participant-editions, existing-15 PnL byte-identical):
  **H56 supported** (F1 family mean −$427,825 beats the baseline mean −$577,542 on both
  prongs — the forward prong via a zero-fire flat window, recorded explicitly), **H57
  refuted** (F2 family mean −$1,029,544 trails; CreekCasey still printed the family's only
  ≥5x edition at 6.636686x while ruining 8/24 — the H30 collapse pattern, and per
  `research/strategy/C19-VARIANT-GATE.md` F2 stays frozen).
- **Forward-test ledger extended to the futures division** (engine `forward-ledger-2`,
  suggestion #4 of the prior pass completed): `divisions.futures` replays the 19-user futures
  roster on the season artifact's `latest_edition` window (2026-08-19..2026-09-17, 21 sessions)
  under the frozen `futures_amp_sep2026` profile; stock divisions byte-identical to the prior
  engine. Totals: **229 usernames, 3,007 closed tranches, 229/229 cross-checks green** (every
  username within one cent per tranche of its `latest_edition` — the first real-data proof that
  `run_participant_window` (futures profile, latency 0) reproduces the legacy season engine).
- **Short-side eligibility re-read completed** (prior pass suggestion #5): the full Magnificent
  Seven rules text contains no short/sell/borrow clause anywhere (unverified-not-forbidden
  stands), and the official Paper Trading help page documents `side (buy/sell)` in the order
  ticket — evidence file `research/evidence/TV-PAPER-TRADING-SHORT-SIDE-2026-09-22.md`.
  A borrow/locate cost scenario is still open (limitation #6 below).
- Registers: hypotheses **H56–H59** (count 59), irregularities **IR-37** (count 37), sources
  **110**; live returns row re-synced to capture #11 (12.9311x / 102,886);
  `intelligence_report.json` re-derived for the 19-user roster; site rebuilt (hero R13).
  Verification: **444 checks passed / 0 failed / 1 warning (IR-22)**; 183 unit tests green.

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

3. **Roll the forward window on a schedule.** The forward ledger (both divisions) is frozen
   at the last capture (futures window ends 2026-09-17; daily 2026-09-18; hourly 2026-09-17).
   A weekly scheduled `capture-intraday` → `derive-intraday` cycle (already automated in
   `.github/workflows/`) plus `scripts/run_forward_test.py` extends true forward tracking.
   Consider a standing "forward PnL since 2026-09-22" accumulator so the ledger grows an
   out-of-sample record rather than only sliding windows.

4. **Capture the contest's FINAL board (Sep 30) and enter it if possible.** Registration
   closes 2026-09-23 08:00 UTC; the trading window runs to 2026-09-30 12:00 UTC. The final
   frontier capture (suggestion #8's sibling, now the highest-value *measurement*) shows where
   rank 50 — the last cash prize — actually finishes, and the post-contest results post
   extends `data/verified_explosive_returns.json` with the official 2026-09 champion.

5. **Add a borrow/locate cost scenario for the short families.** The rules re-read (this pass)
   found no short-side prohibition and the official Paper Trading docs confirm a sell side,
   but `intel/backtest.py` CostScenario still models shorts with the same slippage/commission
   as longs. A borrow-cost line would complete the short-side realism picture for C18/C31/
   C33/C34 and F2's upthrust leg (the re-read evidence:
   `research/evidence/TV-PAPER-TRADING-SHORT-SIDE-2026-09-22.md`).

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
   prize — actually finishes; captures 10–11 already bracket the final registration week.

9. **Re-run the mechanical verdict pipeline after each capture refresh:**
   `run_competition.py` → `run_stock_competition.py` →
   `assign_full_pool_verdicts.py --write-hypotheses` → `run_forward_test.py` →
   `build_exec_summary.py` → `build_site.py`, then `verify.py`.
   H52–H55 are **refuted** on their first full-pool run and H57 (F2) is **refuted** on its
   first full run; per `research/strategy/C19-VARIANT-GATE.md` a refuted model stays frozen —
   do not retune it. New variants need new pre-registered hypotheses (next free id: **H60**).

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
6. **Short-side models (C18/C31/C33/C34, F2 upthrust) ignore borrow and locate costs.** The
   twenty-second pass re-read the official Mag7 rules line by line: no short/sell/borrow clause
   exists anywhere (unverified-not-forbidden, evidence file committed), and the official Paper
   Trading docs document `side (buy/sell)` — but the engine still prices shorts exactly like
   longs (no borrow fee; see suggestion #5).
7. **Fill model is ATR-fraction slippage + 0.01% commission** (`intel/backtest.py`
   CostScenario "moderate"); the latency study shows mean multiples are insensitive from 0 to
   5 bars of delay (`data/intraday_study.json`), but tail fills in a real flash move would
   differ from any model. Sizes in `data/exec_summary.json` are indicative at the last
   captured close; the actual fill would be at the next bar's open, which is unknown.
8. **Ranks below 250 are never published**, so the true rank-50 prize frontier can only be
   estimated from the visible rows (suggestion #8).
9. **Counter sources disagree (IR-35).** Landing page and contest page displayed participant
   counts 18 apart at R12 and 3 apart at R13 (102,883 vs 102,886); both are official text.
   Downstream arithmetic does not depend on the counter, but any screenshot-level claim
   should cite which page it came from.
10. **The TradingView Pine-vs-Python benchmark is blocked** (`data/tv_benchmark.json`,
    status `blocked`) until an authenticated Strategy Report export exists; the emulator
    agreement figures in `intel/pine_emulator.py` remain fixture-tested only.

---

## 4. Verification commands (run before trusting any figure)

```bash
python3 scripts/verify.py                        # full offline provenance + arithmetic suite
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/run_competition.py               # regenerate the futures season (deterministic)
python3 scripts/run_stock_competition.py         # regenerate the stock season (deterministic)
python3 scripts/assign_full_pool_verdicts.py --write-hypotheses
python3 scripts/run_forward_test.py              # regenerate the forward ledger (both divisions)
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
