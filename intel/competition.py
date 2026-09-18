"""Shadow-competition engine: portfolio simulation under official contest rules.

This module implements the repository's OWN paper competition ("shadow
competition"). It replicates the official The Leap rule constants transcribed
in data/contest_config.json:

- every participant account starts at 250,000 virtual USD;
- futures buying power is 20:1, so total open notional can never exceed
  20 x current equity (whole contracts only);
- per-symbol maximum open positions come from the official section 08 caps
  (data/initial_capacity.json, verified against the rules transcription);
- the ranking metric is REALIZED P/L on closed positions; every position is
  force-closed at the edition's end (the analog of the official
  end-of-competition auto-close), so end-of-edition ranking is fully realized;
- the account can never be reset: once equity <= 0 the participant is ruined
  for that edition (section 08 forbids resets);
- minimum active days (5) are counted per the official definition ("at least
  one action that results in opening or closing a position") and reported as a
  diagnostic, not a penalty.

Order semantics match intel.backtest (and therefore the Pine source):
decisions are evaluated on a bar's close and fill at that series' NEXT bar
open; slippage is a declared fraction of the decision bar's ATR(14) applied
adversely on both legs; commission is per contract per side.

Declared simplifications (NOT rulebook facts): entry-price notional
accounting marked at each symbol's most recent processed open, no intra-bar
margin calls (breaches are counted, not acted on), daily bars only (the
official contest allows intraday trading), and vendor front-month continuous
series with unadjusted roll splices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .backtest import COST_SCENARIOS, CostScenario
from .contrarian import DEFAULT_PARAMS, generate_decisions, resolve_params, warmup
from .data import Bar

START_BALANCE = 250_000.0
LEVERAGE = 20.0
TARGET_MULTIPLES = (5.0, 10.0, 20.0, 50.0, 100.0)
EDITION_CALENDAR_DAYS = 30      # mirrors the official Sep 1 -> Sep 30 window
MIN_EDITION_SESSIONS = 15       # a shorter shared window is discarded
SEASON_STEP_CALENDAR_DAYS = 30  # non-overlapping editions

ENGINE_VERSION = "intel-competition-1"


@dataclass(frozen=True)
class Series:
    """One tradable instrument: validated bars plus its official rule facts."""

    symbol: str
    bars: tuple[Bar, ...]
    contract_multiplier: float
    rules_cap_contracts: int


@dataclass(frozen=True)
class Participant:
    username: str
    model: str
    variant: str | None
    pool: tuple[str, ...]  # symbols this participant may trade


@dataclass
class Trade:
    symbol: str
    direction: str
    contracts: int
    entry_date: str
    exit_date: str
    entry_fill_price: float
    exit_fill_price: float
    net_pnl_usd: float


@dataclass
class EditionResult:
    realized_pnl_usd: float
    equity_multiple: float
    trades: int
    active_days: int
    ruined: bool
    margin_breach_bars: int
    max_drawdown_usd: float
    long_trades: int
    short_trades: int
    add_tranches: int
    skipped_entries: int
    multiple_buckets: list = field(default_factory=list)


def edition_windows(union_dates: list[str], final_window: bool) -> list[tuple[str, str]]:
    """Edition (start_date, end_date) pairs on the shared union calendar.

    Season: non-overlapping 30-calendar-day windows stepping from the first
    session. With final_window=True one extra window is appended, ending at
    the last session (the "live mirror" of the in-progress official edition).
    """
    if not union_dates:
        return []
    first = date.fromisoformat(union_dates[0])
    last = date.fromisoformat(union_dates[-1])
    out: list[tuple[str, str]] = []
    start = first
    while start + timedelta(days=EDITION_CALENDAR_DAYS - 1) <= last:
        end = start + timedelta(days=EDITION_CALENDAR_DAYS - 1)
        sessions = sum(1 for d in union_dates if start.isoformat() <= d <= end.isoformat())
        if sessions >= MIN_EDITION_SESSIONS:
            out.append((start.isoformat(), end.isoformat()))
        start += timedelta(days=SEASON_STEP_CALENDAR_DAYS)
    if final_window:
        fw_start = last - timedelta(days=EDITION_CALENDAR_DAYS - 1)
        sessions = sum(1 for d in union_dates if fw_start.isoformat() <= d <= last.isoformat())
        if sessions >= MIN_EDITION_SESSIONS:
            window = (fw_start.isoformat(), last.isoformat())
            if window not in out:
                out.append(window)
    return out


def _sizing_qty(
    equity: float,
    used_notional: float,
    fill_price: float,
    multiplier: float,
    cap: int,
    deployment: float,
) -> int:
    available = max(0.0, equity * LEVERAGE - used_notional)
    target = available * deployment
    notional_limit = cap * fill_price * multiplier
    room = min(target, notional_limit)
    if fill_price * multiplier <= 0:
        return 0
    return int(room // (fill_price * multiplier))


def run_participant_edition(
    decisions: dict[str, list],
    slices: dict[str, list[Bar]],
    starts: dict[str, int],
    spec_by_symbol: dict[str, Series],
    scenario: CostScenario,
    deployment: float = 1.0,
) -> EditionResult:
    """Simulate one participant over one edition on the shared calendar.

    `decisions` maps symbol -> precomputed Decision list on FULL series bar
    indices. `slices` maps symbol -> bars inside the edition window, and
    `starts` maps symbol -> the full-series index of that slice's first bar,
    so decision indices resolve as starts[sym] + i.
    """
    equity = START_BALANCE
    realized = 0.0
    ruined = False
    margin_breach_bars = 0
    peak = equity
    max_dd = 0.0
    trades: list[Trade] = []
    active_days: set[str] = set()
    add_tranches = 0
    long_trades = 0
    short_trades = 0
    skipped_entries = 0

    positions: dict[str, dict] = {}
    queues: dict[str, list] = {sym: [] for sym in slices}
    ptr = {sym: 0 for sym in slices}
    cursor = {sym: 0 for sym in slices}

    def sign(d: str) -> int:
        return 1 if d == "long" else -1

    def notional_used() -> float:
        total = 0.0
        for sym, pos in positions.items():
            spec = spec_by_symbol[sym]
            q = sum(t["qty"] for t in pos["tranches"])
            total += q * pos["last_open"] * spec.contract_multiplier
        return total

    def close_position(sym: str, pos: dict, exit_index: int, exit_slip_pts: float) -> None:
        """exit_index: full-series bar index of the exit bar (auto-close uses the slice's last bar)."""
        nonlocal realized, equity, long_trades, short_trades
        spec = spec_by_symbol[sym]
        exit_bar = spec.bars[exit_index]
        exit_raw = exit_bar.close
        for t in pos["tranches"]:
            d = sign(pos["dir"])
            raw = d * (exit_raw - t["entry_raw"]) * spec.contract_multiplier * t["qty"]
            slip = -(t["slip_pts"] + exit_slip_pts) * spec.contract_multiplier * t["qty"]
            comm = scenario.commission_per_contract_per_side_usd * t["qty"] + t["commission"]
            net = raw + slip - comm
            realized += net
            equity += net
            trades.append(Trade(
                symbol=sym, direction=pos["dir"], contracts=t["qty"],
                entry_date=t["entry_date"], exit_date=exit_bar.date,
                entry_fill_price=t["entry_raw"] + d * t["slip_pts"],
                exit_fill_price=exit_raw - d * exit_slip_pts,
                net_pnl_usd=net,
            ))
            if pos["dir"] == "long":
                long_trades += 1
            else:
                short_trades += 1
        active_days.add(exit_bar.date)

    calendar = sorted({b.date for bars in slices.values() for b in bars})

    for day in calendar:
        if ruined:
            break
        for sym in sorted(slices):
            if ruined:
                break
            sl = slices[sym]
            if cursor[sym] >= len(sl) or sl[cursor[sym]].date != day:
                continue
            i = cursor[sym]
            bar = sl[i]
            full_i = starts[sym] + i
            spec = spec_by_symbol[sym]

            # ---- fills at this bar's open for orders queued on the prior close ----
            for order in queues[sym]:
                pos = positions.get(sym)
                action = order["action"]
                slip_pts = scenario.slippage_atr_fraction * order["atr"]
                if action in ("long", "short"):
                    if pos is not None and pos["dir"] == action:
                        continue  # same-direction re-entry ignored (adds are explicit)
                    if pos is not None:
                        close_position(sym, pos, full_i, slip_pts)
                        positions.pop(sym, None)
                        pos = None
                    if equity <= 0:
                        ruined = True
                        break
                    qty = _sizing_qty(
                        equity, notional_used(), bar.open,
                        spec.contract_multiplier, spec.rules_cap_contracts, deployment,
                    )
                    if qty >= 1:
                        positions[sym] = {
                            "dir": action,
                            "tranches": [{
                                "qty": qty, "entry_raw": bar.open, "slip_pts": slip_pts,
                                "commission": scenario.commission_per_contract_per_side_usd * qty,
                                "entry_date": day,
                            }],
                            "entry_date": day,
                            "last_open": bar.open,
                        }
                        active_days.add(day)
                    else:
                        skipped_entries += 1
                elif action == "add":
                    if pos is None:
                        continue
                    if equity <= 0:
                        ruined = True
                        break
                    qty = _sizing_qty(
                        equity, notional_used(), bar.open,
                        spec.contract_multiplier, spec.rules_cap_contracts, deployment,
                    )
                    if qty >= 1:
                        pos["tranches"].append({
                            "qty": qty, "entry_raw": bar.open, "slip_pts": slip_pts,
                            "commission": scenario.commission_per_contract_per_side_usd * qty,
                            "entry_date": day,
                        })
                        pos["last_open"] = bar.open
                        add_tranches += 1
                        active_days.add(day)
                    else:
                        skipped_entries += 1
                elif action == "exit":
                    if pos is not None:
                        close_position(sym, pos, full_i, slip_pts)
                        positions.pop(sym, None)
            queues[sym] = []

            pos = positions.get(sym)
            if pos is not None:
                pos["last_open"] = bar.open

            # ---- mark-to-market diagnostics at this bar's close ----
            pos = positions.get(sym)
            if pos is not None:
                q = sum(t["qty"] for t in pos["tranches"])
                first_entry = pos["tranches"][0]["entry_raw"]
                open_pnl = sign(pos["dir"]) * (bar.close - first_entry) * spec.contract_multiplier * q
                mtm = equity + open_pnl
                required_margin = q * first_entry * spec.contract_multiplier / LEVERAGE
                if mtm < required_margin:
                    margin_breach_bars += 1
            else:
                mtm = equity
                if equity <= 0:
                    ruined = True
            peak = max(peak, mtm)
            dd = peak - mtm
            if dd > max_dd:
                max_dd = dd

            # ---- queue decisions evaluated on this bar's close ----
            dl = decisions.get(sym) or []
            while ptr[sym] < len(dl) and dl[ptr[sym]].index < full_i:
                ptr[sym] += 1
            while ptr[sym] < len(dl) and dl[ptr[sym]].index == full_i:
                dec = dl[ptr[sym]]
                ptr[sym] += 1
                queues[sym].append({"action": dec.action, "atr": dec.atr})
            cursor[sym] += 1

    # ---- edition auto-close at each series' last available close in the window ----
    for sym in sorted(positions):
        pos = positions[sym]
        last_full_i = starts[sym] + len(slices[sym]) - 1
        dl = decisions.get(sym) or []
        exit_atr = dl[-1].atr if dl else 0.0
        close_position(sym, pos, last_full_i, scenario.slippage_atr_fraction * exit_atr)

    result = EditionResult(
        realized_pnl_usd=realized,
        equity_multiple=1.0 + realized / START_BALANCE,
        trades=len(trades),
        active_days=len(active_days),
        ruined=ruined,
        margin_breach_bars=margin_breach_bars,
        max_drawdown_usd=max_dd,
        long_trades=long_trades,
        short_trades=short_trades,
        add_tranches=add_tranches,
        skipped_entries=skipped_entries,
    )
    result.multiple_buckets = [m for m in TARGET_MULTIPLES if result.equity_multiple >= m]
    return result


def prepare_decisions(
    series_map: dict[str, Series],
    model: str,
    variant: str | None,
) -> dict[str, list]:
    """Precompute decision lists per symbol for one (model, variant)."""
    out: dict[str, list] = {}
    for sym in sorted(series_map):
        bars = list(series_map[sym].bars)
        need = warmup(model, variant)
        out[sym] = generate_decisions(bars, model, variant) if len(bars) > need else []
    return out


def model_params_label(model: str, variant: str | None) -> str:
    """Human label of the frozen parameter delta a variant applies."""
    if not variant:
        return "default"
    params = resolve_params(model, variant)
    base = DEFAULT_PARAMS.get(model, {})
    diff = {k: v for k, v in params.items() if base.get(k) != v}
    return ", ".join(f"{k}={v}" for k, v in sorted(diff.items())) or "default"
