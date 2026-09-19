# NYSE full-closure table 2016-2026 (rule-based transcription)

- **URL:** https://www.nyse.com/markets/hours-calendars — the authoritative NYSE trading calendar this transcription must be re-verified against (cross-check: https://www.nasdaqtrader.com/Trader.aspx?id=calendar).
- **Accessed (UTC):** 2026-09-19 (transcription written; live page NOT fetched — this sandbox has no network egress, so no verbatim NYSE page text is quoted below)
- **Tier:** official_secondary — NYSE is the listing exchange and its calendar is an official exchange publication; the transcription itself is unverified until the protocol at the bottom is completed.

Source module: `intel/calendar.py` (`nyse-holidays-1`). This file was generated from the module
(see the generator in git history) so the date list below cannot drift from the code by hand-editing.

The two verbatim quotes this evidence file offers are from the transcription module itself, not
from the live NYSE page (which was unreachable from this sandbox). They are quoted so the caveat
is auditable word for word:

> "Not a substitute for the official calendar. The authoritative sources are the NYSE trading
> calendar (https://www.nyse.com/markets/hours-calendars) and the Nasdaq Trader holiday schedule
> (https://www.nasdaqtrader.com/Trader.aspx?id=calendar). Every date produced here must be
> re-verified line by line against those pages on a networked machine before it is treated as
> authoritative; that re-verification is tracked as an irregularity in research/irregularities.json
> until it is done." — intel/calendar.py module docstring, WHAT THIS IS NOT section

> "No network access, no fitting, no guessing: special closures outside the table below are not
> inferred, and years outside 2016-2026 raise rather than silently extrapolating the
> special-closure history." — intel/calendar.py module docstring

Official sources (authoritative; re-verify every date here against them on a networked machine):

- https://www.nyse.com/markets/hours-calendars
- https://www.nasdaqtrader.com/Trader.aspx?id=calendar
- CME Globex (futures differ; NOT encoded here): https://www.cmegroup.com/trading_hours.html

Method: the nine standing NYSE holidays plus weekend observance (Saturday -> preceding Friday,
Sunday -> following Monday) for New Year's Day, Juneteenth (observed from 2022), Independence Day
and Christmas Day; Good Friday via the Gregorian Easter algorithm; plus two individually recorded
special full-day closures (2018-12-05 Bush mourning, 2025-01-09 Carter mourning). Every closure
falls on a weekday. Early closes are informational only and never exclude a session.

## 2016 (9 full closures)

- 2016-01-01 — New Year's Day
- 2016-01-18 — Martin Luther King Jr. Day
- 2016-02-15 — Presidents' Day
- 2016-03-25 — Good Friday
- 2016-05-30 — Memorial Day
- 2016-07-04 — Independence Day
- 2016-09-05 — Labor Day
- 2016-11-24 — Thanksgiving Day
- 2016-12-26 — Christmas Day (observed)

Early closes (informational): 2016-11-25 (Day after Thanksgiving (early close))

## 2017 (9 full closures)

- 2017-01-02 — New Year's Day (observed)
- 2017-01-16 — Martin Luther King Jr. Day
- 2017-02-20 — Presidents' Day
- 2017-04-14 — Good Friday
- 2017-05-29 — Memorial Day
- 2017-07-04 — Independence Day
- 2017-09-04 — Labor Day
- 2017-11-23 — Thanksgiving Day
- 2017-12-25 — Christmas Day

Early closes (informational): 2017-07-03 (July 3 (early close)), 2017-11-24 (Day after Thanksgiving (early close))

## 2018 (10 full closures)

- 2018-01-01 — New Year's Day
- 2018-01-15 — Martin Luther King Jr. Day
- 2018-02-19 — Presidents' Day
- 2018-03-30 — Good Friday
- 2018-05-28 — Memorial Day
- 2018-07-04 — Independence Day
- 2018-09-03 — Labor Day
- 2018-11-22 — Thanksgiving Day
- 2018-12-05 — National Day of Mourning for President George H.W. Bush
- 2018-12-25 — Christmas Day

Early closes (informational): 2018-07-03 (July 3 (early close)), 2018-11-23 (Day after Thanksgiving (early close)), 2018-12-24 (Christmas Eve (early close))

## 2019 (9 full closures)

- 2019-01-01 — New Year's Day
- 2019-01-21 — Martin Luther King Jr. Day
- 2019-02-18 — Presidents' Day
- 2019-04-19 — Good Friday
- 2019-05-27 — Memorial Day
- 2019-07-04 — Independence Day
- 2019-09-02 — Labor Day
- 2019-11-28 — Thanksgiving Day
- 2019-12-25 — Christmas Day

Early closes (informational): 2019-07-03 (July 3 (early close)), 2019-11-29 (Day after Thanksgiving (early close)), 2019-12-24 (Christmas Eve (early close))

## 2020 (9 full closures)

- 2020-01-01 — New Year's Day
- 2020-01-20 — Martin Luther King Jr. Day
- 2020-02-17 — Presidents' Day
- 2020-04-10 — Good Friday
- 2020-05-25 — Memorial Day
- 2020-07-03 — Independence Day (observed)
- 2020-09-07 — Labor Day
- 2020-11-26 — Thanksgiving Day
- 2020-12-25 — Christmas Day

Early closes (informational): 2020-11-27 (Day after Thanksgiving (early close)), 2020-12-24 (Christmas Eve (early close))

## 2021 (9 full closures)

- 2021-01-01 — New Year's Day
- 2021-01-18 — Martin Luther King Jr. Day
- 2021-02-15 — Presidents' Day
- 2021-04-02 — Good Friday
- 2021-05-31 — Memorial Day
- 2021-07-05 — Independence Day (observed)
- 2021-09-06 — Labor Day
- 2021-11-25 — Thanksgiving Day
- 2021-12-24 — Christmas Day (observed)

Early closes (informational): 2021-11-26 (Day after Thanksgiving (early close))

## 2022 (10 full closures)

- 2021-12-31 — New Year's Day (observed)
- 2022-01-17 — Martin Luther King Jr. Day
- 2022-02-21 — Presidents' Day
- 2022-04-15 — Good Friday
- 2022-05-30 — Memorial Day
- 2022-06-20 — Juneteenth National Independence Day (observed)
- 2022-07-04 — Independence Day
- 2022-09-05 — Labor Day
- 2022-11-24 — Thanksgiving Day
- 2022-12-26 — Christmas Day (observed)

Early closes (informational): 2022-11-25 (Day after Thanksgiving (early close))

## 2023 (10 full closures)

- 2023-01-02 — New Year's Day (observed)
- 2023-01-16 — Martin Luther King Jr. Day
- 2023-02-20 — Presidents' Day
- 2023-04-07 — Good Friday
- 2023-05-29 — Memorial Day
- 2023-06-19 — Juneteenth National Independence Day
- 2023-07-04 — Independence Day
- 2023-09-04 — Labor Day
- 2023-11-23 — Thanksgiving Day
- 2023-12-25 — Christmas Day

Early closes (informational): 2023-07-03 (July 3 (early close)), 2023-11-24 (Day after Thanksgiving (early close))

## 2024 (10 full closures)

- 2024-01-01 — New Year's Day
- 2024-01-15 — Martin Luther King Jr. Day
- 2024-02-19 — Presidents' Day
- 2024-03-29 — Good Friday
- 2024-05-27 — Memorial Day
- 2024-06-19 — Juneteenth National Independence Day
- 2024-07-04 — Independence Day
- 2024-09-02 — Labor Day
- 2024-11-28 — Thanksgiving Day
- 2024-12-25 — Christmas Day

Early closes (informational): 2024-07-03 (July 3 (early close)), 2024-11-29 (Day after Thanksgiving (early close)), 2024-12-24 (Christmas Eve (early close))

## 2025 (11 full closures)

- 2025-01-01 — New Year's Day
- 2025-01-09 — National Day of Mourning for President Jimmy Carter
- 2025-01-20 — Martin Luther King Jr. Day
- 2025-02-17 — Presidents' Day
- 2025-04-18 — Good Friday
- 2025-05-26 — Memorial Day
- 2025-06-19 — Juneteenth National Independence Day
- 2025-07-04 — Independence Day
- 2025-09-01 — Labor Day
- 2025-11-27 — Thanksgiving Day
- 2025-12-25 — Christmas Day

Early closes (informational): 2025-07-03 (July 3 (early close)), 2025-11-28 (Day after Thanksgiving (early close)), 2025-12-24 (Christmas Eve (early close))

## 2026 (10 full closures)

- 2026-01-01 — New Year's Day
- 2026-01-19 — Martin Luther King Jr. Day
- 2026-02-16 — Presidents' Day
- 2026-04-03 — Good Friday
- 2026-05-25 — Memorial Day
- 2026-06-19 — Juneteenth National Independence Day
- 2026-07-03 — Independence Day (observed)
- 2026-09-07 — Labor Day
- 2026-11-26 — Thanksgiving Day
- 2026-12-25 — Christmas Day

Early closes (informational): 2026-11-27 (Day after Thanksgiving (early close)), 2026-12-24 (Christmas Eve (early close))

## Re-verification protocol (for a networked reviewer)

1. Open https://www.nyse.com/markets/hours-calendars and cross-check each year above line by line,
   including the two special closures and the Juneteenth start year (2022).
2. Cross-check against https://www.nasdaqtrader.com/Trader.aspx?id=calendar.
3. On any mismatch, fix `intel/calendar.py`, re-generate this file, re-derive the study
   (`python3 scripts/run_intraday_study.py`), rebuild the site and re-run `python3 scripts/verify.py`.
4. Until step 1 is done, the transcription caveat stays open in research/irregularities.json (IR-28).
