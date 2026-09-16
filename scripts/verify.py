#!/usr/bin/env python3
"""
Line-by-line verifier for the TradingViewTheLeap research pipeline.

Every claim stored under data/ and research/ must be traceable to a source registered in
research/sources/sources.json. This script re-derives every computed field from its inputs,
re-counts every declared count, re-checks every symbol against the verified contest universe,
and fails loudly on anything unsourced, arithmetically wrong, or internally inconsistent.

It does NOT reach the network itself. Evidence is captured into research/evidence/ by the
agent (via the fetch_page tool, which is the sandbox's only working network path — direct
curl/wget from the shell is blocked) and this script audits that captured evidence for
completeness, traceability and arithmetic. Every recomputable number (contract exposure,
required price move, stock multiples, threshold counts) is re-derived here from archived
values; a claim survives only if it can be recomputed.

Exit code 0 = all checks passed. Exit code 1 = at least one failure.

Usage:
    python3 scripts/verify.py            # verify
    python3 scripts/verify.py --self-test  # additionally prove each check can fail
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Constants mirrored from the captured evidence. If the rules change, change
# these AND the evidence file; the cross-checks below will catch a mismatch.
# ---------------------------------------------------------------------------
BALANCE = 250_000.0
LEVERAGE = 20.0
MAX_NOTIONAL = BALANCE * LEVERAGE
RANK1_PNL = 2_303_725.00
RANK1_PCT = 921.49
EXPECTED_UNIVERSE_SIZE = 94
EQUITY_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "NASDAQ_MINI"}

OFFICIAL_DOMAINS = (
    "tradingview.com",
    "cmegroup.com",
    "sec.gov",
    "cftc.gov",
    "ampglobal.com",
)

# Market-data vendors are NOT official sources. They are allowed only under the
# "market_data_vendor" tier, only for the archived, recomputable price-history
# evidence in the separate volatile-stocks module, and every such source must
# carry "official_source": false so nobody can launder a vendor into the
# official tiers by accident.
MARKET_DATA_VENDOR_DOMAINS = ("yahoo.com",)

SEVERITIES = ("critical", "high", "medium", "low")
HYP_STATUSES = ("supported", "refuted", "untested", "partially_supported")
VERIFY_STATUSES = ("fully_verified", "identity_verified", "pending_evidence")


class Report:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed.append(msg)

    def fail(self, check: str, msg: str) -> None:
        self.failed.append((check, msg))

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def approx(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_sources(rep: Report) -> dict:
    src = load("research/sources/sources.json")
    declared = src["_meta"]["source_count"]
    actual = len(src["sources"])
    if declared != actual:
        rep.fail("sources.count", f"_meta.source_count={declared} but {actual} sources listed")
    else:
        rep.ok(f"sources.json declares {declared} sources and lists {actual}")

    ids = {}
    for s in src["sources"]:
        sid = s["source_id"]
        if sid in ids:
            rep.fail("sources.unique", f"duplicate source_id {sid}")
        ids[sid] = s
        if s["tier"] not in ("official_primary", "official_secondary", "non_official",
                             "market_data_vendor"):
            rep.fail("sources.tier", f"{sid}: unknown tier {s['tier']!r}")
        host = re.sub(r"^https?://", "", s["url"]).split("/")[0]
        if s["tier"] == "market_data_vendor":
            # Vendor tier: allowed only for known vendors, and must be explicitly
            # labelled non-official so it can never be mistaken for a primary source.
            if not any(host == d or host.endswith("." + d) for d in MARKET_DATA_VENDOR_DOMAINS):
                rep.fail("sources.vendor_domain",
                         f"{sid}: {host} is not an allowed market-data-vendor domain")
            elif s.get("official_source") is not False:
                rep.fail("sources.vendor_honesty",
                         f"{sid}: market_data_vendor source must carry official_source=false")
            else:
                rep.ok(f"{sid}: {host} registered as market-data vendor (explicitly non-official)")
        else:
            if not any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS):
                rep.fail("sources.domain", f"{sid}: {host} is not an official domain")
            else:
                rep.ok(f"{sid}: {host} is an official domain")
        if not s.get("used_for"):
            rep.fail("sources.used_for", f"{sid}: no used_for entries")
        ef = s.get("evidence_file")
        if ef:
            if not os.path.exists(os.path.join(ROOT, ef)):
                rep.fail("sources.evidence_exists", f"{sid}: evidence file missing: {ef}")
            else:
                rep.ok(f"{sid}: evidence file present ({ef})")
        else:
            rep.warn(f"{sid}: no evidence_file declared (claims citing it are less auditable)")
    return ids


def check_evidence_quotes(rep: Report) -> None:
    """Every evidence file must contain verbatim quotations and name its URL + access date."""
    ev_dir = os.path.join(ROOT, "research", "evidence")
    files = sorted(f for f in os.listdir(ev_dir) if f.endswith(".md"))
    if not files:
        rep.fail("evidence.present", "no evidence files found")
        return
    for fn in files:
        text = read(os.path.join("research", "evidence", fn))
        n_quotes = text.count("\n> ")
        if n_quotes < 2:
            rep.fail("evidence.quotes", f"{fn}: only {n_quotes} verbatim quote lines")
        else:
            rep.ok(f"{fn}: {n_quotes} verbatim quote lines")
        if "- **URL:**" not in text:
            rep.fail("evidence.url", f"{fn}: no URL header")
        if "- **Accessed (UTC):**" not in text:
            rep.fail("evidence.accessed", f"{fn}: no access date")
        if "- **Tier:**" not in text:
            rep.fail("evidence.tier", f"{fn}: no tier header")


def check_universe(rep: Report) -> dict:
    uni = load("data/contest_universe.json")
    rows = uni["instruments"]
    n = len(rows)
    if uni["_meta"]["instrument_count"] != n:
        rep.fail("universe.count", f"_meta.instrument_count={uni['_meta']['instrument_count']} but {n} rows")
    else:
        rep.ok(f"contest_universe.json declares {n} and contains {n}")
    if n != EXPECTED_UNIVERSE_SIZE:
        rep.fail("universe.size", f"expected {EXPECTED_UNIVERSE_SIZE} instruments, found {n}")
    else:
        rep.ok(f"universe size matches the {EXPECTED_UNIVERSE_SIZE} instruments transcribed from the rules")

    syms = [r["tradingview_symbol"] for r in rows]
    if len(syms) != len(set(syms)):
        dupes = {s for s in syms if syms.count(s) > 1}
        rep.fail("universe.unique", f"duplicate symbols: {sorted(dupes)}")
    else:
        rep.ok(f"all {len(syms)} symbols unique")

    equities = [r for r in rows if r["exchange"] in EQUITY_EXCHANGES]
    if equities:
        rep.fail("universe.no_equities", f"found {len(equities)} equity instruments: {equities}")
    else:
        rep.ok("universe contains 0 equity instruments (IR-01 corroborated)")

    for r in rows:
        if r["max_open_position_contracts"] <= 0:
            rep.fail("universe.limit", f"{r['tradingview_symbol']}: non-positive position limit")
        if ":" not in r["tradingview_symbol"]:
            rep.fail("universe.symbol_format", f"malformed symbol {r['tradingview_symbol']}")
    rep.ok("every instrument has a positive position limit and a well-formed symbol")
    return {r["tradingview_symbol"]: r for r in rows}


def check_master_list(rep: Report, universe: dict, source_ids: dict) -> None:
    ml = load("data/master_list.json")
    entries = ml["entries"]
    if ml["_meta"]["row_count"] != len(entries):
        rep.fail("master_list.count", f"_meta.row_count={ml['_meta']['row_count']} but {len(entries)} rows")
    else:
        rep.ok(f"master_list.json declares {len(entries)} rows and contains {len(entries)}")

    ids = set()
    for e in entries:
        eid = e["entry_id"]
        if eid in ids:
            rep.fail("master_list.unique", f"duplicate entry_id {eid}")
        ids.add(eid)

        if e["symbol"] not in universe:
            rep.fail("master_list.in_universe", f"{eid}: {e['symbol']} is NOT in the verified contest universe")
        else:
            cap = universe[e["symbol"]]["max_open_position_contracts"]
            if e["max_open_position_contracts"] != cap:
                rep.fail("master_list.cap", f"{eid}: cap {e['max_open_position_contracts']} != rules value {cap}")
            else:
                rep.ok(f"{eid}: {e['symbol']} in universe, cap {cap} matches rules")

        for sid in e["source_ids"]:
            if sid not in source_ids:
                rep.fail("master_list.source", f"{eid}: cites unregistered source {sid}")

        m = e["contract_multiplier"]
        if m is not None:
            if not e["contract_multiplier_source_id"]:
                rep.fail("master_list.mult_source", f"{eid}: multiplier {m} present but no source_id")
            elif e["contract_multiplier_source_id"] not in source_ids:
                rep.fail("master_list.mult_source", f"{eid}: unregistered multiplier source")
            else:
                rep.ok(f"{eid}: multiplier {m} sourced to {e['contract_multiplier_source_id']}")
        else:
            if "multiplier_not_verified_this_session" not in e["flags"]:
                rep.fail("master_list.null_flag", f"{eid}: null multiplier without the required flag")

        mu = e["max_underlying_exposure"]
        if m is not None:
            exp = round(e["max_open_position_contracts"] * m, 6)
            if mu is None or not approx(mu, exp, 1e-6):
                rep.fail("master_list.exposure_math", f"{eid}: exposure {mu} != cap*mult {exp}")
            else:
                rep.ok(f"{eid}: exposure {mu} == cap*mult (recomputed)")
            need = round(RANK1_PNL / exp, 2)
            got = e["underlying_price_move_needed_for_current_rank1_pnl_usd"]
            if got is None or not approx(got, need, 0.011):
                rep.fail("master_list.move_math", f"{eid}: required move {got} != recomputed {need}")
            else:
                rep.ok(f"{eid}: required move ${got:,.2f}/unit recomputed correctly")
        else:
            if mu is not None:
                rep.fail("master_list.exposure_math", f"{eid}: exposure {mu} asserted without a multiplier")

        mult_ret = e["verified_historical_return_multiple"]
        if mult_ret is not None:
            for req in ("return_window_start", "return_window_end", "price_start", "price_end",
                        "return_price_source_id"):
                if not e.get(req):
                    rep.fail("master_list.return_provenance",
                             f"{eid}: asserts {mult_ret}x but is missing {req}")
            else:
                rep.ok(f"{eid}: return multiple {mult_ret}x carries full price provenance")

        if e["verification_status"] not in VERIFY_STATUSES:
            rep.fail("master_list.status", f"{eid}: bad verification_status {e['verification_status']}")
        if e["verification_status"] == "fully_verified" and not e["contract_multiplier_source_id"]:
            rep.fail("master_list.status", f"{eid}: 'fully_verified' with no multiplier source")

    if len(ids) == len(entries):
        rep.ok(f"all {len(entries)} entry_ids unique")

    consts = ml["_meta"]["constants"]
    if not approx(consts["paper_balance_usd"], BALANCE):
        rep.fail("master_list.balance", f"balance {consts['paper_balance_usd']} != {BALANCE}")
    if not approx(consts["futures_leverage"], LEVERAGE):
        rep.fail("master_list.leverage", f"leverage {consts['futures_leverage']} != {LEVERAGE}")
    if not approx(consts["max_notional_usd"], MAX_NOTIONAL):
        rep.fail("master_list.notional", f"max notional {consts['max_notional_usd']} != {MAX_NOTIONAL}")
    else:
        rep.ok(f"max notional {MAX_NOTIONAL:,.0f} == {BALANCE:,.0f} x {LEVERAGE:.0f} (recomputed)")


def check_returns(rep: Report, source_ids: dict) -> None:
    er = load("data/verified_explosive_returns.json")
    recs = er["records"]
    if er["_meta"]["record_count"] != len(recs):
        rep.fail("returns.count", f"_meta.record_count={er['_meta']['record_count']} but {len(recs)}")
    else:
        rep.ok(f"verified_explosive_returns.json declares {len(recs)} records and contains {len(recs)}")

    for r in recs:
        exp = round(1 + r["net_profit_pct_as_published"] / 100.0, 4)
        if not approx(r["return_multiple"], exp, 1e-4):
            rep.fail("returns.math", f"{r['edition_label']}: multiple {r['return_multiple']} != 1+pct/100 = {exp}")
        if r["source_id"] not in source_ids:
            rep.fail("returns.source", f"{r['edition_label']}: unregistered source {r['source_id']}")
        if r["status"] not in ("final", "in_progress"):
            rep.fail("returns.status", f"{r['edition_label']}: bad status {r['status']}")
    rep.ok(f"all {len(recs)} return multiples recomputed from published percentages")

    live = [r for r in recs if r["status"] == "in_progress"]
    for r in live:
        usd = r.get("realized_profit_usd_as_published")
        if usd is None:
            rep.fail("returns.live_usd", f"{r['edition_label']}: in_progress record has no $ figure")
            continue
        exp_usd = BALANCE * (r["return_multiple"] - 1)
        if not approx(usd, exp_usd, 1.0):
            rep.fail("returns.live_consistency",
                     f"{r['edition_label']}: ${usd:,.2f} vs balance*(mult-1)=${exp_usd:,.2f}")
        else:
            rep.ok(f"live leaderboard self-consistent: ${usd:,.2f} == "
                   f"{BALANCE:,.0f} x ({r['return_multiple']}-1) = ${exp_usd:,.2f}")

    thr = er["threshold_analysis"]
    for key, blk in thr.items():
        want = int(key.split("_")[1].rstrip("x"))
        recomputed = sum(1 for r in recs if r["return_multiple"] >= want)
        if blk["count"] != recomputed:
            rep.fail("returns.threshold", f"{key}: count {blk['count']} != recomputed {recomputed}")
        if len(blk["cases"]) != blk["count"]:
            rep.fail("returns.threshold_cases", f"{key}: {len(blk['cases'])} cases listed, count={blk['count']}")
    rep.ok("all threshold counts recomputed from the record set")

    if thr["ge_100x"]["count"] != 0:
        rep.fail("returns.100x", "a >=100x record appeared; IR-03 must be updated")
    else:
        rep.ok("0 records at or above 100x (IR-03 corroborated)")


def check_hypotheses(rep: Report, source_ids: dict, hyp_ids: set) -> None:
    h = load("research/hypotheses/hypotheses.json")
    hs = h["hypotheses"]
    if h["_meta"]["hypothesis_count"] != len(hs):
        rep.fail("hypotheses.count", f"_meta count {h['_meta']['hypothesis_count']} != {len(hs)}")
    else:
        rep.ok(f"hypotheses.json declares {len(hs)} and contains {len(hs)}")
    for x in hs:
        if x["id"] in hyp_ids:
            rep.fail("hypotheses.unique", f"duplicate id {x['id']}")
        hyp_ids.add(x["id"])
        if x["status"] not in HYP_STATUSES:
            rep.fail("hypotheses.status", f"{x['id']}: bad status {x['status']}")
        for f in ("claim", "prediction", "test", "evidence"):
            if not x.get(f):
                rep.fail("hypotheses.fields", f"{x['id']}: missing {f}")
        if not x.get("evidence"):
            rep.fail("hypotheses.evidence", f"{x['id']}: no evidence lines")
        for sid in x["source_ids"]:
            if sid not in source_ids:
                rep.fail("hypotheses.source", f"{x['id']}: unregistered source {sid}")
        if x["status"] in ("supported", "refuted") and not x["evidence"]:
            rep.fail("hypotheses.evidence_required", f"{x['id']}: verdict without evidence")
    rep.ok("every hypothesis has claim, prediction, test, evidence and registered sources")


def check_irregularities(rep: Report, source_ids: dict, hyp_ids: set) -> None:
    ir = load("research/irregularities.json")
    items = ir["irregularities"]
    if ir["_meta"]["count"] != len(items):
        rep.fail("irregularities.count", f"_meta count {ir['_meta']['count']} != {len(items)}")
    else:
        rep.ok(f"irregularities.json declares {len(items)} and contains {len(items)}")
    ids = set()
    for i in items:
        if i["id"] in ids:
            rep.fail("irregularities.unique", f"duplicate id {i['id']}")
        ids.add(i["id"])
        if i["severity"] not in SEVERITIES:
            rep.fail("irregularities.severity", f"{i['id']}: bad severity {i['severity']}")
        for f in ("title", "detail", "observed", "source_ids"):
            if not i.get(f):
                rep.fail("irregularities.fields", f"{i['id']}: missing {f}")
        for sid in i["source_ids"]:
            if sid not in source_ids:
                rep.fail("irregularities.source", f"{i['id']}: unregistered source {sid}")
        lh = i.get("linked_hypothesis")
        if lh and lh not in hyp_ids:
            rep.fail("irregularities.link", f"{i['id']}: links to unknown hypothesis {lh}")
    rep.ok(f"all {len(items)} irregularities well-formed and traceable")


def check_volatile_stocks(rep: Report, source_ids: dict) -> None:
    """Re-derive every volatile-stock multiple from its archived endpoint values.

    data/volatile_stocks.json archives the exact trough and peak adjusted closes captured from the
    Yahoo Finance chart API. A multiple may only exist if this script can recompute it, the record
    is flagged window-bounded, and every cited source_id is registered.
    """
    try:
        vs = load("data/volatile_stocks.json")
    except FileNotFoundError:
        rep.fail("volatile_stocks.present", "data/volatile_stocks.json missing")
        return
    records = vs["records"]
    if vs["_meta"]["record_count"] != len(records):
        rep.fail("volatile_stocks.count",
                 f"_meta.record_count={vs['_meta']['record_count']} but {len(records)} records")
    else:
        rep.ok(f"volatile_stocks.json declares {len(records)} records and contains {len(records)}")

    for r in records:
        rid = r["record_id"]
        tv, pv = r["trough"]["adjclose"], r["peak"]["adjclose"]
        if tv <= 0 or pv <= 0:
            rep.fail("volatile_stocks.positive", f"{rid}: non-positive archived price")
            continue
        if r["peak"]["epoch"] <= r["trough"]["epoch"]:
            rep.fail("volatile_stocks.order", f"{rid}: peak not after trough")
        exp_mult = pv / tv
        if not approx(r["return_multiple"], exp_mult, exp_mult * 0.001):
            rep.fail("volatile_stocks.math",
                     f"{rid}: multiple {r['return_multiple']} != recomputed {exp_mult:.4f}")
        else:
            rep.ok(f"{rid}: {r['symbol']} multiple {r['return_multiple']}x recomputed from archived values")
        if not r.get("window_bounded"):
            rep.fail("volatile_stocks.window", f"{rid}: must be flagged window_bounded")
        for field in ("trough_window", "peak_window"):
            w = r.get(field)
            if not w or not w.get("endpoint") or not w.get("sessions"):
                rep.fail("volatile_stocks.window_meta", f"{rid}: incomplete {field}")
        for sid in r["source_ids"]:
            if sid not in source_ids:
                rep.fail("volatile_stocks.source", f"{rid}: cites unregistered source {sid}")
            elif source_ids[sid]["tier"] not in ("market_data_vendor",):
                rep.fail("volatile_stocks.source_tier",
                         f"{rid}: stock evidence must cite market_data_vendor sources, got {sid}")

    thr = vs["thresholds"]
    for key, t in thr.items():
        want = sorted(r["symbol"] for r in records if r["return_multiple"] >= t["threshold"])
        if sorted(t["symbols"]) != want or t["count"] != len(want):
            rep.fail("volatile_stocks.threshold",
                     f"{key}: declared {t['count']} {sorted(t['symbols'])} != recomputed {len(want)} {want}")
        else:
            rep.ok(f"volatile_stocks threshold {key}: {t['count']} = {', '.join(want)}")


def check_no_unsourced_numbers(rep: Report) -> None:
    """Guard against the failure mode this project exists to prevent: a number with no source."""
    ml = load("data/master_list.json")
    bad = []
    for e in ml["entries"]:
        if e["verified_historical_return_multiple"] is not None and not e.get("return_price_source_id"):
            bad.append(e["entry_id"])
    if bad:
        rep.fail("no_unsourced_numbers", f"return multiples without a price source: {bad}")
    else:
        rep.ok("no historical return multiple is asserted anywhere without a price source")


# ---------------------------------------------------------------------------
# Self-test: prove each check can actually fail
# ---------------------------------------------------------------------------
class _LoadShim:
    """Temporarily serves a mutated payload for one path so a check can be proven to fire.

    The check functions call the module-level load(), so patching load is the only way to
    feed them corrupted data without touching the files on disk.
    """

    def __init__(self, path: str, payload):
        self.path, self.payload = path, payload
        self._real = None

    def __enter__(self):
        global load
        self._real = load
        path, payload = self.path, self.payload

        def shim(rel):
            return copy.deepcopy(payload) if rel == path else self._real(rel)

        load = shim
        return self

    def __exit__(self, *exc):
        global load
        load = self._real
        return False


def self_test(rep: Report) -> None:
    """Corrupt one field at a time and assert the matching check actually fails."""
    print("\n--- SELF-TEST: proving each check can fire ---")
    src = load("research/sources/sources.json")
    uni = load("data/contest_universe.json")
    ml = load("data/master_list.json")
    er = load("data/verified_explosive_returns.json")
    vs = load("data/volatile_stocks.json")
    source_ids = {s["source_id"]: s for s in src["sources"]}
    universe = {r["tradingview_symbol"]: r for r in uni["instruments"]}

    def corrupt_ml(fn):
        m = copy.deepcopy(ml)
        fn(m["entries"][0] if "idx4" not in fn.__name__ else m["entries"][4])
        return "data/master_list.json", m

    def corrupt_er(fn):
        r = copy.deepcopy(er)
        fn(r)
        return "data/verified_explosive_returns.json", r

    def corrupt_uni(fn):
        u = copy.deepcopy(uni)
        fn(u)
        return "data/contest_universe.json", u

    def corrupt_src(fn):
        s = copy.deepcopy(src)
        fn(s)
        return "research/sources/sources.json", s

    def corrupt_vs(fn):
        v = copy.deepcopy(vs)
        fn(v)
        return "data/volatile_stocks.json", v

    def set_cap(e): e["max_open_position_contracts"] = 999.0
    def set_exposure(e): e["max_underlying_exposure"] = 1.0
    def set_move(e): e["underlying_price_move_needed_for_current_rank1_pnl_usd"] = 1.0
    def set_symbol(e): e["symbol"] = "NASDAQ:TSLA"
    def set_ret(e): e["verified_historical_return_multiple"] = 100.0
    def clear_flags_idx4(e): e["flags"] = []
    def bad_status(e): e["verification_status"] = "fully_verified"; e["contract_multiplier_source_id"] = None

    def er_math(r): r["records"][0]["return_multiple"] = 99.0
    def er_thr(r): r["threshold_analysis"]["ge_100x"]["count"] = 3
    def er_100x(r):
        r["records"][0]["return_multiple"] = 150.0
        r["threshold_analysis"]["ge_100x"]["count"] = 1
        r["threshold_analysis"]["ge_100x"]["cases"] = [{}]
    def er_count(r): r["_meta"]["record_count"] = 999

    def uni_size(u): u["instruments"] = u["instruments"][:-1]
    def uni_equity(u): u["instruments"][0]["exchange"] = "NASDAQ"
    def src_count(s): s["_meta"]["source_count"] = 999
    def src_domain(s): s["sources"][0]["url"] = "https://example.com/x"
    def src_vendor_honesty(s):
        for src_ in s["sources"]:
            if src_["tier"] == "market_data_vendor":
                src_["official_source"] = True
                break

    def vs_math(v): v["records"][0]["return_multiple"] = 999.0
    def vs_thr(v): v["thresholds"]["ge_100x"]["count"] = 3
    def vs_source(v): v["records"][0]["source_ids"] = ["FAKE-SRC"]
    def vs_window(v): v["records"][0]["window_bounded"] = False

    scenarios = [
        ("master_list.cap", corrupt_ml(set_cap),
         lambda r: check_master_list(r, universe, source_ids)),
        ("master_list.exposure_math", corrupt_ml(set_exposure),
         lambda r: check_master_list(r, universe, source_ids)),
        ("master_list.move_math", corrupt_ml(set_move),
         lambda r: check_master_list(r, universe, source_ids)),
        ("master_list.in_universe", corrupt_ml(set_symbol),
         lambda r: check_master_list(r, universe, source_ids)),
        ("master_list.return_provenance", corrupt_ml(set_ret),
         lambda r: check_master_list(r, universe, source_ids)),
        ("no_unsourced_numbers", corrupt_ml(set_ret),
         lambda r: check_no_unsourced_numbers(r)),
        ("master_list.status", corrupt_ml(bad_status),
         lambda r: check_master_list(r, universe, source_ids)),
        ("returns.math", corrupt_er(er_math), lambda r: check_returns(r, source_ids)),
        ("returns.threshold", corrupt_er(er_thr), lambda r: check_returns(r, source_ids)),
        ("returns.100x", corrupt_er(er_100x), lambda r: check_returns(r, source_ids)),
        ("returns.count", corrupt_er(er_count), lambda r: check_returns(r, source_ids)),
        ("universe.size", corrupt_uni(uni_size), lambda r: check_universe(r)),
        ("universe.no_equities", corrupt_uni(uni_equity), lambda r: check_universe(r)),
        ("sources.count", corrupt_src(src_count), lambda r: check_sources(r)),
        ("sources.domain", corrupt_src(src_domain), lambda r: check_sources(r)),
        ("sources.vendor_honesty", corrupt_src(src_vendor_honesty), lambda r: check_sources(r)),
        ("volatile_stocks.math", corrupt_vs(vs_math), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.threshold", corrupt_vs(vs_thr), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.source", corrupt_vs(vs_source), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.window", corrupt_vs(vs_window), lambda r: check_volatile_stocks(r, source_ids)),
    ]
    # the null-multiplier flag check: strip the multiplier AND its flag from an entry
    m = copy.deepcopy(ml)
    m["entries"][4]["flags"] = []
    m["entries"][4]["contract_multiplier"] = None
    m["entries"][4]["max_underlying_exposure"] = None
    m["entries"][4]["underlying_price_move_needed_for_current_rank1_pnl_usd"] = None
    m["entries"][4]["verification_status"] = "identity_verified"
    scenarios.append(("master_list.null_flag", ("data/master_list.json", m),
                      lambda r: check_master_list(r, universe, source_ids)))

    for expected, (path, payload), runner in scenarios:
        r = Report()
        with _LoadShim(path, payload):
            runner(r)
        if any(c == expected for c, _ in r.failed):
            rep.ok(f"self-test: '{expected}' fires on corrupted data")
        else:
            rep.fail("self-test", f"'{expected}' did NOT fire on corrupted data")


# ---------------------------------------------------------------------------
def main() -> int:
    rep = Report()
    print("=" * 74)
    print("TradingViewTheLeap research verifier")
    print("=" * 74)

    source_ids = check_sources(rep)
    check_evidence_quotes(rep)
    universe = check_universe(rep)
    check_master_list(rep, universe, source_ids)
    check_returns(rep, source_ids)
    check_volatile_stocks(rep, source_ids)
    hyp_ids: set = set()
    check_hypotheses(rep, source_ids, hyp_ids)
    check_irregularities(rep, source_ids, hyp_ids)
    check_no_unsourced_numbers(rep)

    if "--self-test" in sys.argv:
        self_test(rep)

    print(f"\nPassed : {len(rep.passed)}")
    print(f"Failed : {len(rep.failed)}")
    print(f"Warnings: {len(rep.warnings)}")

    if rep.warnings:
        print("\nWARNINGS")
        for w in rep.warnings:
            print(f"  ! {w}")
    if rep.failed:
        print("\nFAILURES")
        for check, msg in rep.failed:
            print(f"  X [{check}] {msg}")
        return 1

    print("\nAll checks passed. No unsourced numbers, no arithmetic mismatches,")
    print("no symbols outside the verified contest universe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
