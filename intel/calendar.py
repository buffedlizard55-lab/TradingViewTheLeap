"""US equity market holiday calendar (NYSE/Nasdaq regular session).

This module encodes the full-day closures of the US equity market as a
deterministic, rule-based calendar plus an explicit table of special closures.
It exists so the intraday session pipeline (``intel.intraday``) can distinguish
a weekend from a mid-week exchange holiday when it measures gaps and latency,
instead of treating every UTC date boundary identically.

WHAT THIS IS
------------
A rule-based transcription of the standing NYSE holiday schedule:

- New Year's Day (January 1), Martin Luther King Jr. Day (third Monday of
  January), Presidents' Day (third Monday of February), Good Friday, Memorial
  Day (last Monday of May), Juneteenth National Independence Day (June 19,
  observed from 2022), Independence Day (July 4), Labor Day (first Monday of
  September), Thanksgiving Day (fourth Thursday of November), Christmas
  (December 25).
- Weekend observance for the four fixed-date holidays: a Saturday holiday is
  observed on the preceding Friday, a Sunday holiday on the following Monday --
  EXCEPT New Year's Day on a Saturday, which is NOT observed at all (NYSE Rule
  7.2: no Friday closure when it would end a monthly/yearly accounting period).
  The official NYSE calendar states this for 2028 ("Because the holiday falls on
  Saturday, January 1, 2028, no New Year's Day holiday is observed"); the same
  rule applied on 2021-12-31 (Saturday 2022-01-01), a full trading day that the
  captured vendor bars (data/intraday/ENPH_1d.json) also contain.
- Special full-day closures, each recorded individually with its reason in
  ``SPECIAL_CLOSURES`` below.

WHAT THIS IS NOT
----------------
- Not a substitute for the official calendar. The authoritative sources are the
  NYSE trading calendar (https://www.nyse.com/markets/hours-calendars) and the
  Nasdaq Trader holiday schedule
  (https://www.nasdaqtrader.com/Trader.aspx?id=calendar). On 2026-09-19 every
  full closure and early close for 2016-2026 was re-verified line by line against
  the official NYSE tables (live page plus archived captures of the same page)
  and the two ICE/NYSE press releases; the transcription is kept in
  ``OFFICIAL_FULL_CLOSURES`` / ``OFFICIAL_EARLY_CLOSES`` and
  ``verify_against_official()`` proves the rules reproduce it exactly (IR-28
  closed). The one discrepancy found (2021-12-31) was fixed in nyse-holidays-2.
- Not a futures session calendar. The 2026 CME Globex holiday WINDOWS are
  transcribed from the official page (``CME_GLOBEX_2026_HOLIDAY_WINDOWS``) as
  annotation only; product-specific holiday hours are not encoded and no futures
  session is ever dropped (https://www.cmegroup.com/trading-hours.html).
- Early closes (1:00 PM ET, e.g. the day after Thanksgiving) are listed
  separately as informational-only data and are NEVER used to exclude a session:
  the market still trades on those days.

No network access, no fitting, no guessing: special closures outside the table
below are not inferred, and years outside 2016-2026 raise rather than silently
extrapolating the special-closure history.
"""

from __future__ import annotations

from datetime import date, timedelta

CALENDAR_VERSION = "nyse-holidays-2"  # 2: Saturday New Year's Day is not observed (Rule 7.2)
CALENDAR_SOURCES = (
    "https://www.nyse.com/markets/hours-calendars",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar",
)
FUTURES_CALENDAR_SOURCE = "https://www.cmegroup.com/trading-hours.html"
FIRST_YEAR = 2016
LAST_YEAR = 2026

# Full-day special closures inside FIRST_YEAR..LAST_YEAR, each a deliberate
# individual entry (never inferred by rule). Both are National Days of Mourning
# during which NYSE and Nasdaq closed the cash session:
#   2018-12-05  mourning President George H.W. Bush
#   2025-01-09  mourning President Jimmy Carter
# Both verified against the ICE/NYSE press releases cited above OFFICIAL_FULL_CLOSURES.
SPECIAL_CLOSURES: dict[str, str] = {
    "2018-12-05": "National Day of Mourning for President George H.W. Bush",
    "2025-01-09": "National Day of Mourning for President Jimmy Carter",
}


