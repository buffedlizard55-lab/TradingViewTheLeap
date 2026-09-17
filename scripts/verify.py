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
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

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
EXPECTED_COMPETITION_START = "2026-09-01T08:00:00Z"
EXPECTED_COMPETITION_END = "2026-09-30T12:00:00Z"
EXPECTED_REGISTRATION_CLOSE = "2026-09-23T08:00:00Z"
EXPECTED_MINIMUM_ACTIVE_DAYS = 5
EXPECTED_PRIZE_RANKS = 300
EXPECTED_PUBLIC_LAST_RANK = 250
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
HYP_STATUSES = ("supported", "refuted", "untested", "partially_supported", "inconclusive")
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


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
        if not s["url"].startswith("https://"):
            rep.fail("sources.https", f"{sid}: source URL must use https")
        host = re.sub(r"^https?://", "", s["url"]).split("/")[0]
        endpoint_urls = s.get("endpoint_urls", [])
        endpoint_labels = [item.get("label") for item in endpoint_urls]
        endpoint_values = [item.get("url") for item in endpoint_urls]
        if len(endpoint_labels) != len(set(endpoint_labels)) or any(not x for x in endpoint_labels):
            rep.fail("sources.endpoint_labels", f"{sid}: duplicate or empty endpoint label")
        if len(endpoint_values) != len(set(endpoint_values)) or any(
                not isinstance(x, str) or not x.startswith("https://") for x in endpoint_values):
            rep.fail("sources.endpoint_urls", f"{sid}: endpoint URLs must be unique https URLs")
        for endpoint in endpoint_values:
            if isinstance(endpoint, str):
                endpoint_host = re.sub(r"^https?://", "", endpoint).split("/")[0]
                if endpoint_host != host:
                    rep.fail("sources.endpoint_domain",
                             f"{sid}: endpoint host {endpoint_host} differs from primary host {host}")
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


def check_config(rep: Report, source_ids: dict) -> dict:
    """Check the machine-readable transcription of the live rulebook."""
    cfg = load("data/contest_config.json")
    expected = {
        "competition_start_utc": EXPECTED_COMPETITION_START,
        "competition_end_utc": EXPECTED_COMPETITION_END,
        "registration_close_utc": EXPECTED_REGISTRATION_CLOSE,
        "minimum_active_days": EXPECTED_MINIMUM_ACTIVE_DAYS,
        "maximum_prize_recipients": EXPECTED_PRIZE_RANKS,
        "public_leaderboard_last_visible_rank": EXPECTED_PUBLIC_LAST_RANK,
    }
    for field, want in expected.items():
        if cfg.get(field) != want:
            rep.fail("config.official_fact", f"{field}={cfg.get(field)!r}, expected {want!r}")
    if not approx(cfg["starting_balance_virtual_usd"], BALANCE):
        rep.fail("config.balance", f"balance {cfg['starting_balance_virtual_usd']} != {BALANCE}")
    if not approx(cfg["futures_leverage_ratio"], LEVERAGE):
        rep.fail("config.leverage", f"leverage {cfg['futures_leverage_ratio']} != {LEVERAGE}")
    expected_notional = cfg["starting_balance_virtual_usd"] * cfg["futures_leverage_ratio"]
    if not approx(cfg["maximum_initial_notional_usd"], expected_notional):
        rep.fail("config.notional", "maximum initial notional != balance × leverage")
    else:
        rep.ok(f"contest config: {BALANCE:,.0f} balance × {LEVERAGE:.0f}:1 = {MAX_NOTIONAL:,.0f}")

    try:
        start = parse_utc(cfg["competition_start_utc"])
        end = parse_utc(cfg["competition_end_utc"])
        reg = parse_utc(cfg["registration_close_utc"])
        if not start < reg < end:
            rep.fail("config.dates", "expected competition_start < registration_close < competition_end")
        else:
            rep.ok("contest dates are parseable, ordered, and registration remains inside the window")
    except (TypeError, ValueError) as exc:
        rep.fail("config.dates", f"invalid UTC timestamp: {exc}")

    tiers = cfg["prize_tiers"]
    cursor, cash_total = 1, 0.0
    for tier in tiers:
        if tier["from_rank"] != cursor or tier["to_rank"] < tier["from_rank"]:
            rep.fail("config.prize_contiguous", f"prize tier is not contiguous at rank {cursor}: {tier}")
        places = tier["to_rank"] - tier["from_rank"] + 1
        cash_total += places * (tier["cash_usd_each"] or 0.0)
        cursor = tier["to_rank"] + 1
    if cursor - 1 != cfg["maximum_prize_recipients"]:
        rep.fail("config.prize_count", f"tiers end at {cursor - 1}, expected {cfg['maximum_prize_recipients']}")
    if not approx(cash_total, cfg["cash_prize_total_arv_usd"]):
        rep.fail("config.prize_cash", f"tier cash {cash_total} != ARV {cfg['cash_prize_total_arv_usd']}")
    else:
        rep.ok(f"prize tiers are contiguous through rank {cursor - 1}; cash total {cash_total:,.0f} recomputed")
    if cfg["cash_payment_method_threshold_usd"] != 1000.0:
        rep.fail("config.payment", "cash payment-method threshold must preserve the rules value: 1000 USD")
    if cfg["cash_payment_methods"]["at_or_above_1000_usd"] != ["wire", "PayPal"]:
        rep.fail("config.payment", "cash payment methods >=1000 must preserve rules value: wire or PayPal")
    if cfg["cash_payment_methods"]["below_1000_usd"] != ["PayPal"]:
        rep.fail("config.payment", "cash payment method below 1000 must preserve the rules value: PayPal")
    expected_mechanics = {
        "ranking_metric": "realized_profit_loss_usd_on_closed_positions",
        "leaderboard_update_frequency": "no_more_than_once_per_hour",
        "end_of_competition_auto_close": True,
        "account_reset_allowed": False,
    }
    for field, want in expected_mechanics.items():
        if cfg.get(field) != want:
            rep.fail("config.mechanics", f"{field}={cfg.get(field)!r}, expected {want!r}")
    if cfg["public_leaderboard_last_visible_rank"] >= cfg["maximum_prize_recipients"]:
        rep.fail("config.public_boundary", "last public rank must remain below the maximum prize rank")
    if cfg["transaction_rate_prohibited_at_or_above_per_minute"] != 60:
        rep.fail("config.transaction_limit", "transaction prohibition threshold must be 60 per minute")
    for sid in cfg["source_ids"]:
        if sid not in source_ids:
            rep.fail("config.source", f"unregistered source {sid}")
    meta_sid = cfg["_meta"]["source_id"]
    if meta_sid not in source_ids or cfg["_meta"]["source_url"] != source_ids[meta_sid]["url"]:
        rep.fail("config.source", "primary metadata URL does not match the source registry")
    return cfg


