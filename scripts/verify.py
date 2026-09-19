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
import statistics
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
    # Listing-exchange calendars are official exchange publications: NYSE for the US equity
    # full-closure table (intel/calendar.py), Nasdaq Trader as the cross-check source.
    "nyse.com",
    "nasdaqtrader.com",
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


def check_leaderboard_lab(rep: Report, cfg: dict, source_ids: dict) -> None:
    """Re-derive the leaderboard/prize arithmetic lab and cross-check every input join.

    The lab is pure arithmetic on committed, independently verified sources, so it must be
    byte-reproducible: the strongest available check is to re-run its builder in-process and
    require the committed document to be identical, then re-test the arithmetic joins that the
    builder depends on (frontier captures, prize tiers, champion sample, capacity, volatility).
    """
    lab = _load_or_fail(rep, "data/leaderboard_lab.json", "leaderboard_lab.present")
    if lab is None:
        return

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "leaderboard_lab", os.path.join(ROOT, "scripts", "leaderboard_lab.py"))
    lab_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab_mod)
    fresh = lab_mod.build()
    if fresh != lab:
        rep.fail("leaderboard_lab.determinism",
                 "committed artifact differs from a deterministic re-derivation of its inputs")
    else:
        rep.ok("leaderboard_lab.json is exactly reproducible from contest config and captures")

    # --- prize ladder ---------------------------------------------------------
    ladder = lab["prize_ladder"]
    if not approx(ladder["summed_cash_from_tiers_usd"], ladder["declared_cash_arv_usd"], 0.01):
        rep.fail("leaderboard_lab.prize_arv",
                 "summed cash tiers differ from the declared cash ARV")
    if ladder["declared_cash_arv_usd"] != cfg["cash_prize_total_arv_usd"]:
        rep.fail("leaderboard_lab.prize_arv", "declared ARV differs from contest_config")
    tiers_lab = [(t["from_rank"], t["to_rank"], t["cash_usd_each"], t["plan_months_each"])
                 for t in ladder["tiers"]]
    tiers_cfg = [(t["from_rank"], t["to_rank"], t["cash_usd_each"], t["plan_months_each"])
                 for t in cfg["prize_tiers"]]
    if tiers_lab != tiers_cfg:
        rep.fail("leaderboard_lab.prize_tiers", "prize tiers differ from the official transcription")
    if ladder["prize_recipients_total"] != cfg["maximum_prize_recipients"]:
        rep.fail("leaderboard_lab.prize_tiers", "recipient total differs from the rules' 300")
    if ladder["cash_recipients"] != 50 or ladder["last_cash_rank"] != 50:
        rep.fail("leaderboard_lab.prize_tiers", "cash recipients must be ranks 1-50 only")

    # --- capture window and per-row arithmetic --------------------------------
    start = parse_utc(cfg["competition_start_utc"])
    end = parse_utc(cfg["competition_end_utc"])
    fh = load("data/frontier_history.json")
    if len(lab["captures"]) != len(fh["captures"]):
        rep.fail("leaderboard_lab.capture_count", "capture count differs from frontier_history")
    else:
        for lab_cap, fh_cap in zip(lab["captures"], fh["captures"]):
            if lab_cap["captured_at_utc"] != fh_cap["captured_at_utc"]:
                rep.fail("leaderboard_lab.capture_link", "capture timestamps differ from frontier_history")
                continue
            if lab_cap["source_id"] != fh_cap["source_id"]:
                rep.fail("leaderboard_lab.capture_link",
                         f"{lab_cap['captured_at_utc']}: source id differs from frontier_history")
            if lab_cap["participants_displayed"] != fh_cap["participants_displayed"]:
                rep.fail("leaderboard_lab.capture_link",
                         f"{lab_cap['captured_at_utc']}: participants differ from frontier_history")
            for rank, row in lab_cap["rows"].items():
                src_row = fh_cap["rows"].get(str(rank))
                if src_row is None or not approx(src_row["realized_profit_usd"],
                                                 row["realized_profit_usd"], 0.005) or \
                        not approx(src_row["realized_profit_pct"], row["realized_profit_pct"], 1e-9):
                    rep.fail("leaderboard_lab.capture_link",
                             f"{lab_cap['captured_at_utc']} rank {rank}: row differs from frontier_history")
    for cap in lab["captures"]:
        at = parse_utc(cap["captured_at_utc"])
        if not start < at < end:
            rep.fail("leaderboard_lab.window", f"{cap['captured_at_utc']}: capture outside the contest window")
            continue
        elapsed = (at - start).total_seconds() / 86400.0
        remaining = (end - at).total_seconds() / 86400.0
        if not approx(cap["elapsed_days_since_start"], elapsed, 1e-4) or \
                not approx(cap["remaining_days_to_deadline"], remaining, 1e-4):
            rep.fail("leaderboard_lab.window", f"{cap['captured_at_utc']}: elapsed/remaining days are wrong")
        for rank, row in cap["rows"].items():
            multiple = 1.0 + row["realized_profit_pct"] / 100.0
            if not approx(row["balance_multiple"], multiple, 1e-6):
                rep.fail("leaderboard_lab.multiple", f"{cap['captured_at_utc']} rank {rank}: multiple is wrong")
            if not approx(row["average_usd_per_day_since_start"],
                          row["realized_profit_usd"] / elapsed, 1e-3):
                rep.fail("leaderboard_lab.rate", f"{cap['captured_at_utc']} rank {rank}: $/day is wrong")
            daily = 100.0 * (multiple ** (1.0 / remaining) - 1.0)
            if not approx(row["fresh_account_required_daily_compound_pct"], daily, 1e-4) or \
                    not approx(row["fresh_account_required_underlying_pct_per_day_at_20x"],
                               daily / LEVERAGE, 1e-4):
                rep.fail("leaderboard_lab.fresh_account",
                         f"{cap['captured_at_utc']} rank {rank}: required daily compounding is wrong")
        if set(cap["rows"]) != {"1", "50", "100", "250"}:
            rep.fail("leaderboard_lab.ranks", f"{cap['captured_at_utc']}: must carry ranks 1/50/100/250")

    # --- targets --------------------------------------------------------------
    remaining = lab["captures"][-1]["remaining_days_to_deadline"]
    for t in lab["targets"]:
        required = BALANCE * (t["balance_multiple"] - 1)
        if not approx(t["required_net_profit_usd"], required, 0.01) or \
                not approx(t["required_net_profit_pct"], 100 * (t["balance_multiple"] - 1), 1e-9):
            rep.fail("leaderboard_lab.target_profit",
                     f"{t['balance_multiple']}x: required net profit is wrong")
        daily = 100.0 * (t["balance_multiple"] ** (1.0 / remaining) - 1.0)
        if not approx(t["required_daily_compound_pct_over_remaining_window"], daily, 1e-4) or \
                not approx(t["required_underlying_pct_per_day_at_20x"], daily / LEVERAGE, 1e-4):
            rep.fail("leaderboard_lab.target_rate",
                     f"{t['balance_multiple']}x: required daily compounding is wrong")
    tl = load("data/target_lab.json")
    tl_counts = {x["balance_multiple"]: x["completed_sample_at_or_above"] for x in tl["targets"]}
    for t in lab["targets"]:
        if tl_counts.get(t["balance_multiple"]) != t["completed_champion_sample_at_or_above"]:
            rep.fail("leaderboard_lab.target_champions",
                     f"{t['balance_multiple']}x: champion count disagrees with target_lab.json")

    # --- leverage arithmetic --------------------------------------------------
    lm = lab["leverage_math"]
    if lm["maximum_initial_notional_usd"] != MAX_NOTIONAL or \
            not approx(lm["usd_per_1pct_underlying_move_at_max_notional"], MAX_NOTIONAL * 0.01, 0.01) or \
            not approx(lm["adverse_underlying_move_pct_to_erase_the_whole_balance"], 100.0 / LEVERAGE, 1e-9) or \
            not approx(lm["adverse_underlying_move_pct_to_erase_half_the_balance"], 50.0 / LEVERAGE, 1e-9):
        rep.fail("leaderboard_lab.leverage_math", "leverage/exposure arithmetic is wrong")
    if lm["account_reset_allowed"] != cfg["account_reset_allowed"]:
        rep.fail("leaderboard_lab.leverage_math", "account-reset flag differs from the rules")

    # --- champion sample ------------------------------------------------------
    completed = [r for r in load("data/verified_explosive_returns.json")["records"]
                 if r["status"] == "final"]
    multiples = sorted(float(r["return_multiple"]) for r in completed)
    cs = lab["champion_sample"]
    if cs["completed_records"] != len(completed) or \
            not approx(cs["maximum_completed_multiple"], max(multiples), 1e-9) or \
            not approx(cs["minimum_completed_multiple"], min(multiples), 1e-9):
        rep.fail("leaderboard_lab.champion_sample", "champion sample statistics are wrong")
    rank50_multiple = lab["captures"][-1]["rows"]["50"]["balance_multiple"]
    if cs["latest_rank50_multiple"] != rank50_multiple or \
            cs["completed_champions_strictly_below_latest_rank50"] != sum(m < rank50_multiple for m in multiples) or \
            cs["completed_champions_at_or_above_latest_rank50"] != sum(m >= rank50_multiple for m in multiples):
        rep.fail("leaderboard_lab.champion_sample", "champion-vs-frontier comparison is wrong")

    # --- instrument join ------------------------------------------------------
    capacity = {e["symbol"]: e for e in load("data/initial_capacity.json")["entries"]}
    vol = {r["symbol"]: r for r in load("data/volatility_intelligence.json")["records"]}
    rank50_usd = lab["captures"][-1]["rows"]["50"]["realized_profit_usd"]
    for row in lab["cash_frontier_instrument_requirements"]:
        symbol = row["symbol"]
        cap = capacity.get(symbol)
        if cap is None:
            rep.fail("leaderboard_lab.instrument_join", f"{symbol}: not in initial_capacity.json")
            continue
        if not approx(row["modeled_initial_notional_usd"], cap["modeled_initial_notional_usd"], 0.01) or \
                row["max_whole_contracts_at_initial_balance"] != cap["max_whole_contracts_at_initial_balance"]:
            rep.fail("leaderboard_lab.instrument_join", f"{symbol}: capacity fields differ from the source")
        needed = 100.0 * rank50_usd / row["modeled_initial_notional_usd"]
        if not approx(row["favorable_move_pct_needed_for_latest_rank50_level"], needed, 1e-4):
            rep.fail("leaderboard_lab.instrument_join", f"{symbol}: required move is wrong")
        source_vol = vol.get(symbol)
        if source_vol is None:
            if row["vendor_history_sessions"] is not None or \
                    row["best_30d_up_move_pct_in_vendor_history"] is not None:
                rep.fail("leaderboard_lab.instrument_join", f"{symbol}: history fields without a vendor record")
            continue
        if row["vendor_history_sessions"] != source_vol["sessions"] or \
                not approx(row["best_30d_up_move_pct_in_vendor_history"],
                           source_vol["best_30d_up_move_pct"], 1e-9):
            rep.fail("leaderboard_lab.instrument_join", f"{symbol}: history fields differ from the source")
        if row["history_contains_a_30d_window_as_large_as_that_requirement"] != \
                (source_vol["best_30d_up_move_pct"] >= needed):
            rep.fail("leaderboard_lab.instrument_join", f"{symbol}: envelope flag is wrong")
    rep.ok("leaderboard_lab.json re-derived: prize ladder, frontier pace, targets, leverage and "
           "instrument joins all recomputable")


