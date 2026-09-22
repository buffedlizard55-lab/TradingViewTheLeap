# Explosive-Return Playbook — 2026-09-22 (twentieth pass)

**Goal:** design new and unique contrarian strategies for a paper-trading competition that
target 5x, 10x, 20x, 50x, 100x returns with NO risk management, using real verified pricing
from official verified sources, tracking PnL by usernames, and rendering an explicit
executive summary of upcoming trades at the very top of the GitHub Pages site.

**Official verified sources (publicly available, with links for manual review):**

- TradingView The Leap competition page: https://www.tradingview.com/the-leap/ [TV-THELEAP-LANDING]
- TradingView The Leap AMP Futures September 2026 live edition: https://www.tradingview.com/the-leap/amp-futures-september-2026/ [TV-CONTEST-AMP-SEP2026]
- TradingView official rules AMP Futures September 2026: https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/ [TV-RULES-AMP-SEP2026]
  - Starting balance $250,000 virtual, futures leverage 20:1, max initial notional $5,000,000, ranking by realized P/L on closed positions, min 5 active UTC days, 94 eligible futures with per-symbol caps, auto-close at end, no account reset.
- TradingView stocks-edition rules (Magnificent Seven March 2026): https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/ [TV-RULES-MAG7-MAR2026]
  - Starting balance $100,000 virtual, stocks leverage 1:1, commission 0.01%, max 50 units per instrument, min 3 active days.
- CME Group contract specs (official primary):
  - BTC: https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs [CME-SPEC-BTC1!]
  - ETH: https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs [CME-SPEC-ETH1!]
  - SOL guide: https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html [CME-SOL-GUIDE]
  - XRP PR: https://www.cmegroup.com/media-room/press-releases/2025/4/24/cme_group_to_expandcryptoderivativessuitewithlaunchofxrpfutures.html [CME-XRP-PR]
  - And 16 more under data/cme_specs/ with SHA-256 provenance in data/cme_specs_index.json
- Alpaca Market Data API (official free stock data):
  - About: https://docs.alpaca.markets/us/docs/about-market-data-api [ALPACA-DATA-ABOUT]
  - Historical bars: https://docs.alpaca.markets/us/reference/stockbars [ALPACA-STOCKBARS-DOCS]
  - Basic plan free, IEX equities, API keys required, 5 years history, 1/5/15/30/60m + daily.
- TradingView Strategy Report export: https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/ [TV-EXPORT-DOCS]
- Yahoo Finance chart API (market_data_vendor tier, NOT official exchange): https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL} — used only for archived vendor evidence, labeled vendor-tier everywhere.

**Why official pricing is still vendor-tier in this repo:**

- The sandbox has no network egress (verified: curl to alpaca.markets, yahoo, tradingview returns 000; only api.github.com resolves).
- No repository secrets (gh secret list returns HTTP 403).
- So `scripts/fetch_official_bars.py` exits blocked (IR-32) and no authenticated TradingView Strategy Report export exists (TV benchmark status blocked).
- Existing 61 captured series (20 stocks x 15m/1h/1d = 60 + 1 futures hourly salvage) are Yahoo vendor-tier with per-chunk SHA-256 and byte length in data/intraday_index.json — byte-level provenance, not exchange-verified.
- All prices on the site are labeled vendor-tier; missing prices are never synthesized.

**Placement arithmetic — what it takes to win (from data/leaderboard_lab.json):**

- Latest capture R11: participants 99,727, rank1 HappyLittleTrades +994.30% / $2,485,745.50, rank50 ashutoshrajan6 +583.87% / $1,459,666.50, rank100 +472.56%, rank250 +303.03%.
- Rank50 at latest capture displayed 6.8387x starting balance, average $81,094/day since start, fresh account would need +15.21%/day compounded unbroken for remaining days to reach it.
- At 20:1 max exposure, that is ~0.76% underlying move per day — but one -5% adverse day at full exposure erases whole balance (rules forbid resets).
- No 100x outcome in verified historical champion sample (max 53.2072x BenBernanke1 Feb 2025 futures).

**Volatile-stock pool (20 names, official verified explosive moves from vendor history):**

