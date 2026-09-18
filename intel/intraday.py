"""Intraday bar layer: load and validate the committed canonical captures.

Everything here is pure-stdlib, deterministic and offline. It reads only the files
written by ``scripts/fetch_intraday.py`` (``data/intraday/*.json`` plus the
provenance index ``data/intraday_index.json``) and never performs network access.

Capture format (see the script docstring): each file holds

    {"symbol": ..., "interval": "15m"|"1h"|"1d", "endpoint": ..., "captured_at_utc": ...,
     "raw_response_sha256": ..., "rounding_decimals": 5, "bars": [[epoch, o, h, l, c, v], ...]}

Bars are validated on load exactly as the capture validated them, so a corrupted or
hand-edited file fails loudly instead of silently producing study output. Timestamps
are UTC epoch seconds; the vendor's exchange timezone and GMT offset are recorded per
file and used by callers that need session boundaries.

Naming caution: "gap" in this module always means an arithmetic difference between a
stored vendor price and another stored vendor price across a session boundary. It is a
vendor-history measurement, not an exchange opening auction price, and no claim is made
that any participant could have transacted at these prints.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_INDEX = "data/intraday_index.json"
INTERVALS = ("15m", "1h", "1d")


class IntradayError(RuntimeError):
    """Raised when a capture file is missing, malformed, or internally inconsistent."""


@dataclass(frozen=True)
class IBar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc).date().isoformat()

    @property
    def time_utc(self) -> str:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc).strftime("%H:%M:%S")


@dataclass(frozen=True)
class Capture:
    symbol: str
    interval: str
    kind: str
    endpoint: str
    raw_response_sha256: str
    stored_sha256: str
    rounding_decimals: int
    vendor_exchange: str | None
    vendor_timezone: str | None
    first_utc: str
    last_utc: str
    bars: tuple[IBar, ...]

    @property
    def key(self) -> str:
        return f"{self.symbol}:{self.interval}"


def load_index(rel: str = DEFAULT_INDEX) -> dict:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        raise IntradayError(
            f"{rel} not found: run scripts/fetch_intraday.py in a networked environment "
            "(the capture-intraday workflow) before running the intraday study"
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _validate_bars(raw_bars: list, symbol: str, interval: str) -> tuple[IBar, ...]:
    if not raw_bars:
        raise IntradayError(f"{symbol}[{interval}]: capture contains zero bars")
    bars: list[IBar] = []
    prior_ts = None
    for row in raw_bars:
        if not isinstance(row, list) or len(row) != 6:
            raise IntradayError(f"{symbol}[{interval}]: malformed bar row {row!r}")
        ts, o, h, l, c, v = row
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                   and math.isfinite(x) for x in (ts, o, h, l, c, v)):
            raise IntradayError(f"{symbol}[{interval}]: non-numeric bar row {row!r}")
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and min(o, c) > 0):
            raise IntradayError(
                f"{symbol}[{interval}]: OHLC invariant violated at {ts}: "
                f"o={o} h={h} l={l} c={c}"
            )
        if ts != int(ts) or ts < 0 or v != int(v):
            raise IntradayError(f"{symbol}[{interval}]: non-integral timestamp or volume")
        if v < 0:
            raise IntradayError(f"{symbol}[{interval}]: negative volume at {ts}")
        if prior_ts is not None and ts <= prior_ts:
            raise IntradayError(f"{symbol}[{interval}]: timestamps not strictly increasing")
        prior_ts = ts
        bars.append(IBar(int(ts), float(o), float(h), float(l), float(c), int(v)))
    return tuple(bars)


def load_capture(record: dict, rel_dir: str = "data/intraday") -> Capture:
    """Load one capture record from the index into validated bars."""
    path = os.path.join(ROOT, record["file"]) if record["file"].startswith("data") else os.path.join(
        ROOT, rel_dir, os.path.basename(record["file"])
    )
    with open(path, "rb") as fh:
        payload = fh.read()
    stored_sha = hashlib.sha256(payload).hexdigest()
    if stored_sha != record["stored_sha256"]:
        raise IntradayError(
            f"{record['symbol']}[{record['interval']}]: stored SHA-256 {stored_sha} does not "
            f"match the index value {record['stored_sha256']}"
        )
    document = json.loads(payload.decode("utf-8"))
    if document.get("symbol") != record["symbol"]:
        raise IntradayError(f"{path}: symbol mismatch with the index record")
    if document.get("interval") != record["interval"]:
        raise IntradayError(f"{path}: interval mismatch with the index record")
    # Series-level raw digest: present in captures written from script_version 3 onward (the
    # fetch script derives it from every chunk's raw-response digest). It is only compared when
    # the index declares it, and a document that declares it while the index does not is treated
    # as an inconsistent index rather than silently ignored.
    declared_raw = record.get("raw_response_sha256")
    document_raw = document.get("raw_response_sha256")
    if declared_raw is not None and document_raw != declared_raw:
        raise IntradayError(
            f"{path}: raw-response digest mismatch with the index record "
            f"(document {document_raw}, index {declared_raw})"
        )
    if document_raw is not None and declared_raw is None:
        raise IntradayError(
            f"{path}: the capture declares raw_response_sha256 but the index record does not"
        )
    bars = _validate_bars(document["bars"], record["symbol"], record["interval"])
    if len(bars) != record["bar_count"]:
        raise IntradayError(
            f"{path}: {len(bars)} bars but the index declares {record['bar_count']}"
        )
    return Capture(
        symbol=record["symbol"],
        interval=record["interval"],
        kind=record.get("kind", "equity"),
        endpoint=record["endpoint"],
        raw_response_sha256=record["raw_response_sha256"],
        stored_sha256=stored_sha,
        rounding_decimals=record.get("rounding_decimals", 5),
        vendor_exchange=record.get("vendor_reported_exchange"),
        vendor_timezone=record.get("vendor_exchange_timezone"),
        first_utc=record["first_utc"],
        last_utc=record["last_utc"],
        bars=bars,
    )


def load_all(index: dict | None = None, intervals: tuple[str, ...] | None = None) -> dict[str, Capture]:
    """Every captured series, keyed by ``"SYMBOL:interval"``."""
    index = index or load_index()
    out: dict[str, Capture] = {}
    for record in index.get("captures", []):
        if record.get("status") != "captured":
            continue
        if intervals and record["interval"] not in intervals:
            continue
        capture = load_capture(record)
        out[capture.key] = capture
    return out


def sessions(bars: tuple[IBar, ...] | list[IBar]) -> "list[tuple[str, list[IBar]]]":
    """Group bars into UTC calendar sessions, ordered.

    For US equities the regular session (13:30-20:00 UTC) never crosses a UTC date
    boundary, so a UTC date is the session. Futures trade nearly continuously: their
    CME session starts at 22:00/23:00 UTC the previous day, so a UTC-date grouping
    splits the futures session at the daily vendor break. That caveat is reported with
    every futures number derived here and must not be read as an exchange session.
    """
    grouped: dict[str, list[IBar]] = {}
    order: list[str] = []
    for bar in bars:
        day = bar.date
        if day not in grouped:
            grouped[day] = []
            order.append(day)
        grouped[day].append(bar)
    return [(day, grouped[day]) for day in order]


def atr(bars: list, length: int = 14) -> list[float | None]:
    """ATR(14) by Wilder's RMA, seeded with the SMA of the first `length` true ranges.

    Same convention as intel.indicators.atr (Pine ``ta.atr``), duplicated here so this
    module has no dependency on the daily-bar engine.
    """
    out: list[float | None] = [None] * len(bars)
    trs: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
            continue
        prev_close = bars[i - 1].close
        trs.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
    if len(bars) < length:
        return out
    seed = sum(trs[:length]) / length
    out[length - 1] = seed
    prior = seed
    for i in range(length, len(bars)):
        prior = (prior * (length - 1) + trs[i]) / length
        out[i] = prior
    return out


def load_captures_for_symbols(
    index: dict | None = None,
    interval: str = "1d",
    symbols: tuple[str, ...] | None = None,
) -> dict[str, Capture]:
    """Captures of one interval, keyed by symbol (optionally restricted to `symbols`)."""
    index = index or load_index()
    out: dict[str, Capture] = {}
    for record in index.get("captures", []):
        if record.get("status") != "captured" or record.get("interval") != interval:
            continue
        if symbols and record["symbol"] not in symbols:
            continue
        capture = load_capture(record)
        out[capture.symbol] = capture
    return out
