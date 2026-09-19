# NYSE full-closure table 2016-2026 (verified line by line against official NYSE publications)

- **URL:** https://www.nyse.com/markets/hours-calendars — the authoritative NYSE trading calendar (cross-check: https://www.nasdaqtrader.com/Trader.aspx?id=calendar).
- **Accessed (UTC):** 2026-09-19 — live NYSE page (2026-2028 table) and Nasdaq Trader 2026 schedule fetched; earlier years read from Internet Archive captures of the same nyse.com page (URLs below); special closures from ICE/NYSE press releases.
- **Tier:** official_secondary — NYSE is the listing exchange; each date below was compared against the official table for its year. `intel/calendar.py` (`nyse-holidays-2`) carries the transcription in `OFFICIAL_FULL_CLOSURES` / `OFFICIAL_EARLY_CLOSES`, and `verify_against_official()` (run by `scripts/verify.py` and the unit tests) proves the rule engine reproduces it exactly.

## Official source for each year (verbatim table rows quoted)

| Years | Official page | Verbatim excerpt |
|---|---|---|
| 2016-2017 | https://web.archive.org/web/20160605000702/https://www.nyse.com/markets/hours-calendars | "New Years Day \| January 1 \| January 1 (Observed Monday, January 2)" … "Christmas \| December 25 (Observed Monday, December 26) \| December 25" |
| 2018-2021 | https://web.archive.org/web/20181215174802/https://www.nyse.com/markets/hours-calendars | "Independence Day \| Wednesday, July 4 \| Thursday, July 4 \| Friday, July 3 (July 4 holiday observed) \| Monday, July 5 (July 4 holiday observed)" |
| 2021-2023 | https://web.archive.org/web/20211126155609/https://www.nyse.com/markets/hours-calendars | "New Years Day \| Friday, January 1 \| —* \| Monday, January 2 (New Year's holiday observed)" and "* No holiday observed, pursuant to NYSE Rule 7.2, NYSE American Rule 7.2E, NYSE Arca Rules 7.2-O and 7.2-E, NYSE Chicago Rule 7.2, and NYSE National Rule 7.2."; "Juneteenth National Independence Day \| — \| Monday, June 20 (Juneteenth holiday observed) \| Monday, June 19" |
| 2024-2026 | https://web.archive.org/web/20240529214655/https://www.nyse.com/markets/hours-calendars | "Juneteenth National Independence Day \| Wednesday, June 19 \| Thursday, June 19 \| Friday, June 19"; "Independence Day \| Thursday, July 4* \| Friday, July 4* \| Friday, July 3 (Independence Day observed)" |
| 2026-2028 (live) | https://www.nyse.com/markets/hours-calendars | "New Year's Day \| Thursday, January 1 \| Friday, January 1 \| —*" and "* Because the holiday falls on Saturday, January 1, 2028, no New Year's Day holiday is observed." |
| 2026 (cross-check) | https://www.nasdaqtrader.com/Trader.aspx?id=calendar | "U.S. Equity and Options Markets Holiday Schedule 2026" — 10 Closed rows + "November 27, 2026 \| Early Close* \| 1:00 p.m." + "December 24, 2026 \| Early Close* \| 1:00 p.m." |
| 2018-12-05 | https://ir.theice.com/press/news-details/2018/New-York-Stock-Exchange-to-Honor-President-George-H-W-Bush/default.aspx | "NYSE Group Markets to close for Day of Mourning on Wednesday, December 5, 2018" |
| 2025-01-09 | https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx | "it will close all NYSE Group equity and options markets on Thursday, January 9, 2025, in observance of the National Day of Mourning" |

Verbatim quotes (official pages, as fetched 2026-09-19):

> "All NYSE markets observe U.S. holidays as listed below for 2026, 2027, and 2028." — https://www.nyse.com/markets/hours-calendars

> "* Because the holiday falls on Saturday, January 1, 2028, no New Year's Day holiday is observed." — https://www.nyse.com/markets/hours-calendars

> "* No holiday observed, pursuant to NYSE Rule 7.2, NYSE American Rule 7.2E, NYSE Arca Rules 7.2-O and 7.2-E, NYSE Chicago Rule 7.2, and NYSE National Rule 7.2." — archived nyse.com page (2021-11-26 capture), footnote to the 2022 New Years Day cell "—*"

> "All NYSE markets observe U.S. holidays as listed below for 2016 and 2017." — archived nyse.com page (2016-06-05 capture)

> "All NYSE markets observe U.S. holidays as listed below for 2018, 2019, 2020, and 2021." — archived nyse.com page (2018-12-15 capture)

> "All NYSE markets observe U.S. holidays as listed below for 2024, 2025, and 2026." — archived nyse.com page (2024-05-29 capture)

> "NYSE Group Markets to close for Day of Mourning on Wednesday, December 5, 2018" — ir.theice.com press release, 2018-12-01

> "it will close all NYSE Group equity and options markets on Thursday, January 9, 2025, in observance of the National Day of Mourning" — ir.theice.com press release, 2024-12-30

## Correction made by this re-verification

The `nyse-holidays-1` transcription listed **2021-12-31** as "New Year's Day (observed)". The official table says no holiday was observed in 2022 for New Year's Day (Rule 7.2); the captured vendor bars (`data/intraday/ENPH_1d.json`) also contain a 2021-12-31 session. `nyse-holidays-2` removes Saturday-New-Year observance. All other 105 full closures and 24 early closes matched.