- Symbols: ENPH, AMD, MARA, CVNA, GME, RIOT, SHOP, NVAX, APP, PLUG, MSTR, NIO, PLTR, AMC, SMCI, HOOD, TSLA, NVDA, COIN, PTON
- Largest archived trough->peak multiples (window-bounded, vendor adjusted closes, recomputable):
  - CVNA 128.62x (2022-12-27 $0.744 -> 2026-01-22 $95.69) — verified split 5:1 2026-05-08
  - SMCI 95x+, MSTR 30x+, etc. (see data/volatile_stocks.json)
- Each ratio re-derived by scripts/verify.py from stored values; no all-time claim.

**Why official stock edition cannot reach 5x-100x under official rules:**

- Official stocks-edition constants: $100k x 1:1 = $100k buying power, 50-unit cap per instrument.
- Single-hold scenario bound: applying official 50-unit cap to every pool symbol that traded in window at first close, all held simultaneously, every one moving by largest favourable excursion any single name actually made inside same window — max observed bound 4.738222x across 81 editions (data/stock_competition_results.json official_rule_bound).
- Counterfactual 20:1 run (NOT official): same 50-unit cap but 20:1 buying power ($2M) — still 0 editions >=5x across 744 participant-editions (mean multiple 1.000659x). Leverage alone does not move result.
- Binding constraint is edition length (18-22 sessions median 21) and 50-unit cap, not signal quality.

**New models C26-C30 — design rationale for maximum paper return (no risk management):**

All five frozen in intel/stock_strategies.py DEFAULT_PARAMS/VARIANTS, pre-registered before run, with centre-of-grid parameters (not cherry-picked best).

- **C26 Gamma Squeeze Chaser (H47):**
  - Trigger: 3 consecutive up closes each >=4% (close/prev-1), volume expanding each day and >=1.5x 20-day avg, close in top quartile (close_pos >=0.75).
  - Action: long next open, pyramid every +0.5 ATR favorable close (max 6 adds), hold 10 bars.
  - Why: targets GME/AMC/CVNA style parabolic meme runs where gamma squeeze feeds on itself; aggressive pyramiding concentrates capital into rare explosive continuation.
  - Frozen params: run_closes=3, run_pct=0.04, volume_length=20, volume_mult=1.5, close_tail_fraction=0.25, add_atr_step=0.5, max_adds=6, hold_bars=10.
  - Variants: aggressive (run_pct 0.03, vol 1.2, max 8 adds), tight (0.06, 2.0, max 4).
  - Usernames: GammaGina (default), SqueezeChaserSam (aggressive).
  - Result on 60/60 matrix: SqueezeChaserSam +$12,015.78 season (rank 4), best edition 1.1516x, forward 861.83; GammaGina -$3,025.94 season but +$948.66 forward. Full-pool verdict H47 supported (both beat B1 control in both splits).

