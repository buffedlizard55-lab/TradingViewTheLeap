"""Pine Script broker-emulator reference implementation (documented semantics only).

Every rule in this module is transcribed from TradingView's own Pine Script documentation
and cited with the exact sentence it came from. Nothing here is invented, and nothing here
is a claim about what any particular strategy report contains.

Sources (both official TradingView documentation, fetched 2026-09-18):

1. Pine Script v6 User Manual, "Concepts / Strategies"
   https://www.tradingview.com/pine-script-docs/concepts/strategies/
   - Broker emulator section: "TradingView uses a broker emulator to simulate trades while
     running a strategy script. Unlike brokers in real-world trading, the broker emulator
     fills a strategy's orders using only the available chart data by default. Consequently,
     it executes orders on historical bars after a bar closes."
   - Intrabar assumption: "If the opening price of a bar is closer to the high than it is to
     the low, the emulator assumes that the market price moved in this order:
     open -> high -> low -> close." and the mirrored sentence for the low case.
   - Price-based orders: "When filling price-based orders (all orders except market orders),
     the emulator assumes that no gaps exist inside each chart bar; it considers any price
     within the bar's range as a valid level for filling pending orders."
   - Gap rule: "If the market price crosses a price-based order's level during the gap
     between one bar's closing time and the next bar's opening time, the emulator assumes
     that intrabar data does not exist within the gap. Rather than filling the order at the
     specified price in that case, the emulator fills the order at the opening price of the
     bar following the gap."
   - Market orders: "A market order is an instruction to buy or sell an instrument as soon as
     possible, irrespective of the price. Therefore, the broker emulator always executes it
     on the next available tick." With the default calculation behavior (once per bar's
     closing tick) the docs state: "the broker emulator fills each new order at the open of
     the following bar."
   - Bar detail: "If a strategy enables high historical detail, the broker emulator retrieves
     open, high, low, and close prices from the bars on a suitable lower timeframe, when
     possible, to increase the number of ticks available for estimating price action and
     filling orders on historical bars." (Premium/Ultimate setting or
     ``use_bar_magnifier=true``.) This module models the DEFAULT behavior: chart bars only.

2. TradingView Support, "How to export strategy data"
   https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/
   - "you can use the export feature to download it as a CSV file ... if you click on the
     'Download' button from the 'List of Trades' tab, you will only export the trade
     information. Exporting strategy data from the 'Performance Summary' tab will only export
     the metrics."

WHAT THIS MODULE IS NOT: it is not TradingView's code, it is not a replication of any specific
Strategy Report, and it cannot validate a strategy's P/L. It answers one narrow question with
documented rules: given a decision on bar i of a committed vendor series, at what price does
the documented broker emulator fill a market order, a limit order and a stop order?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

DEFAULT_BEHAVIOR_STATEMENT = (
    "Default calculation behavior: the script executes once per bar's closing tick, and the "
    "broker emulator fills a market order at the open of the following bar."
)
INTRABAR_RULE_STATEMENT = (
    "Intrabar assumption: open->high->low->close when the open is closer to the high, "
    "open->low->high->close when it is closer to the low; no gaps exist inside a chart bar."
)
GAP_RULE_STATEMENT = (
    "Gap rule: if a price-based order's level is crossed between bars, the emulator fills at "
    "the opening price of the bar following the gap instead of the order's price."
)


@dataclass(frozen=True)
class Fill:
    index: int                 # bar index of the fill
    price: float               # fill price before slippage
    reason: str                # which documented rule produced it

    def with_slippage(self, direction: str, slippage_ticks: float, tick_size: float) -> "Fill":
        """Pine applies slippage adversely, in ticks, to the fill price."""
        if slippage_ticks <= 0 or tick_size <= 0:
            return self
        delta = slippage_ticks * tick_size
        price = self.price + delta if direction == "long" else self.price - delta
        return Fill(self.index, price, f"{self.reason}+slippage({slippage_ticks} ticks)")


def intrabar_path(open_: float, high: float, low: float, close: float) -> tuple[str, ...]:
    """Documented bar path: which of high/low is assumed to come first."""
    if abs(open_ - high) <= abs(open_ - low):
        return ("open", "high", "low", "close")
    return ("open", "low", "high", "close")


def fill_market_order(bars: Sequence, decision_index: int,
                      direction: str = "long") -> Optional[Fill]:
    """Market order created on bar `decision_index`: fills at the next bar's open.

    Returns None when there is no following bar (the order cannot fill inside the data).
    """
    if decision_index + 1 >= len(bars):
        return None
    nxt = bars[decision_index + 1]
    return Fill(index=decision_index + 1, price=float(nxt.open),
                reason="market-order-next-open (documented default behavior)")


def fill_limit_order(bars: Sequence, decision_index: int, level: float,
                     direction: str = "long") -> Optional[Fill]:
    """Long limit at `level` (buy) / short limit (sell), created on `decision_index`.

    Documented behavior: the emulator considers any price inside a bar's range a valid fill
    level (no intrabar gaps); a limit at a worse price than the market fills on the next
    available tick, i.e. at the next bar's open; if the level is crossed in the gap between
    bars, the fill is at the opening price of the following bar.
    """
    for i in range(decision_index + 1, len(bars)):
        bar = bars[i]
        # A limit only fills when the market reaches its level. If the level is crossed during
        # the gap between bars (the bar OPENS beyond the level, in the direction that crosses
        # it: at or below a long limit, at or above a short limit) the documented gap rule fills
        # the order at the opening price of the bar after the gap instead of at the level.
        if direction == "long":
            if bar.open <= level:
                return Fill(index=i, price=float(bar.open),
                            reason="limit-crossed-in-gap -> next bar open (documented gap rule)")
            if bar.low <= level:
                return Fill(index=i, price=float(level),
                            reason="limit-inside-bar-range (documented no-intrabar-gap rule)")
        else:
            if bar.open >= level:
                return Fill(index=i, price=float(bar.open),
                            reason="limit-crossed-in-gap -> next bar open (documented gap rule)")
            if bar.high >= level:
                return Fill(index=i, price=float(level),
                            reason="limit-inside-bar-range (documented no-intrabar-gap rule)")
    return None


def fill_stop_order(bars: Sequence, decision_index: int, level: float,
                    direction: str = "long") -> Optional[Fill]:
    """Stop order (buy stop above the market / sell stop below), created on `decision_index`."""
    for i in range(decision_index + 1, len(bars)):
        bar = bars[i]
        triggered = (bar.high >= level) if direction == "long" else (bar.low <= level)
        if not triggered:
            continue
        gap_through = (bar.open >= level) if direction == "long" else (bar.open <= level)
        if gap_through:
            return Fill(index=i, price=float(bar.open),
                        reason="stop-gapped-through -> bar open (documented gap rule)")
        return Fill(index=i, price=float(level),
                    reason="stop-inside-bar-range (documented no-intrabar-gap rule)")
    return None


def commission_for_fill(price: float, qty: float, model: str, value: float) -> float:
    """Pine's three declared commission models, applied per order.

    model:
      "percent"  - value is a percentage of the trade value (price x qty)
      "cash_per_order" - value is a flat cash amount per order
      "cash_per_contract" (or "per_contract") - value is cash per contract/unit
    """
    if model in ("percent", "percent_of_value"):
        return price * qty * value / 100.0
    if model == "cash_per_order":
        return value
    if model in ("cash_per_contract", "per_contract"):
        return value * qty
    raise ValueError(f"unknown commission model {model!r}")


def slippage_bps_for_fill(price: float, qty: float, model: str, value: float) -> Optional[float]:
    """Convenience: express a slippage value as basis points of the trade value.

    Returns None for tick-denominated slippage, which requires a tick size and is therefore
    applied through Fill.with_slippage instead.
    """
    if model in ("percent", "percent_of_value"):
        return value * 100.0
    if model in ("cash_per_order", "cash_per_contract", "per_contract", "ticks"):
        return None
    raise ValueError(f"unknown slippage model {model!r}")