# ---------------------------------------------------------------------------
# Official transcription (IR-28 re-verification, 2026-09-19).
#
# Every date below was read line by line from an official NYSE publication and is kept
# here, separately from the rule engine, so that the verifier and the unit tests can
# prove the rules reproduce the official table exactly (see verify_against_official()).
# Sources (nyse.com, live and via the Internet Archive's captures of the same page):
#   2016-2017  https://web.archive.org/web/20160605000702/https://www.nyse.com/markets/hours-calendars
#   2018-2021  https://web.archive.org/web/20181215174802/https://www.nyse.com/markets/hours-calendars
#   2021-2023  https://web.archive.org/web/20211126155609/https://www.nyse.com/markets/hours-calendars
#              ("2022 New Years Day: —* No holiday observed, pursuant to NYSE Rule 7.2 ...")
#   2024-2026  https://web.archive.org/web/20240529214655/https://www.nyse.com/markets/hours-calendars
#   2026-2028  https://www.nyse.com/markets/hours-calendars (live 2026-09-19; 2026 also matches
#              https://www.nasdaqtrader.com/Trader.aspx?id=calendar)
#   2018-12-05 https://ir.theice.com/press/news-details/2018/New-York-Stock-Exchange-to-Honor-President-George-H-W-Bush/default.aspx
#   2025-01-09 https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx
# ---------------------------------------------------------------------------
OFFICIAL_FULL_CLOSURES: dict[int, tuple[str, ...]] = {
    2016: ("2016-01-01", "2016-01-18", "2016-02-15", "2016-03-25", "2016-05-30", "2016-07-04",
           "2016-09-05", "2016-11-24", "2016-12-26"),
    2017: ("2017-01-02", "2017-01-16", "2017-02-20", "2017-04-14", "2017-05-29", "2017-07-04",
           "2017-09-04", "2017-11-23", "2017-12-25"),
    2018: ("2018-01-01", "2018-01-15", "2018-02-19", "2018-03-30", "2018-05-28", "2018-07-04",
           "2018-09-03", "2018-11-22", "2018-12-05", "2018-12-25"),
    2019: ("2019-01-01", "2019-01-21", "2019-02-18", "2019-04-19", "2019-05-27", "2019-07-04",
           "2019-09-02", "2019-11-28", "2019-12-25"),
    2020: ("2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25", "2020-07-03",
           "2020-09-07", "2020-11-26", "2020-12-25"),
    2021: ("2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31", "2021-07-05",
           "2021-09-06", "2021-11-25", "2021-12-24"),
    2022: ("2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20", "2022-07-04",
           "2022-09-05", "2022-11-24", "2022-12-26"),
    2023: ("2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29", "2023-06-19",
           "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25"),
    2024: ("2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19",
           "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25"),
    2025: ("2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
           "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25"),
    2026: ("2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
           "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"),
}
OFFICIAL_EARLY_CLOSES: dict[int, tuple[str, ...]] = {
    2016: ("2016-11-25",),
    2017: ("2017-07-03", "2017-11-24"),
    2018: ("2018-07-03", "2018-11-23", "2018-12-24"),
    2019: ("2019-07-03", "2019-11-29", "2019-12-24"),
    2020: ("2020-11-27", "2020-12-24"),
    2021: ("2021-11-26",),
    2022: ("2022-11-25",),
    2023: ("2023-07-03", "2023-11-24"),
    2024: ("2024-07-03", "2024-11-29", "2024-12-24"),
    2025: ("2025-07-03", "2025-11-28", "2025-12-24"),
    2026: ("2026-11-27", "2026-12-24"),
}


