"""Pine-faithful technical indicators (pure functions over lists).

Every function returns a list aligned with the input series; warmup positions
(before the indicator is defined) are ``None``, matching Pine's ``na`` behaviour.
The seeding conventions follow the official Pine v6 reference documented in the
package docstring.
"""

from __future__ import annotations

import math
from typing import Optional


def sma(src: list[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(src)
    if length <= 0:
        return out
    running = 0.0
    for i, v in enumerate(src):
        running += v
        if i >= length:
            running -= src[i - length]
        if i >= length - 1:
            out[i] = running / length
    return out


def ema(src: list[float], length: int) -> list[Optional[float]]:
    """Pine ta.ema: SMA seed for the first defined value, then recursive."""
    out: list[Optional[float]] = [None] * len(src)
    if length <= 0 or len(src) < length:
        return out
    alpha = 2.0 / (length + 1)
    seed = sum(src[:length]) / length
    out[length - 1] = seed
    value = seed
    for i in range(length, len(src)):
        value = alpha * src[i] + (1 - alpha) * value
        out[i] = value
    return out


def rma(src: list[Optional[float]], length: int) -> list[Optional[float]]:
    """Pine ta.rma: SMA seed, then (src + (length-1)*prev) / length."""
    out: list[Optional[float]] = [None] * len(src)
    if length <= 0:
        return out
    window: list[float] = []
    value: Optional[float] = None
    for i, v in enumerate(src):
        if v is None:
            out[i] = None
            continue
        if value is None:
            window.append(v)
            if len(window) == length:
                value = sum(window) / length
                out[i] = value
            continue
        value = (v + (length - 1) * value) / length
        out[i] = value
    return out


def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(closes)
    for i in range(len(closes)):
        if i == 0:
            out[i] = highs[i] - lows[i]
            continue
        prev_close = closes[i - 1]
        out[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - prev_close),
            abs(lows[i] - prev_close),
        )
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], length: int) -> list[Optional[float]]:
    """Pine ta.atr = ta.rma(ta.tr, length)."""
    return rma(true_range(highs, lows, closes), length)


def rolling_extreme(src: list[Optional[float]], length: int, is_max: bool) -> list[Optional[float]]:
    """Pine ta.highest / ta.lowest over a window inclusive of the current bar.

    Implemented as an O(n) monotonic deque so long series stay fast.
    """
    out: list[Optional[float]] = [None] * len(src)
    from collections import deque

    dq: deque[int] = deque()
    for i, v in enumerate(src):
        if v is None:
            dq.clear()
            continue
        while dq and (
            (src[dq[-1]] is not None)
            and ((src[dq[-1]] <= v) if is_max else (src[dq[-1]] >= v))
        ):
            dq.pop()
        dq.append(i)
        while dq[0] <= i - length:
            dq.popleft()
        if i >= length - 1:
            out[i] = src[dq[0]]
    return out


def highest(src: list[Optional[float]], length: int) -> list[Optional[float]]:
    return rolling_extreme(src, length, True)


def lowest(src: list[Optional[float]], length: int) -> list[Optional[float]]:
    return rolling_extreme(src, length, False)


def stdev(src: list[float], length: int) -> list[Optional[float]]:
    """Pine ta.stdev (biased/population) computed on a rolling window."""
    out: list[Optional[float]] = [None] * len(src)
    if length <= 1:
        return out
    for i in range(length - 1, len(src)):
        window = src[i - length + 1 : i + 1]
        mean = sum(window) / length
        variance = sum((v - mean) ** 2 for v in window) / length
        out[i] = math.sqrt(variance)
    return out


def shift(src: list[Optional[float]], by: int = 1) -> list[Optional[float]]:
    """Pine series[n]: value from `by` bars earlier; None where undefined."""
    if by == 0:
        return list(src)
    out: list[Optional[float]] = [None] * len(src)
    for i in range(by, len(src)):
        out[i] = src[i - by]
    return out