def check_intelligence_report(rep: Report, source_ids: dict) -> None:
    """Check the consolidated intelligence layer without treating it as a prediction."""
    report = _load_or_fail(rep, "data/intelligence_report.json", "intelligence.present")
    if report is None:
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_intelligence", os.path.join(ROOT, "scripts", "build_intelligence.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.build_report() != report:
        rep.fail("intelligence.determinism", "intelligence_report.json differs from deterministic re-derivation")
    else:
        rep.ok("intelligence_report.json is exactly reproducible from committed artifacts")

    meta = report.get("_meta", {})
    if not meta.get("deterministic") or not meta.get("not_a_forecast") or not meta.get("not_trading_advice"):
        rep.fail("intelligence.boundary", "intelligence report must declare deterministic/non-forecast boundaries")
    for rel in meta.get("input_artifacts", []):
        if not os.path.exists(os.path.join(ROOT, rel)):
            rep.fail("intelligence.input", f"missing declared input artifact: {rel}")

    provenance = report.get("provenance", {})
    for key in ("tradingview_official", "cme_official", "market_data_vendor", "repository_simulation"):
        if key not in provenance:
            rep.fail("intelligence.provenance", f"missing provenance class: {key}")
    for key in ("tradingview_official", "cme_official", "market_data_vendor"):
        for sid in provenance.get(key, {}).get("source_ids", []):
            if sid not in source_ids:
                rep.fail("intelligence.source", f"{key}: unregistered source {sid}")
    if provenance.get("market_data_vendor", {}).get("captured_series", 0) < 1:
        rep.fail("intelligence.coverage", "report must account for at least one captured vendor series")

    comp = load("data/competition_results.json")
    result_models = {r.get("model") for r in report.get("model_comparison", {}).get("results", [])}
    expected_models = {m.get("model") for m in comp.get("models", [])}
    if result_models != expected_models:
        rep.fail("intelligence.models", "model comparison does not cover exactly the frozen competition model set")
    expected_users = {p.get("username") for p in comp.get("participants", [])}
    reported_users = {u for r in report.get("model_comparison", {}).get("results", []) for u in r.get("usernames", [])}
    if reported_users != expected_users:
        rep.fail("intelligence.usernames", "model comparison usernames do not match the competition roster/results")
    decision = report.get("model_comparison", {}).get("decision", {})
    for key, expected in (("any_shadow_10x", comp["target_summary"]["ge_10x"] > 0),
                          ("any_shadow_20x", comp["target_summary"]["ge_20x"] > 0),
                          ("any_shadow_50x", comp["target_summary"]["ge_50x"] > 0),
                          ("any_shadow_100x", comp["target_summary"]["ge_100x"] > 0)):
        if decision.get(key) != expected:
            rep.fail("intelligence.thresholds", f"{key} disagrees with competition_results")

    statuses = {"verified", "captured", "completed_with_caveats", "blocked_or_unrun", "blocked_by_public_data"}
    for item in report.get("status_register", []):
        if item.get("status") not in statuses:
            rep.fail("intelligence.status", f"unknown workstream status: {item.get('status')}")
        if not item.get("evidence") or not item.get("next_step"):
            rep.fail("intelligence.status", f"workstream lacks evidence or next step: {item.get('workstream')}")
        for rel in item.get("evidence", []):
            if rel.endswith((".json", ".md", ".py", ".pine")) and not os.path.exists(os.path.join(ROOT, rel)):
                rep.fail("intelligence.evidence", f"missing workstream evidence: {rel}")
    rep.ok("intelligence provenance classes, usernames, thresholds, and blocked-work statuses are auditable")


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
            rep.warn(
                f"market_history.quote_delta: {tv}: vendor close differs from the TradingView "
                f"snapshot quote by {delta:.2f}% (front-contract month and capture time may "
                "differ); recorded for review")
    if captured:
        rep.ok(f"all {len(captured)} raw vendor captures match their sha256, endpoints, "
               "windows and parse with valid OHLC; "
               f"{len(deltas)} cross-checked against TradingView quotes "
               f"({sum(1 for _, d in deltas if d <= 2.0)} within 2%)")
    if failed:
        rep.warn(
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


def check_universe_transcription(rep: Report, text_override: str | None = None) -> None:
    """The §08 transcription in the evidence file must match the committed universe exactly.

    The rules page is captured by the agent (the sandbox has no direct network path), so the
    transcription is the one place where a transcription error could enter. This check removes that
    risk: it parses the quoted `- for SYMBOL maximum amount for an open position is N` lines and
    requires the same order, the same count and identical values as `data/contest_universe.json`.
    `text_override` exists so the mutation self-test can feed a corrupted transcription.
    """
    evidence_rel = "research/evidence/TV-RULES-AMP-SEP2026-R5.md"
    pattern = re.compile(r"^> - for (\S+) maximum amount for an open position is ([\d.]+)\s*$", re.M)
    universe_doc = load("data/contest_universe.json")
    stored = [(e["tradingview_symbol"], float(e["max_open_position_contracts"]))
              for e in universe_doc["instruments"]]
    text = text_override if text_override is not None else read(evidence_rel)
    rows = [(m.group(1), float(m.group(2))) for m in pattern.finditer(text)]
    if not rows:
        rep.fail("universe.transcription", f"{evidence_rel}: no §08 transcription lines found")
        return
    if len(rows) != len(stored):
        rep.fail("universe.transcription",
                 f"{evidence_rel}: {len(rows)} transcribed instruments vs {len(stored)} stored")
        return
    mismatches = [(a, b) for a, b in zip(rows, stored) if a != b]
    if mismatches:
        rep.fail("universe.transcription",
                 f"{evidence_rel}: {len(mismatches)} mismatch(es), first {mismatches[0]}")
        return
    rep.ok(f"{evidence_rel}: all {len(rows)} transcribed instruments and caps match the committed universe")


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
        # The in-progress return row represents the newest official frontier capture.
        # The original live_contest_snapshot.json is intentionally preserved as the
        # first historical capture used by the initial capacity benchmark.
        frontier = load("data/frontier_history.json")
        latest = frontier["captures"][-1]
        rank1 = latest["rows"]["1"]
        sync = (
            approx(r["net_profit_pct_as_published"], rank1["realized_profit_pct"], 1e-9)
            and approx(usd, rank1["realized_profit_usd"], 1e-9)
            and r.get("participants") == latest["participants_displayed"]
            and r.get("captured_at_utc") == latest["captured_at_utc"]
            and r.get("source_id") == latest["source_id"]
        )
        if not sync:
            rep.fail("returns.live_snapshot_sync", f"{r['edition_label']}: live record is stale vs latest frontier capture")
        else:
            rep.ok("in-progress return row matches the latest timestamped official frontier capture")

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


def check_competition(rep: Report, cfg: dict, master: dict, source_ids: dict) -> None:
    """Audit the shadow-competition artifact by deterministically re-running the engine.

    Re-derives every aggregate from the per-edition rows, re-checks every rule
    constant against data/contest_config.json, re-validates the roster against
    the frozen parameter library and the captured eligible universe, and then
    re-runs scripts/run_competition.py from the raw captures and requires
    byte-identical output.
    """
    import subprocess
    import tempfile

    doc = _load_or_fail(rep, "data/competition_results.json", "competition.present")
    roster = _load_or_fail(rep, "data/competition/roster.json", "competition.roster_present")
    if doc is None or roster is None:
        return
    meta = doc["_meta"]

    if meta.get("kind") != "own_shadow_competition_simulation":
        rep.fail("competition.kind", f"unexpected kind {meta.get('kind')!r}")
    if meta.get("engine") != "intel-competition-2":
        rep.fail("competition.engine", f"unexpected engine {meta.get('engine')!r}")
    if meta.get("not_a_forecast") is not True or roster["_meta"].get("not_a_forecast") is not True:
        rep.fail("competition.not_a_forecast", "artifact and roster must declare not_a_forecast: true")

    # Rules constants must mirror the official config transcription.
    rules = doc["rules"]
    for key in ("starting_balance_virtual_usd", "futures_leverage_ratio",
                "ranking_metric", "end_of_competition_auto_close",
                "account_reset_allowed", "minimum_active_days"):
        if rules.get(key) != cfg.get(key):
            rep.fail("competition.rules", f"rules.{key} {rules.get(key)!r} != contest config {cfg.get(key)!r}")
    for sid in rules.get("source_ids", []):
        if sid not in source_ids:
            rep.fail("competition.rules_source", f"unregistered source {sid}")

    # Roster integrity: unique usernames; models known; variants resolvable;
    # every pool symbol eligible; eligibility equals captured >=150-session series.
    roster_rows = roster["participants"]
    usernames = [r["username"] for r in roster_rows]
    if len(usernames) != len(set(usernames)):
        rep.fail("competition.roster", "duplicate usernames in roster")
    if roster["_meta"].get("participant_count") != len(roster_rows):
        rep.fail("competition.roster_count", "roster _meta participant_count mismatch")
    known_models = {"C1", "C2", "C3", "C4", "C5", "S1", "S2", "S3"}
    sys.path.insert(0, ROOT)
    from intel.contrarian import resolve_params  # noqa: E402
    for row in roster_rows:
        if row["model"] not in known_models:
            rep.fail("competition.roster_model", f"{row['username']}: unknown model {row['model']}")
            continue
        try:
            resolve_params(row["model"], row.get("variant"))
        except ValueError as exc:
            rep.fail("competition.roster_variant", f"{row['username']}: {exc}")
        if not row.get("pool"):
            rep.fail("competition.roster_pool", f"{row['username']}: empty pool")
        for sym in row["pool"]:
            if sym not in meta["eligible_symbols"]:
                rep.fail("competition.roster_pool", f"{row['username']}: pool symbol {sym} not eligible")

    master_symbols = {e["symbol"] for e in master["entries"]}
    market_idx = load("data/market_history_index.json")
    rederived_eligible = sorted(
        c["tradingview_symbol"] for c in market_idx["captures"]
        if c.get("status") == "captured" and c.get("sessions_valid", 0) >= 150
    )
    if sorted(meta["eligible_symbols"]) != rederived_eligible:
        rep.fail("competition.eligible", "eligible_symbols != captured series with >=150 sessions")
    if any(s not in master_symbols for s in meta["eligible_symbols"]):
        rep.fail("competition.eligible_master", "an eligible symbol is not on the master list")

    edition_rows = doc["editions"]
    if meta["season_editions"] != len(edition_rows):
        rep.fail("competition.edition_count", "_meta.season_editions != len(editions)")
    edition_ids = [e["edition_id"] for e in edition_rows]
    if edition_ids != [f"E{n:02d}" for n in range(1, len(edition_rows) + 1)]:
        rep.fail("competition.edition_ids", "edition ids must be contiguous E01..Enn")
    balance = cfg["starting_balance_virtual_usd"]

    def check_rows(rows: list, label: str) -> None:
        seen = set()
        keys = [(-r["realized_pnl_usd"], r["username"]) for r in rows]
        if keys != sorted(keys):
            rep.fail("competition.sort", f"{label}: rows not sorted by realized P/L desc, username asc")
        for i, r in enumerate(rows, 1):
            if r.get("rank") != i:
                rep.fail("competition.ranks", f"{label}: rank {r.get('rank')} != {i}")
            if r["username"] in seen:
                rep.fail("competition.dupe_user", f"{label}: {r['username']} appears twice")
            seen.add(r["username"])
            if not approx(1.0 + r["realized_pnl_usd"] / balance, r["equity_multiple"], 5e-5):
                rep.fail("competition.math", f"{label} {r['username']}: multiple != 1+pnl/{balance:,.0f}")
            expected_buckets = [m for m in (5.0, 10.0, 20.0, 50.0, 100.0) if r["equity_multiple"] >= m]
            if r["multiple_buckets"] != expected_buckets:
                rep.fail("competition.buckets", f"{label} {r['username']}: bucket list wrong")
            if r["meets_min_active_days"] != (r["active_days"] >= cfg["minimum_active_days"]):
                rep.fail("competition.active_days", f"{label} {r['username']}: min-active-days flag wrong")

    all_usernames = set(usernames)
    for ed in edition_rows:
        check_rows(ed["rows"], ed["edition_id"])
        if set(r["username"] for r in ed["rows"]) != all_usernames:
            rep.fail("competition.edition_roster", f"{ed['edition_id']}: rows do not cover the roster exactly")
        top = ed["rows"][0]
        if ed["leader"]["username"] != top["username"] or not approx(
                ed["leader"]["realized_pnl_usd"], top["realized_pnl_usd"], 0.005):
            rep.fail("competition.leader", f"{ed['edition_id']}: leader != first row")
    check_rows(doc["latest_edition"]["rows"], "LATEST")
    if doc["latest_edition"]["edition_id"] != "LATEST":
        rep.fail("competition.latest_id", "latest edition id must be LATEST")
    if doc["latest_edition"]["start_date"] <= edition_rows[-1]["start_date"] and \
            doc["latest_edition"]["end_date"] == edition_rows[-1]["end_date"]:
        rep.warn("competition.latest_overlap: LATEST coincides with the final season edition window")
    if {a["username"] for a in doc["participants"]} != all_usernames:
        rep.fail("competition.participants_roster", "participant aggregates do not cover the roster exactly")

    # Aggregates must re-derive from the edition rows.
    model_by_user = {r["username"]: r["model"] for r in roster_rows}
    participants_by_user = {a["username"]: a for a in doc["participants"]}
    for agg in doc["participants"]:
        per = []
        ok = True
        for ed in edition_rows:
            row = next((r for r in ed["rows"] if r["username"] == agg["username"]), None)
            if row is None:
                rep.fail("competition.aggregates",
                         f"{agg['username']}: missing from {ed['edition_id']} rows")
                ok = False
                break
            per.append(row)
        if not ok:
            continue
        checks = (
            ("editions_played", len(per)),
            ("ruined_editions", sum(1 for r in per if r["ruined"])),
            ("negative_editions", sum(1 for r in per if r["equity_multiple"] < 0)),
            ("editions_ge_5x", sum(1 for r in per if r["equity_multiple"] >= 5)),
            ("editions_ge_10x", sum(1 for r in per if r["equity_multiple"] >= 10)),
            ("editions_ge_20x", sum(1 for r in per if r["equity_multiple"] >= 20)),
            ("editions_ge_50x", sum(1 for r in per if r["equity_multiple"] >= 50)),
            ("editions_ge_100x", sum(1 for r in per if r["equity_multiple"] >= 100)),
            ("total_trades", sum(r["trades"] for r in per)),
            ("total_add_tranches", sum(r["add_tranches"] for r in per)),
            ("editions_meeting_min_active_days",
             sum(1 for r in per if r["meets_min_active_days"])),
        )
        for key, expected in checks:
            if agg.get(key) != expected:
                rep.fail("competition.aggregates", f"{agg['username']}: {key} {agg.get(key)} != {expected}")
        if not approx(agg["season_realized_pnl_usd"], round(sum(r["realized_pnl_usd"] for r in per), 2), 0.011):
            rep.fail("competition.aggregates", f"{agg['username']}: season P/L mismatch")
        product = 1.0
        for r in per:
            product *= max(r["equity_multiple"], 0.0)
        if not approx(agg["season_multiple"], round(product, 6), 1e-4):
            rep.fail("competition.aggregates", f"{agg['username']}: season multiple mismatch")
        if agg["best_edition_multiple"] != round(max(r["equity_multiple"] for r in per), 6):
            rep.fail("competition.aggregates", f"{agg['username']}: best edition multiple mismatch")

    lb = doc["leaderboard"]
    lb_keys = [(-r["season_realized_pnl_usd"], r["username"]) for r in lb]
    if lb_keys != sorted(lb_keys):
        rep.fail("competition.sort", "leaderboard not sorted by season P/L desc, username asc")
    if [r["season_rank"] for r in lb] != list(range(1, len(lb) + 1)):
        rep.fail("competition.ranks", "season ranks not contiguous from 1")
    if {r["username"] for r in lb} != all_usernames:
        rep.fail("competition.leaderboard_roster", "leaderboard usernames != roster")
    for row in lb:
        agg = participants_by_user.get(row["username"])
        if agg is None:
            continue  # the set-equality check above already fired
        if row["season_realized_pnl_usd"] != agg["season_realized_pnl_usd"]:
            rep.fail("competition.leaderboard_math", f"{row['username']}: leaderboard P/L != participant aggregate")
        if row["season_rank"] != agg["season_rank"]:
            rep.fail("competition.leaderboard_math", f"{row['username']}: rank mismatch")

    # Target summary re-derivation.
    pe = [r for ed in edition_rows for r in ed["rows"]]
    ts = doc["target_summary"]
    if ts["participant_editions"] != len(pe):
        rep.fail("competition.target_summary", "participant_editions count mismatch")
    for mult, key in ((5, "ge_5x"), (10, "ge_10x"), (20, "ge_20x"), (50, "ge_50x"), (100, "ge_100x")):
        if ts[key] != sum(1 for r in pe if r["equity_multiple"] >= mult):
            rep.fail("competition.target_summary", f"{key} count mismatch")
    if ts["ruined_participant_editions"] != sum(1 for r in pe if r["ruined"]):
        rep.fail("competition.target_summary", "ruined count mismatch")

    # Kind contrast re-derivation.
    for kind_key in ("contrarian", "baseline"):
        block = doc["kind_contrast"][kind_key]
        kinds = {"contrarian": {"C1", "C2", "C3", "C4", "C5"}, "baseline": {"S1", "S2", "S3"}}[kind_key]
        subset = [a for a in doc["participants"]
                  if model_by_user.get(a["username"]) in kinds]
        if block["participants"] != len(subset):
            rep.fail("competition.kind_contrast", f"{kind_key}: participant count mismatch")
        if subset and block["best_single_edition_multiple"] != round(
                max(a["best_edition_multiple"] for a in subset), 6):
            rep.fail("competition.kind_contrast", f"{kind_key}: best single edition multiple mismatch")

    # No shell-corruption artifacts may leak into any published text. Text that
    # deliberately documents the IR-26 corruption event quotes the signatures;
    # a match is allowed only when an explicit documentation marker precedes it.
    corruption_re = re.compile(r"/bin/bash\.00|\(\.5M\b")
    doc_markers = ("became", "→", "->", "expanded", "signature", "signatures",
                   "leaked_shell_text", "IR-26", "restored")

    def has_undocumented_signature(text: str) -> bool:
        for m in corruption_re.finditer(text):
            window = text[max(0, m.start() - 200):m.start()]
            if not any(marker in window for marker in doc_markers):
                return True
        return False

    leak_paths = ["README.md", "index.html",
                  "research/hypotheses/hypotheses.json", "research/irregularities.json"]
    for rel in leak_paths:
        text = read(rel)
        if has_undocumented_signature(text):
            rep.fail("leaked_shell_text", f"{rel} contains shell-expanded corruption ($0/$2 artifacts)")
    for label, payload in (("data/competition_results.json", doc),
                           ("data/competition/roster.json", roster)):
        text = json.dumps(payload)
        if has_undocumented_signature(text):
            rep.fail("leaked_shell_text", f"{label} contains shell-expanded corruption ($0/$2 artifacts)")

    # Deterministic re-run from the raw captures must reproduce the artifact exactly.
    stamp = meta["generated_utc"]
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "run_competition.py"),
             "--stamp", stamp, "--out-dir", tmp],
            capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            rep.fail("competition.rerun", f"engine re-run failed: {proc.stderr[-400:]}")
        else:
            fresh_path = os.path.join(tmp, "competition_results.json")
            with open(fresh_path, encoding="utf-8") as fh_:
                fresh = json.load(fh_)
            if fresh != doc:
                rep.fail("competition.determinism",
                         "committed artifact differs from a deterministic re-run from the raw captures")
    champions = doc["leaderboard"][:3]
    rep.ok("shadow competition re-derived from raw captures: "
           + ", ".join(f"#{c['season_rank']} {c['username']}" for c in champions))


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
# Intraday captures + study, volatile-stock division, executive summary and
# the TradingView export benchmark.
#
# Every check below re-derives its numbers from the artifacts on disk (or, for
# the four builders, by re-running the builder at its pinned stamp and requiring
# field-for-field equality). Nothing here trusts a stored aggregate by itself.
# ---------------------------------------------------------------------------
INTRADAY_INTERVALS = ("15m", "1h", "1d")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def load_opt(rel: str):
    """Load an artifact, or return None when the pipeline has not produced it yet.

    A missing artifact is a warning (the capture workflow may still be running), never a
    silent pass: the caller records which check was skipped and why.
    """
    try:
        return load(rel)
    except FileNotFoundError:
        return None


