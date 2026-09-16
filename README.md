# TradingView The Leap — Verified Research & Instrument Intelligence

An evidence-first research layer for [TradingView's *The Leap*](https://www.tradingview.com/the-leap/)
paper trading competition. Every number in this repository traces to an official source that you can
open and check. Nothing is estimated, interpolated, or written from memory.

**Live site:** https://buffedlizard55-lab.github.io/TradingViewTheLeap/ — GitHub Pages in legacy
mode, published from the repository root of `main` (regenerate with `python3 scripts/build_site.py`).

---

## Start here: the findings

Verified against official sources on **2026-09-16 UTC — two independent passes on the same day**:
the original capture, then a full line-by-line re-fetch of every source (all TradingView contest
pages, all 20 CME contract spec pages, all 16 Yahoo endpoint windows) with zero substantive
changes and two recorded vendor drifts (`IR-09` participant counter, `IR-13` NVDA re-adjustment).
Details and citations in [`research/`](research/) and on the site.

| # | Finding | Evidence |
|---|---|---|
| 1 | **The live contest contains no stocks.** The permitted instrument list is 94 futures contracts and zero equities. A stocks-only strategy cannot be executed in the running edition. | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| 2 | **"Risk management is not necessary" is arithmetically false.** At 20:1 leverage on $250,000, max notional is $5,000,000. A 5.00% adverse move equals the entire balance — and the rules forbid resetting the account. | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| 3 | **Stocks editions produce the *smallest* winning returns** of any asset class: 1.299x and 1.1758x. Futures editions reach 53.2072x. | [The Leap landing page](https://www.tradingview.com/the-leap/) |
| 4 | **Position caps bind, not volatility.** `CME:SOL1!` is capped at 1 contract (500 SOL); reaching the current rank-1 profit needs a $4,607.45 per-SOL move. | Rules §08 + [CME contract specs](https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html) |
| 5 | **≥10x is real and officially recorded** — +5,220.72% (53.2072x) in Feb 2025, and +921.49% (10.2149x) live at day 16 of 30. Both are futures. | [The Leap landing page](https://www.tradingview.com/the-leap/) |
| 6 | **Explosive stock returns are real, archived and recomputable.** Eight trough→peak close multiples captured from Yahoo Finance chart data — GME 124.11x, MSTR 49.45x, PLTR 34.53x, AMC 30.07x, SMCI 22.66x, TSLA 17.02x, NVDA 12.09x, COIN 10.0x — each window-bounded and re-derived by the verifier from archived endpoint values. Vendor data (not official), kept in its own module. | `data/volatile_stocks.json` + `research/evidence/VOLATILE-STOCKS-YAHOO-*.md` |
| 7 | **The leaderboard is ranked by absolute realized USD, not percent** — so compounding a winning balance is the direct multiplier on every future point, and only *closed* P/L counts (hourly snapshot). This is the exploitable structure; the full operational test protocol is in [`research/strategy/testing-plan.md`](research/strategy/testing-plan.md). | [Rules §06–§07](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) + live leaderboard |
| 8 | **Automation is a documented ban risk.** Rules §08 warn that "using various scripts" and ≥60 transactions/minute trigger a 1-hour+ paper-trading ban. A "no manual input" strategy is only viable *inside* that ceiling — the test plan caps order rate at ≤12/min with human confirmation. | [Rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) → `IR-12` (critical) |

### Verified threshold counts — contest records (official)

Across 16 sourced #1-finisher records:

| Target | Verified cases |
|---|---|
| ≥ 5x | 2 |
| ≥ 10x | 2 |
| ≥ 20x | 1 |
| ≥ 50x | 1 |
| **≥ 100x** | **0** |

**No 100x *contest* outcome is attested by any official source.** The verified ceiling is
53.2072x. See `IR-03`.

### Verified threshold counts — stock price multiples (market-data vendor)

Across the 8 archived trough→peak close multiples (`data/volatile_stocks.json`):

| Target | Verified stocks |
|---|---|
| ≥ 5x | 8 |
| ≥ 10x | 8 |
| ≥ 20x | 5 |
| ≥ 50x | 1 |
| **≥ 100x** | **1 (GME, 124.11x close-to-close, 2020-04-03 → 2021-01-27)** |

These are multi-year market-price moves from a commercial data vendor — evidence of what extreme
volatility has done, not contest returns and not tradeable in the futures-only live contest.

---

## Repository layout

```
research/
  sources/sources.json        Source registry (39 sources). A claim may only cite an id registered here.
  evidence/*.md               Verbatim quotations per source, with URL, access date and tier.
  hypotheses/hypotheses.json  12 hypotheses: claim, prediction, test executed, evidence, verdict.
  strategy/testing-plan.md    Operational test protocol: how to place on the live leaderboard.
  irregularities.json         13 flagged items for human review, severity-ranked.
data/
  contest_universe.json       All 94 permitted instruments + position caps, from rules §08.
  master_list.json / .csv     20 candidate entries. Multipliers now sourced for all 20.
  verified_explosive_returns.json  16 sourced #1 net-profit records + threshold analysis.
  volatile_stocks.json        8 verified trough→peak stock multiples (vendor-tier data).
scripts/
  verify.py                   Line-by-line verifier with a self-test that proves each check fires.
  build_site.py               Renders index.html at the repo root from the audited JSON.
index.html                    GitHub Pages output (generated; do not hand-edit).
assets/style.css, app.js      Site styling and table filtering.
.github/workflows/pages.yml   Verifies data, fails on a stale site, and audits the rendered page.
```

### Why the site lives at the repository root

This repository's GitHub Pages site is configured in **legacy** mode against branch `main` at
path `/`. Switching it to Actions-based deployment needs `pages:write`, which the available
credential does not have:

```
PUT /repos/buffedlizard55-lab/TradingViewTheLeap/pages
-> 403 Resource not accessible by integration
```

Because legacy Pages builds from the root of `main`, `build_site.py` writes `index.html` and
`assets/` there, so the site publishes on merge to `main` with **no settings change and no deploy
job**. To move to Actions-based deployment, a repository admin can run
`gh api -X PUT repos/buffedlizard55-lab/TradingViewTheLeap/pages -f build_type=workflow` and
restore an upload/deploy job.

---

## Verify it yourself

```bash
python3 scripts/verify.py             # 203 checks
python3 scripts/verify.py --self-test # + 21 corruption tests proving each check can fail
python3 scripts/build_site.py         # regenerate the site
make serve                            # local preview on :8000
```

The verifier enforces:

- every cited `source_id` exists in the registry
- official-tier sources resolve to official domains; vendor-tier sources resolve to allowed
  vendor domains and must carry `official_source: false` (a vendor can never be laundered official)
- every declared count in every `_meta` block equals the real row count
- every master-list symbol is in the verified universe, with a cap matching the rules value
- `max exposure` recomputes as `cap × multiplier`; `move needed` recomputes as `rank-1 P/L ÷ exposure`
- **every stock multiple recomputes as `peak adjclose ÷ trough adjclose` from archived endpoint
  values**, is flagged window-bounded, and cites vendor-tier sources only
- **any non-null contest return multiple must carry a start price, end price, window and price source, or the build fails**
- every contest return multiple recomputes as `1 + pct/100`
- the live leaderboard is internally consistent: `$ = balance × (multiple − 1)`
- every hypothesis and irregularity is traceable to registered sources

Negative control confirmed: corrupting `max_underlying_exposure` on `ML-2026-09-16-01` makes the
verifier exit 1 and name the row. The `--self-test` run additionally corrupts one field at a time
(including a stock multiple and a vendor source's honesty flag) and asserts each check fires.

---

## Honesty policy

The brief asked for highly volatile **stocks** with verified 5x–100x returns. This was delivered,
with two honesty constraints made explicit rather than hidden:

1. **The live contest permits no stocks** (`IR-01`), so the stock research is a separate module —
   it informs the brief but cannot be executed in the running futures-only edition.
2. **Stock price history comes from a market-data vendor (Yahoo Finance), not an exchange or
   regulator.** Every stock multiple is therefore registered under a `market_data_vendor` tier,
   flagged `official_source: false`, and kept out of any contest or rulebook claim. The verifier
   recomputes each multiple as `peak adjclose ÷ trough adjclose` from the archived endpoint values
   in `data/volatile_stocks.json`, so no figure is trusted that cannot be re-derived.
3. **The official rules warn against scripted activity** (`IR-12`, critical). The brief asked for
   no manual input; the rules say unattended high-frequency scripting risks a 1-hour+ ban and
   disqualification. Both statements are true at the same time — the test plan resolves this by
   capping the order rate at ≤12 transactions/minute (83% under the 60/min threshold) and keeping
   a human confirmation step on batched orders.

Each stock multiple is **window-bounded** — the extreme inside a documented fetch window, not a
guaranteed all-time extreme. Where a longer history contradicted a locator (`IR-11`, SMCI), the
claim was narrowed, never stretched. A row is cheaper to add later than a fabricated number is to
retract.

**Contract multipliers are now verified for all 20 of 20 entries** against CME Group primary
sources (spec pages + the Solana/XRP guides). `max exposure` and the required underlying move are
computed for every row. See `research/evidence/CME-CONTRACT-SPECS-BATCH2.md`.

---

## Known limits

- **`verify.py` itself does not touch the network.** The sandbox blocks direct `curl`/`wget`, so
  evidence is captured through the agent's fetch tool and written to `research/evidence/`. The
  verifier audits that captured evidence for traceability and recomputes every derived number;
  it cannot re-fetch a page to prove a quotation is still live. Re-run the capture step to refresh.
- **Single snapshot:** 2026-09-16 UTC. The live leaderboard moves hourly; contest parameters change
  between editions (`IR-05` shows a position cap moving 100x between consecutive futures editions).
- **Stock price data is vendor-tier.** Yahoo Finance is a commercial data vendor, not an exchange.
  It supports only the recomputable stock records, never a contest or rulebook claim.
- **Stock multiples are window-bounded**, not guaranteed all-time extremes. `IR-11` documents a case
  (SMCI) where the longer history corrected the locator and the claim was narrowed accordingly.

---

## Disclaimer

This is a research and verification layer for a paper-trading competition run with virtual money.
Every figure is a published historical competition result, a value read from official rules, or
arithmetic on those values. **Nothing here is investment advice or a return forecast.** Historical
results in a simulated environment say nothing about future results, and the documented 20:1
leverage can eliminate the entire account on a 5% adverse move.

TradingView is not affiliated with this repository; it is named only because it organises the
competition.