# ---------------------------------------------------------------------------
# CME Globex 2026 holiday schedule (futures), transcribed 2026-09-19 from the official
# "2026 CME Globex Trading Schedule" table on https://www.cmegroup.com/trading-hours.html
# ("CME Globex trading hour and holiday schedules being observed for 2026"). Each row is
# a holiday NAME and the DATE WINDOW the exchange lists for it, verbatim. Whether a given
# product is halted, closed early or trades normally on a date inside the window is
# PRODUCT-SPECIFIC (the same page shows e.g. Energy "13:45 closed" and Cryptocurrencies
# "16:00 closed" on Friday 27 Nov 2026) and is deliberately NOT encoded: nothing here is
# used to drop a futures session. The page also states: "This schedule is subject to
# change. Trading hours are usually finalized approximately two weeks prior to the holiday."
# ---------------------------------------------------------------------------
CME_GLOBEX_CALENDAR_SOURCE = "https://www.cmegroup.com/trading-hours.html"
CME_GLOBEX_2026_HOLIDAY_WINDOWS: tuple[tuple[str, str, str], ...] = (
    # (holiday, first date, last date) — ISO dates for the verbatim "INCLUDES THE FOLLOWING DATES"
    ("New Year's", "2025-12-31", "2026-01-02"),
    ("Dr. Martin Luther King, Jr.", "2026-01-18", "2026-01-20"),
    ("Presidents Day", "2026-02-15", "2026-02-17"),
    ("Good Friday", "2026-04-02", "2026-04-04"),
    ("Memorial Day", "2026-05-24", "2026-05-26"),
    ("Juneteenth", "2026-06-18", "2026-06-19"),
    ("Independence Day", "2026-07-03", "2026-07-05"),
    ("Labor Day", "2026-09-06", "2026-09-08"),
    ("Thanksgiving", "2026-11-26", "2026-11-28"),
    ("Christmas", "2026-12-24", "2026-12-26"),
    ("New Year's", "2026-12-31", "2027-01-01"),
)


def cme_globex_holiday_window(iso_date: str) -> str | None:
    """Name of the 2026 CME Globex holiday window containing `iso_date`, else None.

    Informational only (see the note above CME_GLOBEX_2026_HOLIDAY_WINDOWS): a date inside
    a window may still trade with product-specific hours. Dates outside 2026 return None
    because only the 2026 schedule has been transcribed from the official page.
    """
    day = date.fromisoformat(iso_date)
    for name, first, last in CME_GLOBEX_2026_HOLIDAY_WINDOWS:
        if date.fromisoformat(first) <= day <= date.fromisoformat(last):
            return name
    return None


def verify_against_official() -> list[str]:
    """Return every (year, kind, rule-only, official-only) mismatch; empty means exact match."""
    problems: list[str] = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        rule_full = set(holidays_for_year(year))
        off_full = set(OFFICIAL_FULL_CLOSURES[year])
        if rule_full != off_full:
            problems.append(f"{year} full: rule-only {sorted(rule_full - off_full)} "
                            f"official-only {sorted(off_full - rule_full)}")
        rule_early = set(early_closes_for_year(year))
        off_early = set(OFFICIAL_EARLY_CLOSES[year])
        if rule_early != off_early:
            problems.append(f"{year} early: rule-only {sorted(rule_early - off_early)} "
                            f"official-only {sorted(off_early - rule_early)}")
    return problems


