"""Signal generation for the three pre-registered candidate models.

This module replicates, bar for bar, the logic of
``research/strategy/the-leap-hypothesis-lab.pine`` (Pine Script v6):

- S1 "Donchian breakout": close > prior 20-bar Donchian high, fast EMA above slow
  EMA, and ATR above baseline*factor -> long (short: mirror).
- S2 "EMA impulse": fast/slow EMA crossover while ATR is expanding -> long
  (short: crossunder).
- S3 "Squeeze release": bandwidth was compressed near its 50-bar rolling floor,
  bandwidth now expanding, close above the upper Bollinger band -> long
  (short: below the lower band).

Signals are evaluated on a bar's close. Fills happen on the NEXT bar's open in
the backtest engine, matching Pine's default broker-emulator behaviour for
market orders (``process_orders_on_close`` is not enabled in the Pine source).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import indicators as ind
from .data import Bar

DEFAULT_PARAMS = {
    "fast_length": 20,
    "slow_length": 50,
    "channel_length": 20,
    "atr_length": 14,
    "atr_baseline_length": 50,
    "atr_expansion_factor": 1.05,
    "band_length": 20,
    "band_deviation": 2.0,
    "squeeze_lookback": 50,
}

MODEL_IDS = ("S1", "S2", "S3")


@dataclass
class Signal:
    index: int          # bar index the signal was evaluated on
    date: str           # UTC date of that bar
    direction: str      # "long" | "short"
    atr: float          # ATR at the signal bar (for slippage and brackets)


def _prepare(bars: list[Bar], params: dict) -> dict:
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]

    fast_ema = ind.ema(closes, params["fast_length"])
    slow_ema = ind.ema(closes, params["slow_length"])
    atr_series = ind.atr(highs, lows, closes, params["atr_length"])
    # ta.sma over a series containing na is na until its window is fully defined.
    atr_base = _sma_respecting_nones(atr_series, params["atr_baseline_length"])

    prior_high = ind.shift(ind.highest(highs, params["channel_length"]), 1)
    prior_low = ind.shift(ind.lowest(lows, params["channel_length"]), 1)

    basis = ind.sma(closes, params["band_length"])
    dev = ind.stdev(closes, params["band_length"])
    upper = [
        (b + params["band_deviation"] * d) if (b is not None and d is not None) else None
        for b, d in zip(basis, dev)
    ]
    lower = [
        (b - params["band_deviation"] * d) if (b is not None and d is not None) else None
        for b, d in zip(basis, dev)
    ]
    bandwidth = [
        ((u - l) / abs(b)) if (u is not None and l is not None and b not in (None, 0.0)) else None
        for u, l, b in zip(upper, lower, basis)
    ]
    prior_bandwidth_floor = ind.shift(ind.lowest(bandwidth, params["squeeze_lookback"]), 1)
    prev_bandwidth = ind.shift(bandwidth, 1)

    return {
        "closes": closes,
        "fast_ema": fast_ema,
        "slow_ema": slow_ema,
        "atr": atr_series,
        "atr_base": atr_base,
        "prior_high": prior_high,
        "prior_low": prior_low,
        "upper": upper,
        "lower": lower,
        "bandwidth": bandwidth,
        "prior_bandwidth_floor": prior_bandwidth_floor,
        "prev_bandwidth": prev_bandwidth,
    }


def _sma_respecting_nones(src: list[Optional[float]], length: int) -> list[Optional[float]]:
    """SMA that stays undefined until `length` consecutive defined values exist."""
    out: list[Optional[float]] = [None] * len(src)
    running: list[float] = []
    total = 0.0
    for i, v in enumerate(src):
        if v is None:
            running.clear()
            total = 0.0
            continue
        running.append(v)
        total += v
        if len(running) > length:
            total -= running.pop(0)
        if len(running) == length:
            out[i] = total / length
    return out


def generate_signals(bars: list[Bar], model: str, params: dict | None = None) -> list[Signal]:
    """Return the ordered list of entry signals for one model on one series.

    The Pine strategy holds at most one position and enters on the FIRST
    qualifying signal; the engine consumes these signals in order and ignores
    signals that arrive while a position is already open in the same direction,
    exactly like ``strategy.entry`` with ``pyramiding = 0``.
    """
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    if model not in MODEL_IDS:
        raise ValueError(f"unknown model {model!r}")
    s = _prepare(bars, p)

    signals: list[Signal] = []
    for i in range(len(bars)):
        atr_v = s["atr"][i]
        atr_base_v = s["atr_base"][i]
        if atr_v is None or atr_base_v is None:
            continue
        expanding = atr_v > atr_base_v * p["atr_expansion_factor"]
        if not expanding:
            continue
        direction: Optional[str] = None
        if model == "S1":
            ph, pl = s["prior_high"][i], s["prior_low"][i]
            fe, se = s["fast_ema"][i], s["slow_ema"][i]
            if ph is None or pl is None or fe is None or se is None:
                continue
            close = s["closes"][i]
            if close > ph and fe > se:
                direction = "long"
            elif close < pl and fe < se:
                direction = "short"
        elif model == "S2":
            if i == 0:
                continue
            fe0, se0 = s["fast_ema"][i], s["slow_ema"][i]
            fe1, se1 = s["fast_ema"][i - 1], s["slow_ema"][i - 1]
            if None in (fe0, se0, fe1, se1):
                continue
            if fe0 > se0 and fe1 <= se1:
                direction = "long"
            elif fe0 < se0 and fe1 >= se1:
                direction = "short"
        else:  # S3
            bw, bw_floor, bw_prev = (
                s["bandwidth"][i],
                s["prior_bandwidth_floor"][i],
                s["prev_bandwidth"][i],
            )
            up, lo = s["upper"][i], s["lower"][i]
            if None in (bw, bw_floor, bw_prev, up, lo):
                continue
            was_compressed = bw_prev <= bw_floor * 1.05
            expanding_bw = bw > bw_prev
            close = s["closes"][i]
            if was_compressed and expanding_bw and close > up:
                direction = "long"
            elif was_compressed and expanding_bw and close < lo:
                direction = "short"
        if direction is not None:
            signals.append(Signal(index=i, date=bars[i].date, direction=direction, atr=atr_v))
    return signals


def warmup_bars(model: str, params: dict | None = None) -> int:
    """First bar index at which every indicator the model needs is defined.

    Derived from the parameters, not a magic constant:
    - ATR baseline needs atr_length bars of TR then a full baseline window.
    - S1 needs the ATR baseline plus the channel (shifted).
    - S2 needs both EMAs (slow dominates) plus the ATR baseline.
    - S3 needs bandwidth (band_length bars) then a squeezed lookback window,
      shifted one more bar, plus the ATR baseline.
    """
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    # ATR is defined from index atr_length-1; its SMA baseline needs a further
    # (atr_baseline_length-1) consecutive defined values.
    atr_ready = (p["atr_length"] - 1) + (p["atr_baseline_length"] - 1)
    if model == "S1":
        # prior channel = highest/lowest(channel_length)[1] -> defined from
        # index channel_length; slow EMA from slow_length-1.
        return max(atr_ready, p["channel_length"], p["slow_length"] - 1)
    if model == "S2":
        return max(atr_ready, p["slow_length"] - 1)
    if model == "S3":
        # bandwidth from band_length-1; its squeeze floor is the rolling minimum
        # over squeeze_lookback values, shifted one further bar.
        bandwidth_ready = p["band_length"] - 1
        floor_ready = bandwidth_ready + (p["squeeze_lookback"] - 1) + 1
        return max(atr_ready, floor_ready)
    raise ValueError(f"unknown model {model!r}")