def median_of(values) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    mid = len(vals) // 2
    return float(vals[mid]) if len(vals) % 2 else float((vals[mid - 1] + vals[mid]) / 2)


def _reproduce(rep: Report, check: str, script: str, rel: str, extra: tuple = ()) -> dict | None:
    """Re-run a deterministic builder at its stored stamp and require identical content."""
    import subprocess
    import tempfile

    stored = load_opt(rel)
    if stored is None:
        rep.warn(f"{check}: {rel} not present yet - run scripts/{script} once its inputs exist")
        return None
    stamp = (stored.get("_meta") or {}).get("generated_utc")
    if not stamp or stamp == "unknown":
        rep.fail(f"{check}.stamp",
                 f"{rel}: _meta.generated_utc is {stamp!r}; a pinned deterministic stamp is required")
        return stored
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "reproduced.json")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", script), "--out", out,
             "--stamp", stamp, *extra],
            cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            rep.fail(f"{check}.rerun",
                     f"scripts/{script} exited {proc.returncode}: "
                     f"{(proc.stdout + proc.stderr).strip()[-400:]}")
            return stored
        with open(out, encoding="utf-8") as fh:
            fresh = json.load(fh)
    if fresh != stored:
        rep.fail(f"{check}.determinism",
                 f"{rel} is not reproduced field-for-field by scripts/{script} at stamp {stamp}")
    else:
        rep.ok(f"{rel} reproduced field-for-field by scripts/{script} at stamp {stamp}")
    return stored


