"""Walk-forward protocol: rolling 30-calendar-day windows, aggregation, verdicts.

Implements section 6 (T2/T4/T5) of research/strategy/testing-plan.md:

- non-overlapping 30-calendar-day holdout windows per symbol, each starting with a
  fresh 250,000 USD account, stepping across the captured history;
- because the pre-registered models have NO fitted parameters (defaults frozen in
  the Pine source and in intel.strategy.DEFAULT_PARAMS), every window is
  out-of-sample: nothing was optimised on any window;
- nearby-parameter sensitivity runs are declared in SENSITIVITY_GRID below and
  were frozen before any result was computed;
- verdicts follow each model's registered falsification rule plus the plan's T5
  decision rules.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from .backtest import COST_SCENARIOS, WindowResult, simulate_window
from .data import Bar
from .strategy import generate_signals, warmup_bars, DEFAULT_PARAMS

WINDOW_DAYS = 30          # contest horizon: Sep 1 08:00 -> Sep 30 12:00 UTC
STEP_DAYS = 30            # non-overlapping windows
MIN_WINDOW_BARS = 15      # a window with fewer valid sessions is discarded
MIN_SERIES_BARS = 150     # a symbol needs at least this many bars to be tested
BOOTSTRAP_SEED = 1729
BOOTSTRAP_RESAMPLES = 10_000

# Frozen BEFORE any result was computed. Each entry: (params_label, params dict).
SENSITIVITY_GRID = {
    "S1": [
        ("channel15", {"channel_length": 15}),
        ("channel25", {"channel_length": 25}),
    ],
    "S2": [
        ("ema15x40", {"fast_length": 15, "slow_length": 40}),
        ("ema25x60", {"fast_length": 25, "slow_length": 60}),
    ],
    "S3": [
        ("band15", {"band_length": 15}),
        ("band25", {"band_length": 25}),
    ],
}

SIZING_MODES = ("compounding", "initial_fixed")


@dataclass
class SymbolInput:
    symbol: str
    bars: list[Bar]
    contract_multiplier: float
    rules_cap_contracts: int


def rolling_windows(bars: list[Bar], warmup_index: int) -> list[tuple[str, str]]:
    """Non-overlapping (start_date, end_date) pairs covering the tradable history."""
    out: list[tuple[str, str]] = []
    if len(bars) <= warmup_index:
        return out
    first = date.fromisoformat(bars[warmup_index].date)
    last = date.fromisoformat(bars[-1].date)
    start = first
    while start + timedelta(days=WINDOW_DAYS - 1) <= last:
        end = start + timedelta(days=WINDOW_DAYS - 1)
        lo = next(i for i, b in enumerate(bars) if b.date >= start.isoformat())
        hi = max(i for i, b in enumerate(bars) if b.date <= end.isoformat())
        if hi - lo + 1 >= MIN_WINDOW_BARS:
            out.append((start.isoformat(), end.isoformat()))
        start += timedelta(days=STEP_DAYS)
    return out


def run_symbol(
    inp: SymbolInput,
    model: str,
    *,
    scenario_key: str,
    sizing: str,
    params: Optional[dict] = None,
    params_label: str = "default",
    target_usd: float,
) -> list[WindowResult]:
    params = params or DEFAULT_PARAMS
    warmup = warmup_bars(model, params)
    signals = generate_signals(inp.bars, model, params)
    windows = rolling_windows(inp.bars, warmup)
    scenario = COST_SCENARIOS[scenario_key]
    from . import indicators as ind

    highs = [b.high for b in inp.bars]
    lows = [b.low for b in inp.bars]
    closes = [b.close for b in inp.bars]
    atr_series = ind.atr(highs, lows, closes, DEFAULT_PARAMS["atr_length"])

    results = []
    for start_d, end_d in windows:
        hi = max(i for i, b in enumerate(inp.bars) if b.date <= end_d)
        final_atr = atr_series[hi] or 0.0
        results.append(
            simulate_window(
                inp.bars,
                signals,
                symbol=inp.symbol,
                model=model,
                scenario=scenario,
                sizing=sizing,
                params_label=params_label,
                contract_multiplier=inp.contract_multiplier,
                rules_cap_contracts=inp.rules_cap_contracts,
                start_date=start_d,
                end_date=end_d,
                target_usd=target_usd,
                final_atr=final_atr,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def bootstrap_median_ci(values: list[float], seed: int = BOOTSTRAP_SEED,
                        resamples: int = BOOTSTRAP_RESAMPLES) -> tuple[float, float]:
    """Percentile bootstrap 95% CI of the median (deterministic seed)."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(values)
    medians = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        medians.append(statistics.median(sample))
    medians.sort()
    lo = medians[int(0.025 * resamples)]
    hi = medians[min(resamples - 1, int(0.975 * resamples))]
    return (lo, hi)


