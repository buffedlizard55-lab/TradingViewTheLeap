# CME product trading hours and termination — committed extracts

- **Publisher:** CME Group
- **Accessed (UTC):** 2026-09-19
- **Tier:** official_primary (listing exchange contract specifications)
- **Use:** product-specific Globex hours and last-trade rules only. The engine does **not** drop
  sessions from these hours. Dated 2016–2025 roll calendars are **not** transcribed (`roll_dates`
  is empty). Platinum (PL) hours were not recovered (contractSpecs chunk 1 was footer-only).
- **Honesty:** hours below are copied from official contract-spec pages. Energy (CL/NG/HO/RB) and
  E-mini Nasdaq-100 (NQ) hours live on later page chunks that this pass does not re-fetch; they
  are omitted rather than guessed.

## Silver (SI) — CME-SPEC-SI1!

- **URL:** https://www.cmegroup.com/markets/metals/precious/silver.contractSpecs.html
- **Accessed (UTC):** 2026-09-19 (contractSpecs chunk 0)

> CME Globex: Sunday - Friday 6:00 p.m. - 5:00 p.m. (5:00 p.m. - 4:00 p.m. CT) with a 60-minute
> break each day beginning at 5:00 p.m. (4:00 p.m. CT)
>
> TAS: Sunday - Friday 6:00 p.m. - 1:25 p.m. (5:00 p.m. - 12:25 p.m. CT)
>
> CME ClearPort: Sunday 5:00 p.m. - Friday 4:00 p.m. CT with no reporting Monday - Thursday
> from 4:00 p.m. - 5:00 p.m. CT
>
> Termination of Trading: 12:25 p.m. CT on the third last business day of the contract month

## Ether (ETH) — CME-SPEC-ETH1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs
- **Accessed (UTC):** 2026-09-19 (specs chunk 1)

> CME Globex: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> TAS: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday from 3:00 p.m. to 3:05 p.m. CT
>
> Termination of Trading (Outright): Trading terminates at 4:00 p.m. London time on the last
> Friday of the contract month. If this is not both a London and U.S. business day, trading
> terminates on the prior London or U.S. business day.
>
> TAS terminates at 3:00 p.m. CT on the U.S. business day immediately preceding the last trade
> date for such futures contract.

## Bitcoin (BTC) — CME-SPEC-BTC1!

- **URL:** https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin/specs
- **Accessed (UTC):** 2026-09-19 (specs chunk 0)

> CME Globex: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday 4:00 p.m. to 4:02 p.m. CT
>
> TAS: 24/7 with the exception of the following maintenance windows: Saturday 2:00 a.m. to
> 4:00 a.m. CT & Monday-Friday from 3:00 p.m. to 3:05 p.m. CT
>
> Termination of Trading (Outright): Trading terminates at 4:00 p.m. London time on the last
> Friday of the contract month. If this is not both a London and U.S. business day, trading
> terminates on the prior London or U.S. business day.
>
> TAS: Trading terminates at 3:00 p.m. CT on the U.S. business day immediately preceding the last
> trade date for such futures contract.

## Not transcribed this pass

- CL, NG, HO, RB, NQ: hours sit on later contractSpecs chunks; not re-fetched; not guessed.
- PL: contractSpecs chunk 1 was footer-only; hours not recovered.
- Dated roll schedule 2016–2025: no official product-by-product roll calendar was captured.

## No-hallucination check

- Every hours/termination sentence above is copied from the named CME contract-spec page.
- `data/cme_product_hours.json` stores the same rules as structured fields plus empty `roll_dates`.
