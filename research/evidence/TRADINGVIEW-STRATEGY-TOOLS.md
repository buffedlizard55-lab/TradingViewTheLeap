# Evidence: official TradingView strategy and Paper Trading tools

- **Publisher:** TradingView, Inc.
- **URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/
- **Accessed (UTC):** 2026-09-16
- **Tier:** official_primary

Additional official pages used here:

- https://www.tradingview.com/support/solutions/43000481026-how-to-autotrade-using-pine-script-strategies/
- https://www.tradingview.com/support/solutions/43000717375-how-to-simulate-trading-with-leverage-in-pine-script/
- https://www.tradingview.com/support/solutions/43000719857-how-is-position-profit-and-loss-in-paper-trading-calculated/

## Strategy Report and broker emulator

> Pine Script® strategies are specialized scripts that simulate trades across historical and realtime bars, allowing users to backtest and forward test their trading systems.
> The strategy report visualizes the hypothetical trading performance of a simulated strategy.
> The additional items ... provide quick options where users can customize the testing period and enable Deep Backtesting mode ... [and] control the level of historical bar detail.

## No direct TradingView autotrading

> Strategy trading is limited to the backtesting mode only. Automated strategy trading with a brokerage account is not available on TradingView yet.
> Pine Script does not support placing orders using the brokers integrated via the Trading Panel, or using TradingView's built-in paper trading account.

## Leverage simulation

> All strategy scripts written in Pine Script® v4 and above natively support the simulation of leverage trading.
> Setting the "Margin for long positions" to 5% specifies that the account balance must be at least 5% of the position's value to simulate receiving the other 95% from the broker.
> The formula for MarginRequired is LastPrice × PointValue × AbsPositionSize × (MarginPercent / 100).

## Paper Trading P/L mechanics

> In most cases, buy orders are executed at the ask price, and sell orders at the bid price.
> The formula for long futures positions: (Bid Price − Average Fill Price) × Quantity × Point Value.
> Your profit and loss is calculated in the symbol's currency and then converted to USD, as the dollar is the default currency for Paper Trading.

The source page's displayed short-futures formula omits `Point Value`, while its immediately
following worked example multiplies by point value. This internal documentation inconsistency is
recorded as IR-14 and is not silently resolved here.
