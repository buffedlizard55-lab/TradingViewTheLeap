# Shadow competition — build evidence (2026-09-17, eighth pass)

Session deliverable: the repository's **own paper competition** ("shadow competition") in which
strategies tracked by **usernames** compete on **real captured price data** under the **official
contest rule constants**, with pre-registered **unique contrarian strategies** targeting the
5x-100x return buckets. This file records what was built, what it proves, and every irregularity
found and fixed during the pass.

## 1. Official sources used (for manual review)

| What | Link | Verified constants used |
|---|---|---|
| Official rules, AMP Futures September 2026 | https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/ | $250,000 start, 20:1 leverage, realized-P/L ranking, section 08 caps, auto-close, no reset, 5 active days |
| Official contest page | https://www.tradingview.com/the-leap/amp-futures-september-2026/ | live leaderboard frontiers (context only) |
| The Leap landing | https://www.tradingview.com/the-leap/ | completed-edition champions (context only) |
| Vendor price captures (committed) | `data/market_history_index.json`, endpoint shape `https://query{1,2}.finance.yahoo.com/v8/finance/chart/<TICKER>?...` | 11 eligible front-month continuous series, 503-504 daily sessions each (2024-09-17 .. 2026-09-17) |

No new network capture was performed in this pass (the sandbox has no direct egress; the evidence
convention here captures pages through the tool path and stores them under `research/evidence/`).
All rule constants were re-read from the committed transcription `data/contest_config.json`
(last re-verified against the official rules in `TV-RULES-AMP-SEP2026-R7.md`, ~23:08 UTC today)
and are re-diffed by `scripts/verify.py` on every run.

## 2. What was built, line by line

1. `intel/contrarian.py` — five pre-registered contrarian models (C1 capitulation reversal,
   C2 gap fade, C3 band-pierce reversion, C4 exhaustion-bar reversal, C5 capitulation pyramider)
   plus declared variants; parameters frozen in `DEFAULT_PARAMS`/`VARIANTS` before any run;
   baselines S1-S3 reuse `intel/strategy.py` unchanged.
2. `intel/competition.py` — portfolio engine under official rule constants: fresh $250,000 per
   participant per edition, 20:1 buying power on total open notional, whole contracts, official
   per-symbol caps from `data/initial_capacity.json`, realized-P/L ranking with end-of-edition
   auto-close, terminal ruin (no resets), min-active-days counted per the official definition.
3. `data/competition/roster.json` — 15 usernames (12 contrarian, 3 trend baselines), each bound
   to a frozen model/variant and an instrument pool drawn only from the 11 eligible captures.
4. `scripts/run_competition.py` — deterministic runner: 24 non-overlapping 30-calendar-day
   season editions + 1 latest-edition live mirror on a shared union calendar; primary scenario
   moderate cost ($1.50/contract/side + 5% ATR slippage per leg), zero-cost robustness run;
   writes `data/competition_results.json`.
5. `scripts/verify.py` — new `check_competition()`: schema, rules-vs-config diff, roster/variant
   validation against the frozen parameter library, eligibility re-derivation from the raw
   captures (>=150 sessions), per-edition sort/rank/multiple/bucket math, aggregate
   re-derivation, target-summary and kind-contrast re-derivation, shell-corruption leak scan,
   and a deterministic engine re-run that must reproduce the committed artifact byte-for-byte.
   Eight new self-test mutations prove the check fires.
6. `scripts/build_site.py` — new `#competition` site section (nav "Shadow comp"): season
   leaderboard by username, latest-edition leaderboard, C1-C5 model cards, assumptions; filter
   wired in `assets/app.js`; dataset render checks extended in `.github/workflows/pages.yml`;
   `make competition` target added.

## 3. Headline results (moderate cost; artifact = data/competition_results.json)

- Season champion by realized P/L: `ContrarianQueen` +$2,806,899.58 over 24 editions
  (0.000173x season multiple — see H30).
- Best single edition: 7.239835x (FadeThePanic, E19 2026-03-11..04-09). Four editions >=5x, all
  contrarian; zero for trend baselines (best baseline edition: 1.881351x).
- Latest edition (2026-08-19..09-17, 21 sessions — the live-mirror window): won by GapGoblin
  +$468,102.43 (2.87241x).
- Ruin: 13/360 participant-editions ruined; 20 realized below -100% (the engine counts but does
  not simulate margin liquidation; declared assumption).
- No participant-edition reached 10x on daily bars. Reaching the captured rank-50 frontier
  (+542.25% at capture 7) was achieved by zero participants in any edition.

## 4. Irregularities found and fixed in this pass (IR-26)

A shell-expansion corruption event had mangled dollar amounts in previously committed research
text (`$0.00` -> `/bin/bash.00`; `$2.5M` -> `.5M`; `$1,244,313.50` -> `,244,313.50`;
`+$111,303.63` -> `+11,303.63`; etc.). Every affected value was uniquely reconstructable from
capture-7 evidence and restored line by line:

- `research/hypotheses/hypotheses.json`: H27 (5 tokens), H25 (6 tokens), H26 (1 token)
- `research/irregularities.json`: IR-25 (4 amounts)
- `research/sources/sources.json`: TV-CONTEST-AMP-SEP2026-R7 note (3 amounts)
- `index.html`: regenerated from the fixed registers

`scripts/verify.py` now fails on any `/bin/bash` or `(.5M` signature in published text, and the
self-test proves the check fires.

## 5. Verification state at end of pass

- `python3 scripts/verify.py` — green (0 failures; 1 pre-existing warning: IR-22, the
  newly-listed SIC1! vendor/snapshot quote delta).
- `python3 scripts/verify.py --self-test` — green: every check, including the eight new
  shadow-competition mutations, provably fires on corrupted data.
- `python3 -m unittest discover -s scripts -p "test_*.py"` — green.
- Site rebuilt from data; `index.html` byte-fresh (CI freshness check would fail otherwise).
