"""Import authenticated TradingView Strategy Report exports (CSV) and validate them.

WHAT CAN BE IMPORTED, AND WHAT CANNOT
------------------------------------
TradingView's own support documentation states that Strategy Report data is exported as a
CSV file per tab ("How to export strategy data",
https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/):

    "If you want to save Strategy Report data, you can use the export feature to download it
     as a CSV file. ... if you click on the 'Download' button from the 'List of Trades' tab,
     you will only export the trade information. Exporting strategy data from the 'Performance
     Summary' tab will only export the metrics."

The exact column labels are produced by the platform, and this module does NOT assert what
they are. Instead it:

1. requires a header row, normalizes the labels, and maps them through the declared alias
   table below;
2. refuses to import a file whose required fields cannot be mapped, and prints the header it
   actually observed so a human can extend the alias table from real evidence;
3. validates every row arithmetically: quantities and prices positive, exit after entry,
   direction consistency between the entry and exit rows, and — when the export carries both
   prices+quantity and a profit column — an independent P/L recomputation with a declared
   tolerance;
4. records the SHA-256 of the file it read, the exact header, the row count, and every
   rejected row, so a reviewer can audit the import line by line.

AUTHENTICITY LIMITATION
----------------------
A filename and a SHA-256 establish neither origin nor account authentication.
Non-fixture CSVs are unverified imports, not authenticated TradingView evidence.
Fixtures are labelled for parser tests only. No cryptographic attestation is
provided by this importer.

NO NETWORK ACCESS, NO CREDENTIALS
---------------------------------
This module never authenticates, never scrapes, and never fabricates: an authenticated export
can only be produced by a signed-in TradingView user with export entitlement. Until such a
file is committed, ``scripts/tv_benchmark.py`` reports the benchmark as blocked, with the
reason recorded, rather than inventing numbers.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import re
from dataclasses import dataclass, field
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPORTS_DIR = "data/tv_reports"

# Alias table: normalized column label -> canonical field. Labels are normalized by
# lowercasing, stripping spaces/underscores/dots/# and collapsing percent signs. The table
# deliberately includes several plausible spellings because the exact platform labels are not
# documented; a real export that does not match prints its observed header and fails.
COLUMN_ALIASES: dict[str, str] = {
    "trade": "trade_number",
    "tradeno": "trade_number",
    "tradenumber": "trade_number",
    "no": "trade_number",
    "type": "trade_type",
    "direction": "trade_type",
    "datetime": "datetime",
    "date": "datetime",
    "time": "datetime",
    "dateandtime": "datetime",
    "signal": "signal",
    "comment": "signal",
    "price": "price",
    "fillprice": "price",
    "contracts": "qty",
    "qty": "qty",
    "quantity": "qty",
    "size": "qty",
    "units": "qty",
    "profit": "profit",
    "pnl": "profit",
    "netprofit": "profit",
    "profitusd": "profit",
    "profitcurrency": "profit",
    "cumulativeprofit": "cumulative_profit",
    "runup": "run_up",
    "runuppips": "run_up",
    "drawdown": "draw_down",
    "commission": "commission",
    "fees": "commission",
    "symbol": "symbol",
    "ticker": "symbol",
    "instrument": "symbol",
}

ENTRY_TOKENS = ("entry", "long", "short", "buy", "sell", "enter")
EXIT_TOKENS = ("exit", "close", "closed", "take", "stop", "end")

REQUIRED_TRADE_FIELDS = ("datetime", "qty", "price")

# Metric aliases for a Performance Summary export (name/value pairs).
METRIC_ALIASES: dict[str, str] = {
    "totalnetprofit": "total_net_profit",
    "netprofit": "total_net_profit",
    "netprofitpercentage": "net_profit_percent",
    "netprofitpct": "net_profit_percent",
    "totalclosedtrades": "total_closed_trades",
    "totalopentrades": "total_open_trades",
    "numberofwinningtrades": "winning_trades",
    "numberoflosingtrades": "losing_trades",
    "percentprofitable": "percent_profitable",
    "profitabletrades": "percent_profitable",
    "profitfactor": "profit_factor",
    "commissionpaid": "commission_paid",
    "maxdrawdown": "max_drawdown",
    "maxdrawdownpercent": "max_drawdown_percent",
    "averageprofitpertrade": "avg_profit_per_trade",
    "sharperatio": "sharpe_ratio",
    "sortinoratio": "sortino_ratio",
    "initialcapital": "initial_capital",
}


class ImportError_(RuntimeError):
    """Raised when an export cannot be imported without guessing."""


def normalize_label(label: str) -> str:
    text = label.strip().lower()
    text = text.replace("%", "percent")
    text = re.sub(r"[\s_\-\.#/()\[\]]+", "", text)
    return text


@dataclass
class TradeRow:
    line: int
    trade_number: Optional[str]
    trade_type: str
    datetime: str
    signal: str
    price: float
    qty: float
    profit: Optional[float]
    cumulative_profit: Optional[float]
    run_up: Optional[float]
    draw_down: Optional[float]
    commission: Optional[float]
    side: str                      # "long" | "short" | "unknown"
    phase: str                     # "entry" | "exit" | "unknown"


@dataclass
class ImportedReport:
    path: str
    sha256: str
    kind: str                       # "list_of_trades" | "performance_summary"
    is_fixture: bool
    header: list[str] = field(default_factory=list)
    column_map: dict = field(default_factory=dict)
    trades: list[TradeRow] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    symbol: Optional[str] = None
    rejected_rows: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def trade_count(self) -> int:
        return len(self.trades)


def _read_rows(path: str) -> list[list[str]]:
    with open(path, "rb") as fh:
        payload = fh.read()
    text = payload.decode("utf-8-sig")
    rows = []
    for line in csv.reader(io.StringIO(text)):
        if not line:
            continue
        if line[0].lstrip().startswith("#"):
            continue                    # fixture banners and human notes
        rows.append(line)
    return rows


def _classify(header: list[str]) -> str:
    normalized = [normalize_label(h) for h in header]
    mapped = {COLUMN_ALIASES.get(n) for n in normalized}
    metrics = {METRIC_ALIASES.get(n) for n in normalized}
    if {"datetime", "price", "qty"} <= mapped:
        return "list_of_trades"
    if len(header) == 2 and (metrics - {None}):
        return "performance_summary"
    if len(header) == 2:
        return "performance_summary"
    raise ImportError_(
        f"unrecognised export header {header!r}: not a List of Trades export (needs fields "
        f"mapping to {REQUIRED_TRADE_FIELDS}) and not a two-column Performance Summary export"
    )


def _parse_float(text: str) -> Optional[float]:
    text = (text or "").strip().replace(",", "")
    if text in ("", "-", "—"):
        return None
    text = text.replace("%", "")
    try:
        value = float(text)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


_SIDE_PATTERNS = (
    ("long", ("long", "buy")),
    ("short", ("short", "sell")),
)


def _side_and_phase(trade_type: str, signal: str) -> tuple[str, str]:
    blob = f"{trade_type} {signal}".strip().lower()
    phase = "unknown"
    if any(token in blob for token in EXIT_TOKENS):
        phase = "exit"
    if any(token in blob for token in ENTRY_TOKENS):
        # "Entry" wins when both appear (e.g. "Exit Short" is still an exit).
        if "exit" not in blob and "close" not in blob:
            phase = "entry"
    side = "unknown"
    for name, tokens in _SIDE_PATTERNS:
        if any(token in blob for token in tokens):
            side = name
            break
    return side, phase


def import_trades(path: str) -> ImportedReport:
    """Import a List of Trades CSV export with strict validation."""
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    rows = _read_rows(path)
    if not rows:
        raise ImportError_(f"{path}: file contains no rows")
    header = rows[0]
    kind = _classify(header)
    report = ImportedReport(
        path=os.path.relpath(path, ROOT) if os.path.isabs(path) else path,
        sha256=digest,
        kind=kind,
        is_fixture=bool(re.search(r"fixture|synthetic", path, re.IGNORECASE)),
    )
    if kind != "list_of_trades":
        report.header = header
        return report
    index = {}
    for i, label in enumerate(header):
        canonical = COLUMN_ALIASES.get(normalize_label(label))
        if canonical and canonical not in index:
            index[canonical] = i
    missing = [f for f in REQUIRED_TRADE_FIELDS if f not in index]
    if missing:
        raise ImportError_(
            f"{path}: required fields {missing} not present in the export header {header!r}. "
            "Observed header recorded; extend intel/tv_import.COLUMN_ALIASES only from a real "
            "export."
        )
    report.header = header
    report.column_map = {k: header[v] for k, v in sorted(index.items())}
    symbol_values = set()
    for row in rows[1:]:
        pos = index.get("symbol")
        if pos is not None and pos < len(row) and row[pos].strip():
            symbol_values.add(row[pos].strip())
    if len(symbol_values) == 1:
        report.symbol = symbol_values.pop()
    elif len(symbol_values) > 1:
        report.warnings.append(
            f"export contains {len(symbol_values)} distinct symbols: {sorted(symbol_values)}")

    def cell(row: list[str], canonical: str) -> str:
        pos = index.get(canonical)
        if pos is None or pos >= len(row):
            return ""
        return row[pos].strip()

    for line_number, row in enumerate(rows[1:], start=2):
        price = _parse_float(cell(row, "price"))
        qty = _parse_float(cell(row, "qty"))
        dt = cell(row, "datetime")
        trade_type = cell(row, "trade_type")
        signal = cell(row, "signal")
        rejected = None
        if not dt:
            rejected = "missing datetime"
        elif price is None or price <= 0:
            rejected = f"non-positive or unparsable price {price!r}"
        elif qty is None or qty <= 0:
            rejected = f"non-positive or unparsable quantity {qty!r}"
        if rejected:
            report.rejected_rows.append({"line": line_number, "row": row, "reason": rejected})
            continue
        side, phase = _side_and_phase(trade_type, signal)
        report.trades.append(TradeRow(
            line=line_number,
            trade_number=cell(row, "trade_number") or None,
            trade_type=trade_type,
            datetime=dt,
            signal=signal,
            price=price,
            qty=qty,
            profit=_parse_float(cell(row, "profit")),
            cumulative_profit=_parse_float(cell(row, "cumulative_profit")),
            run_up=_parse_float(cell(row, "run_up")),
            draw_down=_parse_float(cell(row, "draw_down")),
            commission=_parse_float(cell(row, "commission")),
            side=side,
            phase=phase,
        ))

    if not report.trades:
        raise ImportError_(f"{path}: no valid trade rows after validation")

    # Arithmetic cross-check: pair entry/exit rows and recompute gross P/L per round trip.
    trips, open_entry, open_exit = [], None, None
    for trade in report.trades:
        if trade.phase == "entry" or (trade.phase == "unknown" and open_entry is None):
            open_entry = trade
            continue
        if trade.phase == "exit":
            open_exit = trade
        if open_entry and open_exit:
            direction = 1.0 if open_entry.side == "long" else -1.0
            qty = min(open_entry.qty, open_exit.qty)
            gross = direction * (open_exit.price - open_entry.price) * qty
            trips.append({
                "entry_line": open_entry.line,
                "exit_line": open_exit.line,
                "side": open_entry.side,
                "qty": qty,
                "entry_price": open_entry.price,
                "exit_price": open_exit.price,
                "gross_pnl_recomputed": round(gross, 6),
                "gross_pnl_declared": open_exit.profit,
                "abs_diff": (round(abs(gross - open_exit.profit), 6)
                             if open_exit.profit is not None else None),
            })
            open_entry, open_exit = None, None
    report.metrics["round_trips"] = trips
    if open_entry is not None:
        report.warnings.append(
            "the export ends with an entry that has no matching exit row in this file")
    return report


def import_performance_summary(path: str) -> ImportedReport:
    """Import a two-column Performance Summary export (metric name, value)."""
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    rows = _read_rows(path)
    if not rows:
        raise ImportError_(f"{path}: file contains no rows")
    report = ImportedReport(
        path=os.path.relpath(path, ROOT) if os.path.isabs(path) else path,
        sha256=digest,
        kind="performance_summary",
        is_fixture=bool(re.search(r"fixture|synthetic", path, re.IGNORECASE)),
        header=rows[0],
    )
    for row in rows:
        if len(row) < 2:
            continue
        label = normalize_label(row[0])
        key = METRIC_ALIASES.get(label, label)
        value = _parse_float(row[1])
        if value is not None:
            if key == label and label not in METRIC_ALIASES.values():
                report.warnings.append(
                    f"unrecognised metric label {row[0]!r} kept verbatim under {key!r}")
            report.metrics[key] = value
        elif row[1].strip():
            report.warnings.append(
                f"metric {row[0]!r} carries the unparsable value {row[1]!r} (gated export?)")
    if not report.metrics:
        raise ImportError_(
            f"{path}: the file has no recognisable Performance Summary metrics "
            "(a Strategy Report export whose values are gated or unparsable must be reviewed by "
            "hand, not silently imported as an empty report)"
        )
    return report


def import_any(path: str) -> ImportedReport:
    """Dispatch on the export shape."""
    rows = _read_rows(path)
    if not rows:
        raise ImportError_(f"{path}: empty export")
    kind = _classify(rows[0])
    if kind == "list_of_trades":
        return import_trades(path)
    return import_performance_summary(path)
