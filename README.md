# TradingView The Leap — Verified Research & Instrument Intelligence

An evidence-first research layer for [TradingView's *The Leap*](https://www.tradingview.com/the-leap/)
paper trading competition. Every number in this repository traces to an official source that you can
open and check. Nothing is estimated, interpolated, or written from memory.

**Live site:** see GitHub Pages for this repository (built from `site/`).

---

## Start here: the five findings

Verified against official sources on **2026-09-16 UTC**. Details and citations in
[`research/`](research/) and on the site.

| # | Finding | Evidence |
|---|---|---|
| 1 | **The live contest contains no stocks.** The permitted instrument list is 94 futures contracts and zero equities. A stocks-only strategy cannot be executed in the running edition. | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| 2 | **"Risk management is not necessary" is arithmetically false.** At 20:1 leverage on $250,000, max notional is $5,000,000. A 5.00% adverse move equals the entire balance — and the rules forbid resetting the account. | [Official rules §08](https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/) |
| 3 | **Stocks editions produce the *smallest* winning returns** of any asset class: 1.299x and 1.1758x. Futures editions reach 53.2072x. | [The Leap landing page](https://www.tradingview.com/the-leap/) |
| 4 | **Position caps bind, not volatility.** `CME:SOL1!` is capped at 1 contract (500 SOL); reaching the current rank-1 profit needs a $4,607.45 per-SOL move. | Rules §08 + [CME contract specs](https://www.cmegroup.com/articles/2025/the-essential-guide-to-solana-futures.html) |
| 5 | **≥10x is real and officially recorded** — +5,220.72% (53.2072x) in Feb 2025, and +921.49% (10.2149x) live at day 16 of 30. Both are futures. | [The Leap landing page](https://www.tradingview.com/the-leap/) |

### Verified threshold counts

Across 16 sourced records:

| Target | Verified cases |
|---|---|
| ≥ 5x | 2 |
| ≥ 10x | 2 |
| ≥ 20x | 1 |
| ≥ 50x | 1 |
| **≥ 100x** | **0** |

**No 100x outcome is attested by any official source.** The verified ceiling is 53.2072x. See
`IR-03`.

---

## Repository layout

```
research/
  sources/sources.json        Source registry. A claim may only cite an id registered here.
  evidence/*.md               Verbatim quotations per source, with URL, access date and tier.
  hypotheses/hypotheses.json  9 hypotheses: claim, prediction, test executed, evidence, verdict.
  irregularities.json         10 flagged items for human review, severity-ranked.
data/
  contest_universe.json       All 94 permitted instruments + position caps, from rules §08.
  master_list.json / .csv     20 candidate entries. Sourced or explicitly null — never guessed.
  verified_explosive_returns.json  16 sourced #1 net-profit records + threshold analysis.
scripts/
  verify.py                   Line-by-line verifier with a self-test that proves each check fires.
  build_site.py               Renders site/index.html from the audited JSON.
site/                         GitHub Pages output (generated; do not hand-edit index.html).
.github/workflows/pages.yml   Verifies, fails on stale site, publishes to Pages.
```

---

## Verify it yourself

```bash
python3 scripts/verify.py             # 71 checks
python3 scripts/verify.py --self-test # + 16 corruption tests proving each check can fail
python3 scripts/build_site.py         # regenerate the site
make serve                            # local preview on :8000
```

The verifier enforces:

- every cited `source_id` exists in the registry, and every registered source is on an official domain
- every declared count in every `_meta` block equals the real row count
- every master-list symbol is in the verified universe, with a cap matching the rules value
- `max exposure` recomputes as `cap × multiplier`; `move needed` recomputes as `rank-1 P/L ÷ exposure`
- **any non-null return multiple must carry a start price, end price, window and price source, or the build fails**
- every return multiple recomputes as `1 + pct/100`
- the live leaderboard is internally consistent: `$ = balance × (multiple − 1)`
- every hypothesis and irregularity is traceable to registered sources

Negative control confirmed: corrupting `max_underlying_exposure` on `ML-2026-09-16-01` makes the
verifier exit 1 and name the row.

---

## Honesty policy

The brief asked for highly volatile **stocks** with verified 5x–100x returns. Two things made that
impossible to deliver honestly, so it was not delivered:

1. The live contest permits **no stocks** (`IR-01`).
2. **No single-stock multiple could be confirmed against a primary source** in this session, so no
   such figure was written down. The `verified_historical_return_multiple` column is null for all 20
   entries, and the verifier fails the build if it is ever populated without full price provenance.

A row is cheaper to add later than a fabricated number is to retract.

Contract multipliers are verified for 4 of 20 entries (`SOL1!`, `MSL1!`, `XRP1!`, `MXP1!`), against
CME Group primary sources. The other 16 are `null` and flagged. Closing those is the highest-value
next step.

---

## Known limits

- **No network in the build sandbox.** Outbound TLS fails for `tradingview.com`, `stooq.com` and
  `query1.finance.yahoo.com` (verified by direct `curl`). The verifier audits captured evidence for
  traceability and arithmetic; it cannot re-fetch a page to prove a quotation is still live.
- **Single snapshot:** 2026-09-16 UTC. The live leaderboard moves hourly; contest parameters change
  between editions (`IR-05` shows a position cap moving 100x between consecutive futures editions).
- **Two sources are registered without a captured evidence file** and are leads only. The verifier
  reports these as standing warnings.

---

## Disclaimer

This is a research and verification layer for a paper-trading competition run with virtual money.
Every figure is a published historical competition result, a value read from official rules, or
arithmetic on those values. **Nothing here is investment advice or a return forecast.** Historical
results in a simulated environment say nothing about future results, and the documented 20:1
leverage can eliminate the entire account on a 5% adverse move.

TradingView is not affiliated with this repository; it is named only because it organises the
competition.
