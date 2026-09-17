"""Intelligence layer for The Leap research lab.

Pure-stdlib, deterministic, offline. Every module here operates exclusively on the
committed raw vendor captures under ``data/market_history/``; nothing in this
package performs network access.

Numerical conventions replicate Pine Script v6 built-ins as documented in the
official Pine reference (https://www.tradingview.com/pine-script-reference/v6/):

- ``ta.ema``    seeded with the SMA of the first ``length`` values, then recursive;
- ``ta.atr``    RMA of true range, RMA seeded with the SMA of the first ``length``;
- ``ta.stdev``  biased (population) standard deviation;
- ``ta.highest``/``ta.lowest`` rolling max/min inclusive of the current bar.

Results produced from this package are independent daily-bar simulations. They are
NOT TradingView Strategy Report results, NOT Paper Trading account results, and
NOT predictions.
"""

__all__ = ["data", "indicators", "strategy", "backtest", "walkforward"]
