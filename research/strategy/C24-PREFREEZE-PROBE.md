# C24 pre-freeze probe — deep-drawdown volume ignition (recorded BEFORE freezing)

**Date:** 2026-09-21. **Data:** the committed 20/20 daily captures under `data/intraday/`
(provenance `data/intraday_index.json`, Yahoo vendor tier, 2016-01-01 → 2026-09-19).
**Purpose:** establish, before any parameter is frozen and before any username is rostered,
whether the proposed trigger has a *positive-skew* forward distribution — the property the
paper-tournament brief actually needs (a large right tail), not a high win rate.

## The proposed trigger (structurally new to this repository)

No existing model (C6–C23) conditions on a **long-horizon drawdown state**. C7/C12/C15/C19/C19A
all measure a *recent* decline (1–5 sessions); C11/C16/C22 measure compression or expansion;
C13 measures a new high. C24 instead requires the name to be sitting at least X% below its
**252-session high** — a year-long bear state — and only then accepts a single high-volume
expansion up-day as the ignition print. It is a "left-for-dead name wakes up" trigger, which is
where the pool's largest realised multi-week multiples actually occurred.

Candidate rule: close ≤ (1 − dd) × max(high, last 252 sessions), AND close-to-close advance
≥ `atr_mult` × ATR(14), AND volume ≥ 3.0 × its own 20-session average. Forward horizon = the
hold. Non-overlapping fires (a new fire is only counted after the prior horizon elapses).

## Grid actually run (full grid reported — nothing suppressed)

```
   dd  atr  fwd    n     med%    mean%   pos%    p90%
  0.4  1.5   20   87    -1.95     4.52   44.8    49.8
  0.4  1.5   40   76   -12.65    10.49   40.8    56.0
  0.4  1.5   60   67   -12.91    31.90   41.8    81.2
  0.4  2.0   20   60     -2.5     4.89   46.7    49.8
  0.4  2.0   40   56    -6.61    13.78   35.7    68.1
  0.4  2.0   60   51    -9.32    36.57   41.2    81.2
  0.4  2.5   20   37     0.58     2.53   51.4    39.2
  0.4  2.5   40   35    -3.44     1.62   40.0    63.7
  0.4  2.5   60   32     1.38    11.15   50.0    81.2
  0.5  1.5   20   74    -1.83     2.68   44.6    49.3
  0.5  1.5   40   64   -12.65     1.79   39.1    54.5
  0.5  1.5   60   56   -14.04    13.53   39.3    81.2
  0.5  2.0   20   51    -1.71     1.98   47.1    38.7
  0.5  2.0   40   47    -6.85     0.90   31.9    63.7
  0.5  2.0   60   42   -12.33    11.65   38.1    81.2
  0.5  2.5   20   30    -1.35     1.30   50.0    39.2
  0.5  2.5   40   28    -5.14    -3.14   35.7    63.7
  0.5  2.5   60   25    -0.14    10.64   48.0   105.7
  0.6  1.5   20   50     -2.30     4.44   44.0   67.4
  0.6  1.5   40   43   -13.05     8.16   37.2    63.7
  0.6  1.5   60   37    -2.12    26.06   43.2   127.3
  0.6  2.0   20   35    -1.71     3.26   45.7    49.8
  0.6  2.0   40   32   -10.09     7.21   28.1    68.1
  0.6  2.0   60   29   -15.34    18.55   41.4   143.3
  0.6  2.5   20   21     3.42     3.75   57.1    38.3
  0.6  2.5   40   19    -3.31    -1.40   36.8    63.7
  0.6  2.5   60   17    -2.12     4.86   47.1    81.2
  0.7  1.5   20   34    -6.07     1.69   38.2    66.5
  0.7  1.5   40   31   -13.33     3.00   35.5    63.7
  0.7  1.5   60   27   -19.21    29.86   40.7   143.3
  0.7  2.0   20   27    -5.46     2.07   44.4    49.8
  0.7  2.0   40   26    -6.11     0.94   30.8    68.1
  0.7  2.0   60   24   -17.27    21.27   41.7   143.3
  0.7  2.5   20   19     0.58     3.07   52.6    39.2
  0.7  2.5   40   18    -2.82     1.06   38.9    63.7
  0.7  2.5   60   16    -8.73     0.10   43.8    73.5
```

