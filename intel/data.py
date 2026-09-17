"""Load and validate the committed vendor captures into bar series."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Bar:
    __slots__ = ("ts", "date", "open", "high", "low", "close", "volume")

    def __init__(self, ts: int, open_: float, high: float, low: float, close: float, volume):
        self.ts = ts
        self.date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def load_index(rel: str = "data/market_history_index.json") -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def load_series(tradingview_symbol: str, rel_dir: str = "data/market_history") -> list[Bar]:
    """Parse one raw vendor capture into validated bars.

    Raises ValueError on any structural inconsistency. Bars with any null OHLC
    value are dropped (the vendor emits a null close for the in-progress session);
    everything else must satisfy high >= max(open, close), low <= min(open, close),
    strictly increasing timestamps, and strictly positive prices.
    """
    filename = tradingview_symbol.replace(":", "_").replace("!", "") + ".json"
    path = os.path.join(ROOT, rel_dir, filename)
    with open(path, "rb") as fh:
        payload = fh.read()
    document = json.loads(payload.decode("utf-8"))
    chart = document["chart"]
    if chart.get("error") is not None:
        raise ValueError(f"{tradingview_symbol}: vendor error payload: {chart['error']}")
    result = chart["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    bars: list[Bar] = []
    for i, ts in enumerate(timestamps):
        o, h = quote["open"][i], quote["high"][i]
        l, c = quote["low"][i], quote["close"][i]
        v = quote["volume"][i]
        if None in (o, h, l, c):
            continue
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            raise ValueError(
                f"{tradingview_symbol}: OHLC invariant violated at {ts}: o={o} h={h} l={l} c={c}"
            )
        if bars and ts <= bars[-1].ts:
            raise ValueError(f"{tradingview_symbol}: timestamps not strictly increasing at {ts}")
        bars.append(Bar(ts, o, h, l, c, v))
    return bars


def sha256_of(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
