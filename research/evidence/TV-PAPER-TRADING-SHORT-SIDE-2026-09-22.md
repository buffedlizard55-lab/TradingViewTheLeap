# Short-side eligibility re-read — Magnificent Seven rules + official Paper Trading docs

- **URL:** https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
  (second page read for this note: https://www.tradingview.com/support/solutions/43000516466-paper-trading-main-functionality/)
- **Publisher:** TradingView, Inc.
- **Accessed (UTC):** 2026-09-22 ~23:00, twenty-second-pass research session (all four rules
  chunks and the Paper Trading help page fetched and read line by line)
- **Tier:** official_primary (TradingView, Inc.)
- **Use:** next-session suggestion #5 — a full re-read of the official stocks-edition rules for
  short-selling eligibility, plus the official Paper Trading order-side documentation, so the
  short-side strategy families (C18, C31, C33, C34 and the futures F2) rest on documented
  evidence rather than an assumption
- **Status:** official primary capture; completes the re-read requested in
  research/NEXT-SESSION.md §2 item 5

## Verbatim quotations (line-by-line verified against the page text)

Magnificent Seven official rules — the instrument, size, leverage and commission clauses
(the complete set of trading-mechanics constraints in the document):

> Only the following instruments are available for trading within the Competition:
>
> - NASDAQ:NVDA
> - NASDAQ:AAPL
> - NASDAQ:MSFT
> - NASDAQ:GOOGL
> - NASDAQ:AMZN
> - NASDAQ:META
> - NASDAQ:TSLA

> The maximum size of an open position per instrument is limited to 50.0 units. One unit
> represents one share of the underlying instrument.

> The preset balance size for the Paper Trading Competition Account is 100,000 virtual USD.
> Leverage for stocks: 1:1. The commission is 0.01%.

> Only simulated trading is allowed in the Competition. **No real money or cryptocurrency will
> be used for trading during the Competition.**

Official Paper Trading help page — order sides documented by TradingView itself:

> Order ticket: A dedicated trading panel where you can enter detailed order parameters, such
> as side (buy/sell), quantity, order type (market, limit, stop), price levels, and risk
> management settings (stop loss and take profit).

> Paper Trading, also known as demo trading, is a tool that lets you practice buying and
> selling assets using simulated money.

## Line-by-line findings

1. **All four chunks of the Magnificent Seven rules were re-read end to end (§01–§19).** The
   words "short", "sell", "borrow" and "locate" do not appear anywhere in the rules text.
   The rules restrict instruments, size (50 units), leverage (1:1), commission (0.01%),
   activity days (3), the rate limit (60/min) and ranking (realized P/L on closed positions) —
   and nothing else about position direction. **Short positions are neither permitted
   explicitly nor forbidden.**
2. **TradingView's own Paper Trading documentation confirms the engine exposes a sell side**
   ("side (buy/sell)") and describes paper trading as "buying and selling assets using
   simulated money". A sell order is therefore an order type the simulator supports; the
   documentation does not, however, spell out competition-specific short-sale mechanics
   (borrow, locate, uptick) for the seven pool names.
3. **Standing conclusion (unchanged, now re-verified):** shorting is *unverified rather than
   forbidden* for the stocks division. The short-side families (C18, C31, C33, C34) remain
   research-only under this caveat; the long families carry the executable thesis if a real
   stocks edition forbids or constrains short opens. The futures division's short side has no
   such ambiguity in the official futures rules text (futures contracts are two-sided
   instruments and §08 states no direction restriction either).
4. **No borrow-cost data exists in any verified free official source consulted**, so no
   borrow-cost scenario can be honestly parameterised for the stocks division today. The
   Paper Trading engine's commission for this pool is the documented 0.01% only.

## Irregularities

- No new irregularity. This file supersedes the standing caveat's "unread" status in
  `research/evidence/TV-RULES-MAG7-MAR2026.md` finding 4 with a completed line-by-line
  re-read; the caveat itself (mechanics unverified) remains in force.