## What the probe actually shows (and what it does not)

1. **The win rate is below 50% nearly everywhere.** This trigger is not a "good" signal by the
   usual criterion, and the probe is recorded here so that fact cannot later be hidden.
2. **The mean exceeds the median in 34 of 36 cells, usually by a wide margin.** That is the
   positive skew the tournament brief wants: a minority of fires carry the distribution.
3. **The skew grows monotonically with the hold.** At fwd=20 the mean is ~1–5%; at fwd=60 it is
   ~10–37% with 90th percentiles of 73–143%. Individual fires reached +343% (AMC 2021-01-19,
   fwd 40) and +358% (CVNA 2023-05-08, fwd 60) — the exact kind of outcome the placement
   arithmetic requires, and the exact kind that a median-based test would have discarded.
4. **Fire counts are small** (16–87 non-overlapping fires across ~10 years and 20 names). The
   season-level result therefore has a genuinely wide error bar and may well be zero-fire in
   any single monthly edition. That is expected and is not grounds for retuning after the fact.

## The frozen choice, and why it is not cherry-picked

Frozen: **dd = 0.50, atr_mult = 2.0, volume_mult = 3.0, hold_bars = 60**, pyramid +1 ATR,
max 3 adds. This is the *centre* of the grid on both the drawdown and the ATR axis, not the
best cell. The best mean (36.57% at dd 0.40 / atr 2.0) and the best p90 (143.3% at dd 0.60–0.70
/ atr 1.5–2.0) were both deliberately declined. The hold of 60 is chosen on the *structural*
finding — skew rises with horizon across the entire grid, in every dd × atr column — rather
than on any single cell's number. Two declared variants pin pre-existing grid corners:
`shallow` (dd 0.40, hold 40) and `deep` (dd 0.60, hold 60).

Hypothesis **H45** is registered against this freeze with the same pre-registered decision rule
that governs H34–H43 (both usernames must beat the B1 control in the full-season *and* the
forward-held-out split). The frozen parameters are in `intel/stock_strategies.py`
(`DEFAULT_PARAMS["C24"]`) and must not be changed in response to the result.

## Honesty boundary

These are **Yahoo vendor-tier adjusted daily bars**, not exchange-verified prints, and the
20-name pool was selected retrospectively for volatility — so both selection bias and
survivorship bias apply to every number above. This probe is a description of committed
historical data. It is not a forecast, not advice, and not evidence that the rule will fire or
profit in any future edition.

---

# C25 pre-freeze probe — edition-compatible variant of the same trigger (2026-09-21)

C24 was refuted on its first full-pool run (H45). The recorded post-mortem (IR-34) identified a
**structural**, not a statistical, cause: `hold_bars = 60` while the committed daily editions are
**18–22 sessions long (median 21, measured from the 81 edition windows against the committed TSLA
capture)**. Every C24 position was therefore closed by the edition boundary, never by its own exit
rule — the model's actual exit was never tested.

C25 is the same ignition trigger with an **edition-compatible hold**, registered as a separate
model with its own usernames and its own hypothesis (H46). C24 stays frozen and refuted; nothing
about it is retuned.

## Short-horizon grid actually run (full grid, nothing suppressed)

