# CME product trading hours and termination — committed extracts

- **Publisher:** CME Group
- **Accessed (UTC):** 2026-09-19 (SI, ETH, BTC hand-read; retained rows) and 2026-09-20 ~05:15 (the 17 remaining products, via the agent page-fetch proxy)
- **Tier:** official_primary (listing exchange contract specifications)
- **Use:** product-specific Globex hours and last-trade rules only. The engine does **not** drop
  sessions from these hours. Dated roll calendars are **not** transcribed here — the dated schedule
  in `data/cme_roll_schedule.json` is *derived* from these termination rules by the codecs in
  `intel/cme_roll.py`, never transcribed from another page.
- **Capture transports (honesty boundary):**
  - SI / ETH / BTC: hand-read from the official contractSpecs pages on 2026-09-19 (retained rows;
    see the audit history in `data/cme_specs_index.json`).
  - The other 17 products: cmegroup.com answers HTTP 403 to the GitHub-hosted capture lane
    (IR-33) and the research sandbox has no direct egress, so each product's page was fetched
    through the agent platform's page-fetch proxy, which renders the official HTML to markdown.
    The exact delivered text of each page's contract-spec table section is stored under
    `data/cme_specs/<PRODUCT>.agentfetch.md` (SHA-256 and byte length recorded per product in
    `data/cme_specs_index.json`, transport `arena-fetch-page`, `body_format: "markdown"`), and the
    transcription is machine-extracted from that stored text by
    `scripts/fetch_cme_specs.extract_spec_fields_markdown` — the same label matching the CI lane
    applies to HTML. `scripts/adopt_cme_specs_fetch.py` performs the adoption;
    `scripts/verify.py` re-extracts from the stored bodies and fails on any divergence.
- **URL:** per product below (one official contractSpecs page per product, also registered in
  `research/sources/sources.json` as `CME-SPEC-<PRODUCT>1!`).

## Bitcoin (BTC) — CME-SPEC-BTC1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs
- **Accessed (UTC):** 2026-09-19 (hand-read; retained row)

> CME Globex: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading (Outright): Trading terminates at 4:00 p.m. London time on the last
> Friday of the contract month. If this is not both a London and U.S. business day, trading
> terminates on the prior London or U.S. business day.

## Micro Bitcoin (MBT) — CME-SPEC-MBT1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/micro-bitcoin/specs
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading: Outright: Trading terminates at 4:00 p.m. London time on the last Friday
> of the contract month. If this is not both a London and U.S. business day, trading terminates on
> the prior London or the U.S. business day.

## Ether (ETH) — CME-SPEC-ETH1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs
- **Accessed (UTC):** 2026-09-19 (hand-read; retained row)

> CME Globex: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading (Outright): Trading terminates at 4:00 p.m. London time on the last
> Friday of the contract month. If this is not both a London and U.S. business day, trading
> terminates on the prior London or U.S. business day.

## Micro Ether (MET) — CME-SPEC-MET1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/ether/micro-ether/specs
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0-1/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading: Outright: Trading terminates at 4:00 p.m. London time on the last Friday
> of the contract month that is either a London or U.S. business day. If the last Friday of the
> contract month day is not a business day in both London and the U.S., trading terminates on the
> prior London or U.S. business day.

## SOL (SOL) — CME-SPEC-SOL1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/solana/solana/specs
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading: Trading terminates at 4:00 p.m. London time on the last Friday of the
> contract month. If this is not both a London and U.S. business day, trading terminates on the
> prior London or U.S. business day.

## Micro SOL (MSL) — CME-SPEC-MSL1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/solana/micro-solana/specs
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0/2)

> Trading Hours: CME Globex: 24/7 with the exception of the maintenance window on Saturday from
> 2:00 a.m. - 4:00 a.m. CT.
>
> Termination of Trading: Trading terminates at 4:00 p.m. London time on the last Friday of the
> contract month. If this is not both a London and U.S. business day, trading terminates on the
> prior London or U.S. business day.

## XRP (XRP) — CME-SPEC-XRP1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/xrp/xrp.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading: Trading terminates at 4:00 p.m. London time on the last Friday of the
> contract month. If this is not both a London and U.S. business day, trading terminates on the
> prior London or U.S. business day.

## Micro XRP (MXP) — CME-SPEC-MXP1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/xrp/micro-xrp/specs
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> Termination of Trading: Trading terminates at 4:00 p.m. London time on the last Friday of the
> contract month. If this is not both a London and U.S. business day, trading terminates on the
> prior London or U.S. business day.

## E-mini Nasdaq-100 (NQ) — CME-SPEC-NQ1!

- **URL:** https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday 6:00 p.m. - Friday - 5:00 p.m. ET (5:00 p.m. - 4:00 p.m. CT)
> with a daily maintenance period from 5:00 p.m. - 6:00 p.m. ET (4:00 p.m. - 5:00 p.m. CT)
>
> Termination of Trading: Trading terminates at 9:30 a.m. ET on the 3rd Friday of the contract
> month.

## Silver (SI) — CME-SPEC-SI1!

- **URL:** https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html
- **Accessed (UTC):** 2026-09-19 (hand-read; retained row)

> CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with a 60-minute
> break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: 12:25 p.m. CT on the third last business day of the contract month

## 100-Ounce Silver (SIC) — CME-SPEC-SIC1!

- **URL:** https://www.cmegroup.com/markets/metals/precious/100-ounce-silver.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0-1/2)