def _volatile_pool_symbols() -> set:
    vs = load("data/volatile_stocks.json")
    return {r["symbol"] for r in vs["records"]}


def check_intraday(rep: Report, source_ids: dict) -> None:
    """Audit the intraday capture index, the stored capture files, and the study derived from them.

    Re-hashes every capture file, re-validates every bar through the same loader the study
    uses, re-derives the declared first/last timestamps, re-counts the status tallies, and
    (for the study) re-derives every aggregate from the bucket rows and the per-symbol rows.
    """
    import hashlib
    sys.path.insert(0, ROOT)
    from intel import intraday as intraday_mod

    pool = _volatile_pool_symbols()
    idx = load_opt("data/intraday_index.json")
    meta = (idx or {}).get("_meta", {})
    caps = (idx or {}).get("captures", [])
    captured: list[dict] = []

    if idx is None:
        rep.warn("intraday.index: data/intraday_index.json not present yet "
                 "(the capture-intraday workflow has not committed a capture) - "
                 "intraday capture, study and stock-division checks skipped")
    else:
        if meta.get("kind") != "intraday_capture_index":
            rep.fail("intraday.kind", f"unexpected _meta.kind {meta.get('kind')!r}")
        if meta.get("script") != "scripts/fetch_intraday.py":
            rep.fail("intraday.script", f"unexpected _meta.script {meta.get('script')!r}")
        sid = meta.get("vendor_source_id") or meta.get("source_id")
        if sid is None:
            rep.warn("intraday.source: the index does not declare vendor_source_id "
                     "(capture written by a build older than the field) - skipped")
        elif sid not in source_ids:
            rep.fail("intraday.source", f"index cites unregistered source {sid!r}")
        else:
            rep.ok(f"intraday index cites registered market-data-vendor source {sid}")

        seen: set = set()
        failed = deferred = 0
        for record in caps:
            symbol = record.get("symbol")
            interval = record.get("interval")
            status = record.get("status")
            if (symbol, interval) in seen:
                rep.fail("intraday.duplicate", f"duplicate capture record {symbol}[{interval}]")
            seen.add((symbol, interval))
            if interval not in INTRADAY_INTERVALS:
                rep.fail("intraday.interval", f"{symbol}: unknown interval {interval!r}")
            if record.get("kind") == "equity" and symbol not in pool:
                rep.fail("intraday.symbol",
                         f"{symbol}: equity capture is not a member of the 20-stock volatile pool")
            if status in ("failed", "not_attempted"):
                failed += status == "failed"
                deferred += status == "not_attempted"
                if not record.get("error"):
                    rep.fail("intraday.failure_reason",
                             f"{symbol}[{interval}]: {status} record carries no error text")
                continue
            if status != "captured":
                rep.fail("intraday.status", f"{symbol}[{interval}]: unknown status {status!r}")
                continue
            captured.append(record)

            rel = str(record.get("file", ""))
            if not rel.startswith("data/intraday/"):
                rep.fail("intraday.capture_file",
                         f"{symbol}[{interval}]: file {rel!r} is outside data/intraday/")
                continue
            path = os.path.join(ROOT, rel)
            if not os.path.exists(path):
                rep.fail("intraday.capture_file", f"{symbol}[{interval}]: declared file missing: {rel}")
                continue
            with open(path, "rb") as fh:
                payload = fh.read()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != record.get("stored_sha256"):
                rep.fail("intraday.sha256",
                         f"{symbol}[{interval}]: file SHA-256 {digest[:16]}... != index "
                         f"{str(record.get('stored_sha256'))[:16]}...")
                continue
            if record.get("stored_bytes") != len(payload):
                rep.fail("intraday.bytes",
                         f"{symbol}[{interval}]: stored_bytes {record.get('stored_bytes')} != "
                         f"file length {len(payload)}")
            if record.get("vendor_data_granularity") != interval:
                rep.warn(f"intraday.granularity: {symbol}[{interval}]: vendor reported "
                         f"{record.get('vendor_data_granularity')!r}")
            try:
                capture = intraday_mod.load_capture(record)
            except intraday_mod.IntradayError as exc:
                rep.fail("intraday.capture", f"{symbol}[{interval}]: {exc}")
                continue
            # Independent re-derivation of the declared first/last stamps and the plan tally.
            first_iso = datetime.fromtimestamp(capture.bars[0].ts, tz=timezone.utc).isoformat()
            last_iso = datetime.fromtimestamp(capture.bars[-1].ts, tz=timezone.utc).isoformat()
            if parse_utc(record.get("first_utc", "")) != parse_utc(first_iso):
                rep.fail("intraday.timestamps",
                         f"{symbol}[{interval}]: first_utc {record.get('first_utc')!r} != "
                         f"first bar {first_iso!r}")
            if parse_utc(record.get("last_utc", "")) != parse_utc(last_iso):
                rep.fail("intraday.timestamps",
                         f"{symbol}[{interval}]: last_utc {record.get('last_utc')!r} != "
                         f"last bar {last_iso!r}")
            chunks = record.get("chunk_provenance") or []
            if record.get("chunks") != len(chunks):
                rep.fail("intraday.chunks",
                         f"{symbol}[{interval}]: chunks {record.get('chunks')} != "
                         f"{len(chunks)} chunk records")
            total_bytes = 0
            for chunk in chunks:
                if not HEX64.match(str(chunk.get("raw_response_sha256", ""))):
                    rep.fail("intraday.chunk_sha",
                             f"{symbol}[{interval}]: chunk digest "
                             f"{chunk.get('raw_response_sha256')!r} is not a SHA-256")
                if not str(chunk.get("endpoint", "")).startswith("https://"):
                    rep.fail("intraday.chunk_endpoint",
                             f"{symbol}[{interval}]: chunk endpoint {chunk.get('endpoint')!r} is not https")
                nb = chunk.get("raw_response_bytes")
                if not isinstance(nb, int) or nb <= 0:
                    rep.fail("intraday.chunk_bytes",
                             f"{symbol}[{interval}]: chunk raw_response_bytes {nb!r}")
                else:
                    total_bytes += nb
            if record.get("raw_response_bytes_total") != total_bytes:
                rep.fail("intraday.chunk_bytes",
                         f"{symbol}[{interval}]: raw_response_bytes_total "
                         f"{record.get('raw_response_bytes_total')} != {total_bytes}")
        rep.ok(f"intraday index: {len(captured)} captures re-hashed, re-validated and re-counted")

        by_interval: dict = {}
        for record in captured:
            by_interval[record["interval"]] = by_interval.get(record["interval"], 0) + 1
        if meta.get("captured_count") != len(captured):
            rep.fail("intraday.counts",
                     f"_meta.captured_count {meta.get('captured_count')} != {len(captured)} captured records")
        if meta.get("failed_count") != failed:
            rep.fail("intraday.counts", f"_meta.failed_count {meta.get('failed_count')} != {failed}")
        if meta.get("not_attempted_count") != deferred:
            rep.fail("intraday.counts",
                     f"_meta.not_attempted_count {meta.get('not_attempted_count')} != {deferred}")
        if meta.get("symbol_count") != len(caps):
            rep.fail("intraday.counts", f"_meta.symbol_count {meta.get('symbol_count')} != {len(caps)}")
        stored_by_iv = dict(meta.get("captured_by_interval") or {})
        if stored_by_iv != by_interval:
            rep.fail("intraday.counts",
                     f"_meta.captured_by_interval {stored_by_iv} != re-counted {by_interval}")
        unpaid = [s for s in (meta.get("equity_symbols") or []) if s not in pool]
        if unpaid:
            rep.fail("intraday.plan", f"index equity_symbols not in the volatile pool: {unpaid}")
        if len(set(meta.get("equity_symbols") or [])) != len(meta.get("equity_symbols") or []):
            rep.fail("intraday.plan", "index equity_symbols contains duplicates")
        missing_pool = sorted(s for s in pool if s not in set(meta.get("equity_symbols") or []))
        if missing_pool:
            rep.fail("intraday.plan", f"volatile pool symbols absent from the capture plan: {missing_pool}")

    # ---- the study derived from those captures -------------------------------
    study = _reproduce(rep, "intraday.study", "run_intraday_study.py", "data/intraday_study.json")
    if study is None:
        return
    smeta = study.get("_meta", {})
    if smeta.get("kind") != "intraday_study":
        rep.fail("intraday.study_kind", f"unexpected _meta.kind {smeta.get('kind')!r}")
    if smeta.get("engine") != "intraday-study-1":
        rep.fail("intraday.study_engine", f"unexpected _meta.engine {smeta.get('engine')!r}")
    if smeta.get("not_a_forecast") is not True:
        rep.fail("intraday.study_honesty", "study must declare not_a_forecast: true")
    if not smeta.get("methodology") or not smeta.get("assumptions"):
        rep.fail("intraday.study_method", "study must record its methodology and assumptions")

    coverage = study.get("coverage") or []
    by_key = {(row.get("symbol"), row.get("interval")): row for row in coverage}
    for record in captured:
        if record["interval"] == "1d":
            continue  # the study measures intraday series only
        key = (record["symbol"], record["interval"])
        row = by_key.get(key)
        if row is None:
            rep.fail("intraday.study_coverage",
                     f"{key[0]}[{key[1]}] is captured but missing from the study coverage")
            continue
        if row.get("bars") != record.get("bar_count") or row.get("stored_sha256") != record.get("stored_sha256"):
            rep.fail("intraday.study_coverage",
                     f"{key[0]}[{key[1]}]: coverage (bars={row.get('bars')}, sha={str(row.get('stored_sha256'))[:12]}...) "
                     f"does not match the index (bars={record.get('bar_count')}, "
                     f"sha={str(record.get('stored_sha256'))[:12]}...)")

    buckets = (study.get("gap_fill") or {}).get("buckets") or []
    per_symbol = (study.get("gap_fill") or {}).get("per_symbol") or []
    aggregate = (study.get("gap_fill") or {}).get("aggregate_by_kind") or {}
    for kind, arow in aggregate.items():
        rows = [b for b in buckets if b.get("kind") == kind]
        sessions = sum(b["sessions"] for b in rows)
        if sessions != arow.get("sessions_with_gap"):
            rep.fail("intraday.study_aggregate",
                     f"{kind}: bucket sessions {sessions} != sessions_with_gap {arow.get('sessions_with_gap')}")
            continue
        ge1 = [b for b in rows if b.get("bucket") in ("1.0_2.0_atr", "ge_2.0_atr")]
        ge1_sessions = sum(b["sessions"] for b in ge1)
        if ge1_sessions != arow.get("sessions_with_gap_ge_1_atr"):
            rep.fail("intraday.study_aggregate",
                     f"{kind}: >=1 ATR bucket sessions {ge1_sessions} != "
                     f"{arow.get('sessions_with_gap_ge_1_atr')}")
        weighted = sum(b["sessions"] * b["fill_rate"] for b in rows) / sessions if sessions else None
        if weighted is None or not approx(weighted, arow.get("fill_rate_all", -1), 5e-6):
            rep.fail("intraday.study_aggregate",
                     f"{kind}: sessions-weighted bucket fill rate {weighted} != fill_rate_all "
                     f"{arow.get('fill_rate_all')}")
        if ge1_sessions:
            weighted_ge1 = sum(b["sessions"] * b["fill_rate"] for b in ge1) / ge1_sessions
            if not approx(weighted_ge1, arow.get("fill_rate_ge_1_atr", -1), 5e-6):
                rep.fail("intraday.study_aggregate",
                         f"{kind}: weighted >=1 ATR fill rate {weighted_ge1} != "
                         f"{arow.get('fill_rate_ge_1_atr')}")
        # Every session after the first must be accounted for: either it produced a gap row or
        # it was skipped for a reason the study publishes (no ATR baseline yet / opened exactly
        # at the prior close). Not "sessions - 1", which silently assumes every session has an
        # ATR value and a non-zero gap.
        kind_rows = [r for r in per_symbol if r.get("kind") == kind]
        analysed = sum(r.get("gaps_analyzed", 0) for r in kind_rows)
        candidates = sum(r.get("gap_candidates", 0) for r in kind_rows)
        skipped = sum(r.get("gaps_skipped_no_atr", 0) + r.get("gaps_skipped_zero_gap", 0)
                      for r in kind_rows)
        if analysed + skipped != candidates:
            rep.fail("intraday.study_aggregate",
                     f"{kind}: gap accounting does not close: {analysed} analysed + {skipped} "
                     f"skipped != {candidates} sessions after the first")
        elif analysed != sessions:
            rep.fail("intraday.study_aggregate",
                     f"{kind}: per-symbol rows hold {analysed} gaps but the bucket rows hold {sessions}")
        symbol_sessions = sum(r.get("sessions", 0) for r in kind_rows)
        if candidates != symbol_sessions - len(kind_rows):
            rep.fail("intraday.study_aggregate",
                     f"{kind}: {candidates} gap candidates for {symbol_sessions} sessions over "
                     f"{len(kind_rows)} series (expected sessions-1 per series)")
    for row in (study.get("execution_latency") or {}).get("by_kind_interval") or []:
        for name, summary in row.items():
            if not isinstance(summary, dict):
                continue
            if summary.get("observations") == 0:
                continue
            if summary.get("median_abs_bps") is None or summary.get("median_abs_bps") < 0:
                rep.fail("intraday.study_latency",
                         f"{row.get('kind')}[{row.get('interval')}].{name}: median_abs_bps "
                         f"{summary.get('median_abs_bps')!r}")
            if summary.get("mean_signed_bps") is None:
                rep.fail("intraday.study_latency",
                         f"{row.get('kind')}[{row.get('interval')}].{name}: mean_signed_bps missing")
    diag = study.get("calendar_diagnostics") or {}
    cal_identity = (diag.get("calendar") or {}).get("version")
    from intel import calendar as calendar_mod
    if cal_identity != calendar_mod.CALENDAR_VERSION:
        rep.fail("intraday.study_calendar",
                 f"calendar_diagnostics version {cal_identity!r} != "
                 f"intel.calendar {calendar_mod.CALENDAR_VERSION!r}")
    per_series = diag.get("per_series") or []
    studied_keys = {(r["symbol"], r["interval"]) for r in captured if r["interval"] != "1d"}
    diag_keys = {(r.get("symbol"), r.get("interval")) for r in per_series}
    if diag_keys != studied_keys:
        rep.fail("intraday.study_calendar",
                 f"calendar per_series keys {sorted(diag_keys)} != studied captures "
                 f"{sorted(studied_keys)}")
    for label, key in (("sessions_on_full_closure", "sessions_on_full_closure_total"),
                       ("boundaries_spanning_closure", "boundaries_spanning_closure_total"),
                       ("gaps_spanning_closure", "gaps_spanning_closure_total")):
        want = sum(r.get(label, 0) for r in per_series)
        if diag.get(key) != want:
            rep.fail("intraday.study_calendar",
                     f"calendar_diagnostics.{key} {diag.get(key)} != sum of per_series {want}")
    for record in captured:
        if record["interval"] == "1d":
            continue
        row = next((r for r in per_series
                    if (r.get("symbol"), r.get("interval")) == (record["symbol"], record["interval"])), None)
        if row is None:
            continue
        if record.get("kind", "equity") != "equity":
            if row.get("calendar_applies") is not False:
                rep.fail("intraday.study_calendar",
                         f"{record['symbol']}[{record['interval']}]: non-equity series must carry "
                         "calendar_applies=false (no CME calendar is encoded)")
            continue
        if row.get("calendar_applies") is not True:
            rep.fail("intraday.study_calendar",
                     f"{record['symbol']}[{record['interval']}]: equity series must be annotated")
            continue
        try:
            cap = intraday_mod.load_capture(record)
        except intraday_mod.IntradayError as exc:
            rep.fail("intraday.study_calendar",
                     f"{record['symbol']}[{record['interval']}]: reload failed: {exc}")
            continue
        annotated = intraday_mod.sessions_calendar_aware(cap.bars)
        want_on = sorted(s["date"] for s in annotated if s["is_full_closure"])
        if row.get("session_dates_on_full_closure") != want_on:
            rep.fail("intraday.study_calendar",
                     f"{record['symbol']}[{record['interval']}]: sessions on full closure "
                     f"{row.get('session_dates_on_full_closure')} != re-derived {want_on}")
        want_spanned = sum(1 for s in annotated[1:] if s["closures_spanned"])
        if row.get("boundaries_spanning_closure") != want_spanned:
            rep.fail("intraday.study_calendar",
                     f"{record['symbol']}[{record['interval']}]: boundaries_spanning_closure "
                     f"{row.get('boundaries_spanning_closure')} != re-derived {want_spanned}")
    window = diag.get("studied_window") or {}
    if diag.get("equity_series_annotated"):
        want_window = calendar_mod.full_closures_between(window.get("start"), window.get("end"))
        if diag.get("full_closures_in_window") != want_window:
            rep.fail("intraday.study_calendar",
                     "full_closures_in_window does not match intel.calendar over the studied window")
    elif diag.get("full_closures_in_window"):
        rep.fail("intraday.study_calendar",
                 "no equity series studied but full_closures_in_window is non-empty")
    rep.ok(f"intraday study: {len(coverage)} series, {len(buckets)} bucket rows and "
           f"{len(aggregate)} kind aggregates re-derived from the capture index")


