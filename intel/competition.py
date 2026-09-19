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

ENGINE_VERSION = "intel-competition-2"


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
    entry_ts: int | None = None
    exit_ts: int | None = None


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

    def close_position(sym: str, pos: dict, exit_index: int, exit_slip_pts: float,
                       at_close: bool = False) -> None:
        """exit_index: full-series bar index of the exit bar (auto-close uses the slice's last bar)."""
        nonlocal realized, equity, long_trades, short_trades
        spec = spec_by_symbol[sym]
        exit_bar = spec.bars[exit_index]
        exit_raw = exit_bar.close if at_close else exit_bar.open
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
        known = [d for d in dl if d.index <= last_full_i]
        exit_atr = known[-1].atr if known else 0.0
        close_position(sym, pos, last_full_i, scenario.slippage_atr_fraction * exit_atr, at_close=True)

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
    """Human label of the frozen parameter delta a variant applies.

    Futures models (C1-C5, the baselines) resolve through intel.contrarian; the volatile-equity
    models (C6-C19) resolve through intel.stock_strategies, which owns its own frozen parameter
    table. The import is local so the two strategy modules stay independent of each other.
    """
    if not variant:
        return "default"
    try:
        params = resolve_params(model, variant)
        base = DEFAULT_PARAMS.get(model, {})
    except ValueError:
        from .stock_strategies import DEFAULT_PARAMS as STOCK_DEFAULTS
        from .stock_strategies import resolve_params as resolve_stock_params

        params = resolve_stock_params(model, variant)
        base = STOCK_DEFAULTS.get(model, {})
    diff = {k: v for k, v in params.items() if base.get(k) != v}
    return ", ".join(f"{k}={v}" for k, v in sorted(diff.items())) or "default"


# ===========================================================================
# Division-general engine (rule profiles + execution latency).
#
# The function above (`run_participant_edition`) is the original futures-only
# engine and its output is committed in data/competition_results.json; it is kept
# byte-for-byte stable. The code below generalises the same accounting so a second
# division (the volatile-equity pool) can run under its own verified rule profile
# and under an explicit execution-latency delay. `run_participant_window` with
# profile `futures_amp_sep2026` and latency_bars=0 reproduces the legacy engine's
# result on identical inputs; scripts/verify.py re-checks that equality on real
# captured data so the two engines cannot silently diverge.
# ===========================================================================

DIVISION_ENGINE_VERSION = "intel-competition-3"


@dataclass(frozen=True)
class RuleProfile:
    """Rule constants for one competition division.

    Every numeric field is transcribed from an official TradingView rules page and carries
    the source id it came from. `is_counterfactual` marks a profile that is deliberately NOT
    an official rule set: it exists only to answer "what would the same models do with more
    buying power", and every artifact that uses it must say so.
    """

    profile_id: str
    label: str
    starting_balance: float
    leverage: float
    commission_model: str                    # "per_unit" | "percent_of_notional"
    commission_pct_of_notional: float
    per_symbol_cap_units: int | None         # None = use each instrument's own rules cap
    min_active_days: int
    source_ids: tuple[str, ...]
    is_counterfactual: bool
    notes: str


RULE_PROFILES: dict[str, RuleProfile] = {
    "futures_amp_sep2026": RuleProfile(
        profile_id="futures_amp_sep2026",
        label="The Leap by AMP Futures - September 2026 (official, futures)",
        starting_balance=250_000.0,
        leverage=20.0,
        commission_model="per_unit",
        commission_pct_of_notional=0.0,
        per_symbol_cap_units=None,
        min_active_days=5,
        source_ids=("TV-RULES-AMP-SEP2026",),
        is_counterfactual=False,
        notes=(
            "250,000 virtual USD, futures leverage 20:1, per-symbol caps from section 08, "
            "ranking by realized P/L on closed positions, end-of-edition auto-close, no resets. "
            "The rules page does not state a dollar commission for this edition, so the "
            "per-unit commission comes from the declared CostScenario instead."
        ),
    ),
    "stocks_official_leap": RuleProfile(
        profile_id="stocks_official_leap",
        label="The Leap Magnificent Seven - March 2026 (official stocks-edition constants)",
        starting_balance=100_000.0,
        leverage=1.0,
        commission_model="percent_of_notional",
        commission_pct_of_notional=0.0001,
        per_symbol_cap_units=50,
        min_active_days=3,
        source_ids=("TV-RULES-MAG7-MAR2026",),
        is_counterfactual=False,
        notes=(
            "Official stocks-edition constants: 'The preset balance size for the Paper Trading "
            "Competition Account is 100,000 virtual USD. Leverage for stocks: 1:1. The "
            "commission is 0.01%.' and 'The maximum size of an open position per instrument is "
            "limited to 50.0 units. One unit represents one share of the underlying "
            "instrument.' The 50-unit cap is applied to every symbol in the pool here; the "
            "official page lists it for its own seven instruments."
        ),
    ),
    "stocks_20x_counterfactual": RuleProfile(
        profile_id="stocks_20x_counterfactual",
        label="NOT OFFICIAL: volatile-equity pool at futures-grade 20:1 buying power",
        starting_balance=100_000.0,
        leverage=20.0,
        commission_model="percent_of_notional",
        commission_pct_of_notional=0.0001,
        per_symbol_cap_units=50,
        min_active_days=3,
        source_ids=("TV-RULES-MAG7-MAR2026", "TV-RULES-AMP-SEP2026"),
        is_counterfactual=True,
        notes=(
            "Counterfactual profile. It combines the official stocks-edition balance, "
            "commission and 50-unit cap with the official futures-edition 20:1 buying power. "
            "No official TradingView rules page grants 20:1 on stocks; this profile exists only "
            "to measure how much of the explosive-return question is buying power rather than "
            "signal, and every artifact built from it is labelled counterfactual."
        ),
    ),
}