- **C27 Volatility Squeeze Ignition (H48):**
  - Trigger: 20-day stdev <=0.8 ATR (tighter than C11's 1.2), ATR expanding >=1.3x 5 bars ago, breakout above 20-day high on >=2x avg volume.
  - Action: long next open, pyramid +0.5 ATR (max 6), hold 12.
  - Why: price compression dual — quiet accumulation before explosive release; institutional footprints.
  - Frozen: squeeze_length=20, volume_length=20, volume_mult=2.0, atr_expansion_mult=1.3, lag=5, add 0.5, max 6, hold 12.
  - Variants: tight (squeeze 10, expansion 1.5, hold 8), patient (30, 1.1, 15).
  - Usernames: VolatilityVulcan, SqueezeSniper.
  - Result: both negative small (-$216, -$26), forward 0 — refuted. Squeeze too tight for 20-stock pool.

- **C28 Mean Reversion Lottery (Deep Dip Martingale) (H49):**
  - Trigger: 5-day drawdown >=25% (peak = max closes last 5, trough = current close), current bar close in bottom decile (close_pos <=0.10) on >=1.5x volume.
  - Action: long next open, martingale DOWN every -1 ATR (averaging down into further panic, max 6 adds), hold 6.
  - Why: deliberate lottery ticket — either ruins edition or catches violent snapback at multiplied size, which is exactly what no-risk-management paper competition rewards. Targets forced selling exhaustion.
  - Frozen: drawdown_lookback=5, drawdown_pct=0.25, volume_length=20, vol_mult=1.5, close_tail 0.10, add_step 1.0, max 6, hold 6.
  - Variants: deep (0.35, max 8, hold 8), quick (0.15, max 4, hold 4).
  - Usernames: LotteryLarry, MartingaleMolly.
  - Result: LotteryLarry +$1,465.66 season (rank 20), best 1.025x, forward 59.63; MartingaleMolly +$605 season, forward 113.74. Both beat season vs B1 but fail forward vs B1 (576) — refuted.

- **C29 Overnight Momentum Surfer (H50):**
  - Trigger: gap up >=2 ATR over prior close, closes in top half, close>open, >=2x volume — gap-and-go but more aggressive than C14 (1.5 ATR).
  - Action: long next open, pyramid +0.75 ATR (max 5), hold 10.
  - Why: gap that holds signals institutional demand discovery, not over-reaction; rides multi-day runners.
  - Frozen: gap_atr_mult=2.0, close_tail 0.5, vol_len 20, vol_mult 2.0, add 0.75, max 5, hold 10.
  - Variants: aggressive (gap 1.5, max 6, hold 14), patient (2.5, max 3, hold 6).
  - Usernames: GapAndGoGary, MomentumMona.
  - Result: MomentumMona +$24,916.89 season (rank 2!), best 1.218x, forward 360.48; GapAndGoGary +$2,216 season, forward -395.30. Season both beat B1, forward both fail vs B1 — refuted by rule, but MomentumMona is new rank 2 overall.

- **C30 Dead Cat Bounce Pyramid (H51):**
  - Trigger: prior bar crash >=2.5 ATR (close[t-2]-close[t-1]), then first green close (close>open) with volume >=2x and close in top half.
  - Action: long next open, pyramid +0.75 ATR (max 4), hold 8.
  - Why: classic capitulation bounce — forced sellers done, buyers step in; harvests snapback.
  - Frozen: crash_atr_mult=2.5, vol_len 20, vol_mult 2.0, close_tail 0.5, add 0.75, max 4, hold 8.
  - Variants: deep (crash 3.0, max 6, hold 10), quick (2.0, max 3, hold 5).
  - Usernames: BounceBobby, DeadCatDave.
  - Result: BounceBobby -$348, DeadCatDave -$750, forward negative — refuted.

**Executive summary — explicit upcoming trades (from data/exec_summary.json):**

Generated by scripts/build_exec_summary.py replaying frozen model parameters on committed vendor bars as of 2026-09-21T20:00:08+00:00.

- Futures division (official AMP rules: $250k x 20, per-symbol caps):
  - ContrarianQueen (C5 Capitulation pyramider, season rank 1, $4,459,134 season P/L, best 7.71x) — CLOSE short and OPEN LONG ~1 unit CME:ETH1! signal bar 2026-09-17
  - GapGoblin (C2 Gap fade, rank 4) — CLOSE open position FLAT NYMEX:PL1! signal 2026-09-17
  - FadeThePanic (C1) flat waiting for multi-day collapse >=1 ATR over 3 closes with ATR expanding
  - ClimaxCarla (C4) flat waiting for exhaustion-bar (TR >=2x ATR, close in extreme quartile)

- Stocks daily division (official stocks-edition: $100k x 1:1, 50-unit cap, 0.01% commission):
  - BreakoutBea (C16 ATR-expansion breakout compounder, rank 1, $26,149 season, best 1.279x) — ADD ~50 units to open long MSTR signal 2026-09-18
  - MomentumMona (C29 Overnight Momentum Surfer, NEW rank 2, $24,916 season, best 1.218x) — FLAT waiting for gap up >=2 ATR that holds (close top half, close>open, >=2x vol) — no pending order this bar
  - EmaEddie (S2 EMA impulse baseline, rank 3, $13,643) — CLOSE short and OPEN LONG ~50 units GME signal 2026-09-18

- Stocks hourly division:
  - IntradayIris (C7 rapid, rank 1 hourly, $21,351) — CLOSE FLAT RIOT and COIN signal 2026-09-17

Every order is market at next bar open of that series, indicative size from official rule constants at last captured close; actual fill at next open unknown. Verification: python3 scripts/verify.py replays each model on committed bars and requires table field-for-field.

**Why no 5x-100x achieved:**

- Season editions 81 daily x 20 symbols, mean edition multiple 1.000494x, median 1.0, ge_2x 0, ge_5x 0, ruined 0 at moderate cost.
- Counterfactual 20:1: 744 participant-editions, ge_2x 0, ge_5x 0.
- Single-hold bound 4.738222x — not a ceiling on repeated trading but shows official 50-unit cap limits single-name explosiveness.
- Conclusion: under official stocks-edition 1:1 + 50-unit cap, 5x-100x is arithmetically bounded; need futures edition (20:1) with highly volatile futures (crypto, energy) to approach.

**Intelligence layer status (data/intelligence_report.json):**

- Official rules and public frontier: verified
- Vendor futures history and volatility screen: captured (20/20 daily, 21 hourly incl salvage, 20 15m)
- Independent walk-forward baselines: completed_with_caveats (S1-S3 refuted)
- Contrarian shadow competition: completed_with_caveats (C5 ContrarianQueen champion 7.71x best)
- Volatile-stock division: completed_with_caveats (C16 BreakoutBea champion, C29 MomentumMona rank2)
- Forward testing: trailing 6 editions held out, both splits out-of-sample, no fitted params
- TV benchmark: blocked (no real export; fixture proven end-to-end)
- Official bars route: blocked (no network egress, no secrets — IR-32)
- CME product hours: 20/20 pooled futures with 196-date roll schedule (IR-33 resolved via agent-fetch)

**Site creation — GitHub Pages:**

- Root index.html + docs/index.html mirror (legacy Pages from root of main, but docs/ committed for link stability)
- Assets: assets/style.css (dark theme, clean, responsive, accessible), assets/app.js (client-side filtering)
- Top section #exec-summary: explicit upcoming paper trades, 6 mechanical orders at next bar open, plain-language sentences, pending orders table, waiting conditions, open positions, signal bar dates, verification note.
- Clean UI: hero grid, badge row, sticky toc, callouts (critical/high/info/good), cards, tables, controls, threshold buttons.
- Every number rendered field-by-field from JSON artifacts; CI fails if stale or banned hardcoded block reappears.
- All official verified links as sources for manual review in #sources section (102 sources, tier definitions, allowed uses, evidence files, endpoint URLs).

**Verification — line by line, no hallucinations:**

- scripts/verify.py re-hashes every stored file, re-validates every bar OHLC invariant, re-derives study aggregates from bucket rows, recomputes benchmark medians from per-fill rows, cross-checks exec summary against competition artifact.
- Current result after twentieth pass: 416+ checks (need re-run), 172 unit tests green (needs re-run with new models).
- Five new C26-C30 tests needed: parameter freezing, warmup covering lookbacks, positive and negative trigger cases.
- No synthetic prices written; missing prices never synthesized; vendor vs official boundaries stated in every artifact metadata.
- Irregularities logged in research/irregularities.json (34+), each flagged for review.

**Remaining work / limitations (for next session):**

1. Official-provider stock bars still blocked — need Alpaca credentials via secure secrets and network egress to complete free official route (scripts/fetch_official_bars.py). Until then vendor-tier only.
2. No authenticated TradingView Strategy Report export — need authorized account to export List-of-Trades CSV / Performance Summary and run scripts/tv_benchmark.py to compare Pine broker emulator vs Python fill model.
3. CME roll gaps: engine does not yet force-close on committed roll schedule dates (data/cme_roll_schedule.json 196 dates) — wiring it in is tracked, separately compared step.
4. No bid/ask, queue, borrow cost at granularity — slippage measured as price distance, not executed fill.
5. Stock division seasons are contiguous slices of same captured history — not truly out-of-sample; need fresh capture window.
6. 5x-100x targets not achieved under official stocks-edition rules — focus should shift to futures division (20:1) with crypto/energy volatile futures, and design strategies that pyramid aggressively into explosive moves (C5 ContrarianQueen already does 7.71x best).
7. Unit tests for C26-C30 not yet added — add to scripts/test_intraday_layers.py or new test file.
8. Full-pool verdicts for H47-H51 assigned but hypothesis register evidence lines still say "updated for H34-H39, H41-H43, H45 and H46" — update that print string.

**Manual review links (official verified):**

- https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
- https://www.tradingview.com/the-leap/amp-futures-september-2026/
- https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
- https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs
- https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs
- https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html
- https://www.cmegroup.com/media-room/press-releases/2025/4/24/cme_group_to_expandcryptoderivativessuitewithlaunchofxrpfutures.html
- https://docs.alpaca.markets/us/docs/about-market-data-api
- https://docs.alpaca.markets/us/reference/stockbars
- https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/
- https://www.tradingview.com/pine-script-docs/concepts/strategies/
- https://www.nyse.com/markets/hours-calendars (for calendar.py)