> Trading Hours: CME Globex: 24/7 with the exception of the following maintenance windows:
> Saturday 2:00 a.m. to 4:00 a.m. CT. Monday-Friday 4:00p.m. to 4:02 p.m. CT
>
> Termination of Trading: Trading terminates at 12:25 p.m. CT on the third last business day of
> the month prior to the contract month.

## Micro Silver (SIL) — CME-SPEC-SIL1!

- **URL:** https://www.cmegroup.com/markets/metals/precious/1000-oz-silver.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0-1/2)

> Trading Hours: CME Globex: Sunday 5:00 p.m. - Friday - 4:00 p.m. CT with a 60-minute break each
> day beginning at 4:00 p.m. CT
>
> Termination of Trading: Trading terminates on the third last business day of the contract month.

## Platinum (PL) — CME-SPEC-PL1!

- **URL:** https://www.cmegroup.com/markets/metals/precious/platinum.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunks 0-1/2)

> Trading Hours: CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with
> a 60-minute break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: Trading terminates on the third last business day of the contract month.

## Crude Oil (CL) — CME-SPEC-CL1!

- **URL:** https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday - Friday 5:00 p.m. - 4:00 p.m. CT with a 60-minute break each
> day beginning at 4:00 p.m. CT
>
> Termination of Trading: Trading terminates 3 business day before the 25th calendar day of the
> month prior to the contract month. If the 25th calendar day is not a business day, trading
> terminates 4 business days before the 25th calendar day of the month prior to the contract month.

## Micro WTI Crude Oil (MCL) — CME-SPEC-MCL1!

- **URL:** https://www.cmegroup.com/markets/energy/crude-oil/micro-wti-crude-oil.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday 5:00 p.m. - Friday - 4:00 p.m. CT with a 60-minute break each
> day beginning at 4:00 p.m. CT
>
> Termination of Trading: Trading terminates 1 business day before the corresponding CL contract
> month or 4 business days before the 25th calendar of the month prior to the contract month. If
> the 25th calendar day is not a business day, trading terminates 5 business days before the 25th
> calendar day of the month prior to the contract month. (Two disjuncts with no stated precedence:
> no roll codec is written for MCL.)

## E-mini Crude Oil (QM) — CME-SPEC-QM1!

- **URL:** https://www.cmegroup.com/markets/energy/crude-oil/emini-crude-oil.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with a 60-minute
> break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: Trading terminates 1 business day before the corresponding CL contract
> month or 4 business days before the 25th calendar of the month prior to the contract month. (Same
> two-disjunct sentence as MCL: no roll codec is written for QM.)

## Henry Hub Natural Gas (NG) — CME-SPEC-NG1!

- **URL:** https://www.cmegroup.com/markets/energy/natural-gas/natural-gas.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. /CT)
> with a 60-minute break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: Trading terminates on the 3rd last business day of the month prior to
> the contract month.

## Micro Henry Hub Natural Gas (MNG) — CME-SPEC-MNG1!

- **URL:** https://www.cmegroup.com/markets/energy/natural-gas/micro-henry-hub-natural-gas.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday - Friday 5:00 p.m. - 4:00 p.m. with a 60-minute break each day
> beginning at 4:00 p.m.
>
> Termination of Trading: Trading terminates on the 4th last business day of the month prior to
> the contract month.

## NY Harbor ULSD (HO) — CME-SPEC-HO1!

- **URL:** https://www.cmegroup.com/markets/energy/refined-products/heating-oil.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with
> a 60-minute break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: Trading terminates on the last business day of the month prior to the
> contract month.

## RBOB Gasoline (RB) — CME-SPEC-RB1!

- **URL:** https://www.cmegroup.com/markets/energy/refined-products/rbob-gasoline.contractSpecs.html
- **Accessed (UTC):** 2026-09-20T05:15Z (arena-fetch-page, chunk 1/3)

> Trading Hours: CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with
> a 60-minute break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> Termination of Trading: Trading terminates on the last business day of the month prior to the
> contract month.

## Committed roll schedule

`data/cme_roll_schedule.json` (built by `scripts/build_cme_roll_schedule.py`): 196 termination
dates across the 10 products whose captured daily-bar windows contain them (BTC, ETH, NQ, SI, SIL,
CL, HO, NG, PL, RB). Eight further products have codecs but their vendor daily history is a single
day so far (MBT, MET, MSL, MXP, SOL, XRP, SIC, MNG — recorded with that reason), and MCL/QM carry
no codec at all (ambiguous rule text, recorded). Engine wiring status is recorded in the artifact:
the competition does not yet force-close on these dates; that wiring is a tracked next step.

## No-hallucination check

- Every hours/termination sentence above is copied from the named CME contract-spec page (via the
  transports stated at the top).
- `data/cme_product_hours.json` is machine-generated from the stored bodies; `scripts/verify.py`
  re-extracts every field from the stored bytes and fails the build on any divergence.
- Every roll date is derived by a codec bound to the verbatim termination sentence of its own
  product; `scripts/verify.py` re-runs every codec and re-compares each sentence.
- Known limitations, declared rather than hidden: business days come from the NYSE closure table
  (IR-30); the crypto codecs apply the London-business-day leg as "not a weekend"; NQ's rule names
  the 3rd Friday with no adjustment (2026-06-19 is the Juneteenth closure); MCL/QM have no codec.
