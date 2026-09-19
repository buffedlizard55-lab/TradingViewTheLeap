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
  observed on the preceding Friday, a Sunday holiday on the following Monday.
  (So a Saturday January 1 is observed on Friday December 31 of the prior year.)
- Special full-day closures, each recorded individually with its reason in
  ``SPECIAL_CLOSURES`` below.

WHAT THIS IS NOT
----------------
- Not a substitute for the official calendar. The authoritative sources are the
  NYSE trading calendar (https://www.nyse.com/markets/hours-calendars) and the
  Nasdaq Trader holiday schedule
  (https://www.nasdaqtrader.com/Trader.aspx?id=calendar). Every date produced
  here must be re-verified line by line against those pages on a networked
  machine before it is treated as authoritative; that re-verification is tracked
  as an irregularity in research/irregularities.json until it is done.
- Not a futures calendar. CME Globex holidays differ
  (https://www.cmegroup.com/trading_hours.html) and are not encoded here.
- Early closes (1:00 PM ET, e.g. the day after Thanksgiving) are listed
  separately as informational-only data and are NEVER used to exclude a session:
  the market still trades on those days.

No network access, no fitting, no guessing: special closures outside the table
below are not inferred, and years outside 2016-2026 raise rather than silently
extrapolating the special-closure history.
"""

from __future__ import annotations

from datetime import date, timedelta

CALENDAR_VERSION = "nyse-holidays-1"
CALENDAR_SOURCES = (
    "https://www.nyse.com/markets/hours-calendars",
    "https://www.nasdaqtrader.com/Trader.aspx?id=calendar",
)
FUTURES_CALENDAR_SOURCE = "https://www.cmegroup.com/trading_hours.html"
FIRST_YEAR = 2016
LAST_YEAR = 2026

# Full-day special closures inside FIRST_YEAR..LAST_YEAR, each a deliberate
# individual entry (never inferred by rule). Both are National Days of Mourning
# during which NYSE and Nasdaq closed the cash session:
#   2018-12-05  mourning President George H.W. Bush
#   2025-01-09  mourning President Jimmy Carter
# Re-verify against the official NYSE calendar before treating as authoritative.
SPECIAL_CLOSURES: dict[str, str] = {
    "2018-12-05": "National Day of Mourning for President George H.W. Bush",
    "2025-01-09": "National Day of Mourning for President Jimmy Carter",
}


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
    window) because a weekend observance can fall in the adjacent calendar year
    (e.g. Saturday 2022-01-01 is observed on Friday 2021-12-31). A window reaching
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
