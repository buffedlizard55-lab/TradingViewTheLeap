# Strategy research and testing plan

**Status:** research design complete; TradingView Strategy Report runs not performed.

This plan is for a virtual-money competition. Its objective is extreme simulated net profit, not
real-money capital protection. Account survival, margin feasibility, and rule compliance are still
constraints because the competition account cannot be reset and only its final realized P/L is
ranked.

## 1. Verified operating envelope

| Fact | Live-edition value | Authority |
|---|---:|---|
| Competition window | 2026-09-01 08:00 UTC → 2026-09-30 12:00 UTC | Official rules §08 |
| Registration closes | 2026-09-23 08:00 UTC | Official rules §04 and contest FAQ |
| Starting balance | 250,000 virtual USD | Official rules §08 |
| Futures leverage | 20:1 | Official rules §08 |
| Maximum initial notional | 5,000,000 USD (balance × leverage) | Derived and verifier-checked |
| Active-day requirement | At least 5 UTC days with an opening or closing action | Official rules §08 |
| Ranking metric | Realized P/L on closed positions | Official rules §08 |
| Public leaderboard | Ranks 1–250 are displayed; prizes extend through rank 300 | Contest page and rules §09 |
| Position caps | Symbol-specific; `SOL1!` is 1 contract | Official rules §08 |
| End handling | Open positions are automatically closed and included in final P/L | Official rules §08 |
| Transaction ceiling | 60 or more order/position transactions per minute is prohibited | Official rules §08 |

The machine-readable version is [`data/contest_config.json`](../../data/contest_config.json). It is
the source of truth for the site and verifier.

## 2. What the public evidence does and does not establish

- The captured completed-champion sample proves that simulated returns above 10x have occurred in
  futures editions. It does **not** identify the trades, model, leverage path, or drawdown that made
  those returns.
- The live leaderboard is a moving snapshot, not a final threshold. Exceeding a currently displayed
  rank does not guarantee that rank at the deadline or establish prize eligibility.
- Closing a position changes P/L from open to realized; it does not create extra economic profit.
  The same entry and exit have the same final P/L regardless of how often the leaderboard observes
  it. Realized losses can reduce cumulative realized P/L.
- Cap × multiplier measures dollar P/L per underlying point only. It is not a volatility estimate.
  Price, the 20:1 buying-power limit, direction, market movement, spread, liquidity, and fill behavior
  also matter.
- The current public board stops at rank 250. The rank-300 frontier cannot be observed from the
  public page even though ranks through 300 can receive a prize.

## 3. TradingView research tools

1. **Standard candlestick chart:** use standard prices. TradingView warns that non-standard chart
   prices can make strategy simulations unrealistic.
2. **Pine Strategy Report:** run
   [`the-leap-hypothesis-lab.pine`](the-leap-hypothesis-lab.pine), one candidate model and one
   eligible symbol at a time.
3. **Deep Backtesting:** extend the historical sample where the account plan and symbol support it.
4. **Bar Magnifier:** keep it enabled when available to improve the broker emulator's intrabar fill
   assumptions.
5. **Properties:** set initial capital to the rulebook balance, long/short margin to 5% (the inverse
   of 20:1), whole-contract quantity within the symbol cap, and explicit commission and slippage
   scenarios.
6. **Forward testing:** after selecting a model without using the holdout data, observe it on realtime
   bars. Do not call this live account execution.
7. **Paper Trading competition account:** use it only for contest execution. Official TradingView
   documentation states that Pine strategies cannot directly place orders in the built-in Paper
   Trading account or an integrated broker account.

The official documentation links are registered as `TV-PINE-STRATEGIES`, `TV-PINE-LEVERAGE`, and
`TV-PINE-AUTOTRADE` in the source registry.

## 4. Pre-registered candidate models

The exact hypotheses, entries, exits, and falsification rules are machine-readable in
[`models.json`](models.json). All three are currently **untested**:

- **S1 — Donchian trend breakout:** prior-channel break + EMA direction + ATR expansion.
- **S2 — EMA impulse continuation:** EMA crossover + ATR expansion.
- **S3 — Bollinger squeeze release:** bandwidth compression followed by an envelope break.

