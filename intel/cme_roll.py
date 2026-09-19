"""CME front-contract roll schedule, derived from the official termination rules.

What this module is
-------------------
`intel/competition.py` can force-close a position at a declared roll boundary
(`roll_dates=...`), but until now the repository had no roll dates to declare: the CME
contract-spec transcriptions carried the *rule text* and explicitly set
`roll_dates_transcribed: false`. This module turns that rule text into dates, for the
products whose published rule is mechanically decidable, and refuses - loudly, with a
reason - for the ones it is not.

Nothing here is guessed
-----------------------
Every codec is bound to the verbatim termination sentence it implements. The codec's
`rule_verbatim` string is compared by `scripts/verify.py` against the
`termination` field of `data/cme_product_hours.json`, which is itself a transcription of
the product's own official contractSpecs page. If CME rewords a rule, the stored text and
the codec's text diverge and the build fails instead of silently computing dates from a
rule that no longer exists. A product with no codec yields `roll_dates: []` and
`reason: "termination rule has no codec in intel/cme_roll.py"` - never a date derived by
analogy with a neighbouring product.

Business-day basis (declared limitation, tracked as IR-30)
----------------------------------------------------------
"Business day" in a CME rule means a day the exchange is open. This module uses the NYSE
full-closure table in `intel/calendar.py`, which was verified line by line against official
NYSE publications (see research/evidence/NYSE-CALENDAR-2016-2026.md). CME Globex's own
closure set is not independently transcribed here, and CME product-specific holiday
schedules are published at https://www.cmegroup.com/trading-hours.html rather than in this
repository. Every date this module returns therefore carries
`business_day_basis` naming that source, and the artifact declares the dependency. Where a
CME closure differs from an NYSE one, a derived date can be off by one session; that is a
declared, checkable limitation rather than a hidden assumption.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Optional

from . import calendar as us_calendar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURS_ARTIFACT = os.path.join(ROOT, "data", "cme_product_hours.json")

BUSINESS_DAY_BASIS = (
    "NYSE full-closure table (intel/calendar.py, "
    f"version {us_calendar.CALENDAR_VERSION}); CME Globex closure dates are NOT independently "
    "transcribed - see https://www.cmegroup.com/trading-hours.html and irregularity IR-30"
)


# ---------------------------------------------------------------------------
# Business-day helpers over the declared basis
# ---------------------------------------------------------------------------
def is_business_day(day: date) -> bool:
    """True when `day` is a weekday that is not a full US equity market closure."""
    if day.weekday() >= 5:
        return False
    return us_calendar.is_full_closure(day) is None


def previous_business_day(day: date) -> date:
    step = day - timedelta(days=1)
    while not is_business_day(step):
        step -= timedelta(days=1)
    return step


def next_business_day(day: date) -> date:
    step = day + timedelta(days=1)
    while not is_business_day(step):
        step += timedelta(days=1)
    return step


def business_days_before(day: date, n: int) -> date:
    """The date `n` business days strictly before `day` (n >= 1)."""
    if n < 1:
        raise ValueError(f"business_days_before requires n >= 1, got {n}")
    step = day
    for _ in range(n):
        step = previous_business_day(step)
    return step


def nth_last_business_day(year: int, month: int, n: int) -> date:
    """The n-th last business day of a month (n=1 -> last business day)."""
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    while not is_business_day(last):
        last -= timedelta(days=1)
    for _ in range(n - 1):
        last = previous_business_day(last)
    return last


def last_friday(year: int, month: int) -> date:
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    while last.weekday() != 4:  # Monday=0 ... Friday=4
        last -= timedelta(days=1)
    return last


def prior_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


# ---------------------------------------------------------------------------
# Rule codecs. Each one quotes the official sentence it implements.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuleCodec:
    """A mechanically decidable termination rule.

    ``terminates(year, month)`` returns the last trading date of that contract month.
    ``rule_verbatim`` must equal the ``termination`` text stored for the product in
    ``data/cme_product_hours.json``; ``scripts/verify.py`` enforces that.
    """

    name: str
    rule_verbatim: str
    terminates: Callable[[int, int], date]
    note: str = ""


def _si_like(n: int) -> Callable[[int, int], date]:
    def _f(year: int, month: int) -> date:
        return nth_last_business_day(year, month, n)
    return _f


def _cl_like(n: int, n_shifted: int) -> Callable[[int, int], date]:
    """`n` business days before the 25th of the month *prior* to the contract month.

    When the 25th is not itself a business day the official rule moves the count out to
    `n_shifted` business days before that same 25th calendar day.
    """
    def _f(year: int, month: int) -> date:
        py, pm = prior_month(year, month)
        anchor = date(py, pm, 25)
        count = n if is_business_day(anchor) else n_shifted
        return business_days_before(anchor, count)
    return _f


def _crypto_last_friday(year: int, month: int) -> date:
    """Last Friday of the contract month, or the prior such business day.

    The official rule requires the day to be *both* a London and a U.S. business day. Only
    the U.S. leg is checkable from this repository's calendar, so the London leg is applied
    as "not a weekend" and the simplification is declared on the codec.
    """
    day = last_friday(year, month)
    while not is_business_day(day):
        day = previous_business_day(day)
    return day


RULE_CODECS: dict[str, RuleCodec] = {
    "SI": RuleCodec(
        name="comex_si_third_last_business_day",
        rule_verbatim=("12:25 p.m. CT on the third last business day of the contract month"),
        terminates=_si_like(3),
    ),
    "CL": RuleCodec(
        name="nymex_cl_three_business_days_before_prior_month_25th",
        rule_verbatim=(
            "Trading terminates 3 business day before the 25th calendar day of the month prior "
            "to the contract month. If the 25th calendar day is not a business day, trading "
            "terminates 4 business days before the 25th calendar day of the month prior to the "
            "contract month."
        ),
        terminates=_cl_like(3, 4),
    ),
    "BTC": RuleCodec(
        name="cme_btc_last_friday",
        rule_verbatim=(
            "Outright: 4:00 p.m. London time on the last Friday of the contract month; if that "
            "Friday is not both a London and U.S. business day, the prior such business day. "
            "TAS: 3:00 p.m. CT on the U.S. business day immediately preceding the last trade date."
        ),
        terminates=_crypto_last_friday,
        note="the London-business-day leg is applied as 'not a weekend'; only the U.S. leg is "
             "checkable from intel/calendar.py",
    ),
    "ETH": RuleCodec(
        name="cme_eth_last_friday",
        rule_verbatim=(
            "Outright: 4:00 p.m. London time on the last Friday of the contract month; if that "
            "Friday is not both a London and U.S. business day, the prior such business day. "
            "TAS: 3:00 p.m. CT on the U.S. business day immediately preceding the last trade date."
        ),
        terminates=_crypto_last_friday,
        note="the London-business-day leg is applied as 'not a weekend'; only the U.S. leg is "
             "checkable from intel/calendar.py",
    ),
}


# ---------------------------------------------------------------------------
# Roll dates for the continuous front contract
# ---------------------------------------------------------------------------
def roll_dates(product: str, start: date, end: date,
               months: Optional[list[tuple[int, int]]] = None) -> dict:
    """Front-contract termination dates of `product` falling inside [start, end].

    TradingView's ``<PRODUCT>1!`` continuous series stands in for the front contract, so the
    boundary at which the repository's simulation should force-close is the expiry of the
    contract then in front - i.e. the termination dates of successive contract months.

    The window is clamped to the years the business-day basis was reviewed for
    (``intel/calendar.FIRST_YEAR``..``LAST_YEAR``). Requesting dates past that is refused by
    the calendar on purpose, so the clamp is recorded in the result rather than hidden: a
    date derived outside the reviewed closure table would be a guess.

    Returns a dict that always states its own basis and, when no date can be derived, the
    reason why.
    """
    basis_first = date(us_calendar.FIRST_YEAR, 1, 1)
    basis_last = date(us_calendar.LAST_YEAR, 12, 31)
    requested = (start, end)
    start = max(start, basis_first)
    end = min(end, basis_last)
    clamp_note = None
    if (start, end) != requested:
        clamp_note = (f"requested {requested[0].isoformat()}..{requested[1].isoformat()} but the "
                      f"business-day basis is reviewed only for "
                      f"{us_calendar.FIRST_YEAR}-{us_calendar.LAST_YEAR}; window clamped to "
                      f"{start.isoformat()}..{end.isoformat()}")
    if start > end:
        return {
            "product": product,
            "rule_codec": RULE_CODECS[product].name if product in RULE_CODECS else None,
            "rule_verbatim": RULE_CODECS[product].rule_verbatim if product in RULE_CODECS else None,
            "roll_dates": [],
            "termination_dates_iso": [],
            "reason": clamp_note or "empty window",
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "business_day_basis": BUSINESS_DAY_BASIS,
        }

    codec = RULE_CODECS.get(product)
    if codec is None:
        return {
            "product": product,
            "rule_codec": None,
            "rule_verbatim": None,
            "roll_dates": [],
            "termination_dates_iso": [],
            "reason": "termination rule has no codec in intel/cme_roll.py; dates are not "
                      "inferred from another product",
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "window_clamped": clamp_note,
            "business_day_basis": BUSINESS_DAY_BASIS,
        }
    if months is None:
        months = _contract_months_in(product, start, end)
    out = []
    for year, month in months:
        day = codec.terminates(year, month)
        if start <= day <= end:
            out.append({"contract_month": f"{year}-{month:02d}",
                        "termination_date": day.isoformat()})
    return {
        "product": product,
        "rule_codec": codec.name,
        "rule_verbatim": codec.rule_verbatim,
        "codec_note": codec.note or None,
        "roll_dates": out,
        "termination_dates_iso": [r["termination_date"] for r in out],
        "reason": None,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "window_clamped": clamp_note,
        "business_day_basis": BUSINESS_DAY_BASIS,
    }


def _contract_months_in(product: str, start: date, end: date) -> list[tuple[int, int]]:
    """Candidate contract months whose expiry could fall in the window.

    Scans every month from 15 months before `start` to 2 months after `end`, which covers
    every monthly listing whose termination could land inside the window for the codecs
    above (the crude rule expires in the month *prior* to the contract month, so the scan
    has to start well before the window). The scan never crosses the years the business-day
    basis was reviewed for.
    """
    limit_year = us_calendar.LAST_YEAR
    months: list[tuple[int, int]] = []
    y, m = start.year, start.month
    for _ in range(15):
        y, m = prior_month(y, m)
    y = max(y, us_calendar.FIRST_YEAR)
    limit = (limit_year, 12)
    guard = 0
    while (y, m) <= limit and guard < 400:
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        guard += 1
    return months


def describe() -> dict:
    """Machine-readable identity of the roll-schedule logic, for artifact metadata."""
    return {
        "module": "intel/cme_roll.py",
        "calendar_version": us_calendar.CALENDAR_VERSION,
        "business_day_basis": BUSINESS_DAY_BASIS,
        "coded_products": sorted(RULE_CODECS),
        "coded_rule_names": {p: c.name for p, c in sorted(RULE_CODECS.items())},
    }


def load_hours_artifact() -> dict:
    with open(HOURS_ARTIFACT, encoding="utf-8") as fh:
        return json.load(fh)


def codec_matches_transcription(product: str, transcribed_termination: Optional[str]) -> tuple[bool, str]:
    """Compare a codec's verbatim rule text with the transcribed official text."""
    codec = RULE_CODECS.get(product)
    if codec is None:
        return False, f"{product}: no codec"
    if transcribed_termination is None:
        return False, f"{product}: no transcribed termination rule to compare against"
    if codec.rule_verbatim.strip() != transcribed_termination.strip():
        return False, (f"{product}: codec rule text differs from the transcription "
                       f"(codec {codec.rule_verbatim[:60]!r}... vs stored "
                       f"{transcribed_termination[:60]!r}...)")
    return True, "ok"