Method: nine standing NYSE holidays (ten from 2022 with Juneteenth) plus weekend observance for the fixed-date holidays (Saturday -> preceding Friday except New Year's Day, Sunday -> following Monday); Good Friday via the Gregorian Easter algorithm; two individually recorded special full-day closures. Early closes are informational only and never exclude a session.

## 2016 (9 full closures — matches official)

- 2016-01-01 — New Year's Day
- 2016-01-18 — Martin Luther King Jr. Day
- 2016-02-15 — Presidents' Day
- 2016-03-25 — Good Friday
- 2016-05-30 — Memorial Day
- 2016-07-04 — Independence Day
- 2016-09-05 — Labor Day
- 2016-11-24 — Thanksgiving Day
- 2016-12-26 — Christmas Day (observed)

Early closes (informational, official): 2016-11-25 (Day after Thanksgiving (early close))

## 2017 (9 full closures — matches official)

- 2017-01-02 — New Year's Day (observed)
- 2017-01-16 — Martin Luther King Jr. Day
- 2017-02-20 — Presidents' Day
- 2017-04-14 — Good Friday
- 2017-05-29 — Memorial Day
- 2017-07-04 — Independence Day
- 2017-09-04 — Labor Day
- 2017-11-23 — Thanksgiving Day
- 2017-12-25 — Christmas Day

Early closes (informational, official): 2017-07-03 (July 3 (early close)), 2017-11-24 (Day after Thanksgiving (early close))

## 2018 (10 full closures — matches official)

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

Early closes (informational, official): 2018-07-03 (July 3 (early close)), 2018-11-23 (Day after Thanksgiving (early close)), 2018-12-24 (Christmas Eve (early close))

## 2019 (9 full closures — matches official)

- 2019-01-01 — New Year's Day
- 2019-01-21 — Martin Luther King Jr. Day
- 2019-02-18 — Presidents' Day
- 2019-04-19 — Good Friday
- 2019-05-27 — Memorial Day
- 2019-07-04 — Independence Day
- 2019-09-02 — Labor Day
- 2019-11-28 — Thanksgiving Day
- 2019-12-25 — Christmas Day

Early closes (informational, official): 2019-07-03 (July 3 (early close)), 2019-11-29 (Day after Thanksgiving (early close)), 2019-12-24 (Christmas Eve (early close))

## 2020 (9 full closures — matches official)

- 2020-01-01 — New Year's Day
- 2020-01-20 — Martin Luther King Jr. Day
- 2020-02-17 — Presidents' Day
- 2020-04-10 — Good Friday
- 2020-05-25 — Memorial Day
- 2020-07-03 — Independence Day (observed)
- 2020-09-07 — Labor Day
- 2020-11-26 — Thanksgiving Day
- 2020-12-25 — Christmas Day

Early closes (informational, official): 2020-11-27 (Day after Thanksgiving (early close)), 2020-12-24 (Christmas Eve (early close))

## 2021 (9 full closures — matches official)

- 2021-01-01 — New Year's Day
- 2021-01-18 — Martin Luther King Jr. Day
- 2021-02-15 — Presidents' Day
- 2021-04-02 — Good Friday
- 2021-05-31 — Memorial Day
- 2021-07-05 — Independence Day (observed)
- 2021-09-06 — Labor Day
- 2021-11-25 — Thanksgiving Day
- 2021-12-24 — Christmas Day (observed)

Early closes (informational, official): 2021-11-26 (Day after Thanksgiving (early close))

## 2022 (9 full closures — matches official)

- 2022-01-17 — Martin Luther King Jr. Day
- 2022-02-21 — Presidents' Day
- 2022-04-15 — Good Friday
- 2022-05-30 — Memorial Day
- 2022-06-20 — Juneteenth National Independence Day (observed)
- 2022-07-04 — Independence Day
- 2022-09-05 — Labor Day
- 2022-11-24 — Thanksgiving Day
- 2022-12-26 — Christmas Day (observed)

Early closes (informational, official): 2022-11-25 (Day after Thanksgiving (early close))

## 2023 (10 full closures — matches official)

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

Early closes (informational, official): 2023-07-03 (July 3 (early close)), 2023-11-24 (Day after Thanksgiving (early close))

## 2024 (10 full closures — matches official)

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

Early closes (informational, official): 2024-07-03 (July 3 (early close)), 2024-11-29 (Day after Thanksgiving (early close)), 2024-12-24 (Christmas Eve (early close))

## 2025 (11 full closures — matches official)

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

Early closes (informational, official): 2025-07-03 (July 3 (early close)), 2025-11-28 (Day after Thanksgiving (early close)), 2025-12-24 (Christmas Eve (early close))

## 2026 (10 full closures — matches official)

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

Early closes (informational, official): 2026-11-27 (Day after Thanksgiving (early close)), 2026-12-24 (Christmas Eve (early close))

## Re-verification record

1. 2026-09-19: every year 2016-2026 compared against the official NYSE table for that year (URLs above); Nasdaq Trader cross-check for 2026. Result: one mismatch (2021-12-31), fixed; 105/105 full closures and 24/24 early closes now match.
2. `python3 -c "from intel import calendar as c; print(c.verify_against_official())"` must print `[]`; `scripts/verify.py` fails otherwise.
3. Futures (CME Globex) holidays are NOT encoded here: https://www.cmegroup.com/trading-hours.html
