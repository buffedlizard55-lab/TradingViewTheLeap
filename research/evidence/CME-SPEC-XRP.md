# CME Group Contract Specifications — XRP Futures (IR-10 closure)

- **Publisher:** CME Group Inc. (exchange operator; primary source for its own rulebook/spec pages)
- **Tier:** official_primary
- **Accessed (UTC):** 2026-09-16
- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/xrp/xrp.contractSpecs.html
- **Method:** spec page fetched live via `fetch_page`. The "Contract Unit" row is captured verbatim
  below. This page also proves the product is listed and trading, which closes IR-10 (the April
  2025 press release had announced the launch as "pending regulatory review").

## Verbatim spec rows

> Contract Unit: 50,000 XRP, as defined by the CME CF XRP-Dollar Reference Rate (XRPUSD_RR)

> Price Quotation: U.S. dollars and cents per XRP

> Minimum Price Fluctuation: Outright: $0.0005 per XRP = $25.00 per contract

> Exchange Rulebook: CME 435

> Settlement Method: Financially Settled

> Listed Contracts: Monthly contracts listed for 6 consecutive months, quarterly contracts (Mar, Jun, Sep, Dec) listed for 4 additional quarters and a second Dec contract if only one is listed.

## Live-trading proof on the same page (closes IR-10)

The product header on the spec page shows an active front-month contract:

> Globex Code: XRPU6 — Last 1.2985 — Change +0.0010 (+0.08%) — Volume 174
> "Last Updated 15 Sep 2026 09:47:00 PM CT. Market data is delayed by at least 10 minutes"

## Use

- Confirms `contract_multiplier` for `CME:XRP1!` = 50,000 XRP from the CME spec page itself
  (independent of, and consistent with, the April 2025 press release in CME-XRP-PR).
- Resolves IR-10: the product is no longer "pending regulatory review"; it is listed and trading.