def check_live_snapshot(rep: Report, cfg: dict, source_ids: dict) -> dict:
    """Audit timestamped leaderboard rows and displayed quote inputs."""
    snap = load("data/live_contest_snapshot.json")
    meta = snap["_meta"]
    try:
        parse_utc(meta["captured_at_utc"])
    except (TypeError, ValueError) as exc:
        rep.fail("snapshot.timestamp", f"invalid capture timestamp: {exc}")
    rows = snap["leaderboard"]
    quotes = snap["quotes"]
    if not approx(meta["starting_balance_virtual_usd"], cfg["starting_balance_virtual_usd"]):
        rep.fail("snapshot.balance", "snapshot starting balance differs from contest config")
    if snap["participants_displayed"] < cfg["public_leaderboard_last_visible_rank"]:
        rep.fail("snapshot.participants", "displayed participants cannot be below the visible rank range")
    if meta["public_rows_captured"] != len(rows):
        rep.fail("snapshot.row_count", "declared leaderboard row count does not match")
    if meta["quote_rows_captured"] != len(quotes):
        rep.fail("snapshot.quote_count", "declared quote row count does not match")
    ranks = [r["rank"] for r in rows]
    if len(ranks) != len(set(ranks)) or ranks != sorted(ranks):
        rep.fail("snapshot.ranks", "captured leaderboard ranks must be unique and sorted")
    if 1 not in ranks or cfg["public_leaderboard_last_visible_rank"] not in ranks:
        rep.fail("snapshot.boundaries", "snapshot must include rank 1 and last visible rank")
    traders = [r["trader"] for r in rows]
    if len(traders) != len(set(traders)) or any(not t for t in traders):
        rep.fail("snapshot.traders", "captured traders must be nonempty and unique")
    if any(rows[i]["realized_profit_usd"] < rows[i + 1]["realized_profit_usd"]
           or rows[i]["realized_profit_pct"] < rows[i + 1]["realized_profit_pct"]
           for i in range(len(rows) - 1)):
        rep.fail("snapshot.order", "profit must not increase as captured rank number increases")
    rounding_bound = cfg["starting_balance_virtual_usd"] * 0.00005
    for row in rows:
        expected_usd = cfg["starting_balance_virtual_usd"] * row["realized_profit_pct"] / 100
        if abs(row["realized_profit_usd"] - expected_usd) > rounding_bound + 1e-6:
            rep.fail("snapshot.leaderboard_math", f"rank {row['rank']} %/$ differ beyond rounding bound")
    rep.ok(f"all {len(rows)} captured leaderboard rows pass the ±${rounding_bound:.2f} display-rounding check")

    syms = [q["symbol"] for q in quotes]
    if len(syms) != len(set(syms)):
        rep.fail("snapshot.quote_unique", "duplicate quote symbol")
    reported_time_pattern = re.compile(
        rf"{re.escape(meta['captured_at_utc'][:10])} \d{{2}}:\d{{2}} GMT[+-]\d{{1,2}}")
    for q in quotes:
        if q["price"] <= 0:
            rep.fail("snapshot.quote_positive", f"{q['symbol']}: non-positive quote")
        if q["currency"] != "USD" or q["market_state"] not in ("open", "closed"):
            rep.fail("snapshot.quote_metadata", f"{q['symbol']}: invalid currency or market state")
        if not reported_time_pattern.fullmatch(q["source_reported_as_of"]):
            rep.fail("snapshot.quote_time", f"{q['symbol']}: malformed source-reported timestamp")
        if q["source_id"] not in source_ids:
            rep.fail("snapshot.quote_source", f"{q['symbol']}: unregistered source {q['source_id']}")
        else:
            source = source_ids[q["source_id"]]
            if not source.get("url") or q["symbol"] not in source.get("title", ""):
                rep.fail("snapshot.quote_source", f"{q['symbol']}: source lacks matching symbol/manual-review URL")
    expected_source_ids = [meta["leaderboard_source_id"], *[q["source_id"] for q in quotes]]
    if snap["source_ids"] != expected_source_ids:
        rep.fail("snapshot.source_list", "source_ids must exactly list the leaderboard then each quote source")
    for sid in snap["source_ids"]:
        if sid not in source_ids:
            rep.fail("snapshot.source", f"unregistered source {sid}")
    if meta["leaderboard_source_id"] in source_ids and meta["leaderboard_url"] != source_ids[meta["leaderboard_source_id"]]["url"]:
        rep.fail("snapshot.leaderboard_url", "leaderboard URL differs from its registered source")

    registered_quote_ids = [q["source_id"] for q in quotes if q["source_id"] in source_ids]
    quote_evidence_files = {source_ids[sid].get("evidence_file") for sid in registered_quote_ids}
    if len(registered_quote_ids) == len(quotes) and len(quote_evidence_files) == 1 and None not in quote_evidence_files:
        evidence = read(next(iter(quote_evidence_files)))
        for q in quotes:
            match = re.search(
                rf"^> {re.escape(q['symbol'])} — ([\d,.]+) USD — market (open|closed) — "
                rf"(?:as of|at close) (\d{{2}}:\d{{2}} GMT[+-]\d{{1,2}})$",
                evidence,
                re.MULTILINE,
            )
            if not match:
                rep.fail("snapshot.quote_evidence", f"{q['symbol']}: no matching evidence quotation")
                continue
            quoted_price = float(match.group(1).replace(",", ""))
            if not approx(q["price"], quoted_price, 1e-9) or q["market_state"] != match.group(2):
                rep.fail("snapshot.quote_evidence", f"{q['symbol']}: price/state differs from evidence quotation")
            if not q["source_reported_as_of"].endswith(match.group(3)):
                rep.fail("snapshot.quote_evidence", f"{q['symbol']}: source-reported time differs from evidence")
            if f"- {source_ids[q['source_id']]['url']}" not in evidence:
                rep.fail("snapshot.quote_evidence", f"{q['symbol']}: exact review page absent from evidence")
    else:
        rep.fail("snapshot.quote_evidence", "quote sources must resolve to one captured evidence file")
    rep.ok(f"snapshot has {len(quotes)} positive quote inputs matching evidence and manual-review links")
    return snap