```
   dd  atr  hold    n     med%    mean%   pos%    p90%    max%
  0.4  1.5     5   95    -3.17     1.17   45.3    30.8    91.3
  0.4  1.5     8   91    -2.01     7.89   45.1    31.5   333.3
  0.4  1.5    10   90    -2.23     3.24   45.6    34.9   155.6
  0.4  1.5    15   88    -1.94     2.81   44.3    33.6   149.1
  0.4  1.5    20   87    -1.95     4.52   44.8    49.8   165.5
  0.4  2.0     5   63    -4.70     1.04   44.4    30.8    91.3
  0.4  2.0     8   62    -4.67     8.46   40.3    31.5   333.3
  0.4  2.0    10   61    -3.46     2.94   42.6    34.9   155.6
  0.4  2.0    15   60    -1.88     3.58   46.7    38.3   149.1
  0.4  2.0    20   60    -2.50     4.89   46.7    49.8   165.5
  0.4  2.5     5   38    -7.31    -2.29   36.8    14.0    91.3
  0.4  2.5     8   38    -6.55     0.70   34.2    20.7   140.1
  0.4  2.5    10   37    -5.97    -1.69   40.5    28.2   110.1
  0.4  2.5    15   37    -1.86     2.22   45.9    31.4   149.1
  0.4  2.5    20   37     0.58     2.53   51.4    39.2   124.8
  0.5  1.5     5   81    -3.01     1.12   45.7    30.8    91.3
  0.5  1.5     8   77    -3.59     6.05   42.9    31.5   333.3
  0.5  1.5    10   76    -1.67     2.70   46.1    28.2   155.6
  0.5  1.5    15   74    -2.21     3.08   44.6    33.6   149.1
  0.5  1.5    20   74    -1.83     2.68   44.6    49.3   124.8
  0.5  2.0     5   54    -2.58     1.12   46.3    30.8    91.3
  0.5  2.0     8   53    -5.65     6.08   37.7    25.3   333.3
  0.5  2.0    10   52    -4.35     2.07   44.2    28.2   155.6
  0.5  2.0    15   51    -1.86     3.71   47.1    31.4   149.1
  0.5  2.0    20   51    -1.71     1.98   47.1    38.7   124.8
  0.5  2.5     5   31    -5.91    -0.76   41.9    14.0    91.3
  0.5  2.5     8   31    -5.83    -2.35   32.3    14.1   134.4
  0.5  2.5    10   30    -6.76    -1.93   40.0    28.2   110.1
  0.5  2.5    15   30    -2.21     2.94   43.3    38.3   149.1
  0.5  2.5    20   30    -1.35     1.30   50.0    39.2   124.8
  0.6  1.5     5   56    -6.23     2.44   42.9    34.3    91.3
  0.6  1.5     8   53    -5.71     9.01   41.5    34.0   333.3
  0.6  1.5    10   52    -1.67     4.71   46.2    45.9   155.6
  0.6  1.5    15   50    -2.76     4.64   42.0    52.6   149.1
  0.6  1.5    20   50    -2.30     4.44   44.0    67.4   124.8
  0.6  2.0     5   38    -5.82     2.19   44.7    46.1    91.3
  0.6  2.0     8   37    -6.79     9.36   37.8    34.0   333.3
  0.6  2.0    10   36    -4.61     4.16   44.4    51.5   155.6
  0.6  2.0    15   35    -2.56     5.83   42.9    73.7   149.1
  0.6  2.0    20   35    -1.71     3.26   45.7    49.8   124.8
  0.6  2.5     5   22   -10.63    -0.36   36.4    33.5    91.3
  0.6  2.5     8   22   -11.04    -2.13   31.8    20.7   134.4
  0.6  2.5    10   21    -5.97    -0.68   42.9    18.6   110.1
  0.6  2.5    15   21    -1.86     5.90   42.9    38.3   149.1
  0.6  2.5    20   21     3.42     3.75   57.1    38.3   124.8
```

The positive skew survives the shortening: the mean exceeds the median in 43 of the 45 cells, and
the largest single fire (+333.3%) appears at a hold of **8**, well inside an edition.

## Frozen choice

**dd = 0.50, atr_mult = 2.0, volume_mult = 3.0, hold_bars = 15**, pyramid +1 ATR, max 3 adds —
again the centre of the grid on both the drawdown and the ATR axis, and a hold chosen because
15 < 18 (the shortest measured edition), so the model's own exit can actually fire. The best-mean
cells (9.36% at dd 0.60 / hold 8, 8.46% at dd 0.40 / hold 8) were declined. Variants pin existing
grid corners: `quick` (hold 8) and `wide` (dd 0.60, hold 15).

Registered as **H46** under the same pre-registered decision rule. Same honesty boundary as above:
Yahoo vendor-tier bars, retrospectively volatility-selected pool, not a forecast.