def check_stock_competition(rep: Report, source_ids: dict) -> None:
    """Audit the volatile-stock division against its roster and the rule profiles.

    The artifact is re-generated at its own stamp and required to match; the roster join,
    the pool membership and the leaderboard ordering are then re-checked independently.
    """
    doc = _reproduce(rep, "stock_competition", "run_stock_competition.py",
                     "data/stock_competition_results.json")
    if doc is None:
        return
    sys.path.insert(0, ROOT)
    from intel.competition import RULE_PROFILES

    meta = doc.get("_meta", {})
    if meta.get("kind") != "own_stock_competition_simulation":
        rep.fail("stock_competition.kind", f"unexpected _meta.kind {meta.get('kind')!r}")
    if meta.get("engine") != "intel-competition-3":
        rep.fail("stock_competition.engine", f"unexpected _meta.engine {meta.get('engine')!r}")
    if meta.get("not_a_forecast") is not True:
        rep.fail("stock_competition.honesty", "artifact must declare not_a_forecast: true")
    for sid in meta.get("source_ids", []):
        if sid not in source_ids:
            rep.fail("stock_competition.source", f"unregistered source {sid}")
    for profile_name in (meta.get("primary_profile"), meta.get("counterfactual_profile")):
        if profile_name and profile_name not in RULE_PROFILES:
            rep.fail("stock_competition.profile", f"unknown rule profile {profile_name!r}")

    roster = load("data/competition/stock_roster.json")
    usernames = {p["username"] for p in roster["participants"]}
    pool = _volatile_pool_symbols()
    for p in roster["participants"]:
        bad = sorted(set(p["pool"]) - pool)
        if bad:
            rep.fail("stock_competition.pool", f"{p['username']}: pool symbols outside the volatile pool: {bad}")
    for sid in roster["_meta"].get("price_source_ids", []):
        if sid not in source_ids:
            rep.fail("stock_competition.source", f"roster cites unregistered source {sid}")

    covered: set = set()
    for name, division in (doc.get("divisions") or {}).items():
        leaderboard = division.get("leaderboard")
        if not leaderboard:
            continue
        ranks = [row["season_rank"] for row in leaderboard]
        if ranks != list(range(1, len(leaderboard) + 1)):
            rep.fail("stock_competition.ranks", f"{name}: season_rank is not 1..{len(leaderboard)}")
        pnls = [row["season_realized_pnl_usd"] for row in leaderboard]
        if pnls != sorted(pnls, reverse=True):
            rep.fail("stock_competition.sort", f"{name}: leaderboard is not sorted by season P/L")
        for row in leaderboard:
            if row["username"] not in usernames:
                rep.fail("stock_competition.roster", f"{name}: {row['username']} is not on the roster")
            covered.add(row["username"])
            if row.get("best_edition_multiple") is not None and row.get("median_edition_multiple") is not None:
                if row["best_edition_multiple"] + 1e-9 < row["median_edition_multiple"]:
                    rep.fail("stock_competition.multiple",
                             f"{name}/{row['username']}: best edition multiple below the median")
        # Re-derive every season aggregate from the per-edition rows.
        editions = division.get("editions") or []
        per_user: dict[str, list[dict]] = {}
        all_rows: list[dict] = []
        for edition in editions:
            for row in edition.get("rows") or []:
                per_user.setdefault(row["username"], []).append(row)
                all_rows.append(row)
        targets = division.get("target_summary") or {}
        checks = {
            "participant_editions": len(all_rows),
            "ge_1.1x": sum(1 for r in all_rows if r["equity_multiple"] >= 1.1),
            "ge_2x": sum(1 for r in all_rows if r["equity_multiple"] >= 2),
            "ge_5x": sum(1 for r in all_rows if r["equity_multiple"] >= 5),
            "ge_10x": sum(1 for r in all_rows if r["equity_multiple"] >= 10),
            "ge_20x": sum(1 for r in all_rows if r["equity_multiple"] >= 20),
            "ge_50x": sum(1 for r in all_rows if r["equity_multiple"] >= 50),
            "ge_100x": sum(1 for r in all_rows if r["equity_multiple"] >= 100),
            "ruined_participant_editions": sum(1 for r in all_rows if r["ruined"]),
            "mean_equity_multiple": (round(statistics.fmean(
                r["equity_multiple"] for r in all_rows), 6) if all_rows else None),
            "median_equity_multiple": (round(statistics.median(
                r["equity_multiple"] for r in all_rows), 6) if all_rows else None),
        }
        for key, want in checks.items():
            if key in targets and targets[key] != want:
                rep.fail("stock_competition.aggregates",
                         f"{name}: target_summary.{key} {targets[key]!r} != re-derived {want!r}")
        for row in division.get("leaderboard") or []:
            per = per_user.get(row["username"], [])
            want_pnl = round(sum(r["realized_pnl_usd"] for r in per), 2)
            if not approx(row["season_realized_pnl_usd"], want_pnl, 0.011):
                rep.fail("stock_competition.aggregates",
                         f"{name}/{row['username']}: season P/L {row['season_realized_pnl_usd']} != "
                         f"re-derived {want_pnl}")
            product = 1.0
            for r in per:
                product *= max(r["equity_multiple"], 0.0)
            if not approx(row["season_multiple"], round(product, 6), 1e-9):
                rep.fail("stock_competition.aggregates",
                         f"{name}/{row['username']}: season_multiple {row['season_multiple']} != "
                         f"re-derived {round(product, 6)}")
            want_best = round(max(r["equity_multiple"] for r in per), 6)
            if not approx(row["best_edition_multiple"], want_best, 1e-9):
                rep.fail("stock_competition.aggregates",
                         f"{name}/{row['username']}: best_edition_multiple "
                         f"{row['best_edition_multiple']} != re-derived {want_best}")
            if row["editions_ge_2x"] != sum(1 for r in per if r["equity_multiple"] >= 2):
                rep.fail("stock_competition.aggregates",
                         f"{name}/{row['username']}: editions_ge_2x {row['editions_ge_2x']} != "
                         f"re-derived count")
        # The rule-profile constants must mirror the engine's own definition.
        for key, want in (("starting_balance", RULE_PROFILES[division.get("profile", "")].starting_balance
                           if division.get("profile") in RULE_PROFILES else None),
                          ("leverage", RULE_PROFILES[division.get("profile", "")].leverage
                           if division.get("profile") in RULE_PROFILES else None)):
            if want is None:
                continue
            got = (doc.get("_meta", {}).get("profiles", {})
                   .get(division.get("profile"), {}).get(key))
            if got is not None and not approx(got, want, 1e-9):
                rep.fail("stock_competition.profile",
                         f"{name}: _meta.profiles.{division.get('profile')}.{key} {got} != engine {want}")
    for name, division in (doc.get("divisions") or {}).items():
        if not division.get("leaderboard"):
            continue
        fwd = division.get("forward_held_out") or {}
        editions = division.get("editions") or []
        held_n = fwd.get("held_out_editions", 0) or 0
        fwd_lb = fwd.get("forward_leaderboard")
        in_lb = fwd.get("in_sample_leaderboard")
        if (fwd_lb is None) != (in_lb is None):
            rep.fail("stock_competition.forward",
                     f"{name}: in-sample and forward leaderboards must both be present or both null")
            continue
        if fwd_lb is None:
            if held_n == 0:
                rep.ok(f"{name}: forward held-out disabled (held_out_editions=0)")
            elif held_n >= len(editions):
                rep.ok(f"{name}: forward window correctly null ({held_n} held out of "
                       f"{len(editions)} editions)")
            else:
                rep.fail("stock_competition.forward",
                         f"{name}: {held_n} editions held out of {len(editions)} but no forward "
                         "leaderboard stored")
            continue
        window = fwd.get("held_out_window") or {}
        if window.get("start_date") != editions[-held_n]["start_date"] or \
                window.get("end_date") != editions[-1]["end_date"]:
            rep.fail("stock_competition.forward",
                     f"{name}: held_out_window {window} != trailing {held_n} season editions")
        if fwd.get("in_sample_editions") != len(editions) - held_n:
            rep.fail("stock_competition.forward",
                     f"{name}: in_sample_editions {fwd.get('in_sample_editions')} != "
                     f"{len(editions) - held_n}")
        for label, board, ed_slice in (("in_sample", in_lb, editions[:-held_n]),
                                       ("forward", fwd_lb, editions[-held_n:])):
            ranks = [row["season_rank"] for row in board]
            if ranks != list(range(1, len(board) + 1)):
                rep.fail("stock_competition.forward",
                         f"{name}/{label}: season_rank is not 1..{len(board)}")
            pnls = [row["season_realized_pnl_usd"] for row in board]
            if pnls != sorted(pnls, reverse=True):
                rep.fail("stock_competition.forward",
                         f"{name}/{label}: leaderboard is not sorted by season P/L")
            for row in board:
                if row["username"] not in usernames:
                    rep.fail("stock_competition.forward",
                             f"{name}/{label}: {row['username']} is not on the roster")
                    continue
                per = [r for ed in ed_slice for r in ed.get("rows", [])
                       if r["username"] == row["username"]]
                want_pnl = round(sum(r["realized_pnl_usd"] for r in per), 2)
                if not approx(row["season_realized_pnl_usd"], want_pnl, 0.011):
                    rep.fail("stock_competition.forward",
                             f"{name}/{label}/{row['username']}: season P/L "
                             f"{row['season_realized_pnl_usd']} != re-derived {want_pnl} from the "
                             f"{label} edition slice")
    # The counterfactual block must be flagged as a counterfactual wherever it is rendered.
    for name, div in (doc.get("counterfactual_20x") or {}).items():
        if div.get("is_counterfactual") is not True:
            rep.fail("stock_competition.counterfactual",
                     f"counterfactual_20x.{name} must declare is_counterfactual: true")
    bound = (doc.get("official_rule_bound") or {}).get("summary") or {}
    if bound:
        rows = (doc.get("official_rule_bound") or {}).get("editions") or []
        if bound.get("editions_evaluated") != len(rows):
            rep.fail("stock_competition.bound",
                     f"official_rule_bound.summary.editions_evaluated {bound.get('editions_evaluated')} "
                     f"!= {len(rows)} per-edition rows")
        worst = max((r["max_edition_multiple"] for r in rows), default=None)
        if worst is not None and not approx(bound.get("max_edition_multiple_observed_bound", -1), worst, 1e-9):
            rep.fail("stock_competition.bound",
                     f"official_rule_bound max multiple {bound.get('max_edition_multiple_observed_bound')} "
                     f"!= re-derived {worst}")
        if bound.get("single_hold_scenario_ge_5x") != any(r["max_edition_multiple"] >= 5 for r in rows):
            rep.fail("stock_competition.bound", "five_x_reachable disagrees with the per-edition bounds")
        if bound.get("single_hold_scenario_ge_10x") != any(r["max_edition_multiple"] >= 10 for r in rows):
            rep.fail("stock_competition.bound", "ten_x_reachable disagrees with the per-edition bounds")
    missing = sorted(usernames - covered)
    if missing and (doc.get("divisions") or {}):
        rep.warn(f"stock_competition.coverage: {len(missing)} roster usernames appear in no "
                 f"leaderboard: {missing[:6]}{'...' if len(missing) > 6 else ''}")
    rep.ok(f"stock competition: {len(covered)} usernames audited across "
           f"{len(doc.get('divisions') or {})} divisions")


