#!/usr/bin/env python3
"""Render the root GitHub Pages document from audited repository artifacts.

The repository uses legacy GitHub Pages publishing from the root of ``main``. This builder therefore
writes ``index.html`` at the repository root and makes no network requests. Numeric observations are
loaded from JSON; prose distinguishes facts, arithmetic models, and untested hypotheses.
"""

from __future__ import annotations

import html
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def money(value, decimals: int = 2) -> str:
    return f"${value:,.{decimals}f}"


def number(value, decimals: int | None = None) -> str:
    if decimals is not None:
        return f"{value:,.{decimals}f}"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    return f"{value:,}"


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(label)}</a>'


STATUS_PILL = {
    "supported": "ok",
    "refuted": "no",
    "untested": "mut",
    "inconclusive": "warn",
    "partially_supported": "warn",
}
SEVERITY_PILL = {"critical": "no", "high": "warn", "medium": "info", "low": "mut"}
VERIFY_PILL = {"fully_verified": "ok", "identity_verified": "info", "pending_evidence": "warn"}
TIER_PILL = {
    "official_primary": "ok",
    "official_secondary": "info",
    "market_data_vendor": "warn",
    "non_official": "no",
}


def build() -> str:
    cfg = load("data/contest_config.json")
    snapshot = load("data/live_contest_snapshot.json")
    capacity = load("data/initial_capacity.json")
    universe = load("data/contest_universe.json")
    master = load("data/master_list.json")
    returns = load("data/verified_explosive_returns.json")
    stocks = load("data/volatile_stocks.json")
    hypotheses = load("research/hypotheses/hypotheses.json")
    models = load("research/strategy/models.json")
    irregularities = load("research/irregularities.json")
    source_registry = load("research/sources/sources.json")

    sources = source_registry["sources"]
    source_by_id = {s["source_id"]: s for s in sources}
    source_url = {sid: item["url"] for sid, item in source_by_id.items()}
    live_rank = {row["rank"]: row for row in snapshot["leaderboard"]}
    last_visible_rank = cfg["public_leaderboard_last_visible_rank"]
    target_rank = capacity["_meta"]["target_rank"]
    live_return = next(row for row in returns["records"] if row["status"] == "in_progress")
    completed_returns = [row for row in returns["records"] if row["status"] == "final"]
    completed_best = max(completed_returns, key=lambda row: row["return_multiple"])
    exchange_counts = Counter(row["exchange"] for row in universe["instruments"])
    snapshot_at = snapshot["_meta"]["captured_at_utc"]

    out: list[str] = []
    add = out.append

    add(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Leap Research Lab — evidence, capacity, and strategy tests</title>
<meta name="description" content="Evidence-first research for TradingView's The Leap: official rules, live snapshots, verified returns, capacity arithmetic, and untested Pine strategy candidates.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site"><div class="wrap"><div class="hero-grid"><div>
<div class="eyebrow">Evidence-first · virtual-money competition</div>
<h1>The Leap Research Lab</h1>
<p class="sub">Official rules, point-in-time leaderboard evidence, futures capacity arithmetic,
historical return records, and falsifiable strategy candidates. Facts, models, and untested ideas
are labeled separately.</p>
<div class="actions">
{link(source_url['TV-RULES-AMP-SEP2026'], 'Open official rules ↗')}
{link(source_url['TV-CONTEST-AMP-SEP2026'], 'Open live contest ↗')}
<a href="research/strategy/testing-plan.md">Testing protocol</a>
</div></div>
<div class="snapshot-card"><span class="pill ok">live edition</span>
<strong>{esc(cfg['edition_label'])}</strong>
<span>Research snapshot</span><code>{esc(snapshot_at)}</code>
<span>Displayed participants</span><strong>{number(snapshot['participants_displayed'])}</strong>
</div></div>
<div class="badge-row">
<span class="badge">{number(universe['_meta']['instrument_count'])} eligible futures</span>
<span class="badge">{number(master['_meta']['row_count'])} selected contracts</span>
<span class="badge">{number(returns['_meta']['record_count'])} contest return records</span>
<span class="badge">{number(stocks['_meta']['record_count'])} stock market records</span>
<span class="badge">{number(models['_meta']['model_count'])} untested strategy candidates</span>
<span class="badge warn">{number(irregularities['_meta']['count'])} irregularities logged</span>
</div></div></header>
<nav class="toc"><div class="wrap"><ul>
<li><a href="#overview">Overview</a></li>
<li><a href="#rules">Rules</a></li>
<li><a href="#frontier">Live frontier</a></li>
<li><a href="#capacity">Capacity</a></li>
<li><a href="#strategies">Strategies</a></li>
<li><a href="#returns">Contest returns</a></li>
<li><a href="#stocks">Stock history</a></li>
<li><a href="#hypotheses">Hypotheses</a></li>
<li><a href="#masterlist">Selected futures</a></li>
<li><a href="#universe">Universe</a></li>
<li><a href="#irregularities">Irregularities</a></li>
<li><a href="#sources">Sources</a></li>
<li><a href="#method">Method</a></li>
</ul></div></nav>
<main class="wrap">
""")

    # Overview
    add(f"""<section id="overview"><h2>What matters now</h2>
<p class="lead">A concise read of the current evidence. Live values are snapshots, historical
champions are simulated outcomes, and stock multiples are real market-price ratios.</p>
<div class="grid cols-4">
<div class="card"><h3>Live rank 1</h3><div class="stat accent">{live_return['return_multiple']}x</div>
<div class="note">+{number(live_rank[1]['realized_profit_pct'], 2)}% · {money(live_rank[1]['realized_profit_usd'])} realized P/L</div></div>
<div class="card"><h3>Last public row</h3><div class="stat amber">rank {last_visible_rank}</div>
<div class="note">+{number(live_rank[last_visible_rank]['realized_profit_pct'], 2)}% · not the hidden rank-{cfg['maximum_prize_recipients']} frontier</div></div>
<div class="card"><h3>Best completed sample</h3><div class="stat green">{completed_best['return_multiple']}x</div>
<div class="note">{esc(completed_best['asset_class_label'])} · official champion summary</div></div>
<div class="card"><h3>Captured ≥100x contest outcomes</h3><div class="stat red">{returns['threshold_analysis']['ge_100x']['count']}</div>
<div class="note">unattested in this sample, not proven impossible</div></div>
</div>
<div class="callout info"><h3>Evidence boundary</h3>
<p>The official champion summaries show outcomes, not the trades that produced them. The capacity
screen shows arithmetic feasibility, not direction or expected return. The Pine models below have
no published performance result because no authenticated Strategy Report run was available.</p></div>
<div class="grid cols-2">
<div class="callout good"><h3>Verified</h3><ul>
<li>The live universe contains {universe['_meta']['instrument_count']} futures and no single-stock equities.</li>
<li>Ranking uses realized P/L on closed positions; final automatic closes count.</li>
<li>The completed official sample contains returns above 10x.</li>
<li>Each historical stock ratio is recomputable from archived adjusted closes.</li>
</ul></div>
<div class="callout high"><h3>Not established</h3><ul>
<li>No strategy, direction, or instrument is proven to win.</li>
<li>No normalized volatility comparison covers the eligible universe.</li>
<li>The public page does not reveal rank {cfg['maximum_prize_recipients']}.</li>
<li>No captured official contest record verifies 100x.</li>
</ul></div></div></section>""")

    # Rulebook
    add(f"""<section id="rules"><h2>Live rulebook, structured</h2>
<p class="lead">Values below come from <code>data/contest_config.json</code>, transcribed from the
official edition rules. Edition-specific rules control.</p>
<div class="grid cols-4">
<div class="card"><h3>Window</h3><div class="stat small accent">{esc(cfg['competition_start_utc'][:10])}</div><div class="note">{esc(cfg['competition_start_utc'][11:16])} UTC → {esc(cfg['competition_end_utc'])}</div></div>
<div class="card"><h3>Registration closes</h3><div class="stat small accent">{esc(cfg['registration_close_utc'][:10])}</div><div class="note">{esc(cfg['registration_close_utc'][11:16])} UTC</div></div>
<div class="card"><h3>Starting balance</h3><div class="stat accent">{money(cfg['starting_balance_virtual_usd'], 0)}</div><div class="note">virtual USD · no reset</div></div>
<div class="card"><h3>Futures leverage</h3><div class="stat accent">{number(cfg['futures_leverage_ratio'], 0)}:1</div><div class="note">{money(cfg['maximum_initial_notional_usd'], 0)} maximum initial notional</div></div>
</div>
<div class="callout info"><h3>Ranking mechanics</h3>
<p>Place is determined by realized profit/loss on closed positions. The leaderboard updates no more
than once per hour. Open positions are automatically closed at the competition end and included in
the final calculation. Closing changes when P/L becomes realized; it does not manufacture profit.</p>
<p>Prize qualification also requires activity on at least <strong>{cfg['minimum_active_days']} UTC days</strong>.
The official definition: {esc(cfg['active_day_definition'])}</p></div>
<h3 class="minor-heading">Prize ladder</h3>
<div class="table-wrap"><table><thead><tr><th>Ranks</th><th class="num">Prize each</th><th class="num">Places</th></tr></thead><tbody>""")
    for tier in cfg["prize_tiers"]:
        ranks = str(tier["from_rank"]) if tier["from_rank"] == tier["to_rank"] else f"{tier['from_rank']}–{tier['to_rank']}"
        prize = money(tier["cash_usd_each"], 0) if tier["cash_usd_each"] is not None else f"{tier['plan_months_each']}-month TradingView plan"
        places = tier["to_rank"] - tier["from_rank"] + 1
        add(f'<tr><td>{ranks}</td><td class="num">{esc(prize)}</td><td class="num">{places}</td></tr>')
    add(f"""</tbody></table></div>
<p class="note">Cash-prize ARV: {money(cfg['cash_prize_total_arv_usd'], 0)}. Rules state prizes at or above
{money(cfg['cash_payment_method_threshold_usd'], 0)} are payable by {esc(' or '.join(cfg['cash_payment_methods']['at_or_above_1000_usd']))};
smaller cash prizes by {esc(' or '.join(cfg['cash_payment_methods']['below_1000_usd']))}. Every winner
remains a potential winner pending TradingView verification.</p>
<div class="callout high"><h3>Operational limits</h3>
<p>The rules prohibit {cfg['transaction_rate_prohibited_at_or_above_per_minute']} or more transactions
with orders and positions per minute and warn that excessive Paper Trading activity, including
various scripts, can trigger a ban. This repository does not automate the competition account.</p></div></section>""")

    # Live frontier
    add(f"""<section id="frontier"><h2>Timestamped public frontier</h2>
<p class="lead">Selected rows captured at <code>{esc(snapshot_at)}</code>. They can move after capture.
The percentage/dollar pairs are verifier-checked against the starting balance and display rounding.</p>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Trader</th><th class="num">Realized profit %</th><th class="num">Realized profit $</th><th>Tier at capture</th></tr></thead><tbody>""")
    for row in snapshot["leaderboard"]:
        rank = row["rank"]
        tier = next(t for t in cfg["prize_tiers"] if t["from_rank"] <= rank <= t["to_rank"])
        prize = money(tier["cash_usd_each"], 0) if tier["cash_usd_each"] is not None else f"{tier['plan_months_each']}-month plan"
        add(f"<tr><td class=\"num\">{rank}</td><td>{esc(row['trader'])}</td><td class=\"num\">+{number(row['realized_profit_pct'], 2)}%</td><td class=\"num\">+{money(row['realized_profit_usd'])}</td><td>{esc(prize)}</td></tr>")
    add(f"""</tbody></table></div>
<div class="callout critical"><h3>No guaranteed live cutoff</h3>
<p>The public table ends at rank {cfg['public_leaderboard_last_visible_rank']}, while prizes extend
through rank {cfg['maximum_prize_recipients']}. The unseen last-prize row cannot be recovered from
this page. Crossing any displayed in-progress row does not guarantee a final place or eligibility.</p>
<p>{link(source_url['TV-CONTEST-AMP-SEP2026'], 'Review the moving leaderboard ↗')}</p></div></section>""")

    # Capacity
    top_symbols = ", ".join(row["symbol"] for row in capacity["entries"][:4])
    add(f"""<section id="capacity"><h2>Initial-balance capacity screen</h2>
<p class="lead">A feasibility model for the {len(capacity['entries'])} selected futures. It combines
captured TradingView display prices, verified contract multipliers, rule caps, and initial {number(cfg['futures_leverage_ratio'], 0)}:1
buying power. It is not a volatility forecast, backtest, or recommendation.</p>
<div class="callout good"><h3>Lowest modeled move requirements in this selected set</h3>
<p><code>{esc(top_symbols)}</code> are the first four rows when sorting by favorable underlying
percentage move needed to equal the captured rank-{target_rank} P/L. This says
only that they provide the largest modeled initial notional among these rows; it says nothing about
the probability or direction of that move.</p></div>
<div class="table-wrap"><table id="capacity-table"><thead><tr>
<th>Symbol</th><th>Group</th><th class="num">Display price</th><th class="num">Rules cap</th>
<th class="num">Modeled contracts</th><th>Initial constraint</th><th class="num">Modeled notional</th>
<th class="num">P/L at favorable 1%</th><th class="num">Move to rank {target_rank}</th><th>Quote</th>
</tr></thead><tbody>""")
    for row in capacity["entries"]:
        qurl = source_url[row["quote_source_id"]]
        add(f"""<tr data-group="{esc(row['asset_class_group'])}">
<td class="sym">{esc(row['symbol'])}</td><td>{esc(row['asset_class_group'].replace('_', ' '))}</td>
<td class="num">{number(row['quote_price'], 4)}</td><td class="num">{number(row['rules_position_cap_contracts'])}</td>
<td class="num">{row['max_whole_contracts_at_initial_balance']}</td><td>{esc(row['initial_constraint'].replace('_', ' '))}</td>
<td class="num">{money(row['modeled_initial_notional_usd'], 0)}</td>
<td class="num">{money(row['modeled_pnl_for_favorable_1pct_move_usd'], 0)}</td>
<td class="num">{number(row['favorable_move_pct_needed_for_rank250_snapshot'], 2)}%</td>
<td>{link(qurl, 'open ↗')}</td></tr>""")
    add('</tbody></table></div><details class="assumptions"><summary>Model assumptions and omissions</summary><ul>')
    for assumption in capacity["_meta"]["assumptions"]:
        add(f"<li>{esc(assumption)}</li>")
    add("</ul></details></section>")

    # Strategy models
    add(f"""<section id="strategies"><h2>Strategy candidates and test tools</h2>
<p class="lead">The models are pre-registered before a result exists. Their purpose is to test
long/short volatility-expansion mechanisms on eligible TradingView charts—not to predict a winner.</p>
<div class="callout high"><h3>Platform status: {esc(models['_meta']['platform_validation_status'].replace('_', ' '))}</h3>
<p>{esc(models['_meta']['platform_validation_reason'])}</p></div>
<div class="grid cols-3">""")
    for model in models["models"]:
        pill = STATUS_PILL[model["status"]]
        add(f"""<article class="card strategy-card"><div class="model-head"><span class="mono">{esc(model['id'])}</span><span class="pill {pill}">{esc(model['status'])}</span></div>
<h3>{esc(model['name'])}</h3><p>{esc(model['hypothesis'])}</p>
<dl><dt>Entry</dt><dd>{esc(model['entry_logic'])}</dd><dt>Exit</dt><dd>{esc(model['exit_logic'])}</dd>
<dt>Reject when</dt><dd>{esc(model['falsification_rule'])}</dd></dl></article>""")
    add(f"""</div>
<div class="grid cols-2"><div class="callout info"><h3>TradingView study stack</h3><ol>
<li>Standard candlestick chart.</li><li>Pine Strategy Report and Deep Backtesting.</li>
<li>Bar Magnifier plus declared commission, slippage, and limit-fill sensitivity.</li>
<li>Rolling holdouts that match the contest horizon, followed by forward testing.</li></ol>
<p>{link(source_url['TV-PINE-STRATEGIES'], 'Official strategy documentation ↗')}</p></div>
<div class="callout info"><h3>Execution boundary</h3><p>Official documentation says Pine strategies
cannot directly place orders in TradingView's built-in Paper Trading account. Strategy Report fills
are hypothetical broker-emulator results, not competition-account results.</p>
<p>{link(source_url['TV-PINE-AUTOTRADE'], 'Official automation limitation ↗')}</p></div></div>
<p class="file-links"><a href="research/strategy/the-leap-hypothesis-lab.pine">Pine source</a>
<a href="research/strategy/models.json">Model register</a>
<a href="research/strategy/testing-plan.md">Full testing protocol</a></p></section>""")

    # Contest returns
    add(f"""<section id="returns"><h2>Official simulated contest outcomes</h2>
<p class="lead">Completed #1 outcomes from TradingView's official history, plus one explicitly
in-progress live row. Return multiple = 1 + published net-profit percentage / 100.</p>
<div class="grid cols-4">""")
    for key in ("ge_5x", "ge_10x", "ge_20x", "ge_50x"):
        block = returns["threshold_analysis"][key]
        label = key.replace("ge_", "≥").replace("x", "x")
        add(f'<div class="card"><h3>{esc(label)}</h3><div class="stat accent">{block["count"]}</div><div class="note">captured records</div></div>')
    add("</div><div class=\"controls\"><input id=\"ret-q\" type=\"search\" placeholder=\"Filter edition, winner, asset…\" aria-label=\"Filter contest returns\"><span id=\"ret-count\" class=\"count\"></span></div>")
    add("""<div class="table-wrap"><table id="ret-table"><thead><tr><th>Status</th><th>Edition</th><th>Asset</th><th>Winner</th><th class="num">Participants</th><th class="num">Published net profit</th><th class="num">Return multiple</th><th>Official result</th></tr></thead><tbody>""")
    for row in sorted(returns["records"], key=lambda r: r["return_multiple"], reverse=True):
        pill = "ok" if row["status"] == "final" else "warn"
        search = " ".join(str(row.get(k, "")) for k in ("edition_label", "asset_class_label", "winner")).lower()
        participants = number(row["participants"]) if row.get("participants") is not None else "not published"
        add(f"""<tr data-search="{esc(search)}"><td><span class="pill {pill}">{esc(row['status'])}</span></td>
<td>{esc(row['edition_label'])}</td><td>{esc(row['asset_class_label'])}</td><td>{esc(row['winner'])}</td>
<td class="num">{participants}</td><td class="num">+{number(row['net_profit_pct_as_published'], 2)}%</td>
<td class="num"><strong>{row['return_multiple']}x</strong></td><td>{link(row['results_url'], 'review ↗')}</td></tr>""")
    add(f"""</tbody></table></div>
<div class="callout high"><h3>100x remains unattested in this contest sample</h3>
<p>The maximum completed value is {completed_best['return_multiple']}x. That is the sample maximum,
not a universal ceiling. The in-progress row is not counted as a final champion.</p></div></section>""")

    # Historical stocks
    threshold_buttons = ['<button class="active" data-t="0">All</button>']
    for threshold in stocks["thresholds"].values():
        value = threshold["threshold"]
        threshold_buttons.append(f'<button data-t="{value}">≥{value}x</button>')
    add(f"""<section id="stocks"><h2>Historical stock market moves</h2>
<p class="lead">Window-bounded trough-to-later-peak adjusted-close ratios. These are real historical
market-price observations from a commercial vendor, not The Leap account returns and not evidence
that a strategy captured the move.</p>
<div id="vs-thresh" class="thresh">{''.join(threshold_buttons)}</div>
<div class="controls"><input id="vs-q" type="search" placeholder="Filter ticker or company…" aria-label="Filter historical stock records"><span id="vs-count" class="count"></span></div>
<div class="table-wrap"><table id="vs-table"><thead><tr><th>Symbol</th><th>Company</th><th class="num">Trough adjclose</th><th class="num">Peak adjclose</th><th class="num">Multiple</th><th>Exact source windows</th></tr></thead><tbody>""")
    for row in stocks["records"]:
        search = f"{row['symbol']} {row['name']}".lower()
        add(f"""<tr data-search="{esc(search)}" data-mult="{row['return_multiple']}"><td class="sym">{esc(row['symbol'])}</td><td>{esc(row['name'])}</td>
<td class="num">{number(row['trough']['adjclose'], 4)}<br><span class="note">{esc(row['trough']['date_utc'])}</span></td>
<td class="num">{number(row['peak']['adjclose'], 4)}<br><span class="note">{esc(row['peak']['date_utc'])}</span></td>
<td class="num"><strong>{row['return_multiple']}x</strong></td>
<td>{link(row['trough_window']['endpoint'], 'trough endpoint ↗')}<br>{link(row['peak_window']['endpoint'], 'peak endpoint ↗')}</td></tr>""")
    add("""</tbody></table></div>
<div class="callout high"><h3>Source tier and scope</h3><p>Yahoo Finance is explicitly registered as
<em>market_data_vendor</em>, not official primary evidence. Every ratio is recomputed from values
stored in the repository. Claims are limited to the documented windows; no all-time claim is made.</p></div></section>""")

    # Hypotheses
    add(f"""<section id="hypotheses"><h2>Research hypothesis register</h2>
<p class="lead">Falsifiable claims about rules and observed outcomes. “Supported” and “refuted”
apply only to the stated test and captured evidence—not to a trading forecast.</p>""")
    for item in hypotheses["hypotheses"]:
        pill = STATUS_PILL[item["status"]]
        evidence_html = "".join(f"<li>{esc(line)}</li>" for line in item["evidence"])
        refs = " · ".join(link(source_url[sid], sid) for sid in item["source_ids"])
        add(f"""<article class="hyp"><div class="top"><span class="id">{esc(item['id'])}</span><span class="pill {pill}">{esc(item['status'])}</span><span class="claim">{esc(item['claim'])}</span></div>
<dl><dt>Prediction</dt><dd>{esc(item['prediction'])}</dd><dt>Test</dt><dd>{esc(item['test'])}</dd>
<dt>Evidence</dt><dd><ul>{evidence_html}</ul></dd><dt>Sources</dt><dd>{refs}</dd></dl></article>""")
    add("</section>")

    # Master list — retain data-class exactly once per row for CI/client filter.
    classes = sorted({row["volatility_class"] for row in master["entries"]})
    add(f"""<section id="masterlist"><h2>Selected live-edition futures</h2>
<p class="lead">A focused research subset of the eligible universe. “Group” is a descriptive
classification, not a measured volatility rank. Caps and multipliers are source-verified.</p>
<div class="controls"><input id="ml-q" type="search" placeholder="Filter symbol, name, underlying…" aria-label="Filter selected futures">
<select id="ml-class" aria-label="Filter by group"><option value="">All groups</option>""")
    for cls in classes:
        add(f'<option value="{esc(cls)}">{esc(cls.replace("_", " "))}</option>')
    add('</select><span id="ml-count" class="count"></span></div><div class="table-wrap"><table id="ml-table"><thead><tr><th>Symbol</th><th>Name</th><th>Group</th><th class="num">Rules cap</th><th class="num">Multiplier</th><th class="num">Rules max underlying</th><th>Status</th><th>Selection rationale</th></tr></thead><tbody>')
    for row in master["entries"]:
        search = f"{row['symbol']} {row['name']} {row['underlying']} {row['exchange']}".lower()
        pill = VERIFY_PILL[row["verification_status"]]
        cap_link = link(source_url["TV-RULES-AMP-SEP2026"], number(row["max_open_position_contracts"]))
        multiplier_label = f"{number(row['contract_multiplier'])} {row['contract_multiplier_unit']}"
        multiplier_link = link(source_url[row["contract_multiplier_source_id"]], multiplier_label)
        add(f"""<tr data-search="{esc(search)}" data-class="{esc(row['volatility_class'])}"><td class="sym">{esc(row['symbol'])}</td><td>{esc(row['name'])}</td>
<td>{esc(row['volatility_class'].replace('_', ' '))}</td><td class="num">{cap_link}</td>
<td class="num">{multiplier_link}</td>
<td class="num">{number(row['max_underlying_exposure'])} {esc(row['max_underlying_exposure_unit'])}</td>
<td><span class="pill {pill}">{esc(row['verification_status'])}</span></td><td>{esc(row['selection_rationale'])}</td></tr>""")
    add("</tbody></table></div></section>")

    # Full universe — data-ex exactly once per row for CI/client filtering.
    add(f"""<section id="universe"><h2>Full eligible universe</h2>
<p class="lead">All {universe['_meta']['instrument_count']} symbols and caps transcribed from the
live rules. Exchange counts: {esc(', '.join(f'{k} {v}' for k, v in sorted(exchange_counts.items())))}.</p>
<div class="controls"><input id="un-q" type="search" placeholder="Filter symbol…" aria-label="Filter eligible universe">
<select id="un-ex" aria-label="Filter exchange"><option value="">All exchanges</option>""")
    for exchange in sorted(exchange_counts):
        add(f'<option value="{esc(exchange)}">{esc(exchange)}</option>')
    add('</select><span id="un-count" class="count"></span></div><div class="table-wrap"><table id="un-table"><thead><tr><th>#</th><th>TradingView symbol</th><th>Exchange</th><th>Root</th><th class="num">Maximum open position</th></tr></thead><tbody>')
    for ordinal, row in enumerate(universe["instruments"], start=1):
        add(f"""<tr data-search="{esc(row['tradingview_symbol'].lower())}" data-ex="{esc(row['exchange'])}"><td class="num">{ordinal}</td>
<td class="sym">{esc(row['tradingview_symbol'])}</td><td>{esc(row['exchange'])}</td><td class="sym">{esc(row['root_code'])}</td><td class="num">{number(row['max_open_position_contracts'])}</td></tr>""")
    add("</tbody></table></div></section>")

    # Irregularities
    add(f"""<section id="irregularities"><h2>Irregularity register</h2>
<p class="lead">Contradictions, missing fields, stale assumptions, and source limitations are kept
visible even after resolution.</p>""")
    for item in irregularities["irregularities"]:
        pill = SEVERITY_PILL[item["severity"]]
        status = item.get("status", "open")
        refs = " · ".join(link(source_url[sid], sid) for sid in item["source_ids"])
        add(f"""<article class="hyp"><div class="top"><span class="id">{esc(item['id'])}</span><span class="pill {pill}">{esc(item['severity'])}</span><span class="pill mut">{esc(status)}</span><span class="claim">{esc(item['title'])}</span></div>
<dl><dt>Detail</dt><dd>{esc(item['detail'])}</dd><dt>Observed</dt><dd>{esc(item['observed'])}</dd>
<dt>Resolution</dt><dd>{esc(item.get('resolution', 'Open'))}</dd><dt>Sources</dt><dd>{refs}</dd></dl></article>""")
    add("</section>")

    # Source registry
    add(f"""<section id="sources"><h2>Source registry and manual review</h2>
<p class="lead">All {source_registry['_meta']['source_count']} registered sources, their evidence
tier, allowed use, captured evidence file, and exact URL. Vendor stock sources also expose both
endpoint windows independently.</p><div class="source-grid">""")
    for source in sources:
        pill = TIER_PILL[source["tier"]]
        uses = "".join(f"<li>{esc(use)}</li>" for use in source["used_for"])
        evidence = source.get("evidence_file")
        endpoint_links = ""
        if source.get("endpoint_urls"):
            endpoint_links = '<div class="endpoint-links">' + " · ".join(
                link(item["url"], f"{item['label']} ↗") for item in source["endpoint_urls"]
            ) + "</div>"
        evidence_link = f'<a href="{esc(evidence)}">captured evidence</a>' if evidence else "no local evidence file"
        add(f"""<details class="source-item"><summary><span class="pill {pill}">{esc(source['tier'].replace('_', ' '))}</span>
<strong>{esc(source['source_id'])}</strong> · {esc(source['title'])}</summary>
<p>{link(source['url'], source['url'])}</p>{endpoint_links}
<p class="note">{esc(source['publisher'])} · accessed {esc(source['accessed_utc'])} · {evidence_link}</p>
<strong>Allowed uses</strong><ul>{uses}</ul></details>""")
    add("</div></section>")

    # Method and limitations
    add(f"""<section id="method"><h2>Method, verification, and limits</h2>
<p class="lead">The site is deterministic and network-free. Public evidence is captured first;
the offline verifier then checks provenance and re-derives arithmetic.</p>
<div class="pipeline"><div><span>1</span><strong>Capture</strong><p>Save official quotations, exact URLs, and access times.</p></div>
<div><span>2</span><strong>Register</strong><p>Assign source tier and narrowly define what it may prove.</p></div>
<div><span>3</span><strong>Derive</strong><p>Compute return multiples, capacity, thresholds, and counts from stored inputs.</p></div>
<div><span>4</span><strong>Mutate</strong><p>Corrupt test copies and prove each critical verifier check fails.</p></div>
<div><span>5</span><strong>Publish</strong><p>Render this page from checked JSON and fail CI when it is stale.</p></div></div>
<h3 class="minor-heading">Reproduce</h3>
<pre>python3 scripts/verify.py
python3 scripts/verify.py --self-test
python3 scripts/build_site.py
python3 -m py_compile scripts/verify.py scripts/build_site.py</pre>
<div class="grid cols-2"><div class="callout info"><h3>Verifier coverage</h3><ul>
<li>Rule constants, timestamps, prize continuity, cash arithmetic, and payment methods.</li>
<li>Leaderboard percentage/dollar consistency and live-record synchronization.</li>
<li>Quote provenance and all capacity fields.</li><li>Universe caps, contract multipliers, and CSV parity.</li>
<li>Both exact stock endpoint windows per record and every adjusted-close ratio.</li>
<li>Strategy files, contest settings, and explicit untested/null result state.</li>
</ul></div><div class="callout high"><h3>Material limitations</h3><ul>
<li>The verifier is offline; captured public pages can later change.</li>
<li>Leaderboard rows and display prices are asynchronous, non-executable snapshots.</li>
<li>No licensed consistent intraday history covers all eligible symbols here.</li>
<li>Champion summaries contain no trade history.</li><li>Continuous-contract roll effects require separate testing.</li>
<li>No authenticated Strategy Report or forward-test artifact exists.</li>
</ul></div></div>
<div class="disclaimer"><strong>Scope.</strong> This project concerns a virtual-money competition.
It is not investment advice, a return forecast, or evidence that any historical result will repeat.
TradingView and CME Group are not affiliated with this repository.</div></section>
</main>
<footer><div class="wrap"><span>Snapshot <code>{esc(snapshot_at)}</code></span>
<span>Built from audited repository artifacts</span><span>{link(source_url['TV-RULES-AMP-SEP2026'], 'Official rules ↗')}</span>
<span><a href="README.md">Project README</a></span></div></footer>
<script src="assets/app.js"></script>
</body></html>
""")
    return "".join(out)


def main() -> int:
    html_text = build()
    path = os.path.join(ROOT, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    with open(os.path.join(ROOT, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    print(f"wrote {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
