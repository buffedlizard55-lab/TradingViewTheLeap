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


NY_ARCA_OPEN_ET = "09:30"
NY_ARCA_CLOSE_ET = "16:00"
CME_FUTURES_SESSION_OPEN_UTC_WINTER = "23:00"  # CME Globex: 17:00 CT = 23:00 UTC (CST)
CME_FUTURES_SESSION_OPEN_UTC_SUMMER = "22:00"  # 17:00 CT = 22:00 UTC (CDT)
EQUITY_REGULAR_HOURS_UTC_WINTER = ("14:30", "21:00")  # 09:30-16:00 ET = 14:30-21:00 UTC (EST)
EQUITY_REGULAR_HOURS_UTC_SUMMER = ("13:30", "20:00")  # 09:30-16:00 ET = 13:30-20:00 UTC (EDT)


def sessions(bars: tuple[IBar, ...] | list[IBar]) -> "list[tuple[str, list[IBar]]]":
    """Group bars into UTC calendar sessions, ordered.

    For US equities the regular session (09:30-16:00 ET, 13:30-20:00 UTC in EDT
    and 14:30-21:00 UTC in EST) never crosses a UTC date boundary, so a UTC date
    is the session. This matches the vendor's exchangeTimezoneName America/New_York
    reports (see research/evidence/YAHOO-INTRADAY-CAPTURE.md) and the capture
    probe observations (AAPL 15m: 26 bars per session, NVDA 1h: 21 bars).

    Futures trade nearly continuously: their CME session starts at 17:00 CT
    (22:00 UTC summer / 23:00 UTC winter, CME Globex), so a UTC-date grouping
    splits the futures session at the daily vendor break. That caveat is reported
    with every futures number derived here and must not be read as an official
    exchange session (see data/intraday_study.json assumptions and this module's
    docstring: these are vendor-history measurements, not exchange auction prices).

    DST handling: this grouping deliberately uses UTC dates, not ET dates, so no
    DST conversion is needed for correctness; the constants above are documented
    for reviewers to verify that no regular-hour bar crosses midnight UTC. For a
    future exchange-session-accurate grouping, join these bars with an official
    NYSE/CME holiday calendar (NYSE calendar: https://www.nyse.com/markets/hours-calendars
    and CME calendar: https://www.cmegroup.com/trading-hours.html) and re-derive
    the study; the current UTC method is the honest, verifiable baseline.

    Use only publicly available official calendars; no hallucinated sessions.

    For the calendar-aware variant that annotates these same sessions with the
    US equity full-closure table (weekend gaps vs gaps spanning an exchange
    holiday), see sessions_calendar_aware(); the study reports both.
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


def sessions_calendar_aware(
    bars: tuple[IBar, ...] | list[IBar],
    calendar_id: str = "NYSE",
) -> "list[dict]":
    """UTC sessions annotated with the US equity holiday calendar.

    The grouping is identical to :func:`sessions` (the honest baseline: one UTC
    date is one session for regular-hours equities); each session is then
    annotated with the ``intel.calendar`` full-closure table so downstream
    measurements can tell a weekend gap from a gap that spans a mid-week
    exchange holiday. Holiday sessions are NEVER dropped here: vendor bars
    dated on a full closure are an anomaly the study reports, not data to
    delete silently.

    Returns one dict per session, in order::

        {"date": ..., "bars": [...], "bar_count": N,
         "is_full_closure": bool, "closure_name": str | None,
         "closures_spanned": [iso dates strictly between the prior session
                              and this one that are full closures]}

    Only ``calendar_id="NYSE"`` is supported; futures need the CME Globex
    calendar, which is not encoded (see intel.calendar).
    """
    if calendar_id != "NYSE":
        raise IntradayError(
            f"unknown calendar {calendar_id!r}: only 'NYSE' is encoded; "
            "futures need the CME Globex calendar (not implemented)"
        )
    from .calendar import full_closures_between

    groups = sessions(bars)
    if not groups:
        return []
    first_day = groups[0][0]
    last_day = groups[-1][0]
    closures = full_closures_between(first_day, last_day)
    annotated: list[dict] = []
    prior_day: str | None = None
    for day, day_bars in groups:
        spanned = sorted(
            iso for iso in closures
            if prior_day is not None and prior_day < iso < day
        )
        annotated.append({
            "date": day,
            "bars": day_bars,
            "bar_count": len(day_bars),
            "is_full_closure": day in closures,
            "closure_name": closures.get(day),
            "closures_spanned": spanned,
        })
        prior_day = day
    return annotated


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