def check_exec_summary(rep: Report, source_ids: dict) -> None:
    """Audit the executive-summary orders: reproduced, cross-checked against the competitions."""
    doc = _reproduce(rep, "exec_summary", "build_exec_summary.py", "data/exec_summary.json")
    if doc is None:
        return
    meta = doc.get("_meta", {})
    if meta.get("kind") != "executive_summary_recommendations":
        rep.fail("exec_summary.kind", f"unexpected _meta.kind {meta.get('kind')!r}")
    if meta.get("engine") != "exec-summary-1":
        rep.fail("exec_summary.engine", f"unexpected _meta.engine {meta.get('engine')!r}")
    if meta.get("not_a_forecast") is not True:
        rep.fail("exec_summary.honesty", "artifact must declare not_a_forecast: true")
    if not meta.get("honesty_note"):
        rep.fail("exec_summary.honesty", "artifact must carry the paper-trading honesty note")

    comp = load_opt("data/competition_results.json") or {}
    season_pnl = {}
    for row in (comp.get("season_leaderboard") or comp.get("leaderboard") or []):
        if isinstance(row, dict) and "username" in row and "season_realized_pnl_usd" in row:
            season_pnl[row["username"]] = row["season_realized_pnl_usd"]

    orders = 0
    for name, division in (doc.get("divisions") or {}).items():
        status = division.get("status")
        if status and status != "run":
            # The builder is re-run above and must match the artifact byte for byte, so a
            # non-run status is the builder's current, honest output (typically a division that
            # cannot be evaluated yet). It is reported, not treated as a failure.
            reason = str(division.get("reason", ""))[:120]
            rep.warn(f"exec_summary.division: {name} status {status!r} - {reason}")
            continue
        ranking = division.get("ranking") or []
        pnls = [row["season_realized_pnl_usd"] for row in ranking]
        if pnls != sorted(pnls, reverse=True):
            rep.fail("exec_summary.ranking", f"{name}: ranking is not sorted by season P/L")
        if [row["season_rank"] for row in ranking] != list(range(1, len(ranking) + 1)):
            rep.fail("exec_summary.ranking", f"{name}: season_rank is not 1..{len(ranking)}")
        for row in ranking:
            if row["username"] in season_pnl and not approx(
                    row["season_realized_pnl_usd"], season_pnl[row["username"]], 0.01):
                rep.fail("exec_summary.ranking",
                         f"{name}/{row['username']}: season P/L {row['season_realized_pnl_usd']} != "
                         f"competition artifact {season_pnl[row['username']]}")
        for rec in division.get("recommendations") or []:
            if rec["username"] not in {r["username"] for r in ranking}:
                rep.fail("exec_summary.recommendation",
                         f"{name}/{rec['username']}: recommended but absent from the ranking")
            if rec.get("rule_profile") != division.get("rule_profile"):
                rep.fail("exec_summary.recommendation",
                         f"{name}/{rec['username']}: rule profile {rec.get('rule_profile')!r} != "
                         f"division profile {division.get('rule_profile')!r}")
            for order in rec.get("pending_orders") or []:
                orders += 1
                for field in ("symbol", "action", "decided_on", "order_type", "sizing_rule"):
                    if not order.get(field):
                        rep.fail("exec_summary.order",
                                 f"{name}/{rec['username']}: pending order missing {field}")
                if order.get("decided_on") != rec.get("as_of_last_bar"):
                    rep.fail("exec_summary.order",
                             f"{name}/{rec['username']}: order decided_on {order.get('decided_on')!r} "
                             f"!= as_of_last_bar {rec.get('as_of_last_bar')!r}")
                size = order.get("indicative_size_units")
                if size is None:
                    if "exit" not in order.get("action", "").lower():
                        rep.fail("exec_summary.order",
                                 f"{name}/{rec['username']}: only exit legs may omit a size")
                elif not isinstance(size, int) or size <= 0:
                    rep.fail("exec_summary.order",
                             f"{name}/{rec['username']}: indicative_size_units {size!r}")
                if "not a forecast" not in (meta.get("honesty_note") or "") and not meta.get("not_a_forecast"):
                    rep.fail("exec_summary.honesty", "orders presented without the not-a-forecast flag")
    if meta.get("pending_order_count") != orders:
        rep.fail("exec_summary.count",
                 f"_meta.pending_order_count {meta.get('pending_order_count')} != {orders} "
                 "pending orders in the artifact")
    rep.ok(f"exec summary: {orders} pending orders re-derived and cross-checked "
           f"against {len(season_pnl)} competition rows")


