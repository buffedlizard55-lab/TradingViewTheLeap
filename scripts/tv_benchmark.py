#!/usr/bin/env python3
"""Benchmark Pine broker-emulator fills against the Python backtest fills.

Input
-----
1. Every CSV under data/tv_reports/ (excluding *_fixtures/*), i.e. TradingView Strategy
   Report exports placed there by an authenticated user. TradingView's support documentation
   states the Strategy Report export is a CSV, one tab at a time ("List of Trades" for trade
   information, "Performance Summary" for the metrics):
   https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/
2. The committed vendor captures under data/market_history/ and data/intraday/, used to place
   every exported fill on a real bar.

What is compared
----------------
For every exported fill, the script reports the distance between

  (a) the exported fill price (what the Pine broker emulator produced and the platform
      printed), and
  (b) the same bar's vendor OPEN price — the documented default emulator rule is that a
      market order created on a bar's closing tick fills at the open of the following bar
      (see intel/pine_emulator.py for the verbatim rule and its source),
  (c) the previous bar's vendor CLOSE price — the naive "the signal price is the fill price"
      assumption, and
  (d) the Python engine's fill for the same decision: next bar open plus the declared
      ATR-fraction slippage model used by intel.backtest and intel.competition.

All four are arithmetic on committed bars. Nothing is fitted.

Output
------
data/tv_benchmark.json — one record per export, including the observed header, the column
mapping used, the SHA-256 of the file read, every rejected row, the arithmetic P/L
cross-check of each round trip, and the fill deltas.

If no real export exists, the benchmark is reported as `blocked` with the exact reason and the
steps needed, and the same pipeline is run against the clearly-labelled synthetic fixture in
data/tv_reports/_fixtures/ so the code path is proven rather than asserted. Fixture results
are never presented as TradingView output.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import pine_emulator as pine  # noqa: E402
from intel.backtest import COST_SCENARIOS, CostScenario  # noqa: E402
from intel.data import Bar, load_series  # noqa: E402
from intel.tv_import import ImportError_, import_any  # noqa: E402

REPORTS_DIR = "data/tv_reports"
FIXTURE_MARKER = "_fixtures"
PROFIT_TOLERANCE = 0.02          # absolute currency units for the arithmetic cross-check
DEFAULT_SCENARIO = "moderate"


def load_bars_for(symbol: str) -> tuple[list[Bar], str]:
    """Bars for a TradingView-style symbol from whichever capture holds it."""
    candidates = []
    intraday_dir = os.path.join(ROOT, "data", "intraday")
    if os.path.isdir(intraday_dir):
        for path in sorted(glob.glob(os.path.join(intraday_dir, f"{symbol}_*.json"))):
            candidates.append(("intraday", path))
    daily_path = os.path.join(ROOT, "data", "market_history",
                              symbol.replace(":", "_").replace("!", "") + ".json")
    if os.path.exists(daily_path):
        candidates.append(("market_history", daily_path))
    if len(candidates) > 1:
        raise ImportError_("Ambiguous bar interval: multiple captures exist; explicit interval mapping required")
    for kind, path in candidates:
        if kind == "market_history":
            bars = load_series(symbol)
            return bars, path
        with open(path, encoding="utf-8") as fh:
            document = json.load(fh)
        bars = [Bar(int(b[0]), float(b[1]), float(b[2]), float(b[3]), float(b[4]), b[5])
                for b in document["bars"]]
        return bars, path
    raise ImportError_(
        f"no committed capture contains symbol {symbol!r}; import its bars first "
        "(scripts/fetch_intraday.py or scripts/fetch_market_data.py)")


def index_of_timestamp(bars: list[Bar], stamp: str) -> int | None:
    """Locate the bar a timestamp string refers to (epoch, ISO datetime or plain date)."""
    text = stamp.strip().replace("T", " ")
    candidates: list[str] = []
    if text.isdigit():
        return next((i for i, b in enumerate(bars) if b.ts == int(text)), None)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M",
                "%m/%d/%Y %H:%M", "%d/%m/%Y", "%m/%d/%Y", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        epoch = int(parsed.timestamp())
        exact = next((i for i, b in enumerate(bars) if b.ts == epoch), None)
        if exact is not None and len(text) != 10:
            return exact
        date_text = parsed.date().isoformat()
        same_day = [i for i, b in enumerate(bars) if b.date == date_text]
        if len(same_day) == 1 and len(text) == 10:
            return same_day[0]
        candidates.append(date_text)
    return None


def benchmark_report(report, scenario: CostScenario, interval_filter: str | None = None) -> dict:
    """Compare every exported fill with the vendor bars and the Python fill model."""
    record = {
        "path": report.path,
        "sha256": report.sha256,
        "kind": report.kind,
        "is_fixture": report.is_fixture,
        "authentication_status": "synthetic_fixture" if report.is_fixture else "unverified_origin",
        "header_observed": report.header,
        "column_map": report.column_map,
        "symbol": report.symbol,
        "trade_rows": report.trade_count,
        "rejected_rows": report.rejected_rows,
        "warnings": report.warnings,
    }
    if report.kind == "performance_summary":
        record["metrics"] = report.metrics
        record["fill_benchmark"] = {"status": "not_applicable",
                                    "reason": "performance summary carries no individual fills"}
        return record

    trips = report.metrics.get("round_trips", [])
    record["round_trips"] = len(trips)
    diffs = [t["abs_diff"] for t in trips if t["abs_diff"] is not None]
    record["arithmetic_cross_check"] = {
        "tolerance": PROFIT_TOLERANCE,
        "round_trips_with_declared_profit": len(diffs),
        "max_abs_diff": max(diffs) if diffs else None,
        "median_abs_diff": round(statistics.median(diffs), 6) if diffs else None,
        "within_tolerance": bool(diffs) and max(diffs) <= PROFIT_TOLERANCE,
        "method": (
            "gross P/L recomputed as direction x (exit price - entry price) x quantity from the "
            "export's own entry/exit rows, then compared to the export's declared profit column"
        ),
    }

    if not report.symbol:
        record["fill_benchmark"] = {
            "status": "needs_symbol_mapping",
            "reason": (
                "the export carries no symbol column and no manifest; fills cannot be placed on "
                "a captured bar series without knowing the instrument"
            ),
            "resolution": (
                "re-export including the symbol column, or add data/tv_reports/<same-stem>."
                "manifest.json containing {\"symbol\": \"NVDA\", \"interval\": \"1h\"}"
            ),
        }
        return record

    try:
        bars, source = load_bars_for(report.symbol)
    except ImportError_ as exc:
        record["fill_benchmark"] = {"status": "needs_bars", "reason": str(exc)}
        return record

    atr_source = _atr_series(bars)
    rows = []
    for trade in report.trades:
        idx = index_of_timestamp(bars, trade.datetime)
        if idx is None:
            rows.append({"line": trade.line, "datetime": trade.datetime,
                         "status": "bar_not_found"})
            continue
        bar = bars[idx]
        prior_close = bars[idx - 1].close if idx > 0 else None
        atr_value = atr_source[idx - 1] if idx > 0 else None
        slip = (scenario.slippage_atr_fraction * atr_value) if atr_value else 0.0
        direction = trade.side if trade.side in ("long", "short") else "long"
        python_fill = bar.open + (slip if direction == "long" else -slip)
        row = {
            "line": trade.line,
            "datetime": trade.datetime,
            "phase": trade.phase,
            "side": trade.side,
            "qty": trade.qty,
            "exported_price": trade.price,
            "vendor_bar": {"date": bar.date, "time_utc": bar.time_utc if hasattr(bar, "time_utc")
                           else None, "open": bar.open, "high": bar.high, "low": bar.low,
                           "close": bar.close},
            "prior_close": prior_close,
            "delta_vs_bar_open": round(trade.price - bar.open, 6),
            "delta_vs_prior_close": round(trade.price - prior_close, 6)
            if prior_close is not None else None,
            "python_fill_next_open_plus_slippage": round(python_fill, 6),
            "delta_vs_python_fill": round(trade.price - python_fill, 6),
            "abs_delta_vs_bar_open_bps": round(abs(trade.price - bar.open) / bar.open * 10_000, 4),
        }
        if prior_close:
            row["abs_delta_vs_prior_close_bps"] = round(
                abs(trade.price - prior_close) / prior_close * 10_000, 4)
        if bar.open:
            row["abs_delta_vs_python_fill_bps"] = round(
                abs(trade.price - python_fill) / bar.open * 10_000, 4)
        rows.append(row)

    compared = [r for r in rows if "delta_vs_bar_open" in r]
    def median(values):
        values = [v for v in values if v is not None]
        return round(statistics.median(values), 4) if values else None

    record["fill_source"] = os.path.relpath(source, ROOT)
    record["fill_benchmark"] = {
        "status": "measured" if compared else "no_fills_matched",
        "bars_source_file": os.path.relpath(source, ROOT),
        "fills_compared": len(compared),
        "fills_unmatched": len(rows) - len(compared),
        "share_exact_open_match": round(
            sum(1 for r in compared if abs(r["delta_vs_bar_open"]) < 1e-9) / len(compared), 6)
        if compared else None,
        "median_abs_delta_vs_bar_open_bps": median(
            [r["abs_delta_vs_bar_open_bps"] for r in compared]),
        "median_abs_delta_vs_prior_close_bps": median(
            [r.get("abs_delta_vs_prior_close_bps") for r in compared]),
        "median_abs_delta_vs_python_fill_bps": median(
            [r.get("abs_delta_vs_python_fill_bps") for r in compared]),
        "python_fill_model": (
            f"next bar open {'+' if True else '-'} {scenario.slippage_atr_fraction} x ATR(14) "
            "against the direction of the trade"
        ) if scenario.slippage_atr_fraction else "next bar open (zero-cost scenario)",
        "rows": rows,
    }
    return record


def _atr_series(bars: list[Bar]) -> list[float | None]:
    from intel.indicators import atr
    return atr([b.high for b in bars], [b.low for b in bars], [b.close for b in bars], 14)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--out", default="data/tv_benchmark.json")
    ap.add_argument("--scenario", default=DEFAULT_SCENARIO)
    args = ap.parse_args()
    if args.stamp:
        stamp = args.stamp
    else:
        stamps = []
        for rel in ("data/intraday_index.json", "data/market_history_index.json"):
            path = os.path.join(ROOT, rel)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    meta = json.load(fh).get("_meta", {})
                if meta.get("fetched_at_utc"):
                    stamps.append(meta["fetched_at_utc"])
        stamp = max(stamps) if stamps else "unknown"
    scenario = COST_SCENARIOS[args.scenario]

    reports_dir = os.path.join(ROOT, REPORTS_DIR)
    real_paths, fixture_paths = [], []
    if os.path.isdir(reports_dir):
        for path in sorted(glob.glob(os.path.join(reports_dir, "**", "*"), recursive=True)):
            if not os.path.isfile(path) or not path.lower().endswith((".csv", ".xlsx")):
                continue
            (fixture_paths if FIXTURE_MARKER in path else real_paths).append(path)

    real_records, fixture_records = [], []
    for path in real_paths:
        try:
            real_records.append(benchmark_report(import_any(path), scenario))
        except ImportError_ as exc:
            real_records.append({"path": os.path.relpath(path, ROOT), "status": "import_failed",
                                 "reason": str(exc)})
    for path in fixture_paths:
        try:
            fixture_records.append(benchmark_report(import_any(path), scenario))
        except ImportError_ as exc:
            fixture_records.append({"path": os.path.relpath(path, ROOT), "status": "import_failed",
                                    "reason": str(exc)})

    if real_records:
        status = "unverified_imports"
        blocked_reason = ("CSV origin is not authenticated by filename or hash. "
                          "Any fill comparisons are diagnostic only; failed imports are not measurements.")
    else:
        status = "blocked"
        blocked_reason = (
            "No authenticated TradingView Strategy Report export is present in "
            f"{REPORTS_DIR}/. Producing one requires a signed-in TradingView account with "
            "export entitlement (the official support page documents the CSV export button in "
            "the Strategy Report). This environment holds no TradingView credentials and does "
            "not fabricate platform output, so the Pine-vs-Python fill benchmark cannot be "
            "completed from real exports yet."
        )

    doc = {
        "_meta": {
            "kind": "pine_vs_python_fill_benchmark",
            "description": (
                "Comparison of exported Pine Strategy Report fills against the repository's "
                "Python fill model on the same committed vendor bars, plus a strict import audit "
                "of every export (header, column mapping, SHA-256, rejected rows, arithmetic "
                "P/L cross-check)."
            ),
            "engine": "tv-benchmark-1",
            "generated_utc": stamp,
            "scenario": {
                "key": args.scenario,
                "label": scenario.label,
                "commission_per_contract_per_side_usd":
                    scenario.commission_per_contract_per_side_usd,
                "slippage_atr_fraction": scenario.slippage_atr_fraction,
            },
            "status": status,
            "blocked_reason": blocked_reason,
            "reports_dir": REPORTS_DIR,
            "real_exports_found": len(real_paths),
            "fixture_exports_found": len(fixture_paths),
            "pine_emulator_rules": {
                "market_order_default": pine.DEFAULT_BEHAVIOR_STATEMENT,
                "intrabar_assumption": pine.INTRABAR_RULE_STATEMENT,
                "gap_rule": pine.GAP_RULE_STATEMENT,
                "source": "https://www.tradingview.com/pine-script-docs/concepts/strategies/",
            },
            "how_to_complete_this_benchmark": [
                "Sign in to TradingView on a plan that includes Strategy Tester export.",
                "Run the strategy on a chart, open the Strategy Report, and use the Download "
                "button on the 'List of Trades' tab (CSV or XLSX) - optionally also download "
                "the 'Performance Summary' tab.",
                "Commit the downloaded file to data/tv_reports/ (any filename).",
                "Re-run: python3 scripts/tv_benchmark.py",
                "The import audit runs immediately; the fill benchmark additionally needs the "
                "symbol, either in the export or in a <stem>.manifest.json beside it.",
            ],
            "not_a_forecast": True,
        },
        "exports": real_records,
        "fixtures": fixture_records,
        "fixture_notice": (
            "Records under 'fixtures' are SYNTHETIC files written by this repository to prove "
            "the import and benchmark code path. They are not TradingView output and their "
            "numbers must never be quoted as platform results."
        ),
    }
    out_path = os.path.join(ROOT, args.out)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print(f"tv benchmark: status={status} real_exports={len(real_paths)} "
          f"fixtures={len(fixture_paths)}")
    for record in real_records:
        fb = record.get("fill_benchmark", {})
        print(f"  {record['path']}: {fb.get('status')} "
              f"fills_compared={fb.get('fills_compared')} "
              f"exact_open_share={fb.get('share_exact_open_match')}")
    for record in fixture_records:
        fb = record.get("fill_benchmark", {})
        print(f"  [fixture] {record['path']}: {fb.get('status')} "
              f"fills_compared={fb.get('fills_compared')} "
              f"median_abs_delta_vs_bar_open_bps={fb.get('median_abs_delta_vs_bar_open_bps')}")
    if blocked_reason:
        print(f"  blocked: {blocked_reason}")
    print(f"wrote {os.path.relpath(out_path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