def aggregate(windows: list[WindowResult]) -> dict:
    profits = [w.net_profit_usd for w in windows]
    multiples = [w.equity_multiple for w in windows]
    trades = sum(len(w.trades) for w in windows)
    wins = sum(1 for w in windows if w.net_profit_usd > 0)
    med = statistics.median(profits) if profits else None
    mean = statistics.fmean(profits) if profits else None
    ci = bootstrap_median_ci(profits) if profits else (None, None)
    by_symbol: dict[str, list[float]] = {}
    for w in windows:
        by_symbol.setdefault(w.symbol, []).append(w.net_profit_usd)
    best = max(windows, key=lambda w: w.net_profit_usd) if windows else None
    worst = min(windows, key=lambda w: w.net_profit_usd) if windows else None
    return {
        "windows": len(windows),
        "trades": trades,
        "positive_windows": wins,
        "positive_windows_pct": round(100.0 * wins / len(windows), 2) if windows else None,
        "median_net_profit_usd": round(med, 2) if med is not None else None,
        "mean_net_profit_usd": round(mean, 2) if mean is not None else None,
        "bootstrap95_median_ci_usd": [round(ci[0], 2), round(ci[1], 2)]
        if profits else None,
        "best_window": {
            "symbol": best.symbol, "start": best.start_date, "end": best.end_date,
            "net_profit_usd": round(best.net_profit_usd, 2),
            "equity_multiple": round(best.equity_multiple, 4),
            "trades": len(best.trades),
        } if best else None,
        "worst_window": {
            "symbol": worst.symbol, "start": worst.start_date, "end": worst.end_date,
            "net_profit_usd": round(worst.net_profit_usd, 2),
            "equity_multiple": round(worst.equity_multiple, 4),
            "trades": len(worst.trades),
        } if worst else None,
        "windows_ge_5x": sum(1 for m in multiples if m >= 5),
        "windows_ge_10x": sum(1 for m in multiples if m >= 10),
        "windows_ge_20x": sum(1 for m in multiples if m >= 20),
        "windows_ge_50x": sum(1 for m in multiples if m >= 50),
        "windows_ge_100x": sum(1 for m in multiples if m >= 100),
        "ruined_windows": sum(1 for w in windows if w.ruined),
        "total_skipped_entries": sum(w.skipped_entries for w in windows),
        "total_margin_breach_bars": sum(w.margin_breach_bars for w in windows),
        "long_trades": sum(w.long_trades for w in windows),
        "short_trades": sum(w.short_trades for w in windows),
        "by_symbol_median_net_profit_usd": {
            sym: round(statistics.median(v), 2) for sym, v in sorted(by_symbol.items())
        } if by_symbol else {},
    }


def concentration_check(windows: list[WindowResult]) -> dict:
    """Does the pooled result depend on a single symbol or a single window?"""
    if not windows:
        return {"single_symbol_dependent": None, "single_window_dependent": None}
    profits = [w.net_profit_usd for w in windows]
    pooled_median = statistics.median(profits)

    by_symbol: dict[str, list[float]] = {}
    for w in windows:
        by_symbol.setdefault(w.symbol, []).append(w.net_profit_usd)
    best_symbol = max(by_symbol, key=lambda s: statistics.median(by_symbol[s]))
    rest = [p for s, v in by_symbol.items() if s != best_symbol for p in v]
    sym_dep = statistics.median(rest) <= 0 if rest else True

    best_window_profit = max(profits)
    rest_w = [p for p in profits if p != best_window_profit]
    win_dep = statistics.median(rest_w) <= 0 if rest_w else True

    return {
        "pooled_median_usd": round(pooled_median, 2),
        "best_symbol": best_symbol,
        "median_excluding_best_symbol_usd": round(statistics.median(rest), 2) if rest else None,
        "single_symbol_dependent": sym_dep,
        "median_excluding_best_window_usd": round(statistics.median(rest_w), 2) if rest_w else None,
        "single_window_dependent": win_dep,
    }