def check_capacity(rep: Report, cfg: dict, snap: dict, master: dict, source_ids: dict) -> None:
    """Recompute the initial capacity screen from config, quotes, caps and multipliers."""
    cap = load("data/initial_capacity.json")
    rows = cap["entries"]
    if cap["_meta"]["row_count"] != len(rows) or len(rows) != len(master["entries"]):
        rep.fail("capacity.count", "capacity count must match its metadata and master list")
    qmap = {q["symbol"]: q for q in snap["quotes"]}
    mmap = {m["symbol"]: m for m in master["entries"]}
    lmap = {r["rank"]: r for r in snap["leaderboard"]}
    target = lmap[cap["_meta"]["target_rank"]]["realized_profit_usd"]
    if not approx(cap["_meta"]["target_realized_profit_usd"], target):
        rep.fail("capacity.target", "capacity target does not match snapshot rank")
    if cap["_meta"]["target_snapshot_utc"] != snap["_meta"]["captured_at_utc"]:
        rep.fail("capacity.target_time", "capacity target timestamp does not match snapshot")
    expected_order = []
    for row in rows:
        sym = row["symbol"]
        if sym not in mmap or sym not in qmap:
            rep.fail("capacity.symbol", f"{sym}: missing master or quote input")
            continue
        m, q = mmap[sym], qmap[sym]
        per_contract = q["price"] * m["contract_multiplier"]
        margin_floor = math.floor(cfg["maximum_initial_notional_usd"] / per_contract)
        quantity = min(int(m["max_open_position_contracts"]), margin_floor)
        notional = quantity * per_contract
        expected = {
            "quote_price": q["price"],
            "contract_multiplier": m["contract_multiplier"],
            "rules_position_cap_contracts": m["max_open_position_contracts"],
            "max_whole_contracts_at_initial_balance": quantity,
            "modeled_initial_notional_usd": notional,
            "modeled_pnl_for_favorable_1pct_move_usd": notional * 0.01,
            "favorable_move_pct_needed_for_rank250_snapshot": target / notional * 100,
            "favorable_move_pct_needed_for_rank1_snapshot": lmap[1]["realized_profit_usd"] / notional * 100,
            "underlying_move_needed_for_rank250_snapshot": target / (quantity * m["contract_multiplier"]),
            "underlying_move_needed_for_rank1_snapshot": lmap[1]["realized_profit_usd"] / (quantity * m["contract_multiplier"]),
        }
        for field, want in expected.items():
            got = row[field]
            tol = max(1e-6, abs(want) * 1e-7)
            if not approx(got, want, tol):
                rep.fail("capacity.math", f"{sym}.{field}={got} != {want}")
        constraint = "rules_position_cap" if int(m["max_open_position_contracts"]) <= margin_floor else "20_to_1_buying_power"
        if row["initial_constraint"] != constraint:
            rep.fail("capacity.constraint", f"{sym}: wrong initial constraint label")
        if row["quote_source_id"] != q["source_id"] or q["source_id"] not in source_ids:
            rep.fail("capacity.source", f"{sym}: quote provenance mismatch")
        expected_order.append(expected["favorable_move_pct_needed_for_rank250_snapshot"])
    if expected_order != sorted(expected_order):
        rep.fail("capacity.order", "capacity rows must be sorted by rank-250 required move")
    else:
        rep.ok(f"all {len(rows)} capacity rows and their ordering were re-derived from source inputs")