Each model can trade long or short. None predicts today's direction, promises a return, or has a
published result in this repository.

## 5. Capacity screen before alpha testing

Use [`data/initial_capacity.json`](../../data/initial_capacity.json) only as a feasibility screen.
For each selected symbol it computes:

```text
contract notional = captured continuous-contract price × contract multiplier
whole contracts allowed initially = min(rule cap, floor(5,000,000 / contract notional))
modeled notional = whole contracts allowed × contract notional
P/L for a favorable 1% underlying move = modeled notional × 1%
required favorable move = target realized P/L / modeled notional
```

This arithmetic narrows where an extreme P/L is even numerically plausible at the initial balance.
It is not an expected-return ranking. The table intentionally does not normalize by historical
volatility because no licensed, consistent intraday history for all 94 eligible symbols is stored
in this repository.

## 6. Controlled test protocol

### T1 — Data and chart controls

- Run only an eligible symbol from [`data/contest_universe.json`](../../data/contest_universe.json).
- Record the exact TradingView symbol, timeframe, chart type, contract/continuous-series setting,
  timezone, model commit, Properties values, and test timestamps.
- Treat continuous-contract rolls as a possible source of artificial signals. Where licensed data
  is available, compare TradingView results with CME's official settlement-based continuous series.

### T2 — Walk-forward design

- Freeze one parameter grid before reading holdout results.
- Use repeated rolling windows: a training segment, a validation segment, then a untouched
  30-calendar-day holdout that matches the contest horizon.
- Advance the window and repeat across different volatility regimes and across all selected symbols.
- Keep every run, including failures. Selecting only the best symbol/window is selection bias.

The segment lengths and parameter grid are experimental assumptions, not rulebook facts. They must
be declared in the result artifact before a run receives a verdict.

### T3 — Cost and fill sensitivity

Run each frozen configuration under at least three declared scenarios:

1. Strategy Report defaults.
2. Nonzero commission and slippage.
3. Higher slippage plus stricter limit-fill verification.

The competition rules do not state a commission schedule. Therefore zero commission may be a
platform setting, but it must not be silently treated as proof of cost-free fills. Paper Trading P/L
uses bid/ask mechanics, while the Pine broker emulator is a separate simulation.

### T4 — Outcome metrics

For every 30-day holdout save:

- net profit USD and `1 + net_profit / 250,000` return multiple;
- closed trades, profitable-trade percentage, average trade, and profit factor;
- maximum equity drawdown and any margin-call events as feasibility diagnostics;
- long/short split and symbol concentration;
- whether net profit exceeded the **captured** rank-250 P/L, with snapshot timestamp;
- whether the equity multiple crossed 5x, 10x, 20x, 50x, or 100x.

Historical market multiples in `data/volatile_stocks.json` are trough-to-later-peak adjusted-close
ratios. They are not Strategy Report returns and must never be mixed into these outcome fields.

### T5 — Decision rules

- Mark a model **supported** only after out-of-sample results reproduce across multiple windows and
  symbols, remain positive under declared costs, and survive nearby-parameter sensitivity.
- Mark it **refuted** when its registered falsification rule fires.
- Leave it **inconclusive** when the sample is too small, data is inconsistent, or results are
  dominated by one window.
- A single explosive backtest is a lead for audit, not validation. Check lookahead bias, selection
  bias, roll gaps, fill assumptions, and overfitting first.

### T6 — Forward test and contest separation

- Forward-test the frozen model before relying on it.
- Keep Strategy Report results labeled **hypothetical broker-emulator results**.
- Keep competition-account outcomes labeled **The Leap simulated results**.
- Do not claim automated execution: Pine cannot submit directly to the built-in competition account.
- Stay below the explicit transaction prohibition and re-read the official rules before every
  edition, because caps, leverage, balance, symbols, and prizes change.

## 7. Why no model result is published yet

The repository environment can read public pages and generate Pine source, but it has no
TradingView login, chart session, Pine compiler, realtime entitlement, Strategy Report export, or
competition account. Inventing performance numbers would violate the evidence standard. The honest
state is therefore: **candidate models implemented; platform backtests and forward tests not run**.