def check_tv_benchmark(rep: Report, source_ids: dict) -> None:
    """Audit the Pine-vs-Python fill benchmark: import integrity, arithmetic, honesty.

    Every median and share is recomputed from the stored per-fill rows; every declared file
    digest is re-hashed from disk; a synthetic fixture can never be labelled a real export.
    """
    import hashlib
    doc = _reproduce(rep, "tv_benchmark", "tv_benchmark.py", "data/tv_benchmark.json")
    if doc is None:
        return
    meta = doc.get("_meta", {})
    if meta.get("kind") != "pine_vs_python_fill_benchmark":
        rep.fail("tv_benchmark.kind", f"unexpected _meta.kind {meta.get('kind')!r}")
    if meta.get("engine") != "tv-benchmark-1":
        rep.fail("tv_benchmark.engine", f"unexpected _meta.engine {meta.get('engine')!r}")
    if meta.get("not_a_forecast") is not True:
        rep.fail("tv_benchmark.honesty", "artifact must declare not_a_forecast: true")
    rules = meta.get("pine_emulator_rules") or {}
    for key in ("market_order_default", "intrabar_assumption", "gap_rule"):
        if not rules.get(key):
            rep.fail("tv_benchmark.rules", f"pine_emulator_rules.{key} is empty")
    if "tradingview.com" not in str(rules.get("source", "")):
        rep.fail("tv_benchmark.rules", f"pine_emulator_rules.source {rules.get('source')!r} is not a "
                                       "TradingView URL")

    exports = doc.get("exports") or []
    fixtures = doc.get("fixtures") or []
    if meta.get("real_exports_found") != len(exports):
        rep.fail("tv_benchmark.counts",
                 f"_meta.real_exports_found {meta.get('real_exports_found')} != {len(exports)}")
    if meta.get("fixture_exports_found") != len(fixtures):
        rep.fail("tv_benchmark.counts",
                 f"_meta.fixture_exports_found {meta.get('fixture_exports_found')} != {len(fixtures)}")
    if not exports:
        if meta.get("status") != "blocked":
            rep.fail("tv_benchmark.status",
                     f"no real export present but status is {meta.get('status')!r}")
        if not meta.get("blocked_reason"):
            rep.fail("tv_benchmark.status", "a blocked benchmark must state the reason")
        if not meta.get("how_to_complete_this_benchmark"):
            rep.fail("tv_benchmark.status", "a blocked benchmark must state how to complete it")
    elif meta.get("status") not in ("measured", "unverified_imports"):
        rep.fail("tv_benchmark.status", f"real exports are present but status is {meta.get('status')!r}")
    if fixtures and "SYNTHETIC" not in str(doc.get("fixture_notice", "")):
        rep.fail("tv_benchmark.fixture_notice",
                 "fixtures are present without a notice stating they are synthetic")
    for record in fixtures:
        if record.get("is_fixture") is not True:
            rep.fail("tv_benchmark.fixture_notice",
                     f"{record.get('path')}: a record under 'fixtures' must carry is_fixture: true")

    for record in exports + fixtures:
        rel = record.get("path")
        if not rel:
            rep.fail("tv_benchmark.record", "record without a path")
            continue
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            rep.fail("tv_benchmark.file", f"{rel}: declared export file is missing")
            continue
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        if digest != record.get("sha256"):
            rep.fail("tv_benchmark.sha256",
                     f"{rel}: file SHA-256 {digest[:16]}... != stored {str(record.get('sha256'))[:16]}...")
        fb = record.get("fill_benchmark") or {}
        rows = fb.get("rows") or []
        compared = [r for r in rows if r.get("vendor_bar")]
        if fb.get("fills_compared") != len(compared):
            rep.fail("tv_benchmark.fills",
                     f"{rel}: fills_compared {fb.get('fills_compared')} != {len(compared)} matched rows")
        if fb.get("fills_unmatched") != len(rows) - len(compared):
            rep.fail("tv_benchmark.fills",
                     f"{rel}: fills_unmatched {fb.get('fills_unmatched')} != {len(rows) - len(compared)}")
        if fb.get("status") != ("measured" if compared else "no_fills_matched"):
            rep.fail("tv_benchmark.status", f"{rel}: fill_benchmark.status {fb.get('status')!r}")
        if compared:
            share = round(sum(1 for r in compared if abs(r["delta_vs_bar_open"]) < 1e-9) / len(compared), 6)
            if not approx(share, fb.get("share_exact_open_match", -1), 1e-9):
                rep.fail("tv_benchmark.arithmetic",
                         f"{rel}: share_exact_open_match {fb.get('share_exact_open_match')} != "
                         f"re-derived {share}")
            for field, source_key in (("median_abs_delta_vs_bar_open_bps", "abs_delta_vs_bar_open_bps"),
                                      ("median_abs_delta_vs_prior_close_bps", "abs_delta_vs_prior_close_bps"),
                                      ("median_abs_delta_vs_python_fill_bps", "abs_delta_vs_python_fill_bps")):
                want = median_of([r.get(source_key) for r in compared])
                want = round(want, 4) if want is not None else None
                if not approx(want if want is not None else -1, fb.get(field, -2), 1e-9):
                    rep.fail("tv_benchmark.arithmetic",
                             f"{rel}: {field} {fb.get(field)} != re-derived {want}")
            for r in compared:
                bar = r["vendor_bar"]
                if not approx(round(r["delta_vs_bar_open"], 6),
                              round(r["exported_price"] - bar["open"], 6), 1e-9):
                    rep.fail("tv_benchmark.arithmetic",
                             f"{rel} line {r.get('line')}: delta_vs_bar_open is not "
                             "exported_price - bar open")
        cross = record.get("arithmetic_cross_check") or {}
        if cross.get("within_tolerance") is not True:
            rep.fail("tv_benchmark.cross_check",
                     f"{rel}: the export's own declared profit does not reconcile with its prices")
        if cross.get("tolerance") is not None and cross["tolerance"] > 0.02:
            rep.fail("tv_benchmark.cross_check", f"{rel}: profit tolerance {cross['tolerance']} is too loose")
        if not record.get("rejected_rows") and record.get("trade_rows") == 0:
            rep.fail("tv_benchmark.record", f"{rel}: record parsed zero trade rows without saying why")
    rep.ok(f"TV benchmark: {len(exports)} real export(s) and {len(fixtures)} fixture(s) "
           "re-hashed, recomputed and honesty-checked")


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

    def transcription_case():
        text = read("research/evidence/TV-RULES-AMP-SEP2026-R5.md")
        return text.replace("CME_MINI:MES1! maximum amount for an open position is 500.0",
                            "CME_MINI:MES1! maximum amount for an open position is 499.0")

    def corrupt_lab(fn):
        v = copy.deepcopy(load("data/leaderboard_lab.json"))
        fn(v)
        return ("data/leaderboard_lab.json", v)

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
    def lab_tier(v): v["prize_ladder"]["tiers"][5]["cash_usd_each"] = 999.0
    def lab_target(v): v["targets"][1]["required_daily_compound_pct_over_remaining_window"] += 1.0
    def lab_fresh(v): v["captures"][-1]["rows"]["50"]["fresh_account_required_daily_compound_pct"] += 1.0
    def lab_leverage(v): v["leverage_math"]["adverse_underlying_move_pct_to_erase_the_whole_balance"] = 1.0
    def lab_champion(v): v["champion_sample"]["completed_champions_at_or_above_latest_rank50"] = 9
    def lab_instrument(v): v["cash_frontier_instrument_requirements"][0]["favorable_move_pct_needed_for_latest_rank50_level"] += 1.0
    def lab_capture_link(v): v["captures"][-1]["participants_displayed"] += 1
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

    def corrupt_comp(fn):
        c = copy.deepcopy(load("data/competition_results.json"))
        fn(c)
        return "data/competition_results.json", c

    def corrupt_comp_roster(fn):
        r = copy.deepcopy(load("data/competition/roster.json"))
        fn(r)
        return "data/competition/roster.json", r

    def comp_pnl(c): c["participants"][0]["season_realized_pnl_usd"] += 1.0
    def comp_rules(c): c["rules"]["starting_balance_virtual_usd"] = 1.0
    def comp_lb_order(c):
        c["leaderboard"][0], c["leaderboard"][1] = c["leaderboard"][1], c["leaderboard"][0]
    def comp_eligible(c): c["_meta"]["eligible_symbols"] = c["_meta"]["eligible_symbols"][:-1]
    def comp_stray(c): c["stray_field"] = True
    def comp_leak(c): c["models"][0]["claim"] = "median net profit of /bin/bash.00 (corrupted)"
    def roster_ghost(r): r["participants"][0]["username"] = "GhostUser"
    def roster_variant(r): r["participants"][0]["variant"] = "does-not-exist"

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
        ("universe.transcription", ("unused", None),
         lambda r: check_universe_transcription(r, transcription_case())),
        ("leaderboard_lab.prize_tiers", corrupt_lab(lab_tier),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.target_rate", corrupt_lab(lab_target),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.fresh_account", corrupt_lab(lab_fresh),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.leverage_math", corrupt_lab(lab_leverage),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.champion_sample", corrupt_lab(lab_champion),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.instrument_join", corrupt_lab(lab_instrument),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
        ("leaderboard_lab.capture_link", corrupt_lab(lab_capture_link),
         lambda r: check_leaderboard_lab(r, cfg, source_ids)),
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
        ("competition.aggregates", corrupt_comp(comp_pnl),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.rules", corrupt_comp(comp_rules),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.sort", corrupt_comp(comp_lb_order),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.eligible", corrupt_comp(comp_eligible),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.determinism", corrupt_comp(comp_stray),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("leaked_shell_text", corrupt_comp(comp_leak),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.leaderboard_roster", corrupt_comp_roster(roster_ghost),
         lambda r: check_competition(r, cfg, ml, source_ids)),
        ("competition.roster_variant", corrupt_comp_roster(roster_variant),
         lambda r: check_competition(r, cfg, ml, source_ids)),
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

    # --- new artifacts: proves the intraday / division / exec-summary / TV checks fire ---
    fake_index = {
        "_meta": {"kind": "intraday_capture_index", "script": "scripts/fetch_intraday.py",
                  "vendor_source_id": "YAHOO-INTRADAY-CHART", "captured_count": 1,
                  "failed_count": 0, "not_attempted_count": 0, "symbol_count": 1,
                  "captured_by_interval": {"15m": 1},
                  "equity_symbols": sorted(_volatile_pool_symbols())},
        "captures": [{"symbol": sorted(_volatile_pool_symbols())[0], "interval": "15m",
                      "kind": "equity", "status": "captured",
                      "file": "data/intraday/synthetic_missing_15m.json", "stored_sha256": "0" * 64,
                      "bar_count": 1, "first_utc": "2026-09-17T13:30:00+00:00",
                      "last_utc": "2026-09-17T13:30:00+00:00",
                      "chunks": 0, "chunk_provenance": []}]}
    scenarios.append(("intraday.capture_file", ("data/intraday_index.json", fake_index),
                      lambda r: check_intraday(r, source_ids)))

    fake_study = {"_meta": {"kind": "not_an_intraday_study", "engine": "intraday-study-1",
                            "generated_utc": "2026-01-01T00:00:00Z", "not_a_forecast": True,
                            "methodology": ["x"], "assumptions": ["x"]},
                  "coverage": [], "gap_fill": {"aggregate_by_kind": {}, "buckets": [], "per_symbol": []},
                  "execution_latency": {"by_kind_interval": []}}
    scenarios.append(("intraday.study_kind", ("data/intraday_study.json", fake_study),
                      lambda r: check_intraday(r, source_ids)))

    fake_stock = {"_meta": {"kind": "not_a_stock_division", "engine": "intel-competition-2",
                            "generated_utc": "2026-01-01T00:00:00Z", "not_a_forecast": True},
                  "divisions": {}}
    scenarios.append(("stock_competition.kind", ("data/stock_competition_results.json", fake_stock),
                      lambda r: check_stock_competition(r, source_ids)))

    exec_doc = load_opt("data/exec_summary.json")
    if exec_doc is not None:
        mutated = copy.deepcopy(exec_doc)
        mutated["_meta"]["pending_order_count"] = (mutated["_meta"]["pending_order_count"] or 0) + 1
        scenarios.append(("exec_summary.determinism", ("data/exec_summary.json", mutated),
                          lambda r: check_exec_summary(r, source_ids)))

    tv_doc = load_opt("data/tv_benchmark.json")
    if tv_doc is not None:
        mutated = copy.deepcopy(tv_doc)
        mutated["_meta"]["fixture_exports_found"] = (mutated["_meta"]["fixture_exports_found"] or 0) + 1
        scenarios.append(("tv_benchmark.determinism", ("data/tv_benchmark.json", mutated),
                          lambda r: check_tv_benchmark(r, source_ids)))
        mutated = copy.deepcopy(tv_doc)
        mutated["_meta"]["status"] = "measured"
        scenarios.append(("tv_benchmark.status", ("data/tv_benchmark.json", mutated),
                          lambda r: check_tv_benchmark(r, source_ids)))

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
    check_universe_transcription(rep)
    master = check_master_list(rep, universe, source_ids)
    check_master_csv(rep, master)
    check_returns(rep, source_ids, cfg, snap)
    check_capacity(rep, cfg, snap, master, source_ids)
    check_frontier(rep, cfg, source_ids)
    check_leaderboard_lab(rep, cfg, source_ids)
    check_intelligence_report(rep, source_ids)
    check_market_history(rep, source_ids, snap, master)
    check_volatile_stocks(rep, source_ids)
    check_backtests(rep, cfg, snap, master, source_ids)
    check_competition(rep, cfg, master, source_ids)
    check_strategy_models(rep, cfg, source_ids)
    check_intraday(rep, source_ids)
    check_stock_competition(rep, source_ids)
    check_exec_summary(rep, source_ids)
    check_tv_benchmark(rep, source_ids)
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