def _load_or_fail(rep: Report, rel: str, check: str):
    """Load a required artifact, recording a clean failure when it is absent."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        rep.fail(check, f"{rel} is missing; run the pipeline step that produces it")
        return None
    return load(rel)


def check_frontier(rep: Report, cfg: dict, source_ids: dict) -> None:
    """Audit the leaderboard frontier capture history."""
    fh = _load_or_fail(rep, "data/frontier_history.json", "frontier.present")
    if fh is None:
        return
    captures = fh["captures"]
    if fh["_meta"]["capture_count"] != len(captures):
        rep.fail("frontier.count", "declared capture count does not match")
    if len(captures) < 2:
        rep.fail("frontier.min_rows", "at least two captures are required to track drift")
    times = [c["captured_at_utc"] for c in captures]
    for t in times:
        try:
            parse_utc(t)
        except (TypeError, ValueError) as exc:
            rep.fail("frontier.timestamp", f"invalid capture timestamp {t!r}: {exc}")
    if times != sorted(times):
        rep.fail("frontier.order", "captures must be chronologically sorted")
    balance = cfg["starting_balance_virtual_usd"]
    rounding_bound = balance * 0.00005
    for c in captures:
        ranks = {int(k): v for k, v in c["rows"].items()}
        if set(ranks) != {1, 50, 100, 250}:
            rep.fail("frontier.ranks", f"{c['captured_at_utc']}: must record ranks 1/50/100/250")
            continue
        if c["participants_displayed"] < cfg["public_leaderboard_last_visible_rank"]:
            rep.fail("frontier.participants", f"{c['captured_at_utc']}: participants below 250")
        for rank, row in ranks.items():
            expected_usd = balance * row["realized_profit_pct"] / 100
            if abs(row["realized_profit_usd"] - expected_usd) > rounding_bound + 1e-6:
                rep.fail("frontier.math",
                         f"{c['captured_at_utc']} rank {rank}: %/$ differ beyond rounding bound")
        usds = [ranks[r]["realized_profit_usd"] for r in (1, 50, 100, 250)]
        pcts = [ranks[r]["realized_profit_pct"] for r in (1, 50, 100, 250)]
        if any(usds[i] < usds[i + 1] for i in range(3)) or any(
                pcts[i] < pcts[i + 1] for i in range(3)):
            rep.fail("frontier.monotonic", f"{c['captured_at_utc']}: profit must fall with rank")
        if c["source_id"] not in source_ids:
            rep.fail("frontier.source", f"{c['captured_at_utc']}: unregistered source {c['source_id']}")
        else:
            src = source_ids[c["source_id"]]
            if src.get("url") != fh["_meta"]["leaderboard_url"]:
                rep.fail("frontier.url", f"{c['captured_at_utc']}: source URL differs from leaderboard URL")
            if not src.get("evidence_file") or not os.path.exists(
                    os.path.join(ROOT, src["evidence_file"])):
                rep.fail("frontier.evidence", f"{c['captured_at_utc']}: evidence file missing")
    # Cross-file consistency: the first capture must equal the live snapshot rows.
    snap = load("data/live_contest_snapshot.json")
    first = captures[0]
    for rank, row in {int(k): v for k, v in first["rows"].items()}.items():
        snap_row = next((r for r in snap["leaderboard"] if r["rank"] == rank), None)
        if snap_row is None:
            rep.fail("frontier.snapshot_link", f"rank {rank} absent from live snapshot")
            continue
        if (snap_row["trader"] != row["trader"]
                or not approx(snap_row["realized_profit_pct"], row["realized_profit_pct"], 1e-9)
                or not approx(snap_row["realized_profit_usd"], row["realized_profit_usd"], 1e-9)):
            rep.fail("frontier.snapshot_link", f"rank {rank} differs from live_contest_snapshot")
    if first["participants_displayed"] != snap["participants_displayed"]:
        rep.fail("frontier.snapshot_participants", "first capture participants differ from snapshot")
    if first["captured_at_utc"] != snap["_meta"]["captured_at_utc"]:
        rep.fail("frontier.snapshot_time", "first capture timestamp differs from snapshot")
    rep.ok(f"all {len(captures)} frontier captures re-derived, cross-checked against the live snapshot")


def check_market_history(rep: Report, source_ids: dict, snap: dict, master: dict) -> dict:
    """Audit the raw vendor captures and their provenance index."""
    import hashlib

    sys.path.insert(0, ROOT)
    from intel.data import load_series  # noqa: E402
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fetch_market_data", os.path.join(ROOT, "scripts", "fetch_market_data.py"))
    fetch_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch_mod)

    idx = _load_or_fail(rep, "data/market_history_index.json", "market_history.present")
    if idx is None:
        return
    captures = idx["captures"]
    meta = idx["_meta"]
    if meta["symbol_count"] != len(captures):
        rep.fail("market_history.count", "declared symbol count does not match")
    captured = [c for c in captures if c.get("status") == "captured"]
    failed = [c for c in captures if c.get("status") == "failed"]
    if meta.get("captured_count") != len(captured) or meta.get("failed_count") != len(failed):
        rep.fail("market_history.status_counts", "captured/failed counts do not match")
    if meta["capture_window_start_utc"] != fetch_mod.PERIOD1_UTC or \
            meta["capture_window_end_utc"] != fetch_mod.PERIOD2_UTC:
        rep.fail("market_history.window", "index window differs from the fetch script constants")
    period1 = fetch_mod.epoch_of(fetch_mod.PERIOD1_UTC)
    period2 = fetch_mod.epoch_of(fetch_mod.PERIOD2_UTC)
    symbol_map = {tv: yh for tv, yh in fetch_mod.SYMBOL_MAP}
    master_symbols = {e["symbol"] for e in master["entries"]}
    quote_map = {q["symbol"]: q for q in snap["quotes"]}
    deltas = []
    for c in captures:
        tv = c["tradingview_symbol"]
        if symbol_map.get(tv) != c.get("yahoo_ticker"):
            rep.fail("market_history.mapping", f"{tv}: ticker pair not in the frozen symbol map")
            continue
        if tv not in master_symbols:
            rep.fail("market_history.master", f"{tv}: not in the selected master list")
        if c.get("status") != "captured":
            if not c.get("error"):
                rep.fail("market_history.failed_reason", f"{tv}: failed record without error text")
            continue
        path = os.path.join(ROOT, c["file"])
        if not os.path.exists(path):
            rep.fail("market_history.file", f"{tv}: raw file missing at {c['file']}")
            continue
        with open(path, "rb") as fh_:
            payload = fh_.read()
        if hashlib.sha256(payload).hexdigest() != c["sha256"]:
            rep.fail("market_history.sha256", f"{tv}: stored bytes differ from indexed sha256")
            continue
        if len(payload) != c["bytes"]:
            rep.fail("market_history.bytes", f"{tv}: stored byte length differs from index")
        expected_url = fetch_mod.ENDPOINT_TEMPLATES[0].format(
            ticker=c["yahoo_ticker"], period1=period1, period2=period2)
        if c["endpoint"] not in (
                expected_url,
                fetch_mod.ENDPOINT_TEMPLATES[1].format(
                    ticker=c["yahoo_ticker"], period1=period1, period2=period2)):
            rep.fail("market_history.endpoint", f"{tv}: endpoint does not match the frozen window/ticker")
        try:
            bars = load_series(tv)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            rep.fail("market_history.parse", f"{tv}: raw capture failed validation: {exc}")
            continue
        if len(bars) != c["sessions_valid"]:
            rep.fail("market_history.sessions", f"{tv}: valid session count differs from index")
        if bars and (bars[0].date != c["first_session_utc"]
                     or bars[-1].date != c["last_session_utc"]
                     or not approx(bars[0].close, c["first_close"], 1e-9)
                     or not approx(bars[-1].close, c["last_close"], 1e-9)):
            rep.fail("market_history.bounds", f"{tv}: first/last session or close differs from index")
        if c.get("transport") not in ("direct", "allorigins-relay"):
            rep.fail("market_history.transport", f"{tv}: unknown transport {c.get('transport')!r}")
        if tv in quote_map:
            delta = abs(bars[-1].close - quote_map[tv]["price"]) / quote_map[tv]["price"] * 100
            deltas.append((tv, delta))
            if delta > 15.0:
                rep.fail("market_history.quote_crosscheck",
                         f"{tv}: vendor close is {delta:.2f}% away from the TradingView quote "
                         "- ticker mapping is probably wrong")
    for tv, delta in deltas:
        if delta > 2.0:
            rep.warning(
                f"market_history.quote_delta: {tv}: vendor close differs from the TradingView "
                f"snapshot quote by {delta:.2f}% (front-contract month and capture time may "
                "differ); recorded for review")
    if captured:
        rep.ok(f"all {len(captured)} raw vendor captures match their sha256, endpoints, "
               "windows and parse with valid OHLC; "
               f"{len(deltas)} cross-checked against TradingView quotes "
               f"({sum(1 for _, d in deltas if d <= 2.0)} within 2%)")
    if failed:
        rep.warning(
            f"market_history.incomplete: {len(failed)} symbol(s) failed capture and are "
            "excluded downstream: " + ", ".join(c["tradingview_symbol"] for c in failed))
    return idx


def check_backtests(rep: Report, cfg: dict, snap: dict, master: dict, source_ids: dict) -> dict:
    """Audit the walk-forward artifacts by deterministically re-running the engine."""
    import subprocess
    import tempfile

    results = _load_or_fail(rep, "data/backtest_results.json", "backtest.present")
    vol = _load_or_fail(rep, "data/volatility_intelligence.json", "backtest.present")
    if results is None or vol is None:
        return
    meta = results["_meta"]
    models = {m["id"]: m for m in results["models"]}
    if set(models) != {"S1", "S2", "S3"}:
        rep.fail("backtest.models", "expected exactly models S1, S2, S3")
        return results
    cc = meta["contest_constants"]
    if not approx(cc["starting_balance_virtual_usd"], cfg["starting_balance_virtual_usd"]):
        rep.fail("backtest.constants", "starting balance differs from contest config")
    if not approx(cc["futures_leverage_ratio"], cfg["futures_leverage_ratio"]):
        rep.fail("backtest.constants", "leverage differs from contest config")
    rank250 = next(r for r in snap["leaderboard"] if r["rank"] == 250)
    if not approx(cc["rank250_target_usd"], rank250["realized_profit_usd"]):
        rep.fail("backtest.constants", "rank-250 target differs from the live snapshot")
    if cc["rank250_target_snapshot_utc"] != snap["_meta"]["captured_at_utc"]:
        rep.fail("backtest.constants", "rank-250 target timestamp differs from the live snapshot")

    master_symbols = {e["symbol"] for e in master["entries"]}
    tested = meta["symbols_tested"]
    if not tested or any(s not in master_symbols for s in tested):
        rep.fail("backtest.symbols", "symbols_tested must be a nonempty subset of the master list")
    if len(tested) != len(set(tested)):
        rep.fail("backtest.symbols_unique", "duplicate symbols in symbols_tested")

    for mid, m in models.items():
        if m["verdict"] not in ("supported", "refuted", "inconclusive"):
            rep.fail("backtest.verdict", f"{mid}: invalid verdict {m['verdict']!r}")
        if not m.get("verdict_reasons"):
            rep.fail("backtest.reasons", f"{mid}: verdict without reasons")
        for scenario in ("zero", "moderate", "high"):
            agg = m["scenarios"].get(scenario)
            if not agg or agg.get("windows") is None or agg.get("median_net_profit_usd") is None:
                rep.fail("backtest.scenario", f"{mid}: missing {scenario} aggregate")
                continue
            rows = m["window_rows"].get(scenario, [])
            if len(rows) != agg["windows"]:
                rep.fail("backtest.window_rows", f"{mid}/{scenario}: row count != windows")
            if sum(r["trades"] for r in rows) != agg["trades"]:
                rep.fail("backtest.trade_count", f"{mid}/{scenario}: trades mismatch vs rows")
            if sum(1 for r in rows if r["equity_multiple"] >= 5) != agg["windows_ge_5x"]:
                rep.fail("backtest.bucket_count", f"{mid}/{scenario}: >=5x count mismatch")
            for r in rows:
                if not approx(1 + r["net_profit_usd"] / 250000.0, r["equity_multiple"], 5e-4):
                    rep.fail("backtest.row_math", f"{mid}/{scenario} {r['symbol']}: multiple != 1+pnl/250k")
                    break

    # models.json must agree with the backtest verdicts.
    models_json = load("research/strategy/models.json")
    for row in models_json["models"]:
        m = models[row["id"]]
        if row["status"] != m["verdict"]:
            rep.fail("backtest.models_status",
                     f"{row['id']}: models.json status {row['status']!r} != backtest verdict {m['verdict']!r}")
        if row["status"] != "untested":
            res = row.get("result") or {}
            if not isinstance(res, dict) or res.get("artifact") != "data/backtest_results.json":
                rep.fail("backtest.models_result", f"{row['id']}: result must cite the artifact")
            elif res.get("run_stamp_utc") != meta["generated_utc"]:
                rep.fail("backtest.models_stamp", f"{row['id']}: result stamp differs from artifact")

    # volatility intelligence cross-checks
    if {r["symbol"] for r in vol["records"]} != set(tested):
        rep.fail("backtest.vol_symbols", "volatility records must cover exactly symbols_tested")
    for r in vol["records"]:
        needed = r.get("favorable_move_pct_needed_for_rank250_snapshot")
        best = r.get("best_30d_up_move_pct")
        implied = r.get("rank250_pnl_if_best_30d_up_move_recurred_usd")
        if needed is None or best is None:
            continue
        if not approx(implied, round(best / 100.0 * r["modeled_initial_notional_usd"], 2), 0.02):
            rep.fail("backtest.vol_math", f"{r['symbol']}: implied best-move P/L arithmetic is wrong")
        if r["note_if_best_move_exceeds_rank250_requirement"] != (best >= needed):
            rep.fail("backtest.vol_flag", f"{r['symbol']}: best-move-vs-requirement flag is wrong")

    # Deterministic re-run: the committed artifacts must be reproducible. The
    # comparison is against the LOADED documents (not disk bytes) so a corrupted
    # value anywhere in either artifact fails here even if the on-disk file is
    # otherwise untouched.
    stamp = meta["generated_utc"]
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "run_backtests.py"),
             "--stamp", stamp, "--out-dir", tmp],
            capture_output=True, text=True, timeout=1200)
        if proc.returncode != 0:
            rep.fail("backtest.rerun", f"engine re-run failed: {proc.stderr[-400:]}")
        else:
            for name, loaded in (("backtest_results.json", results),
                                 ("volatility_intelligence.json", vol)):
                fresh_path = os.path.join(tmp, name)
                if not os.path.exists(fresh_path):
                    rep.fail("backtest.rerun", f"engine re-run did not produce {name}")
                    continue
                with open(fresh_path, encoding="utf-8") as fh_:
                    fresh = json.load(fh_)
                if fresh != loaded:
                    rep.fail("backtest.determinism",
                             f"{name}: committed artifact differs from a deterministic "
                             "re-run from the raw captures")
    rep.ok(f"backtest artifacts re-derived from raw captures: verdicts "
           + ", ".join(f"{mid}={m['verdict']}" for mid, m in models.items()))
    return results


def check_strategy_models(rep: Report, cfg: dict, source_ids: dict) -> None:
    models = load("research/strategy/models.json")
    rows = models["models"]
    if models["_meta"]["model_count"] != len(rows):
        rep.fail("strategy.count", "strategy model count mismatch")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        rep.fail("strategy.unique", "duplicate strategy model id")
    for row in rows:
        for field in ("name", "hypothesis", "entry_logic", "exit_logic", "falsification_rule"):
            if not row.get(field):
                rep.fail("strategy.fields", f"{row['id']}: missing {field}")
        if row["status"] == "untested" and row.get("result") is not None:
            rep.fail("strategy.result", f"{row['id']}: untested model must have null result")
        if row["status"] not in ("untested", "supported", "refuted", "inconclusive"):
            rep.fail("strategy.status", f"{row['id']}: invalid status")
        if row["status"] != "untested":
            res = row.get("result")
            if not isinstance(res, dict) or not res.get("basis") or not res.get("artifact"):
                rep.fail("strategy.result",
                         f"{row['id']}: verdict requires a result with basis and artifact")
            elif "independent daily-bar simulation" not in res["basis"]:
                rep.fail("strategy.result",
                         f"{row['id']}: result basis must name the independent simulation")
    for sid in models["_meta"]["source_ids"]:
        if sid not in source_ids:
            rep.fail("strategy.source", f"unregistered source {sid}")
    for field in ("implementation_file", "test_protocol_file"):
        rel = models["_meta"][field]
        if not os.path.exists(os.path.join(ROOT, rel)):
            rep.fail("strategy.file", f"missing {rel}")
    pine = read(models["_meta"]["implementation_file"])
    margin_pct = 100 / cfg["futures_leverage_ratio"]
    required_tokens = (
        "//@version=6",
        f"initial_capital = {int(cfg['starting_balance_virtual_usd'])}",
        f"margin_long = {margin_pct:g}",
        f"margin_short = {margin_pct:g}",
        "use_bar_magnifier = true",
        "calc_on_every_tick = false",
    )
    for token in required_tokens:
        if token not in pine:
            rep.fail("strategy.pine_config", f"Pine implementation missing {token!r}")
    if models["_meta"]["platform_validation_status"] != "not_run":
        rep.fail("strategy.validation_status", "no platform export exists, so status must remain not_run")
    sim_status = models["_meta"].get("independent_simulation_status")
    if sim_status not in (None, "not_run", "completed"):
        rep.fail("strategy.simulation_status", f"invalid independent_simulation_status {sim_status!r}")
    rep.ok(f"{len(rows)} pre-registered strategy models carry implementation/protocol files; "
           "TradingView platform validation remains not_run by construction")


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


def check_master_list(rep: Report, universe: dict, source_ids: dict) -> dict:
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
        if not e.get("selection_rationale"):
            rep.fail("master_list.rationale", f"{eid}: missing selection_rationale")
        if "volatility_rationale" in e:
            rep.fail("master_list.stale_field", f"{eid}: stale volatility_rationale field remains")
        if "launch_date_pending_regulatory_review_confirmation" in e["flags"]:
            rep.fail("master_list.resolved_flag", f"{eid}: resolved XRP launch flag remains")

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
    return ml


def check_master_csv(rep: Report, master: dict, rows: list[dict] | None = None) -> None:
    """Check that the convenience CSV projection has not drifted from JSON."""
    if rows is None:
        with open(os.path.join(ROOT, "data", "master_list.csv"), newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    entries = master["entries"]
    if len(rows) != len(entries):
        rep.fail("master_csv.count", f"CSV has {len(rows)} rows, JSON has {len(entries)}")
        return
    expected_fields = list(entries[0])
    if list(rows[0]) != expected_fields:
        rep.fail("master_csv.columns", "CSV columns do not exactly match the JSON entry schema")
    csv_by_symbol = {r["symbol"]: r for r in rows}
    for entry in entries:
        row = csv_by_symbol.get(entry["symbol"])
        if not row:
            rep.fail("master_csv.symbol", f"missing {entry['symbol']}")
            continue
        for field in expected_fields:
            value = entry[field]
            if isinstance(value, list):
                want = "|".join(map(str, value))
            elif value is None:
                want = ""
            else:
                want = str(value)
            if row.get(field) != want:
                rep.fail("master_csv.parity", f"{entry['symbol']}.{field}: {row.get(field)!r} != {want!r}")
    rep.ok(f"master_list.csv exactly matches all fields in {len(entries)} JSON rows")


def check_returns(rep: Report, source_ids: dict, cfg: dict, snap: dict) -> None:
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
        balance = cfg["starting_balance_virtual_usd"]
        exp_usd = balance * (r["return_multiple"] - 1)
        if not approx(usd, exp_usd, 1.0):
            rep.fail("returns.live_consistency",
                     f"{r['edition_label']}: ${usd:,.2f} vs balance*(mult-1)=${exp_usd:,.2f}")
        else:
            rep.ok(f"live leaderboard self-consistent: ${usd:,.2f} == "
                   f"{balance:,.0f} x ({r['return_multiple']}-1) = ${exp_usd:,.2f}")
        rank1 = next(x for x in snap["leaderboard"] if x["rank"] == 1)
        sync = (
            approx(r["net_profit_pct_as_published"], rank1["realized_profit_pct"], 1e-9)
            and approx(usd, rank1["realized_profit_usd"], 1e-9)
            and r.get("participants") == snap["participants_displayed"]
            and r.get("captured_at_utc") == snap["_meta"]["captured_at_utc"]
        )
        if not sync:
            rep.fail("returns.live_snapshot_sync", f"{r['edition_label']}: live record is stale vs snapshot")
        else:
            rep.ok("in-progress return row matches the timestamped live snapshot")

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
        for field, observation in (("trough_window", r["trough"]), ("peak_window", r["peak"])):
            w = r.get(field)
            if not w or not w.get("endpoint") or not w.get("sessions"):
                rep.fail("volatile_stocks.window_meta", f"{rid}: incomplete {field}")
                continue
            expected_endpoint = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{r['symbol']}"
                f"?period1={w['period1']}&period2={w['period2']}&interval=1d"
            )
            if w["endpoint"] != expected_endpoint:
                rep.fail("volatile_stocks.window_endpoint", f"{rid}: malformed exact endpoint for {field}")
            if not w["period1"] <= observation["epoch"] < w["period2"]:
                rep.fail("volatile_stocks.window_bounds", f"{rid}: observation outside {field}")
            start = datetime.fromisoformat(w["start_utc"]).replace(tzinfo=timezone.utc)
            end = datetime.fromisoformat(w["end_utc"]).replace(tzinfo=timezone.utc)
            # Some archived requests use the next trading boundary (up to a weekend) for
            # period1/period2. Preserve the human-readable inclusive range, but reject
            # timestamps more than three calendar days away from those labels.
            if abs(w["period1"] - start.timestamp()) > 3 * 86_400:
                rep.fail("volatile_stocks.window_date", f"{rid}: period1/start_utc differ by >3 days for {field}")
            if abs(w["period2"] - end.timestamp()) > 3 * 86_400:
                rep.fail("volatile_stocks.window_date", f"{rid}: period2/end_utc differ by >3 days for {field}")
            observation_date = datetime.fromtimestamp(observation["epoch"], timezone.utc).date()
            if observation_date.isoformat() != observation["date_utc"]:
                rep.fail("volatile_stocks.observation_date", f"{rid}: epoch/date mismatch for {field}")
            if not start.date() <= observation_date <= end.date():
                rep.fail("volatile_stocks.window_label_bounds", f"{rid}: observation outside labeled {field}")
        if not all(r.get(field, {}).get("endpoint") for field in ("trough_window", "peak_window")):
            continue
        endpoint_owners = []
        for sid in r["source_ids"]:
            if sid not in source_ids:
                rep.fail("volatile_stocks.source", f"{rid}: cites unregistered source {sid}")
            elif source_ids[sid]["tier"] not in ("market_data_vendor",):
                rep.fail("volatile_stocks.source_tier",
                         f"{rid}: stock evidence must cite market_data_vendor sources, got {sid}")
            elif source_ids[sid].get("endpoint_urls"):
                endpoint_owners.append(sid)
                registered_map = {x["label"]: x["url"] for x in source_ids[sid]["endpoint_urls"]}
                expected_map = {
                    "trough_window": r["trough_window"]["endpoint"],
                    "peak_window": r["peak_window"]["endpoint"],
                }
                registered = set(registered_map.values())
                if registered_map != expected_map:
                    rep.fail("volatile_stocks.endpoint_registry",
                             f"{rid}: registry endpoints do not match labeled trough/peak windows")
                elif source_ids[sid]["url"] not in registered:
                    rep.fail("volatile_stocks.endpoint_primary",
                             f"{rid}: primary registry URL is not one of the two exact windows")
        if len(endpoint_owners) != 1:
            rep.fail("volatile_stocks.source_count",
                     f"{rid}: expected one daily source record owning both endpoints, got {endpoint_owners}")

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
    cfg = load("data/contest_config.json")
    snap = load("data/live_contest_snapshot.json")
    capacity = load("data/initial_capacity.json")
    models = load("research/strategy/models.json")
    frontier = load("data/frontier_history.json")
    market_idx = load("data/market_history_index.json")
    backtests = load("data/backtest_results.json")
    vol_intel = load("data/volatility_intelligence.json")
    with open(os.path.join(ROOT, "data", "master_list.csv"), newline="", encoding="utf-8") as fh:
        master_csv_rows = list(csv.DictReader(fh))
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

    def corrupt_cfg(fn):
        value = copy.deepcopy(cfg)
        fn(value)
        return "data/contest_config.json", value

    def corrupt_snap(fn):
        value = copy.deepcopy(snap)
        fn(value)
        return "data/live_contest_snapshot.json", value

    def corrupt_capacity(fn):
        value = copy.deepcopy(capacity)
        fn(value)
        return "data/initial_capacity.json", value

    def corrupt_models(fn):
        value = copy.deepcopy(models)
        fn(value)
        return "research/strategy/models.json", value

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
    def src_endpoint(s):
        owner = next(item for item in s["sources"] if item.get("endpoint_urls"))
        owner["endpoint_urls"][1]["url"] = owner["endpoint_urls"][0]["url"]
    def src_vendor_honesty(s):
        for src_ in s["sources"]:
            if src_["tier"] == "market_data_vendor":
                src_["official_source"] = True
                break

    def vs_math(v): v["records"][0]["return_multiple"] = 999.0
    def vs_thr(v): v["thresholds"]["ge_100x"]["count"] = 3
    def vs_source(v): v["records"][0]["source_ids"] = ["FAKE-SRC"]
    def vs_window(v): v["records"][0]["window_bounded"] = False
    def vs_endpoint(v): v["records"][0]["peak_window"]["endpoint"] += "&corrupt=1"
    def cfg_notional(v): v["maximum_initial_notional_usd"] = 1.0
    def snapshot_math(v): v["leaderboard"][0]["realized_profit_usd"] += 100.0
    def snapshot_quote(v): v["quotes"][0]["price"] += 1.0
    def capacity_math(v): v["entries"][0]["modeled_initial_notional_usd"] += 1_000.0
    def model_result(v): v["models"][0]["result"] = {"net_profit": 1}

    def corrupt_frontier(fn):
        f = copy.deepcopy(frontier)
        fn(f)
        return "data/frontier_history.json", f

    def corrupt_market_idx(fn):
        m = copy.deepcopy(market_idx)
        fn(m)
        return "data/market_history_index.json", m

    def corrupt_backtests(fn):
        b = copy.deepcopy(backtests)
        fn(b)
        return "data/backtest_results.json", b

    def corrupt_vol(fn):
        v = copy.deepcopy(vol_intel)
        fn(v)
        return "data/volatility_intelligence.json", v

    def corrupt_models_status(v):
        v["models"][0]["status"] = "supported"
        v["models"][0]["result"] = {
            "basis": "independent daily-bar simulation (not a TradingView Strategy Report)",
            "artifact": "data/backtest_results.json",
            "run_stamp_utc": backtests["_meta"]["generated_utc"],
        }

    def frontier_math(f): f["captures"][1]["rows"]["50"]["realized_profit_usd"] += 100.0
    def mh_sha(m):
        cap = next(c for c in m["captures"] if c.get("status") == "captured")
        cap["sha256"] = "0" * 64
    def mh_sessions(m):
        cap = next(c for c in m["captures"] if c.get("status") == "captured")
        cap["sessions_valid"] += 1
    def bt_median(b): b["models"][0]["scenarios"]["zero"]["median_net_profit_usd"] += 1.0
    def bt_rows(b): b["models"][0]["window_rows"]["zero"][0]["trades"] += 1
    def vol_flag(v): v["records"][0]["note_if_best_move_exceeds_rank250_requirement"] = \
        not v["records"][0]["note_if_best_move_exceeds_rank250_requirement"]

    bad_master_csv = copy.deepcopy(master_csv_rows)
    bad_master_csv[0]["max_open_position_contracts"] = "999"

    scenarios = [
        ("master_list.cap", corrupt_ml(set_cap),
         lambda r: check_master_list(r, universe, source_ids)),
        ("master_csv.parity", ("unused-self-test-path", None),
         lambda r: check_master_csv(r, ml, bad_master_csv)),
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
        ("returns.math", corrupt_er(er_math), lambda r: check_returns(r, source_ids, cfg, snap)),
        ("returns.threshold", corrupt_er(er_thr), lambda r: check_returns(r, source_ids, cfg, snap)),
        ("returns.100x", corrupt_er(er_100x), lambda r: check_returns(r, source_ids, cfg, snap)),
        ("returns.count", corrupt_er(er_count), lambda r: check_returns(r, source_ids, cfg, snap)),
        ("universe.size", corrupt_uni(uni_size), lambda r: check_universe(r)),
        ("universe.no_equities", corrupt_uni(uni_equity), lambda r: check_universe(r)),
        ("sources.count", corrupt_src(src_count), lambda r: check_sources(r)),
        ("sources.domain", corrupt_src(src_domain), lambda r: check_sources(r)),
        ("sources.endpoint_urls", corrupt_src(src_endpoint), lambda r: check_sources(r)),
        ("sources.vendor_honesty", corrupt_src(src_vendor_honesty), lambda r: check_sources(r)),
        ("volatile_stocks.math", corrupt_vs(vs_math), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.threshold", corrupt_vs(vs_thr), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.source", corrupt_vs(vs_source), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.window", corrupt_vs(vs_window), lambda r: check_volatile_stocks(r, source_ids)),
        ("volatile_stocks.endpoint_registry", corrupt_vs(vs_endpoint),
         lambda r: check_volatile_stocks(r, source_ids)),
        ("config.notional", corrupt_cfg(cfg_notional), lambda r: check_config(r, source_ids)),
        ("snapshot.leaderboard_math", corrupt_snap(snapshot_math),
         lambda r: check_live_snapshot(r, cfg, source_ids)),
        ("snapshot.quote_evidence", corrupt_snap(snapshot_quote),
         lambda r: check_live_snapshot(r, cfg, source_ids)),
        ("capacity.math", corrupt_capacity(capacity_math),
         lambda r: check_capacity(r, cfg, snap, ml, source_ids)),
        ("strategy.result", corrupt_models(model_result),
         lambda r: check_strategy_models(r, cfg, source_ids)),
        ("frontier.math", corrupt_frontier(frontier_math),
         lambda r: check_frontier(r, cfg, source_ids)),
        ("market_history.sha256", corrupt_market_idx(mh_sha),
         lambda r: check_market_history(r, source_ids, snap, ml)),
        ("market_history.sessions", corrupt_market_idx(mh_sessions),
         lambda r: check_market_history(r, source_ids, snap, ml)),
        ("backtest.determinism", corrupt_backtests(bt_median),
         lambda r: check_backtests(r, cfg, snap, ml, source_ids)),
        ("backtest.trade_count", corrupt_backtests(bt_rows),
         lambda r: check_backtests(r, cfg, snap, ml, source_ids)),
        ("backtest.models_status", corrupt_models(corrupt_models_status),
         lambda r: check_backtests(r, cfg, snap, ml, source_ids)),
        ("backtest.vol_flag", corrupt_vol(vol_flag),
         lambda r: check_backtests(r, cfg, snap, ml, source_ids)),
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
    cfg = check_config(rep, source_ids)
    snap = check_live_snapshot(rep, cfg, source_ids)
    universe = check_universe(rep)
    master = check_master_list(rep, universe, source_ids)
    check_master_csv(rep, master)
    check_returns(rep, source_ids, cfg, snap)
    check_capacity(rep, cfg, snap, master, source_ids)
    check_frontier(rep, cfg, source_ids)
    check_market_history(rep, source_ids, snap, master)
    check_volatile_stocks(rep, source_ids)
    check_backtests(rep, cfg, snap, master, source_ids)
    check_strategy_models(rep, cfg, source_ids)
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

    print("\nAll configured offline provenance, schema, arithmetic, endpoint,")
    print("strategy-state, and contest-universe checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