def _check_year(year: int) -> None:
    if not isinstance(year, int) or isinstance(year, bool):
        raise ValueError(f"year must be an integer, got {year!r}")
    if year < FIRST_YEAR or year > LAST_YEAR:
        raise ValueError(
            f"year {year} is outside the reviewed {FIRST_YEAR}-{LAST_YEAR} window: "
            "extend SPECIAL_CLOSURES deliberately (with evidence) instead of extrapolating"
        )


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th `weekday` (Monday=0) of a month."""
    first = date(year, month, 1)
    delta = (weekday - first.weekday()) % 7
    return first + timedelta(days=delta + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """The last `weekday` (Monday=0) of a month."""
    if month == 12:
        probe = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        probe = date(year, month + 1, 1) - timedelta(days=1)
    return probe - timedelta(days=(probe.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous/Meeus-Jones-Butcher algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed_fixed(holiday: date) -> date:
    """Weekend observance for a fixed-date holiday: Sat -> prior Fri, Sun -> next Mon."""
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def holidays_for_year(year: int) -> dict[str, str]:
    """Full-day US equity market closures for `year`, ISO date -> holiday name.

    Includes the observed date (with "(observed)" marked) whenever a fixed-date
    holiday falls on a weekend, plus any special closure in SPECIAL_CLOSURES.
    """
    _check_year(year)
    out: dict[str, str] = {}

    def add(day: date, name: str) -> None:
        out[day.isoformat()] = name

    # Fixed-date holidays with weekend observance.
    for month, day, name in (
        (1, 1, "New Year's Day"),
        (6, 19, "Juneteenth National Independence Day"),
        (7, 4, "Independence Day"),
        (12, 25, "Christmas Day"),
    ):
        if month == 6 and year < 2022:
            continue  # NYSE first observed Juneteenth in 2022
        actual = date(year, month, day)
        observed = _observed_fixed(actual)
        if month == 1 and actual.weekday() == 5:
            # NYSE Rule 7.2: a Saturday New Year's Day is not observed on the preceding
            # Friday (year-end accounting period). 2021-12-31 traded; 2027-12-31 will.
            continue
        if observed != actual:
            add(observed, f"{name} (observed)")
        else:
            add(actual, name)
    # Monday-anchored holidays (no observance shift possible).
    add(_nth_weekday(year, 1, 0, 3), "Martin Luther King Jr. Day")
    add(_nth_weekday(year, 2, 0, 3), "Presidents' Day")
    add(_last_weekday(year, 5, 0), "Memorial Day")
    add(_nth_weekday(year, 9, 0, 1), "Labor Day")
    # Thanksgiving is always a Thursday; Good Friday always a Friday.
    add(_nth_weekday(year, 11, 3, 4), "Thanksgiving Day")
    add(_easter_sunday(year) - timedelta(days=2), "Good Friday")
    for iso, reason in SPECIAL_CLOSURES.items():
        if iso.startswith(f"{year}-"):
            if iso in out:
                raise AssertionError(f"special closure {iso} collides with {out[iso]}")
            out[iso] = reason
    return dict(sorted(out.items()))


def early_closes_for_year(year: int) -> dict[str, str]:
    """Informational-only 1:00 PM ET early closes (regular session still trades).

    Rule-based and MUST be re-verified against the official NYSE calendar: the
    day after Thanksgiving (always), July 3 when it falls Monday-Thursday, and
    December 24 when it falls Monday-Thursday. A date that is a full closure is
    never listed here. These entries must not be used to exclude sessions.
    """
    _check_year(year)
    full = set(holidays_for_year(year))
    out: dict[str, str] = {}
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    day_after = thanksgiving + timedelta(days=1)
    if day_after.isoformat() not in full:
        out[day_after.isoformat()] = "Day after Thanksgiving (early close)"
    july3 = date(year, 7, 3)
    if july3.weekday() < 4 and july3.isoformat() not in full:
        out[july3.isoformat()] = "July 3 (early close)"
    dec24 = date(year, 12, 24)
    if dec24.weekday() < 4 and dec24.isoformat() not in full:
        out[dec24.isoformat()] = "Christmas Eve (early close)"
    return dict(sorted(out.items()))


def full_closures_between(start_iso: str, end_iso: str) -> dict[str, str]:
    """Full closures with start_iso <= date <= end_iso, ISO date -> name.

    The scan covers one neighbouring year on each side (clamped to the reviewed
    window) because a weekend observance could in principle fall in the adjacent
    calendar year (a Saturday January 1 is, by Rule 7.2, NOT observed on the
    preceding Friday, so in practice no closure crosses the year boundary; the
    neighbouring-year scan is kept as a safeguard). A window reaching
    outside the reviewed years fails loudly instead of silently reporting no
    closures where the table simply does not apply.
    """
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    if end < start:
        raise ValueError(f"end {end_iso} precedes start {start_iso}")
    if start.year < FIRST_YEAR or end.year > LAST_YEAR:
        raise ValueError(
            f"window {start_iso}..{end_iso} exceeds the reviewed {FIRST_YEAR}-{LAST_YEAR} "
            "window: extend the calendar deliberately (with evidence) instead of extrapolating"
        )
    out: dict[str, str] = {}
    for year in range(max(start.year - 1, FIRST_YEAR), min(end.year + 1, LAST_YEAR) + 1):
        for iso, name in holidays_for_year(year).items():
            if start_iso <= iso <= end_iso:
                out[iso] = name
    return out


def is_full_closure(day: str | date) -> str | None:
    """Holiday name if `day` is a full US equity market closure, else None."""
    iso = day.isoformat() if isinstance(day, date) else day
    date.fromisoformat(iso)  # validate shape eagerly
    name = full_closures_between(iso, iso).get(iso)
    return name


def describe() -> dict:
    """Machine-readable calendar identity for artifact metadata."""
    return {
        "calendar_id": "NYSE",
        "version": CALENDAR_VERSION,
        "years": [FIRST_YEAR, LAST_YEAR],
        "sources": list(CALENDAR_SOURCES),
        "futures_calendar_source": FUTURES_CALENDAR_SOURCE,
        "special_closures": dict(SPECIAL_CLOSURES),
        "verification": (
            "Rule-based transcription; every date must be re-verified against the "
            "official NYSE calendar before authoritative use."
        ),
    }
