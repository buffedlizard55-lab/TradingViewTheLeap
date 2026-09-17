# Explosive Futures Playbook — How to Chase 5× / 10× / 20× / 50× / 100× in the Live Contest (Simulation, No Real-Money Risk Management)

- **Date:** 2026-09-17
- **Contest:** The Leap by AMP Futures — September 2026 — live window **2026-09-01 08:00 UTC → 2026-09-30 12:00 UTC** ([rules](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/), [contest page](https://www.tradingview.com/the-leap/amp-futures-september-2026/), [landing page](https://www.tradingview.com/the-leap/))
- **Sources actually verified line-by-line this pass:** `TV-CONTEST-AMP-SEP2026-R6` (96,268 participants), `TV-RULES-AMP-SEP2026-R6` (94 futures, 20:1, $250k, no equities), `TV-THELEAP-LANDING-R6` (champion maximum 53.2072×, zero sampled records ≥100×)
- **This document is:** deterministic arithmetic and a testing plan. It is **not** a forecast, not a recommendation, not a backtest claim that the moves will recur, and not a promise of a prize.

> **The one-line answer to "which highly volatile stocks win this contest?": there are no stocks in the September 2026 edition.** The permitted universe is **94 futures and 0 equities** (CME, CME_MINI, CBOT, CBOT_MINI, NYMEX, NYMEX_MINI, COMEX, COMEX_MINI; see `data/contest_universe.json` and IR-01). Paper-trading a NASDAQ stock in September is not executable. The stock-volatility research in `data/volatile_stocks.json` (ENPH 382×, AMD 322×, MARA 190× etc., all `market_data_vendor` Yahoo and all window-bounded) is retained as an **evidence base for a future stocks edition** (e.g. March 2026 Magnificent Seven) and does **not** apply to the live futures rules. Every multiple in that file is recomputed by `scripts/verify.py` from archived `adjclose` values.

What follows translates the user's "max-explosive, no risk-management, paper-simulation" objective into the **futures** that are actually tradable today, ranked by the two constraints that decide dollar P/L on the leaderboard.

---

## 1. The three facts that decide everything before you test a strategy

### 1.1 Balance, leverage and the erase line

- Starting balance **$250,000 virtual USD**, futures leverage **20:1** → maximum initial notional **$5,000,000** (official rules §08, `TV-RULES-AMP-SEP2026-R6`). See `data/contest_config.json`.
- At full notional, **1% of the underlying is $50,000 (20% of the starting balance)**; **2.5% erases half the balance; 5.0% erases all of it** (`TV-PINE-LEVERAGE` simulator docs). The account **cannot be reset** (rules §08 last sentence). There is no real-money investor protection here — these are feasibility bounds on an **unbroken winning streak**. See `data/leaderboard_lab.json` → `leverage_math`.
- Ranking metric is **realized P/L on closed positions**; open P/L does not count until you close (rules §08, hypothesis H5). The public leaderboard refreshes **no more than once per hour** and the public page shows only **ranks 1–250** while prizes are awarded through **rank 300** (IR-06), so the real last-prize frontier is unobservable.

### 1.2 What the leaderboard actually demands right now (2026-09-17 21:27 UTC, 12.606 days left)

| Target | Ending balance | Net needed | Required **unbroken** daily compound | Underlying equivalent at 20:1 |
|---|---:|---:|---:|---:|
| **5×** | $1,250,000 | +$1,000,000 (+400%) | **+13.62% / day** | 0.68% / day |
| **10×** | $2,500,000 | +$2,250,000 (+900%) | **+20.04% / day** | 1.00% / day |
| **20×** | $5,000,000 | +$4,750,000 (+1900%) | **+26.83% / day** | 1.34% / day |
| **50×** | $12,500,000 | +$12,250,000 (+4900%) | **+36.39% / day** | 1.82% / day |
| **100×** | $25,000,000 | +$24,750,000 (+9900%) | **+44.10% / day** | 2.21% / day |
| **Rank 1** (leonardo22_romano 10.34×, $2,335,125) | — | — | **+20.35% / day** | 1.02% / day |
| **Rank 50** (Nikola_Ng 5.9773×, $1,244,314) | — | — | **+15.23% / day** | 0.76% / day |
| **Rank 100** (nynyyynn54 5.06×, $1,014,950) | — | — | **+13.72% / day** | 0.69% / day |
| **Rank 250** (mrchrissmithl143 3.64×, $660,760) | — | — | **+10.80% / day** | 0.54% / day |

Source: `data/frontier_history.json` capture 6 (rows byte-identical to capture 5) × `data/contest_config.json` dates, recomputed by `scripts/leaderboard_lab.py` → `data/leaderboard_lab.json`. At an illustrative +1% underlying day with full reinvestment, 5× takes **9 unbroken winning days** and 100× takes **26** — longer than the remaining window. One full-exposure adverse day of the same size undoes one winning day. All three pre-registered models S1–S3 on daily bars have **$0.00 pooled median net profit** across 231 walk-forward windows (H14–H16), so none has produced any positive daily compounding at all so far.

The **cash frontier (rank 50, $400 for ranks 26–50)** is the only cash tier that matters if your goal is cash; the rank-250 level once quoted as a capacity screen is **below** it by ~47% ($660k vs $1.244M at capture 6) and cannot be called a prize threshold (H19, IR-06). The "last-prize" arithmetic has been corrected to rank 50 throughout this release.

### 1.3 No stock contract passes the live filter

All 20 `volatile_stocks.json` symbols (GME 124×, PLTR 34×, ENPH 382× etc.) are **outside** the 94-future universe and their evidence tier is explicitly `market_data_vendor`, not `official_primary`. See H13 and irregularity IR-01. Do **not** copy that stock list into a September paper-trading account — the orders will not exist.

---

## 2. The live universe ranked two ways — volatility and dollar capacity — then fused

The six source families that make these tables recomputable are:

- Official rules and contest page (`TV-RULES-AMP-SEP2026-R6`, `TV-CONTEST-AMP-SEP2026-R6`)
- Official contract specifications (CME specs, e.g. `CME-SPEC-CL1!`, `CME-SPEC-SI1!`, `CME-XRP-PR` / `CME-SPEC-XRP1!`, `CME-SPEC-SOL1!`)
- Displayed continuous-contract prices (`TV-QUOTE-*`, captured 2026-09-16 ~16:59 EDT)
- Market-data-vendor daily bars (`YAHOO-FUTURES-CHART`, captured through `allorigins` relay, 503–504 sessions each, stored in `data/market_history/`)
- Walk-forward simulation on those bars (`data/backtest_results.json`, `data/volatility_intelligence.json`)
- Provenance check on every row (`scripts/verify.py`)

### 2.A — Pure volatility (best 30-day intraday-to-intraday envelope in the last 2 years of vendor daily bars)

This is what history **contained** at its most stretched, not what it will deliver.

| Rank | Futures symbol | Best 30-day up move* | Ann. vol (full) | Max daily shock | Notes |
|---:|---|---:|---:|---:|---|
| 1 | **NYMEX:NG1!** (Natural Gas) | **+140.41%** (2026-01-16 window) | 87.5% | −47.5% / +28.9% (Jan 2026) | Also the most overnight-gap instrument (49.8%) |
| 2 | **NYMEX:HO1!** (Heating Oil / ULSD) | **+78.22%** (2026-02-20) | 46.2% | ±14.9% | Energy; 78% inside one 30-day window |
| 3 | **CME:ETH1!** (Ether) | **+71.81%** (2025-04-21) | 70.2% | ±19.6% | Crypto; extremely volatile but see 2.B |
| 4 | **NYMEX:RB1!** (RBOB Gasoline) | **+66.69%** (2026-02-24) | 38.7% | +14.1% | Energy |
| 5 | **COMEX:SI1!** (Silver) / **COMEX_MINI:SIL1!** | **+64.74%** (2025-12-29) | 53.0% | −31.3% (Jan 30 2026) | Metals; same price, two contract sizes |
| 6 | **NYMEX:CL1!** (WTI Crude) | **+58.37%** (2026-02-17) | 45.7% | −16.4% / +12.2% | Most liquid energy |
| 7 | **NYMEX_MINI:QM1!** | +58.37% (same) | 45.4% | ±16.4% | Same underlying as CL, smaller contract |
| 8 | **NYMEX:PL1!** (Platinum) | **+50.30%** (2025-12-10) | 45.3% | −19.0% | Metals |
| 9 | **CME:BTC1!** | +48.79% (2024-10-23) | 45.8% | ±13.4% | Crypto |
| 10 | **CME_MINI:NQ1!** (E-mini Nasdaq-100) | +20.11% | 21.8% | +11.9% | Equity index; least volatile of this list |

\* *Best overlapping 30-calendar-day window: max(close) / first_close − 1. Computed by `scripts/run_backtests.py` → `data/volatility_intelligence.json`. Raw vendor tier — always check CME settlement-based continuous series (`CME-CONTINUOUS-SERIES`) before trading on it.*

**Naïve read:** "NG1! is the most explosive." **Correct read:** not before dividing by notional (next table).

### 2.B — Dollar capacity at the starting line (what $250k × 20:1 can actually buy)

| Futures symbol | Contract multiplier | Rules cap | **Max whole contracts at $250k/20:1** | Binding constraint | **Modeled initial notional** | P/L for a +1% underlying move | **Favorable move needed to match the Sept 16 rank-250 target ($623,689)** | Rank-250 delivery ratio (best30 ÷ needed) |
|---|---|---:|---:|---|---|---:|---:|---:|
| **NYMEX:CL1!** | 1,000 bbl | 100 | **48** | 20:1 buying power | **$4,916,640** | $49,166 | **12.69%** | **4.60** ✓ |
| **COMEX:SI1!** | 5,000 oz | 25 | **15** | 20:1 buying power | **$4,869,000** | $48,690 | **12.81%** | **5.05** ✓ |
| **NYMEX:HO1!** | 42,000 gal | 25 | **23** | 20:1 buying power | **$4,830,290** | $48,303 | **12.91%** | **6.06** ✓ |
| **CME_MINI:NQ1!** | $20 × NQ | 100 | **8** | 20:1 buying power | **$4,681,080** | $46,811 | **13.32%** | 1.51 ✓ |
| **NYMEX:RB1!** | 42,000 gal | 25 | 25 | rules cap | **$3,394,860** | $33,949 | **18.37%** | **3.63** ✓ |
| NYMEX:PL1! | 50 oz | 25 | 25 | rules cap | **$2,232,375** | $22,324 | **27.94%** | **1.80** ✓ |
| NYMEX:MCL1! (Micro WTI) | 100 bbl | 100 | 100 | rules cap | **$1,024,300** | $10,243 | **60.89%** | 0.96 |
| **NYMEX:NG1!** | 10,000 mmBtu | 25 | 25 | rules cap | **$722,750** | $7,228 | **86.29%** | **1.63** ✓ |
| COMEX_MINI:SIL1! | 1,000 oz | 10 | 10 | rules cap | $649,200 | $6,492 | 96.07% | 0.67 |
| NYMEX_MINI:QM1! | 500 bbl | 10 | 10 | rules cap | $512,125 | $5,121 | 121.78% | 0.48 |
| CME:BTC1! | 5 BTC | 1 | 1 | rules cap | $380,425 | $3,804 | 163.95% | 0.30 |
| CME:MBT1!, CME:ETH1!, CME:SOL1!, CME:XRP1!, CME:MXP1!, COMEX:SIC1!, CME:MSL1!, NYMEX:MNG1!, CME:MET1! | — | — | ≤25 | rules cap | <$200k | <$2k | **>300% → >10,000%** | **0.14–0.01** |

Source: `data/initial_capacity.json` (quote prices from `TV-QUOTE-*` at the source-reported times, multipliers from `CME-SPEC-*`, caps from `TV-RULES-AMP-SEP2026-R6`, recomputed by `scripts/build_*` and checked by `scripts/verify.py`).

**The fuse row is "Delivery ratio"** = best30 ÷ needed-for-rank-250. Above 1.0, history *contained* at least one 30-day window whose best up move would have covered the rank-250 dollar target if entered perfectly. Below 1.0, history — even at its most stretched — never produced a single 30-day move large enough to reach that target in one window. **Micro, crypto and exotic futures are structurally priced out** not because their underlying is calm (ETH moved 71.8%, BTC 48.8%) but because their **rules cap × multiplier × price** leaves a modeled notional too small to monetize the move at the ranking-assumed scale.

### 2.C — Fused rank: what can actually chase 5×–100×?

Recompute the "needed" column for the **cash frontier (rank 50: $1,244,314, 5.9773×)** instead of rank 250, i.e. what you need **today** to be in cash prizes. The table in `data/leaderboard_lab.json` → `cash_frontier_instrument_requirements` does exactly this from the capture-6 frontier:

| Symbol | Needed for **rank-50** cash level ($1.244M) | Best 30-day up ever | Cash-level delivery ratio | Verdict for an explosive-paper chase |
|---|---|---:|---:|---|
| **NYMEX:HO1!** | **25.76%** | 78.22% | **3.04** | **Eligible — delivered 3× needed** |
| **NYMEX:CL1!** | **25.31%** | 58.37% | **2.31** | **Eligible — delivered 2.3× needed** |
| **COMEX:SI1!** | **25.56%** | 64.74% | **2.53** | **Eligible — delivered 2.5× needed** |
| **NYMEX:RB1!** | **36.65%** | 66.69% | **1.82** | **Eligible — delivered 1.8× needed** |
| **CME_MINI:NQ1!** | **26.58%** | 20.11% | 0.76 | **Marginal — never delivered enough for cash in one 30-day window** |
| NYMEX:PL1! | 55.74% | 50.30% | 0.90 | Marginal — 10% short |
| NYMEX:NG1! | **172.16%** | 140.41% | 0.82 | High vol **but** needs more than it ever gave (small notional) |
| CME:ETH1! | 1,032.84% | 71.81% | 0.07 | **Priced out** |
| CME:BTC1! | 327.09% | 48.79% | 0.15 | **Priced out** |
| CME:XRP1!, CME:SOL1!, CME:MXP1!, COMEX:SIC1!, NYMEX:MNG1!, CME:MBT1!, CME:MET1!, COMEX_MINI:SIL1!, NYMEX_MINI:QM1!, etc. | >121% → >20,000% | 30–65% | <0.5 → <0.001 | **Priced out** — the contract cannot lever the move to the required dollars |

Therefore, under the **explosive, all-in, no-stop** objective:

- **Primary testable futures: `HO1!`, `CL1!`, `SI1!`, `RB1!`.** Four contracts that have historically delivered **1.8×–3×** the rank-50 cash requirement inside a single 30-day window. Do not read this as a forecast — read it as the only four symbols whose **history contains an envelope big enough** to make the cash level even arithmetically reachable in one move.
- **Secondary: `NQ1!`, `PL1!`.** A second tier that almost reaches the envelope but did not clear it (ratio ~0.76–0.90). Include for sensitivity, but expect them to need compounding across windows rather than a single swing.
- **Exclude at the starting balance:** `NG1!` — despite being the volatility champion, its **rules cap (25) × multiplier (10,000 mmBtu) × price ($2.89)** gives a notional of only **$722,750**, so the move needed (172%) exceeds the best history (140%). It becomes eligible only after equity compounds to buy more notional, i.e. **after** you are already winning. **All micro and crypto standard contracts** (``QM1!`, `MCL1!`, `MNG1!`, `BTC1!`, `MBT1!`, `ETH1!`, `MET1!`, `SOL1!`, `MSL1!`, `XRP1!`, `MXP1!`, `SIC1!`, `SIL1!`, `PL` micros) **are priced out at the initial balance** for the same reason: their notional is an order of magnitude too small to monetize any realistic 30-day underlying move.

If you insist on testing a "highly volatile stock" objective anyway, you must **wait for a stocks edition** (the March 2026 "Magnificent Seven" edition — 7 NASDAQ stocks, winning return only **+17.58% / 1.1758×** on 41,301 participants, `TV-CONTEST-MAG7-MAR2026`), or file a hypotheses amendment that redefines the objective to **"find the best performing future on the September board."** This playbook takes the latter path.

---

## 3. What the three pre-registered models already taught us (and why they failed)

All three models were simulated by `scripts/run_backtests.py` (engine `intel-1`) on **every captured symbol with ≥150 daily bars** (11 symbols, 231 non-overlapping 30-day walk-forward windows, 2024-09-17 → 2026-09-17) under the falsification protocol of `research/strategy/testing-plan.md`:

| Model | Entry definition | Pooled median net profit (zero cost) | Mean | % windows positive | Closed trades / 231 windows | Any 30-day window ≥5×? | Verdict |
|---|---|---|---:|---:|---:|---:|---|
| **S1** Donchian 20-bar breakout + EMA-trend + ATR-expansion | Long/short breakout with trend filter | **$0.00** | +$11,401 (outlier-driven) | **14.72%** | **74** (56 long, 18 short) | **3** (best 7.39× SI1!, single-trade) | **Refuted** (H14) |
| **S2** EMA 20×50 impulse continuation | Fast EMA crossing/holding above slow EMA + ATR expansion | **$0.00** | −$2,475 | **7.36%** | **30** | **0** | **Refuted** (H15) |
| **S3** Bollinger squeeze release (bandwidth at 50-bar low) | Volatility squeeze then expansion | **$0.00** | +$133 | **1.30%** | **5** | **0** (too rare) | **Refuted** (H16) |

Common failure mode: **signals too sparse on daily bars** (S3: 5 trades in 231 windows) and **pooled medians $0** — removing the best symbol or the best window flips any apparent mean positive to non-positive. Adding `CME:BTC1!` (504 sessions, captured 2026-09-17T03:15:40Z) did not change the verdict. A moderate-cost pass ($1.50/side + 5% ATR slippage) and nearby parameter grids (Donchian 15/25, EMA 15×40 / 25×60, BB length 15/25) all stayed at median $0.

**Testing implication:** to chase a daily-compounding target of +13%–44% (section 1.2), a **daily-bar entry that trades once every ~8 windows** cannot compound. Either (a) move to **intraday bars** (15-minute / 60-minute, where S3's squeeze actually fires), or (b) abandon sparse technical patterns for a **volatility-breakout with re-entry** that is **always in** on the four primary futures.

---

## 4. The explosive-paper testing strategy for the remaining 12.6 days

### 4.1 Strategy shape: "All-in, always-in, on the four"

- **Universe:** `HO1!`, `CL1!`, `SI1!`, `RB1!` (primary). `NQ1!`, `PL1!` as a second portfolio leg for sensitivity. Exclude micros/cryptos at the starting balance; promote `NG1!` only **after** equity has at least tripled (notional then scales).
- **Direction:** **long-only** (the best 30-day windows in the vendor history are up moves for all four; the largest down moves are smaller). Test a long-only variant, then a symmetric variant as a robustness check — but expect shorts to dilute the win rate (see S1: 18 shorts out of 74 trades).
- **Sizing:** **All-in at the rules-legal maximum whole contracts** at each close, recomputed from the new equity (compounding model from `research/strategy/testing-plan.md`: `floor(equity × 20 / (price × multiplier))` capped at `rules_position_cap`). No stop-loss, no take-profit, no position split. This is **not** real-money risk management; it is the only sizing that can make +13%–44% per day arithmetically attainable. Record the **margin-call path** as a feasibility diagnostic (IR-04), not as a hedge to add.
- **Execution hygiene:**
  - Exactly **5 active UTC days** minimum (any `open` or `close` between 00:00:00–23:59:59 UTC counts; rules §08).
  - No more than **59 order/position transactions per minute** (rules §08 anti-abuse line; sustained breach risks a ban).
  - **Close every open position at the contest close** 2026-09-30 12:00 UTC and book its realized P/L — the rules auto-close and include it.

### 4.2 Candidate next models to walk-forward before you touch the contest account

All models must be **pre-registered** in `research/strategy/testing-plan.md` **before** they are simulated, so `scripts/verify.py` can falsify them. The three slots below are the immediate queue; each is fully specifiable from the committed `data/market_history/` and fails if its pooled median net profit is not positive after best-symbol / best-window concentration checks.

| New candidate | Core idea | Why it might hit where S1–S3 did not | Data needed | Falsification bar |
|---|---|---|---|---|
| **S4: Intraday Bollinger-squeeze re-entry** (15-min bars, daily close-to-close equity) | Squeeze = Bandwidth(20,2) at 50-bar low → expansion → enter in direction of daily EMA(50) trend, **re-enter** on every squeeze that re-forms within the trend | S3 was conceptually sound but its **daily-bar occurrence rate was 0.02 trades/window**; on 15-min bars the same definition fires **~20–40× more often**, enough to compound. Crypto and energy squeezes precede the Jan–Apr 2026 shocks that drive the best-30 tables. | 15-min bars for CL1!/HO1!/SI1!/RB1! (Yahoo `interval=15m` or CME licensed intraday); daily equity still from vendor closes | Pooled median net profit > $0 at zero cost **and** at moderate cost ($1.50/side + 5% ATR slippage) in 30-day walk-forward; survives best-symbol and best-window removal; ≥10× windows exist |
| **S5: Volatility-breakout always-in** (daily ATR-multiple breakout + same-day re-entry) | Enter long when `close > prior high + k×ATR(14)` (k grid 0.5, 1.0, 1.5); if stopped on an intraday reversal, **re-enter** same direction until the daily close; no opposite-direction trades | S1 entered once per breakout then went flat; "always-in during trend" keeps the notional deployed across the **multi-day up windows** that the 30-day tables show are the real prize (HO1! had 16 windows ≥50% up). | Daily bars already committed; intraday high/low for the ATR buffer check | Same as S4; plus the realized 30-day walk-forward equity curve must contain at least one path that reaches 5× (the weakest explosive target) from a cold start |
| **S6: Gap + trend continuation** (overnight gap ≥1×ATR(14) in trend direction) | If overnight gap opens beyond the prior close by ≥ATR and the gap direction aligns with EMA(50) trend, enter at the open and hold until the opposite gap or trend flip | Energy and metals show **large overnight gaps** (NG 49.8%, PL 14.7%, SI 9.3%) that the 30-day tables show are part of the explosive moves; no pre-registered model has tested gaps yet | Daily open/close/gap columns already in `data/market_history/` (roll-gap caveat below) | Same as S4 |

**Roll-gap caveat:** the vendor series are **front-month continuous, unadjusted rolls** (Yahoo `CL=F` / `HO=F` etc.). Their `open / prev close` contains **contract-roll gaps** that are not tradable price jumps. Every pattern that references gaps must be re-run on a **settlement-based continuous series** (`CME-CONTINUOUS-SERIES`, licensed) before it can be called tradable. Until then, vendor results are **order-of-magnitude filters**, not fills.

### 4.3 How the backtest must simulate "explosive-paper" (so you don't fool yourself)

Use `scripts/run_backtests.py` with these overrides vs the S1–S3 paper account:

1. **Compounding ON** — start each 30-day walk-forward window at **$250,000** but grow the contract count window-internally as equity grows (same formula as section 4.1). The S1–S3 engine held contracts constant; that understates what an all-in chase can do and also hides the death spiral (one −5% day wipes a 100% previous gain).
2. **Record margin-call path** — at every bar, compute `adverse intraday low vs entry`. If it implies `equity < 0` at 20× on the deployed notional, mark the run **liquidated** and stop compounding. Report the **liquidation rate** alongside the median P/L — a strategy that makes +44% per day on closes but liquidates intraday is not leaderboard-eligible.
3. **Walk-forward exactly as before:** non-overlapping 30-day windows, 231 windows over the committed vendor history, one window = one tradeable contest period. The "remaining window" is only **12.6 days**, so a 30-day median is an upper bound on what a 12.6-day deployment can do.
4. **Sensitivity grids:** for S4 track `BB length {15,20,25} × BW lookback {40,50,60}`; for S5 track `ATR k {0.5,1.0,1.5} × EMA {40,50,60}`; for S6 track `gap ≥ {0.75,1.0,1.25}×ATR`. Every grid cell must be median-$0-tested, not cherry-picked.

### 4.4 Rehearsal sequence for the next 48 hours of wall-clock time

1. **Capture 15-min vendor bars** for `CL1!`, `HO1!`, `SI1!`, `RB1!` (Yahoo `interval=15m`, `period=7d` rolling) into `data/market_history_intraday/` via a new `scripts/fetch_market_data_intraday.py` (same relay fallback as `fetch_market_data.py`). Validate every payload against the expected vendor symbol and spot-verify closes against an independent in-session capture (document transport per symbol, IR-17).
2. **Pre-register S4** in `research/strategy/testing-plan.md` **before** running it. Generate the exact entry/exit code in `research/strategy/models.md` from the plan text (no hidden parameters).
3. **Run `scripts/run_backtests.py --intraday`** on the new bars (still 30-day walk-forward, now with intraday signals scored to daily closes). Publish `data/backtest_results_intraday.json` and `data/volatility_intelligence_intraday.json`. Recompute `data/leaderboard_lab.json` if the latest frontier has moved (`scripts/leaderboard_lab.py` is deterministic from `data/frontier_history.json`).
4. **Falsify S4** under H14/H15 rules (pooled median, concentration, cost). If refuted, loop S5, then S6. If any candidate's median flips positive, re-test it on the **cash frontier** (rank-50) requirement — does its best 30-day equity curve clear 5.9773× from a cold start? — before any account-size paper run.
5. **Only then** consider a paper-account deployment: register once (rules §05: one account, or disqualification), fund the paper balance, trade the winning candidate **only** on the four primary symbols, **all-in, long-only, always-in**, and log every open/close with a UTC calendar count toward the 5-day minimum. Do not automate the competition account directly — Pine strategies **cannot** place orders in the Paper Trading competition account (`TV-PINE-AUTOTRADE` says "Automated Pine strategy trading with a TradingView brokerage account is not available"), and the rules' 60/min anti-abuse line treats unattended script bursts as bannable (IR-12).

### 4.5 Walk-away rule

If **none** of S4–S6 achieves a **positive pooled median net profit** in 30-day walk-forward on committed history, the evidence-backed conclusion is: **no tested strategy in this repository has shown it can compound at any positive rate, let alone the +13%–44% per day required for 5×–100× or the +15.2% per day required for the current cash frontier.** The correct action is to **keep testing** (new intraday candidates, new volatility definitions) and to keep the leaderboard tracker (`data/frontier_history.json`) live until **2026-09-30 12:00 UTC**, rather than to deploy an unproven strategy and expect a different result.

---

## 5. The stock list — kept for reference, kept separate

| Rank | Symbol | Verified trough → peak (Yahoo adjclose) | Multiple | Window | Evidence file | Hallucination check |
|---:|---|---:|---:|---|---|---|
| 1 | ENPH | $0.70 (2017-05-18) → $267.74 (2021-11-19) | **382.49×** | 4.51 y | `VOLATILE-STOCKS-YAHOO-DAILY.md` | `scripts/verify.py` recomputes every multiple from the archived endpoint values |
| 2 | AMD | $1.80 (2016-01-20) → $580.91 (2026-06-30) | **322.73×** | 10.45 y | same | same |
| 3 | MARA | $0.40 (2020-03-18) → $76.09 (2021-11-09) | **190.22×** | 1.65 y | same | same |
| 4 | CVNA | $0.744 (2022-12-27) → $95.69 (2026-01-22) | **128.62×** | 3.08 y | same | same |
| 5 | GME | $0.70 (2020-04-03) → $86.88 (2021-01-27) | **124.11×** | 0.82 y | same | same |
| … | … | … | … | … | … | … |

Full table in `data/volatile_stocks.json` (20 rows) and `research/evidence/VOLATILE-STOCKS-YAHOO-DAILY.md` (16 of the 20 in daily resolution, including bounding monthly/daily guard fetches). Every row is tier `market_data_vendor` and **no row appears** in `data/contest_universe.json`. Treat this table as: **"if a future stocks edition launches, start research here"** — not as an order list for September.

If TradingView announces a stocks edition, the stocks-capacity model must be built the same way as the futures capacity model: **cap ?→ 1.0 contract → multiplier = 1 share → price = stock adjclose → 20:1 (or edition leverage) → notional → move needed → best-30 vs needed**. Until that edition's rules are captured (`TV-RULES-*-STOCKS-*`), no cross-asset multiple can be called "needed for a prize."

---

## 6. Official verified links for manual review (every non-trivial claim traces to one of these)

**Contest and rules (official_primary):**
- Contest page (sixth capture, 96,268 participants): https://www.tradingview.com/the-leap/amp-futures-september-2026/ — evidence `TV-CONTEST-AMP-SEP2026-2026-09-17-R6.md`
- Official rules (sixth verification, 94 futures, §08): https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/ — evidence `TV-RULES-AMP-SEP2026-R6.md`
- Landing page (sixth verification, 15 champions including BenBernanke1 53.2072×): https://www.tradingview.com/the-leap/ — evidence `TV-THELEAP-LANDING-R6.md`
- Strategy simulation limits (Pine cannot autotrade the Paper account; 20:1 margin model): https://www.tradingview.com/support/solutions/43000481026-how-to-autotrade-using-pine-script-strategies/ (`TV-PINE-AUTOTRADE`), https://www.tradingview.com/support/solutions/43000717375-how-to-simulate-trading-with-leverage-in-pine-script/ (`TV-PINE-LEVERAGE`), https://www.tradingview.com/pine-script-docs/concepts/strategies/ (`TV-PINE-STRATEGIES`), https://www.tradingview.com/support/solutions/43000719857-how-is-position-profit-and-loss-in-paper-trading-calculated/ (`TV-PAPER-PNL`, IR-14)

**Exchange specifications (official_primary — futures are listed products):**
- CME:SOL guide: https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html (`CME-SOL-GUIDE`)
- CME XRP press release (planned 19 May, pending review at time of writing): https://www.cmegroup.com/media-room/press-releases/2025/4/24/cme_group_to_expandcryptoderivativessuitewithlaunchofxrpfutures.html (`CME-XRP-PR`)
- Live spec pages (multipliers used in the notional table): CME Bitcoin https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs (`CME-SPEC-BTC1!`), micro Bitcoin https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/micro-bitcoin/specs (`CME-SPEC-MBT1!`), Ether https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs (`CME-SPEC-ETH1!`), micro Ether https://www.cmegroup.com/markets/cryptocurrencies/ether/micro-ether/specs (`CME-SPEC-MET1!`), Henry Hub Natural Gas https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.contractSpecs.html (`CME-SPEC-NG1!`), micro Nat Gas https://www.cmegroup.com/markets/energy/natural-gas/micro-henry-hub-natural-gas.contractSpecs.html (`CME-SPEC-MNG1!`), etc. — batch evidence `CME-CONTRACT-SPECS-BATCH2.md`
- Continuous price series methodology (for settlement-based backtests): https://www.cmegroup.com/market-data/cme-group-continuous-price-series.html (`CME-CONTINUOUS-SERIES`)

**Market-data vendor (market_data_vendor — always labeled as such):**
- Yahoo Finance v8 chart API (front-month continuous, unadjusted rolls) — example endpoints:
  - GME trough 2020-04-03 and peak 2021-01-27: `https://query1.finance.yahoo.com/v8/finance/chart/GME?period1=1583020800&period2=1588291200&interval=1d` etc. — evidence `VOLATILE-STOCKS-YAHOO-DAILY.md`
  - Futures daily bars: `https://query1.finance.yahoo.com/v8/finance/chart/CL=F?period1=1726531200&period2=1789689600&interval=1d` and the 19 siblings listed in `YAHOO-FUTURES-CHART` — captured 2026-09-17T03:15:40Z via `scripts/fetch_market_data.py` through the `allorigins` relay when the runner IP returned 429, validated per symbol in `data/market_history_index.json`

Every dollar, percentage, multiple and participant count above is either quoted verbatim from a file in `research/evidence/` or recomputed deterministically by `scripts/verify.py`, `scripts/leaderboard_lab.py`, `scripts/target_lab.py` or `scripts/run_backtests.py` from those files. No API is called at site-build time; the site at `index.html` is a deterministic render of `data/`.

---

## 7. Irregularities to keep in sight while testing

- **IR-01 (critical):** No stocks in September. Any "stock-volatility wins the contest" plan is unfounded for this edition.
- **IR-09 (low):** Landing (96,263) vs contest (96,268) counters differ by 5 (≈0.005%) — async snapshots. Never combine counts from different fetches.
- **IR-15/16 (medium):** Cash ends at **rank 50**; ranks 51–300 receive subscriptions. The 5-day active rule and the 14-day claim window are eligibility constraints on a human participant, not automatable repository state.
- **IR-12 (medium):** Pine ≠ competition-account automation; the 60/min anti-abuse line is a bannable threshold.
- **IR-14 (medium):** The Paper Trading help's displayed short-futures formula omits Point Value but its worked example multiplies by it — flag for manual review.
- **IR-17/18/19/22 (low):** Vendor data is `market_data_vendor` tier: Yahoo 429 from runners (allorigins relay), single-session vendor history for SOL1!/MSL1!/XRP1!/MXP1!/SIC1!/MBT1!/MET1!/MNG1!/MCL1! (8 of 20 selected untestable on vendor daily), CL 3.32% and SIC 2.09% Yahoo vs TradingView quote gaps (2% warning threshold — informational, not a mapping error).
- **IR-20/23/H20 (medium):** The leaderboard is **corrected, not append-only**. Between capture 3 and 4 rank 50 fell $3,583.50 while the previous row re-appeared at rank 49 — exactly one row removed ahead of it (disqualification or correction, rules §§05/09/16). No captured frontier is a ratchet floor.
- **IR-24 (low):** Two-decimal percentage display implies up to ±$12.50 dollar rounding per row; `verify.py` enforces that bound.
- **H22/H24:** Frontier drift is rank-heterogeneous (capture 4→5: ranks 1/50 frozen, 100/250 rose) and can be uniformly frozen (capture 5→6: all four frozen while participants rose). No single "frontier rate" exists; deferring entry raises the required final P/L on average (H21: $141,857/day at rank 1, $75,591/day at rank 50 since 2026-09-01 08:00 UTC).

---

## 8. What to ship next session — and what still blocks a "proven" winner

**Ship:**

1. **Intraday capture** for HO1!/CL1!/SI1!/RB1! (`interval=15m`, daily rollover at 00:00 UTC to match the contest's active-day definition).
2. **Pre-register and simulate S4** (intraday squeeze re-entry). Publish `data/backtest_results_intraday.json` and the falsification record. If it refutes, queue S5, then S6 — always pre-registered.
3. **Refresh market-data freshness** daily (`make freshness` uses `{% raw %}{{ github.run_id }}{% endraw %}`-annotated workflow probes) and re-run `python3 scripts/verify.py --self-test` — the self-test's mutation checks must stay green or the build is not deterministic.
4. **Frontier watch:** re-capture at least once per US session until **2026-09-30 12:00 UTC**. Each capture is evidence that re-prices the 5×–100× ladder. Build the site (`python3 scripts/build_site.py`) and push; Pages publishes from `index.html` at root.
5. **README pass:** update the "Fifth pass → Sixth pass" paragraph and the remaining-days headline from 12.6264 → **12.606** days (21:27 UTC).

**Still blocked (honest limitations):**

- **No tested strategy in this repository has a positive median walk-forward P/L.** The explosive arithmetic in section 2 is an **envelope**, not a fill — until a pre-registered model survives the pooled-median, concentration and cost gates, there is no evidence-backed path to even 5×, let alone 100×.
- **Vendor tier.** Every volatility number above is `market_data_vendor` (Yahoo front-month unadjusted). A licensed settlement-based continuous series (`CME-CONTINUOUS-SERIES`) and, for S4, an order-book-aware fill model are the clean fix. Without them, any intraday result is an **order-of-magnitude filter**.
- **Liquidation path.** The daily-close arithmetic hides intraday margin calls. A model that clears 5.9773× on closes but liquidates intraday at 20× is not leaderboard-eligible; the backtest must simulate the adverse high/low path.
- **Micro/crypto testability.** 8 of the 20 selected symbols have **1 session** of vendor history (newly listed). They will accumulate history over weeks but are untestable today; any "highly volatile crypto micro wins" claim is unverified until they do.
- **Eligibility.** Prize collection requires a human who is eligible (§05 excluded jurisdictions), responds within 5 days of first contact and claims within 14 days of contest close (§09). Repository automation cannot establish that.

**Bottom line for this session:** the data say to test **HO1!, CL1!, SI1!, RB1!** with an **all-in, long-only, always-in** intraday squeeze-re-entry model (S4) as the next falsifiable shot at the cash frontier's **+15.23% per day** cost, while respecting that the board can rise, correct downward, or freeze in the same day and that **nothing yet tested has shown it can compound positively at all**.