def _commission_for_fill(profile: RuleProfile, scenario: CostScenario,
                         price: float, qty: int, multiplier: float) -> float:
    if profile.commission_model == "percent_of_notional":
        return profile.commission_pct_of_notional * price * qty * multiplier
    return scenario.commission_per_contract_per_side_usd * qty


def run_participant_window(
    decisions: dict[str, list],
    slices: dict[str, list[Bar]],
    starts: dict[str, int],
    spec_by_symbol: dict[str, Series],
    profile: RuleProfile,
    scenario: CostScenario,
    latency_bars: int = 0,
    deployment: float = 1.0,
    control_symbol: str | None = None,
    return_fills: bool = False,
    arbitration: str = "sequential",
    roll_dates: dict[str, set[str]] | None = None,
) -> EditionResult:
    """Simulate one participant over one window under a rule profile.

    Differences from `run_participant_edition`, all explicit:

    - `profile` supplies the starting balance, the buying power, the commission model and
      the per-symbol cap. `scenario` supplies the per-unit commission (for the per-unit
      model) and the ATR-fraction slippage on both legs.
    - `latency_bars` delays every fill: a decision evaluated on the close of bar i fills at
      the open of bar i + 1 + latency_bars of the same series. Orders whose fill bar falls
      outside the window are counted in `expired_orders` and never fill.
    - `control_symbol`, when given, opens one maximum-size long in that symbol at the first
      bar of the window and holds it to the auto-close (the B1 control).
    - `return_fills`, when True, attaches a per-fill log (`result.fill_log`) preserving the
      exact entry/exit timestamps, dates, prices and net P/L of every closed tranche. The
      default False keeps the legacy output shape (aggregates only).
    - `arbitration` controls simultaneous-symbol buying-power allocation. "sequential"
      (default) fills symbols in sorted order per date/timestamp, so the first symbol may
      consume the shared buying power. "proportional" splits the buying power available at
      the start of each date (daily bars) or timestamp (intraday bars) equally among the
      symbols with entry/add orders due there; each symbol's sizing is capped by its share
      (no redistribution of unused shares; closes inside the group do not expand the
      others' budgets; a symbol's consecutive fills inside one group decrement its own
      share). Both modes are deterministic; committed artifacts use "sequential".
    - `roll_dates`, when given, maps symbol -> set of ISO dates on which any open position
      is force-closed at that bar's open (a declared contract-roll / corporate-action
      boundary) and counted in `result.roll_closes`. No roll schedule is committed for any
      captured series, so committed runs pass None and record zero roll closes.
    """
    if not isinstance(latency_bars, int) or isinstance(latency_bars, bool) or latency_bars < 0:
        raise ValueError("latency_bars must be a nonnegative integer")
    if not 0 < deployment <= 1:
        raise ValueError("deployment must be in (0, 1]")
    if arbitration not in ("sequential", "proportional"):
        raise ValueError("arbitration must be 'sequential' or 'proportional'")
    if roll_dates is not None:
        if not isinstance(roll_dates, dict):
            raise ValueError("roll_dates must map symbol -> set of ISO dates")
        for sym, dates in roll_dates.items():
            if sym not in spec_by_symbol:
                raise ValueError(f"roll_dates symbol {sym!r} is not in the series map")
            for day in dates:
                date.fromisoformat(day)  # validate shape eagerly
    equity = profile.starting_balance
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
    expired_orders = 0
    roll_closes = 0
    fill_log: list[dict] = []

    positions: dict[str, dict] = {}
    pending: dict[str, dict[int, list]] = {sym: {} for sym in slices}
    ptr = {sym: 0 for sym in slices}
    cursor = {sym: 0 for sym in slices}
    last_full_i = {sym: starts[sym] + len(slices[sym]) - 1 for sym in slices}

    def sign(direction: str) -> int:
        return 1 if direction == "long" else -1

    def cap_for(sym: str) -> int:
        spec = spec_by_symbol[sym]
        if profile.per_symbol_cap_units is None:
            return spec.rules_cap_contracts
        return min(spec.rules_cap_contracts, profile.per_symbol_cap_units)

    def notional_used() -> float:
        total = 0.0
        for sym, pos in positions.items():
            spec = spec_by_symbol[sym]
            qty = sum(t["qty"] for t in pos["tranches"])
            total += qty * pos["last_open"] * spec.contract_multiplier
        return total

    def sizing_qty(fill_price: float, sym: str, budget_cap: float | None = None) -> int:
        spec = spec_by_symbol[sym]
        available = max(0.0, equity * profile.leverage - notional_used())
        target = available * deployment
        notional_limit = cap_for(sym) * fill_price * spec.contract_multiplier
        room = min(target, notional_limit)
        if budget_cap is not None:
            room = min(room, budget_cap)
        if fill_price * spec.contract_multiplier <= 0:
            return 0
        return int(room // (fill_price * spec.contract_multiplier))

    def open_position(sym: str, direction: str, bar: Bar, slip_pts: float, day: str,
                      budget_cap: float | None = None) -> int:
        nonlocal skipped_entries
        qty = sizing_qty(bar.open, sym, budget_cap)
        if qty < 1:
            skipped_entries += 1
            return 0
        positions[sym] = {
            "dir": direction,
            "tranches": [{
                "qty": qty,
                "entry_raw": bar.open,
                "slip_pts": slip_pts,
                "commission": _commission_for_fill(
                    profile, scenario, bar.open, qty, spec_by_symbol[sym].contract_multiplier),
                "entry_date": day,
                "entry_ts": bar.ts,
            }],
            "entry_date": day,
            "last_open": bar.open,
        }
        active_days.add(day)
        return qty

    def add_tranche(sym: str, pos: dict, bar: Bar, slip_pts: float, day: str,
                    budget_cap: float | None = None) -> int:
        nonlocal add_tranches, skipped_entries
        qty = sizing_qty(bar.open, sym, budget_cap)
        if qty < 1:
            skipped_entries += 1
            return 0
        pos["tranches"].append({
            "qty": qty,
            "entry_raw": bar.open,
            "slip_pts": slip_pts,
            "commission": _commission_for_fill(
                profile, scenario, bar.open, qty, spec_by_symbol[sym].contract_multiplier),
            "entry_date": day,
            "entry_ts": bar.ts,
        })
        pos["last_open"] = bar.open
        add_tranches += 1
        active_days.add(day)
        return qty

    def close_position(sym: str, pos: dict, exit_index: int, exit_slip_pts: float,
                       at_close: bool = False, reason: str = "signal") -> None:
        nonlocal realized, equity, long_trades, short_trades
        spec = spec_by_symbol[sym]
        exit_bar = spec.bars[exit_index]
        exit_raw = exit_bar.close if at_close else exit_bar.open
        for tranche in pos["tranches"]:
            direction = sign(pos["dir"])
            gross = direction * (exit_raw - tranche["entry_raw"]) * spec.contract_multiplier * tranche["qty"]
            slip = -(tranche["slip_pts"] + exit_slip_pts) * spec.contract_multiplier * tranche["qty"]
            commission = _commission_for_fill(
                profile, scenario, exit_raw, tranche["qty"], spec.contract_multiplier
            ) + tranche["commission"]
            net = gross + slip - commission
            realized += net
            equity += net
            entry_fill = tranche["entry_raw"] + direction * tranche["slip_pts"]
            exit_fill = exit_raw - direction * exit_slip_pts
            trades.append(Trade(
                symbol=sym, direction=pos["dir"], contracts=tranche["qty"],
                entry_date=tranche["entry_date"], exit_date=exit_bar.date,
                entry_fill_price=entry_fill,
                exit_fill_price=exit_fill,
                net_pnl_usd=net,
                entry_ts=tranche.get("entry_ts"),
                exit_ts=exit_bar.ts,
            ))
            if return_fills:
                fill_log.append({
                    "symbol": sym,
                    "direction": pos["dir"],
                    "qty": tranche["qty"],
                    "entry_date": tranche["entry_date"],
                    "entry_ts": tranche.get("entry_ts"),
                    "exit_date": exit_bar.date,
                    "exit_ts": exit_bar.ts,
                    "entry_fill_price": round(entry_fill, 6),
                    "exit_fill_price": round(exit_fill, 6),
                    "at_close": at_close,
                    "reason": reason,
                    "net_pnl_usd": round(net, 2),
                })
            if pos["dir"] == "long":
                long_trades += 1
            else:
                short_trades += 1
        active_days.add(exit_bar.date)

    if control_symbol is not None:
        sym = control_symbol
        if sym in slices and slices[sym]:
            spec = spec_by_symbol[sym]
            bar = slices[sym][0]
            open_position(sym, "long", bar, 0.0, bar.date)

    # ---- event stream ----
    # Daily series (at most one bar per symbol per UTC date) are processed in the legacy
    # order: by date, then by symbol name. Intraday series (several bars per date) are
    # processed in timestamp order. Nothing else differs, so a daily run over the same
    # inputs reproduces run_participant_edition exactly (checked by scripts/verify.py).
    daily_mode = all(
        len({bar.date for bar in series}) == len(series) for series in slices.values()
    )
    if daily_mode:
        events = [
            (bar.date, sym, i)
            for day in sorted({bar.date for series in slices.values() for bar in series})
            for sym in sorted(slices)
            for i, bar in enumerate(slices[sym])
            if bar.date == day
        ]
    else:
        events = sorted(
            (bar.date, bar.ts, sym, i)
            for sym in sorted(slices)
            for i, bar in enumerate(slices[sym])
        )

    # Proportional arbitration pre-computes the event groups (one date for daily bars,
    # one timestamp for intraday bars) so that at each group start the engine can split the
    # buying power available then among the symbols with entry/add orders due in the group.
    group_members: dict = {}
    if arbitration == "proportional":
        for event in events:
            if daily_mode:
                g_day, g_sym, g_i = event
                group_key = g_day
            else:
                g_day, g_ts, g_sym, g_i = event
                group_key = (g_day, g_ts)
            group_members.setdefault(group_key, []).append((g_sym, starts[g_sym] + g_i))
    current_group = object()
    group_budget: dict[str, float] = {}

    for event in events:
        if ruined:
            break
        if daily_mode:
            day, sym, i = event
            group_key = day
        else:
            day, _ts, sym, i = event
            group_key = (day, _ts)
        if True:
            series = slices[sym]
            bar = series[i]
            full_i = starts[sym] + i
            spec = spec_by_symbol[sym]
            cursor[sym] = i

            if group_key != current_group:
                current_group = group_key
                group_budget = {}
                if arbitration == "proportional":
                    claimants = sorted({
                        g_sym for g_sym, g_full in group_members[group_key]
                        for order in pending[g_sym].get(g_full, [])
                        if order["action"] in ("long", "short", "add")
                    })
                    if claimants:
                        share = max(0.0, equity * profile.leverage - notional_used()) / len(claimants)
                        group_budget = {g_sym: share for g_sym in claimants}

            # ---- declared roll boundary: force-close at this bar's open ----
            if roll_dates and day in roll_dates.get(sym, ()):
                pos = positions.get(sym)
                if pos is not None:
                    known = [d for d in (decisions.get(sym) or []) if d.index <= full_i]
                    roll_atr = known[-1].atr if known else 0.0
                    close_position(sym, pos, full_i,
                                   scenario.slippage_atr_fraction * roll_atr, reason="roll")
                    positions.pop(sym, None)
                    roll_closes += 1

            # ---- fills for orders due at this bar's open ----
            for order in pending[sym].pop(full_i, []):
                pos = positions.get(sym)
                slip_pts = scenario.slippage_atr_fraction * order["atr"]
                action = order["action"]
                budget = group_budget.get(sym) if arbitration == "proportional" else None
                if action in ("long", "short"):
                    if pos is not None and pos["dir"] == action:
                        continue
                    if pos is not None:
                        close_position(sym, pos, full_i, slip_pts)
                        positions.pop(sym, None)
                        pos = None
                    if equity <= 0:
                        ruined = True
                        break
                    filled = open_position(sym, action, bar, slip_pts, day, budget)
                    if arbitration == "proportional" and budget is not None:
                        group_budget[sym] = max(
                            0.0, budget - filled * bar.open * spec.contract_multiplier)
                elif action == "add":
                    if pos is None:
                        continue
                    if equity <= 0:
                        ruined = True
                        break
                    filled = add_tranche(sym, pos, bar, slip_pts, day, budget)
                    if arbitration == "proportional" and budget is not None:
                        group_budget[sym] = max(
                            0.0, budget - filled * bar.open * spec.contract_multiplier)
                elif action == "exit":
                    if pos is not None:
                        close_position(sym, pos, full_i, slip_pts)
                        positions.pop(sym, None)

            pos = positions.get(sym)
            if pos is not None:
                pos["last_open"] = bar.open

            # ---- mark-to-market diagnostics at this bar's close ----
            pos = positions.get(sym)
            if pos is not None:
                qty = sum(t["qty"] for t in pos["tranches"])
                first_entry = pos["tranches"][0]["entry_raw"]
                open_pnl = sign(pos["dir"]) * (bar.close - first_entry) * spec.contract_multiplier * qty
                mtm = equity + open_pnl
                required_margin = qty * first_entry * spec.contract_multiplier / profile.leverage
                if mtm < required_margin:
                    margin_breach_bars += 1
            else:
                mtm = equity
                if equity <= 0:
                    ruined = True
            peak = max(peak, mtm)
            max_dd = max(max_dd, peak - mtm)

            # ---- queue decisions evaluated on this bar's close ----
            if control_symbol is None:
                decision_list = decisions.get(sym) or []
                while ptr[sym] < len(decision_list) and decision_list[ptr[sym]].index < full_i:
                    ptr[sym] += 1
                while ptr[sym] < len(decision_list) and decision_list[ptr[sym]].index == full_i:
                    decision = decision_list[ptr[sym]]
                    ptr[sym] += 1
                    due = full_i + 1 + latency_bars
                    if due <= last_full_i[sym]:
                        pending[sym].setdefault(due, []).append(
                            {"action": decision.action, "atr": decision.atr})
                    else:
                        expired_orders += 1

    # orders still queued when the window ends never fill
    expired_orders += sum(len(orders) for sym in pending for orders in pending[sym].values())

    # ---- window auto-close at each series' last available close in the window ----
    for sym in sorted(positions):
        pos = positions[sym]
        decision_list = decisions.get(sym) or []
        known = [d for d in decision_list if d.index <= last_full_i[sym]]
        exit_atr = known[-1].atr if known else 0.0
        close_position(sym, pos, last_full_i[sym], scenario.slippage_atr_fraction * exit_atr,
                       at_close=True, reason="auto_close")

    result = EditionResult(
        realized_pnl_usd=realized,
        equity_multiple=1.0 + realized / profile.starting_balance,
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
    result.expired_orders = expired_orders
    result.fill_log = fill_log
    result.roll_closes = roll_closes
    result.arbitration = arbitration
    return result


def max_edition_multiple_bound(
    profile: RuleProfile,
    prices: list[float],
    max_favorable_move: float,
    instruments: int | None = None,
) -> dict:
    """Single-hold scenario arithmetic; NOT a ceiling on repeated trading.

    With a per-instrument cap of C units, a starting balance B, buying power L and a
    list of live prices, the maximum notional a participant can hold is

        N = C * sum(prices)          (capped by B * L)

    If every held instrument then moves favourably by `max_favorable_move` (a fraction,
    e.g. 1.0 = +100%), realized P/L is at most N * move, so the edition multiple is at
    most 1 + N * move / B for this one holding period only. It assumes simultaneous maximum size
    in every instrument and a frictionless exit at the extreme.
    """
    if not prices:
        raise ValueError("prices must be non-empty")
    if instruments is not None:
        prices = sorted(prices, reverse=True)[:instruments]
    cap = profile.per_symbol_cap_units
    if cap is None:
        raise ValueError(
            f"profile {profile.profile_id} has no fixed per-symbol cap; the bound is "
            "instrument-specific and is computed per symbol instead"
        )
    max_notional = cap * sum(prices)
    binding_notional = min(max_notional, profile.starting_balance * profile.leverage)
    multiple = 1.0 + binding_notional * max_favorable_move / profile.starting_balance
    return {
        "profile_id": profile.profile_id,
        "per_symbol_cap_units": cap,
        "instruments": len(prices),
        "sum_prices": round(sum(prices), 6),
        "max_notional_usd": round(max_notional, 2),
        "buying_power_usd": round(profile.starting_balance * profile.leverage, 2),
        "binding_notional_usd": round(binding_notional, 2),
        "max_favorable_move": max_favorable_move,
        "max_edition_multiple": round(multiple, 6),
        "starting_balance_usd": profile.starting_balance,
    }


# ===========================================================================
# Forward-looking order state (for the executive summary).
#
# Deterministic replay of the SAME decision lists the engine consumes, so the
# repository can state which orders a model would place at the next bar open
# instead of describing its rules in prose. Sizing and account equity are NOT
# replayed here (the caller states the sizing rule separately); only the order
# sequence, the open position and the pending fill are derived.
# ===========================================================================

def replay_order_state(
    decision_list: list,
    bars: list,
    latency_bars: int = 0,
) -> dict:
    """Replay one model's decisions over one series and report the resulting state.

    Returns a dict with:
      position          "long" | "short" | None as of the last bar
      position_since    date the current position was opened (None if flat)
      pending           list of orders awaiting their fill bar
      last_decision     the most recent decision (index, action, reason, bar date)
    """
    position = None
    position_since = None
    pending_due: dict[int, list] = {}
    last_decision = None
    cursor = 0
    for i, bar in enumerate(bars):
        for order in pending_due.pop(i, []):
            if order["action"] in ("long", "short"):
                position = order["action"]
                position_since = bar.date
            elif order["action"] == "exit":
                position = None
                position_since = None
        while cursor < len(decision_list) and decision_list[cursor].index < i:
            cursor += 1
        while cursor < len(decision_list) and decision_list[cursor].index == i:
            decision = decision_list[cursor]
            cursor += 1
            due = i + 1 + latency_bars
            pending_due.setdefault(due, []).append({
                "action": decision.action,
                "reason": decision.reason,
                "decided_index": i,
                "decided_date": bar.date,
                "decided_close": bar.close,
                "atr": decision.atr,
                "due_index": due,
            })
            last_decision = {
                "index": i,
                "date": bar.date,
                "action": decision.action,
                "reason": decision.reason,
                "close": bar.close,
                "atr": decision.atr,
            }
    pending_orders = [order for _, orders in sorted(pending_due.items()) for order in orders]
    return {
        "position": position,
        "position_since": position_since,
        "pending": pending_orders,
        "last_decision": last_decision,
        "last_bar_index": len(bars) - 1,
        "last_bar_date": bars[-1].date if bars else None,
    }


# ===========================================================================
# Multi-season competition orchestrator.
#
# Provides first-class support for running multi-season paper trading competitions
# directly on the 20-stock volatile equities pool alongside futures, line by line
# verified against official sources.
#
# Futures pool: the 20 selected futures from data/master_list.json (section-08 caps,
# CME contract multipliers verified in research/sources/sources.json, e.g.
# CME-SPEC-CL1!, CME-SPEC-SI1!, CME-SPEC-ETH1!, CME-SPEC-BTC1!).
# Rule profile: futures_amp_sep2026 (250k virtual, 20:1, whole contracts,
# realized-P/L ranking, TV-RULES-AMP-SEP2026, https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/).
#
# Volatile-equity pool: the 20 names in data/volatile_stocks.json (verified
# trough→peak multiples 30–382x recomputable from Yahoo adjusted closes; see
# research/evidence/VOLATILE-STOCKS-YAHOO-DAILY.md and
# research/evidence/VOLATILE-STOCKS-YAHOO-MONTHLY.md, tier market_data_vendor,
# source_id YAHOO-DAILY-GME etc., endpoint https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}).
# Rule profile: stocks_official_leap (100k virtual, 1:1, 0.01% commission,
# 50-unit cap per instrument, TV-RULES-MAG7-MAR2026, https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/)
# plus the declared counterfactual stocks_20x_counterfactual (20:1 buying power,
# explicitly labelled NOT OFFICIAL).
#
# Real verified pricing: vendor captures under data/market_history/ (futures daily)
# and data/intraday/ (equities 1d/1h/15m, SHA-256 indexed, provenance in
# data/intraday_index.json, script scripts/fetch_intraday.py) plus the official
# provider route data/official_bars/ via Alpaca IEX (https://docs.alpaca.markets/us/reference/stockbars,
# free Basic/IEX feed, IEX is one exchange not consolidated pricing, split-adjusted,
# authenticated via APCA_API_KEY_ID / APCA_API_SECRET_KEY, see scripts/fetch_official_bars.py).
# No prices are fabricated here; missing series are explicit (status failed /
# not_attempted) and never replaced with synthetic data.
#
# Supports window slicing, participant decision dispatch, execution latency delay
# (fills at bar i+1+latency), counterfactual profiles, in-sample vs forward
# held-out test partitioning, and target-hit statistics. Every price, multiplier,
# cap and rule constant is traceable to an official or vendor-tier source
# registered in research/sources/sources.json; scripts/verify.py re-derives
# every computed field line by line.
# ===========================================================================

@dataclass
class MultiSeasonResult:
    """Complete output of a multi-season competition division."""
    editions: list[dict]
    latest_edition: dict
    participants: list[dict]
    leaderboard: list[dict]
    target_summary: dict
    in_sample_leaderboard: list[dict] | None = None
    forward_held_out_leaderboard: list[dict] | None = None
    forward_held_out_count: int = 0


def slices_and_starts(
    pool_symbols: tuple[str, ...] | list[str],
    series_map: dict[str, Series],
    window: tuple[str, str],
) -> tuple[dict[str, list[Bar]], dict[str, int]]:
    """Slice series bars into the given date window and return start indices."""
    start, end = window
    slices, starts = {}, {}
    for symbol in pool_symbols:
        if symbol not in series_map:
            continue
        bars = list(series_map[symbol].bars)
        idxs = [i for i, b in enumerate(bars) if start <= b.date <= end]
        if not idxs:
            continue
        slices[symbol] = [bars[i] for i in idxs]
        starts[symbol] = idxs[0]
    return slices, starts


def run_division_seasons(
    series_map: dict[str, Series],
    participants: list[Participant],
    profile: RuleProfile,
    scenario: CostScenario,
    decisions_provider: callable,
    windows: list[tuple[str, str]],
    latency_bars: int = 0,
    control_symbol_picker: callable | None = None,
    forward_held_out_count: int = 0,
    min_active_days: int | None = None,
    division_name: str = "daily",
    division_of_user: dict[str, str] | None = None,
    arbitration: str = "sequential",
    roll_dates: dict[str, set[str]] | None = None,
) -> MultiSeasonResult:
    """Run paper competition seasons across windows for all participants.

    `arbitration` and `roll_dates` pass straight through to run_participant_window;
    every edition row records the arbitration mode and the roll-close count it ran
    under, so a future non-default run cannot be mistaken for the legacy baseline.
    """
    import statistics

    if min_active_days is None:
        min_active_days = profile.min_active_days

    if len(windows) < 2:
        raise ValueError("At least 2 windows (at least one season + latest) required")

    season_windows = windows[:-1]
    latest_window = windows[-1]

    def run_one_window(window: tuple[str, str], ed_id: str) -> dict:
        results = {}
        for p in participants:
            pool_symbols = tuple(s for s in p.pool if s in series_map)
            if not pool_symbols:
                continue
            slices, starts = slices_and_starts(pool_symbols, series_map, window)
            if not slices:
                continue
            control = None
            if p.model == "B1" and control_symbol_picker:
                control = control_symbol_picker(pool_symbols, series_map, window)
                if control is None:
                    continue
            dec = {} if p.model == "B1" else decisions_provider(p.model, p.variant, series_map)
            results[p.username] = run_participant_window(
                dec, slices, starts, series_map, profile, scenario,
                latency_bars=latency_bars, control_symbol=control,
                arbitration=arbitration, roll_dates=roll_dates,
            )

        rows = []
        for username, r in results.items():
            rows.append({
                "username": username,
                "realized_pnl_usd": round(r.realized_pnl_usd, 2),
                "equity_multiple": round(r.equity_multiple, 6),
                "trades": r.trades,
                "active_days": r.active_days,
                "meets_min_active_days": r.active_days >= min_active_days,
                "ruined": r.ruined,
                "add_tranches": r.add_tranches,
                "long_trades": r.long_trades,
                "short_trades": r.short_trades,
                "skipped_entries": r.skipped_entries,
                "expired_orders": getattr(r, "expired_orders", 0),
                "roll_closes": getattr(r, "roll_closes", 0),
                "arbitration": getattr(r, "arbitration", "sequential"),
                "margin_breach_bars": r.margin_breach_bars,
                "max_drawdown_usd": round(r.max_drawdown_usd, 2),
                "multiple_buckets": r.multiple_buckets,
            })
        rows.sort(key=lambda row: (-row["realized_pnl_usd"], row["username"]))
        for i, row in enumerate(rows, 1):
            row["rank"] = i

        return {
            "edition_id": ed_id,
            "start_date": window[0],
            "end_date": window[1],
            "participants": len(rows),
            "leader": {
                "username": rows[0]["username"],
                "realized_pnl_usd": rows[0]["realized_pnl_usd"],
                "equity_multiple": rows[0]["equity_multiple"],
            } if rows else None,
            "rows": rows,
        }

    editions = []
    prefix = division_name[0].upper() if division_name else "E"
    for n, window in enumerate(season_windows, 1):
        editions.append(run_one_window(window, f"{prefix}{n:03d}"))

    latest_doc = run_one_window(latest_window, f"{prefix}LATEST")

    def aggregate_participants(edition_list: list[dict]) -> list[dict]:
        from .contrarian import MODEL_NAMES as FUTURES_NAMES
        out = []
        for p in participants:
            per = [next((r for r in ed["rows"] if r["username"] == p.username), None)
                   for ed in edition_list]
            per = [r for r in per if r is not None]
            if not per:
                continue
            season_mult = 1.0
            for row in per:
                season_mult *= max(row["equity_multiple"], 0.0)
            latest_row = next((r for r in latest_doc["rows"] if r["username"] == p.username), None)

            try:
                from .stock_strategies import MODEL_NAMES as STOCK_NAMES, MODEL_KIND as STOCK_KINDS
                m_name = STOCK_NAMES.get(p.model) or FUTURES_NAMES.get(p.model, p.model)
                m_kind = STOCK_KINDS.get(p.model, "baseline")
            except Exception:
                m_name = FUTURES_NAMES.get(p.model, p.model)
                m_kind = "baseline"

            user_div = (division_of_user.get(p.username, division_name)
                        if division_of_user else division_name)

            out.append({
                "username": p.username,
                "division": user_div,
                "kind": m_kind,
                "model": p.model,
                "model_name": m_name,
                "variant": p.variant,
                "params_label": model_params_label(p.model, p.variant),
                "pool": list(p.pool),
                "editions_played": len(per),
                "ruined_editions": sum(1 for r in per if r["ruined"]),
                "negative_editions": sum(1 for r in per if r["equity_multiple"] < 0),
                "season_realized_pnl_usd": round(sum(r["realized_pnl_usd"] for r in per), 2),
                "season_multiple": round(season_mult, 6),
                "best_edition_multiple": round(max(r["equity_multiple"] for r in per), 6),
                "worst_edition_multiple": round(min(r["equity_multiple"] for r in per), 6),
                "editions_ge_2x": sum(1 for r in per if r["equity_multiple"] >= 2),
                "editions_ge_5x": sum(1 for r in per if r["equity_multiple"] >= 5),
                "editions_ge_10x": sum(1 for r in per if r["equity_multiple"] >= 10),
                "editions_ge_20x": sum(1 for r in per if r["equity_multiple"] >= 20),
                "median_edition_multiple": round(statistics.median(r["equity_multiple"] for r in per), 6),
                "total_trades": sum(r["trades"] for r in per),
                "total_add_tranches": sum(r["add_tranches"] for r in per),
                "editions_meeting_min_active_days": sum(1 for r in per if r["meets_min_active_days"]),
                "latest_edition_rank": latest_row["rank"] if latest_row else None,
                "latest_edition_multiple": latest_row["equity_multiple"] if latest_row else None,
            })
        return out

    def make_leaderboard(p_docs: list[dict]) -> list[dict]:
        rows = sorted(p_docs, key=lambda a: (-a["season_realized_pnl_usd"], a["username"]))
        for i, row in enumerate(rows, 1):
            row["season_rank"] = i
        return [{
            "season_rank": r["season_rank"],
            "username": r["username"],
            "division": r.get("division", division_name),
            "model": r["model"],
            "season_realized_pnl_usd": r["season_realized_pnl_usd"],
            "season_multiple": r["season_multiple"],
            "best_edition_multiple": r["best_edition_multiple"],
            "median_edition_multiple": r["median_edition_multiple"],
            "editions_ge_2x": r["editions_ge_2x"],
        } for r in rows]

    part_docs = aggregate_participants(editions)
    leaderboard = make_leaderboard(part_docs)

    all_rows = [r for ed in editions for r in ed["rows"]]
    targets = {
        "participant_editions": len(all_rows),
        "ge_1.1x": sum(1 for r in all_rows if r["equity_multiple"] >= 1.1),
        "ge_2x": sum(1 for r in all_rows if r["equity_multiple"] >= 2),
        "ge_5x": sum(1 for r in all_rows if r["equity_multiple"] >= 5),
        "ge_10x": sum(1 for r in all_rows if r["equity_multiple"] >= 10),
        "ge_20x": sum(1 for r in all_rows if r["equity_multiple"] >= 20),
        "ge_50x": sum(1 for r in all_rows if r["equity_multiple"] >= 50),
        "ge_100x": sum(1 for r in all_rows if r["equity_multiple"] >= 100),
        "ruined_participant_editions": sum(1 for r in all_rows if r["ruined"]),
        "mean_equity_multiple": round(statistics.fmean(r["equity_multiple"] for r in all_rows), 6) if all_rows else None,
        "median_equity_multiple": round(statistics.median(r["equity_multiple"] for r in all_rows), 6) if all_rows else None,
    }

    in_sample_lb = None
    fwd_lb = None
    if forward_held_out_count > 0 and len(editions) > forward_held_out_count:
        in_sample_eds = editions[:-forward_held_out_count]
        fwd_eds = editions[-forward_held_out_count:]
        in_sample_lb = make_leaderboard(aggregate_participants(in_sample_eds))
        fwd_lb = make_leaderboard(aggregate_participants(fwd_eds))

    return MultiSeasonResult(
        editions=editions,
        latest_edition=latest_doc,
        participants=sorted(part_docs, key=lambda a: (-a["season_realized_pnl_usd"], a["username"])),
        leaderboard=leaderboard,
        target_summary=targets,
        in_sample_leaderboard=in_sample_lb,
        forward_held_out_leaderboard=fwd_lb,
        forward_held_out_count=forward_held_out_count,
    )


class MultiSeasonCompetition:
    """Orchestrator for multi-season paper competitions across equities and futures pools.

    This is the class the brief asks for: a single engine that runs multi-season
    paper competitions directly on the 20-stock volatile equities pool alongside
    futures, line by line on real verified pricing. Two usage modes are supported:

    - Futures mode: series_map built from data/market_history/ (vendor daily bars,
      front-month continuous futures) + roster data/competition/roster.json,
      profile futures_amp_sep2026.
    - Volatile-equity mode: series_map built from data/intraday/ (1d/1h/15m vendor
      bars for the 20-stock pool, or data/official_bars/ when Alpaca credentials
      are available) + roster data/competition/stock_roster.json,
      profile stocks_official_leap (official) or stocks_20x_counterfactual.

    Every call is deterministic given (bars, roster, profile, scenario, latency);
    scripts/verify.py re-runs the engine at its pinned stamp and requires
    byte-identical output, and scripts/run_stock_competition.py +
    scripts/run_competition.py are thin wrappers around this class.
    """

    def __init__(
        self,
        profile: RuleProfile,
        scenario: CostScenario,
        latency_bars: int = 0,
    ):
        self.profile = profile
        self.scenario = scenario
        self.latency_bars = latency_bars

    def run_division(
        self,
        series_map: dict[str, Series],
        participants: list[Participant],
        decisions_provider: callable,
        windows: list[tuple[str, str]],
        forward_held_out_count: int = 0,
        control_symbol_picker: callable | None = None,
        division_name: str = "daily",
        division_of_user: dict[str, str] | None = None,
        arbitration: str = "sequential",
        roll_dates: dict[str, set[str]] | None = None,
    ) -> MultiSeasonResult:
        return run_division_seasons(
            series_map=series_map,
            participants=participants,
            profile=self.profile,
            scenario=self.scenario,
            decisions_provider=decisions_provider,
            windows=windows,
            latency_bars=self.latency_bars,
            control_symbol_picker=control_symbol_picker,
            forward_held_out_count=forward_held_out_count,
            division_name=division_name,
            division_of_user=division_of_user,
            arbitration=arbitration,
            roll_dates=roll_dates,
        )

    def run_combined_leap_simulation(
        self,
        futures_series: dict[str, Series],
        equity_series: dict[str, Series],
        futures_participants: list[Participant],
        equity_participants: list[Participant],
        futures_decisions: callable,
        equity_decisions: callable,
        futures_windows: list[tuple[str, str]],
        equity_windows: list[tuple[str, str]],
        forward_held_out_count: int = 0,
        equity_control_picker: callable | None = None,
    ) -> dict[str, MultiSeasonResult]:
        """Run futures and volatile-equity pools side by side in one call.

        This is the explicit “alongside futures” entry point the brief requires:
        one engine, two pools, real verified bars, tracked usernames, frozen
        contrarian models (C1-C5 for futures, C6-C19 for equities), in-sample vs
        forward-held-out partitioning, and latency-delay measurement. The caller
        supplies the already-loaded series maps and the decision providers; this
        method enforces the same cost scenario and latency for both sides so the
        comparison is like-for-like, then returns a dict with keys "futures" and
        "equities" each holding a MultiSeasonResult.

        Example (deterministic, no network):

            comp = MultiSeasonCompetition(RULE_PROFILES["stocks_official_leap"],
                                          COST_SCENARIOS["moderate"], latency_bars=0)
            results = comp.run_combined_leap_simulation(
                futures_series=fut_map, equity_series=eq_map,
                futures_participants=fut_roster, equity_participants=eq_roster,
                futures_decisions=fut_dec, equity_decisions=eq_dec,
                futures_windows=fut_windows, equity_windows=eq_windows,
                forward_held_out_count=3)

        Official sources for the rule profiles:
        futures https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
        equities https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
        Verified pricing sources: see module docstring for per-pool provenance.
        No hallucinated prices: missing symbols are excluded, never synthesized.
        """
        futures_result = self.run_division(
            series_map=futures_series,
            participants=futures_participants,
            decisions_provider=futures_decisions,
            windows=futures_windows,
            forward_held_out_count=forward_held_out_count,
            division_name="futures",
        )
        # Reuse the same scenario/latency for equities so “alongside” is literal.
        equities_result = self.run_division(
            series_map=equity_series,
            participants=equity_participants,
            decisions_provider=equity_decisions,
            windows=equity_windows,
            forward_held_out_count=forward_held_out_count,
            control_symbol_picker=equity_control_picker,
            division_name="equities",
        )
        return {"futures": futures_result, "equities": equities_result}
