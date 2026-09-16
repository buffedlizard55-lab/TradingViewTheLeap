# CME Group Contract Specifications — Batch 2 (16 contract multipliers)

- **Publisher:** CME Group Inc. (exchange operator; primary source for its own rulebook/spec pages)
- **Tier:** official_primary
- **Accessed (UTC):** 2026-09-16
- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs — first of 16 pages; every other page is listed with its own quote in the per-product sections below
- **Method:** each spec page fetched live via `fetch_page`; the "Contract Unit" row quoted below
  is captured verbatim from the rendered spec table. One page per product. URLs are listed per
  product so each quote can be manually re-verified independently.

Verbatim "Contract Unit" rows, with the rulebook chapter shown on the same page where captured
(chapter shown in parentheses; "chapter not captured" means the unit quote was captured but the
chapter number was not transcribed this session):

## Crypto

**BTC1! — Bitcoin futures** — URL: https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs

> Contract Unit: 5 bitcoin (rule CME 350)

**MBT1! — Micro Bitcoin futures** — URL: https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/micro-bitcoin/specs

> Contract Unit: 0.10 bitcoin (rule chapter not captured)

**ETH1! — Ether futures** — URL: https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs

> Contract Unit: 50 ether (rule CME 349)

**MET1! — Micro Ether futures** — URL: https://www.cmegroup.com/markets/cryptocurrencies/ether/micro-ether/specs

> Contract Unit: 0.1 ether (rule chapter not captured)

## Energy (NYMEX)

**NG1! — Henry Hub Natural Gas** — URL: https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.contractSpecs.html

> Contract Unit: 10,000 mmBtu (rule NYMEX 220)

**MNG1! — Micro Henry Hub Natural Gas** — URL: https://www.cmegroup.com/markets/energy/natural-gas/micro-henry-hub-natural-gas.contractSpecs.html

> Contract Unit: 1,000 mmBtu (rule NYMEX 440)

**CL1! — Crude Oil (Light Sweet, WTI, Cushing delivery)** — URL: https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.contractSpecs.html

> Contract Unit: 1,000 barrels (rule NYMEX 200)

**MCL1! — Micro WTI Crude Oil (financially settled vs. CL)** — URL: https://www.cmegroup.com/markets/energy/crude-oil/micro-wti-crude-oil.contractSpecs.html

> Contract Unit: 100 barrels (rule NYMEX 309)

**QM1! — E-mini Crude Oil** — URL: https://www.cmegroup.com/markets/energy/crude-oil/emini-crude-oil.contractSpecs.html

> Contract Unit: 500 barrels (rule NYMEX 401)

**RB1! — RBOB Gasoline** — URL: https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.contractSpecs.html

> Contract Unit: 42,000 gallons (rule NYMEX 191)

**HO1! — NY Harbor ULSD (Heating Oil)** — URL: https://www.cmegroup.com/markets/energy/refined-products/heating-oil.contractSpecs.html

> Contract Unit: 42,000 gallons (rule NYMEX 150)

## Metals (COMEX / NYMEX)

**SI1! — Silver** — URL: https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html

> Contract Unit: 5,000 troy ounces (rule COMEX 112)

**SIC1! — 100-Ounce Silver (financially settled)** — URL: https://www.cmegroup.com/markets/metals/precious/100-ounce-silver.contractSpecs.html

> Contract Unit: 100 troy ounces (rule COMEX 130; tick 0.01/oz = $1.00)

**SIL1! — Micro Silver (1000-oz)** — URL: https://www.cmegroup.com/markets/metals/precious/1000-oz-silver.contractSpecs.html

> Contract Unit: 1,000 troy ounces (outright tick 0.005/oz = $5.00; deliverable)

**PL1! — Platinum** — URL: https://www.cmegroup.com/markets/metals/precious/platinum.contractSpecs.html

> Contract Unit: 50 troy ounces (tick 0.10 = $5.00; rule chapter not captured)

## Equity index

**NQ1! — E-mini Nasdaq-100** — URL: https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html

> Contract Unit: $20 x Nasdaq-100 Index (rule CME 359; tick 0.25 index points = $5.00; financially settled)

Note: NQ's multiplier is USD per index point ($20 per point), so exposure is denominated in
index points, not shares. The same "$20 x the Nasdaq-100 index" wording appears on CME's margins
page for the product (https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.margins.html).

## Cross-check

All 16 units above are used as `contract_multiplier` in `data/master_list.json`, each sourced to
its own per-page source_id registered in `research/sources/sources.json`
(CME-SPEC-BTC1! … CME-SPEC-NQ1!). `scripts/verify.py` recomputes
`max_underlying_exposure = cap × multiplier` and the required underlying move for the current
rank-1 P/L ($2,303,725.00) and fails on any mismatch.


## Re-verification pass — 2026-09-16 (second pass)

All 18 spec pages in this batch were re-fetched live on 2026-09-16 (~18:00–18:15 UTC); every
contract unit matches the original capture above. Live spot levels at re-fetch (context only,
10-min delayed quotes): BTC 75,370 (BTCU6) / 75,375 (MBTU6); ETH 2,372.00 (ETHU6) / 2,377.00
(METU6); NG 2.888 (NGV6, vol 108,702); MNG 2.885 (MNGV6); CL 102.43 (CLV6, vol 236,128);
MCL 102.43; QM 102.400 (QMV6, vol 5,230); RB 3.4621 (RBV6, vol 36,631); HO 5.2279 (HOV6, vol
27,448); SI 64.840 (SIZ6, vol 31,852); SIC 64.85 (SICZ6); SIL 64.840 (SILZ6, vol 39,564);
PL 1,784.50 (PLV6); NQ 29,431.00 (NQZ6, vol 329,027); MCL 102.43 (vol 174,336).

Three spec pages were captured for the first time on this pass and registered in
research/sources/sources.json:

- CME-SPEC-SOL1! — /markets/cryptocurrencies/solana/solana/specs — Contract Unit "500 SOL, as
  defined by the CME CF Solana-Dollar Reference Rate (SOLUSD_RR)"; rule CME 439; SOLU6 last 96.05,
  volume 1,405.
- CME-SPEC-MSL1! — /markets/cryptocurrencies/solana/micro-solana/specs — Contract Unit "25 SOL,
  as defined by the CME CF Solana-Dollar Reference Rate (SOLUSD_RR)"; rule CME 440; MSLU6 last
  96.10, volume 1,028.
- CME-SPEC-MXP1! — /markets/cryptocurrencies/xrp/micro-xrp/specs — Contract Unit "2,500 XRP, as
  defined by the CME CF XRP-Dollar Reference Rate (XRPUSD_RR)"; rule CME 436; MXPU6 last 1.2520,
  volume 5,280.

Result: all 20 master-list rows now cite a CME contract-spec page verified live on 2026-09-16.
