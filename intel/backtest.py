"""Window portfolio simulation under contest constraints.

Simulates ONE (symbol, model, parameters, cost scenario, sizing basis) combination
over ONE date window on an account that starts at the contest balance.

Contest constraints replicated from the official rules (data/contest_config.json):
- starting equity 250,000 virtual USD; futures buying power 20:1;
- whole contracts only; per-symbol maximum open position (rules cap);
- every position is closed by the end of the window (realized-P/L ranking).

Order semantics replicate the Pine source's broker-emulator defaults:
- signals are evaluated on a bar's close and queue a market order;
- market orders fill at the NEXT bar's open; an opposite-direction
  ``strategy.entry`` reverses the position in one fill at that open
  (``pyramiding = 0``: same-direction signals are ignored);
- a signal on the final bar of a window cannot fill (no next bar);
- a position still open at the end of the window is closed at the final bar's
  close (analog of the end-of-competition auto-close).

Explicit modelling assumptions (declared, NOT rulebook facts):
- position size at entry = min(rules cap, floor(sizing equity * 20 / notional at
  the fill price)), sizing equity being the running equity (``compounding``) or
  the fixed starting balance (``initial_fixed``);
- no margin-call liquidation is simulated; bars whose open position's initial
  margin (notional / 20) exceeds mark-to-market equity are counted as
  ``margin_breach_bars`` instead;
- slippage is modelled as a declared fraction of the signal bar's ATR(14),
  applied adversely on BOTH legs; commission is per contract per side;
- if equity <= 0 while flat the window stops trading (ruin). The rules forbid
  resetting the competition account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .data import Bar
from .strategy import Signal

START_BALANCE = 250_000.0
LEVERAGE = 20.0
TARGET_MULTIPLES = (5.0, 10.0, 20.0, 50.0, 100.0)


@dataclass(frozen=True)
class CostScenario:
    key: str
    label: str
    commission_per_contract_per_side_usd: float
    slippage_atr_fraction: float  # adverse price points = fraction * ATR(14) at signal bar


COST_SCENARIOS = {
    "zero": CostScenario("zero", "no commission, no slippage", 0.0, 0.0),
    "moderate": CostScenario(
        "moderate", "commission $1.50/contract/side + slippage 5% of ATR(14) per leg", 1.50, 0.05
    ),
    "high": CostScenario(
        "high", "commission $2.50/contract/side + slippage 10% of ATR(14) per leg", 2.50, 0.10
    ),
}


@dataclass
class Trade:
    direction: str
    contracts: int
    entry_date: str
    exit_date: str
    entry_fill_price: float
    exit_fill_price: float
    raw_pnl_usd: float
    slippage_usd: float
    commission_usd: float
    net_pnl_usd: float


@dataclass
class WindowResult:
    symbol: str
    model: str
    scenario: str
    sizing: str
    params_label: str
    start_date: str
    end_date: str
    bars: int
    trades: list = field(default_factory=list)
    net_profit_usd: float = 0.0
    equity_multiple: float = 1.0
    profitable_trades: int = 0
    gross_profit_usd: float = 0.0
    gross_loss_usd: float = 0.0
    profit_factor: Optional[float] = None
    max_drawdown_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    skipped_entries: int = 0
    margin_breach_bars: int = 0
    ruined: bool = False
    hit_target_usd: bool = False
    multiple_buckets: list = field(default_factory=list)


def _sizing_qty(sizing: str, equity: float, fill_price: float, multiplier: float, cap: int) -> int:
    notional = fill_price * multiplier
    sizing_equity = equity if sizing == "compounding" else START_BALANCE
    if notional <= 0:
        return 0
    return min(cap, int(sizing_equity * LEVERAGE // notional))


def simulate_window(
    bars: list[Bar],
    signals: list[Signal],
    *,
    symbol: str,
    model: str,
    scenario: CostScenario,
    sizing: str,
    params_label: str,
    contract_multiplier: float,
    rules_cap_contracts: int,
    start_date: str,
    end_date: str,
    target_usd: float,
    final_atr: float,
) -> WindowResult:
    lo = next((i for i, b in enumerate(bars) if b.date >= start_date), None)
    hi = max((i for i, b in enumerate(bars) if b.date <= end_date), default=None)
    if lo is None or hi is None or hi <= lo:
        raise ValueError("empty window")

    result = WindowResult(
        symbol=symbol,
        model=model,
        scenario=scenario.key,
        sizing=sizing,
        params_label=params_label,
        start_date=bars[lo].date,
        end_date=bars[hi].date,
        bars=hi - lo + 1,
    )

    equity = START_BALANCE
    position: Optional[dict] = None
    pending: Optional[Signal] = None
    sig_ptr = 0
    peak = equity

    def sign(direction: str) -> int:
        return 1 if direction == "long" else -1

    def execute_exit(pos: dict, exit_index: int, exit_raw: float, exit_slip_pts: float) -> None:
        nonlocal equity, position
        qty = pos["contracts"]
        d = sign(pos["direction"])
        raw = d * (exit_raw - pos["entry_raw"]) * contract_multiplier * qty
        slip = -(pos["entry_slip_pts"] + exit_slip_pts) * contract_multiplier * qty
        comm = scenario.commission_per_contract_per_side_usd * qty
        comm_total = pos["entry_commission"] + comm
        net = raw + slip - comm_total
        equity += net
        result.trades.append(
            Trade(
                direction=pos["direction"],
                contracts=qty,
                entry_date=bars[pos["entry_i"]].date,
                exit_date=bars[exit_index].date,
                entry_fill_price=pos["entry_raw"] + d * pos["entry_slip_pts"],
                exit_fill_price=exit_raw - d * exit_slip_pts,
                raw_pnl_usd=raw,
                slippage_usd=slip,
                commission_usd=comm_total,
                net_pnl_usd=net,
            )
        )
        if pos["direction"] == "long":
            result.long_trades += 1
        else:
            result.short_trades += 1
        position = None

    for i in range(lo, hi + 1):
        bar = bars[i]

        # ---- fills at this bar's open for orders queued on the prior close ----
        if pending is not None:
            d = sign(pending.direction)
            slip_pts = scenario.slippage_atr_fraction * pending.atr
            if position is not None and position["direction"] != pending.direction:
                # Single-fill reversal at the open, like strategy.entry.
                execute_exit(position, i, bar.open, slip_pts)
            if position is None and equity > 0:
                qty = _sizing_qty(sizing, equity, bar.open, contract_multiplier, rules_cap_contracts)
                if qty < 1:
                    result.skipped_entries += 1
                else:
                    commission = scenario.commission_per_contract_per_side_usd * qty
                    position = {
                        "direction": pending.direction,
                        "contracts": qty,
                        "entry_raw": bar.open,
                        "entry_i": i,
                        "entry_slip_pts": slip_pts,
                        "entry_commission": commission,
                    }
            # same-direction signal while already positioned: ignored (pyramiding 0)
        pending = None

        # ---- evaluate this bar's close ----
        while sig_ptr < len(signals) and signals[sig_ptr].index < i:
            sig_ptr += 1  # drop stale/pre-window signals
        if sig_ptr < len(signals) and signals[sig_ptr].index == i:
            sig = signals[sig_ptr]
            sig_ptr += 1
            if position is None or position["direction"] != sig.direction:
                pending = sig

        # ---- mark-to-market diagnostics ----
        if position is not None:
            d = sign(position["direction"])
            open_pnl = d * (bar.close - position["entry_raw"]) * contract_multiplier * position["contracts"]
            mtm = equity + open_pnl
            required_margin = (
                position["contracts"] * position["entry_raw"] * contract_multiplier / LEVERAGE
            )
            if mtm < required_margin:
                result.margin_breach_bars += 1
        else:
            mtm = equity
            if equity <= 0:
                result.ruined = True
        peak = max(peak, mtm)
        dd = peak - mtm
        if dd > result.max_drawdown_usd:
            result.max_drawdown_usd = dd
            result.max_drawdown_pct = dd / peak if peak > 0 else float("inf")

    # ---- end of window: auto-close any open position at the final close ----
    if position is not None:
        execute_exit(
            position,
            hi,
            bars[hi].close,
            scenario.slippage_atr_fraction * final_atr,
        )

    # ---- aggregates ----
    result.net_profit_usd = equity - START_BALANCE
    result.equity_multiple = 1.0 + result.net_profit_usd / START_BALANCE
    for t in result.trades:
        if t.net_pnl_usd > 0:
            result.profitable_trades += 1
            result.gross_profit_usd += t.net_pnl_usd
        else:
            result.gross_loss_usd += abs(t.net_pnl_usd)
    result.profit_factor = (
        round(result.gross_profit_usd / result.gross_loss_usd, 4)
        if result.gross_loss_usd > 0
        else None
    )
    result.hit_target_usd = result.net_profit_usd >= target_usd
    result.multiple_buckets = [m for m in TARGET_MULTIPLES if result.equity_multiple >= m]
    return result
