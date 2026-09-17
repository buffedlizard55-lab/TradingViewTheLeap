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
    frontier_history = load("data/frontier_history.json")
    market_index = load("data/market_history_index.json")
    backtests = load("data/backtest_results.json")
    vol_intel = load("data/volatility_intelligence.json")

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
    captured_syms = [c for c in market_index["captures"] if c.get("status") == "captured"]

    out: list[str] = []
    add = out.append

    add(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Leap Research Lab — evidence, capacity, and strategy tests</title>
<meta name="description" content="Evidence-first research for TradingView's The Leap: official rules, live snapshots, verified returns, capacity arithmetic, market-data captures, and walk-forward strategy test results.">
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
<span class="badge">{number(len(captured_syms))} captured vendor series</span>
<span class="badge">{number(len(backtests['models']))} walk-forward tested models</span>
<span class="badge">{number(models['_meta']['model_count'])} untested strategy candidates</span>
<span class="badge warn">{number(irregularities['_meta']['count'])} irregularities logged</span>
</div></div></header>
<nav class="toc"><div class="wrap"><ul>
<li><a href="#overview">Overview</a></li>
<li><a href="#rules">Rules</a></li>
<li><a href="#frontier">Live frontier</a></li>
<li><a href="#capacity">Capacity</a></li>
<li><a href="#intelligence">Market data</a></li>
<li><a href="#strategies">Strategies</a></li>
<li><a href="#backtests">Backtest lab</a></li>
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
<h3>Frontier tracker</h3>
<p class="note">Every capture of the same four frontier ranks, newest last. Deltas are raw
subtractions against the previous capture, not growth rates. A threshold that looks frozen can
still move before the deadline, and rank 1 or rank 250 repeating a value across captures means
only that those participants had not realized new P/L between captures.</p>
<div class="table-wrap"><table id="frontier-history"><thead><tr><th>Captured (UTC)</th><th class="num">Participants</th>
<th class="num">Rank 1 $</th><th class="num">Rank 50 $</th><th class="num">Rank 100 $</th><th class="num">Rank 250 $</th><th>Evidence</th></tr></thead><tbody>""")
    prev = None
    for cap in frontier_history["captures"]:
        rows = {int(k): v for k, v in cap["rows"].items()}
        cells = []
        for rank in (1, 50, 100, 250):
            value = rows[rank]["realized_profit_usd"]
            if prev is not None:
                delta = value - prev[rank]
                sign = "+" if delta >= 0 else "−"
                cells.append(f'{money(value)} <span class="{"up" if delta >= 0 else "down"}">({sign}{money(abs(delta), 0)})</span>')
            else:
                cells.append(money(value))
        ev_link = link(cap["evidence_file"], "evidence ↗") if cap.get("evidence_file") else ""
        add(f"""<tr data-frontier="{esc(cap['captured_at_utc'])}"><td><code>{esc(cap['captured_at_utc'])}</code></td>
<td class="num">{number(cap['participants_displayed'])}</td>
<td class="num">{cells[0]}</td><td class="num">{cells[1]}</td><td class="num">{cells[2]}</td><td class="num">{cells[3]}</td>
<td>{ev_link}</td></tr>""")
        prev = {int(k): v["realized_profit_usd"] for k, v in cap["rows"].items()}
    add(f"""</tbody></table></div>
<p class="note">Observed so far: {esc(frontier_history['_meta']['observed_notes'][0])}</p>
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

    # Market-data intelligence layer
    mh_meta = market_index["_meta"]
    captured_syms = [c for c in market_index["captures"] if c.get("status") == "captured"]
    failed_syms = [c for c in market_index["captures"] if c.get("status") == "failed"]
    quote_map = {q["symbol"]: q for q in snapshot["quotes"]}
    mh_caveat = (
        "Series are Yahoo front-month continuous futures with unadjusted roll splices — roll "
        "gaps can create artificial jumps. Capture runs through the automated workflow; the "
        "relay transport and IP-blocking detail is tracked as IR-15. The offline verifier "
        "re-checks every stored file's hash, endpoint, window, OHLC invariants, and "
        "cross-checks the last close against the TradingView quote snapshot."
    )
    add(f"""<section id="intelligence"><h2>Market-data intelligence layer</h2>
<p class="lead">Daily-bar vendor history for {len(captured_syms)} of the {mh_meta['symbol_count']} selected
futures, captured {esc(mh_meta['capture_window_start_utc'][:10])} → {esc(mh_meta['capture_window_end_utc'][:10])} and stored as
raw, SHA-256-indexed files. This is the data the walk-forward engine and the volatility table below
run on. It is vendor-tier evidence, not an official record.</p>
<div class="callout warn"><h3>What this data is and is not</h3>
<p>{esc(mh_caveat)}</p>
<p>{link(source_url['YAHOO-FUTURES-CHART'], 'Vendor source registry entry ↗')} · <a href="research/evidence/YAHOO-FUTURES-CAPTURE-2026-09-17.md">Capture evidence file</a></p></div>
<div class="table-wrap"><table id="mh-table"><thead><tr><th>Symbol</th><th>Vendor contract</th><th>Transport</th>
<th class="num">Sessions</th><th>First</th><th>Last</th><th class="num">Last close</th><th class="num">Δ vs TV quote</th><th>Raw endpoint</th></tr></thead><tbody>""")
    for c in market_index["captures"]:
        if c.get("status") != "captured":
            continue
        tv = c["tradingview_symbol"]
        delta_cell = "—"
        if tv in quote_map:
            d_pct = abs(c["last_close"] - quote_map[tv]["price"]) / quote_map[tv]["price"] * 100
            cls = "down" if d_pct > 2.0 else "up"
            delta_cell = f'<span class="{cls}">{number(d_pct, 2)}%</span>'
        add(f"""<tr data-mhsym="{esc(tv)}"><td class="sym">{esc(tv)}</td>
<td>{esc(c.get('vendor_reported_contract') or '?')}</td><td>{esc(c.get('transport') or '?')}</td>
<td class="num">{number(c['sessions_valid'])}</td><td>{esc(c['first_session_utc'])}</td><td>{esc(c['last_session_utc'])}</td>
<td class="num">{number(c['last_close'], 4)}</td><td class="num">{delta_cell}</td>
<td>{link(c['endpoint'], 'raw ↗')}</td></tr>""")
    if failed_syms:
        add('<tr><td colspan="9" class="note">Failed captures (recorded, retried on the next run): '
            + esc(", ".join(c["tradingview_symbol"] for c in failed_syms)) + "</td></tr>")
    add(f"""</tbody></table></div>
<h3>Realized volatility and explosive-move screen</h3>
<p class="note">Computed from the captured daily bars. "Best 30d" is the largest
close-to-extreme move inside any overlapping 30-calendar-day window in the captured period — an
upper envelope of what history offered on that ticker, not an expectation, not a trade, and not a
forecast. The final columns join the capacity screen: if the best historical 30-day move recurred
at the modeled initial notional, would it have covered the captured rank-{target_rank} P/L?</p>
<div class="table-wrap"><table id="vol-table"><thead><tr><th>Symbol</th><th class="num">Ann. vol</th>
<th class="num">Mean ATR14 %</th><th class="num">Best 30d up</th><th class="num">Best 30d down</th>
<th class="num">30d windows ≥10% up</th><th class="num">≥25% up</th><th class="num">Largest gap %</th>
<th class="num">Move needed for rank {target_rank}</th><th class="num">Best-move P/L at modeled notional</th></tr></thead><tbody>""")
    for r in vol_intel["records"]:
        flag = "yes" if r.get("note_if_best_move_exceeds_rank250_requirement") else "no"
        cls = "up" if flag == "yes" else ""
        add(f"""<tr data-vol="{esc(r['symbol'])}"><td class="sym">{esc(r['symbol'])}</td>
<td class="num">{number(r['ann_vol_full_pct'], 1)}%</td>
<td class="num">{number(r['mean_atr14_pct'], 2)}%</td>
<td class="num">{number(r['best_30d_up_move_pct'], 1)}%</td>
<td class="num">−{number(r['best_30d_down_move_pct'], 1)}%</td>
<td class="num">{number(r['windows_30d_ge_10pct_up'])}</td>
<td class="num">{number(r['windows_30d_ge_25pct_up'])}</td>
<td class="num">{number(r['largest_abs_overnight_gap_pct'], 2)}%</td>
<td class="num">{number(r['favorable_move_pct_needed_for_rank250_snapshot'], 2)}%</td>
<td class="num {cls}">{money(r['rank250_pnl_if_best_30d_up_move_recurred_usd'], 0) if r['rank250_pnl_if_best_30d_up_move_recurred_usd'] is not None else '—'} ({flag})</td></tr>""")
    add(f"""</tbody></table></div>
<p class="note">Metric definitions: {esc('; '.join(f'{k} = {v}' for k, v in vol_intel['_meta']['metric_definitions'].items()))}.</p>
<p class="file-links"><a href="data/market_history_index.json">Capture index (JSON)</a>
<a href="data/volatility_intelligence.json">Volatility records (JSON)</a></p></section>""")


    # Strategy models
    add(f"""<section id="strategies"><h2>Strategy candidates and test tools</h2>
<p class="lead">The models were pre-registered before any result existed. Their purpose is to test
long/short volatility-expansion mechanisms on eligible TradingView charts—not to predict a winner.
The independent walk-forward results are in the <a href="#backtests">backtest lab</a> below;
TradingView-platform Strategy Report validation remains a separate, still-pending step.</p>
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

    # Backtest lab (independent daily-bar simulation)
    bt_meta = backtests["_meta"]
    bt_stamp = bt_meta["generated_utc"]
    bt_syms = bt_meta["symbols_tested"]
    rank250_usd = bt_meta["contest_constants"]["rank250_target_usd"]
    add(f"""<section id="backtests"><h2>Backtest lab — first walk-forward results</h2>
<p class="lead">The three pre-registered models were run through the repository's own deterministic
engine on the captured vendor daily bars: non-overlapping 30-calendar-day windows, each starting
from a fresh {money(cfg['starting_balance_virtual_usd'], 0)} account at {number(cfg['futures_leverage_ratio'], 0)}:1, across
{len(bt_syms)} symbols with sufficient history. These are independent daily-bar simulations —
NOT TradingView Strategy Report results, NOT competition-account results, and NOT recommendations.</p>
<div class="callout high"><h3>Read the verdicts correctly</h3>
<p>Verdicts apply each model's pre-registered falsification rule plus the testing plan's T5
decision rules. A "refuted" verdict means the rule fired (for example a non-positive median
across windows) — it does not prove the mechanism can never win a window, and a handful of
extreme windows can still exist. Engine re-runs are byte-verified by the offline verifier.</p></div>
<div class="grid cols-3">""")
    for m in backtests["models"]:
        zero = m["scenarios"]["zero"]
        pill = STATUS_PILL.get(m["verdict"], "mut")
        reasons = " ".join(m["verdict_reasons"][:2])
        add(f"""<article class="card strategy-card" data-verdict="{esc(m['id'])}"><div class="model-head"><span class="mono">{esc(m['id'])}</span><span class="pill {pill}">{esc(m['verdict'])}</span></div>
<h3>{esc(m['name'])}</h3>
<div class="stat accent">{money(zero['median_net_profit_usd'], 0)}</div>
<div class="note">median net profit per 30-day window (zero-cost, compounding sizing)</div>
<dl><dt>Windows / trades</dt><dd>{number(zero['windows'])} / {number(zero['trades'])}</dd>
<dt>Bootstrap 95% CI of median</dt><dd>{money(zero['bootstrap95_median_ci_usd'][0], 0)} … {money(zero['bootstrap95_median_ci_usd'][1], 0)}</dd>
<dt>Windows ≥ 5x / ≥ 10x</dt><dd>{number(zero['windows_ge_5x'])} / {number(zero['windows_ge_10x'])}</dd>
<dt>Best window</dt><dd>{esc(zero['best_window']['symbol'])} {esc(zero['best_window']['start'])} → {esc(zero['best_window']['end'])}: {money(zero['best_window']['net_profit_usd'], 0)} ({number(zero['best_window']['equity_multiple'], 2)}x)</dd>
<dt>Why</dt><dd>{esc(reasons)}</dd></dl></article>""")
    add(f"""</div>
<h3>Cost-scenario medians (net profit per window, compounding sizing)</h3>
<div class="table-wrap"><table id="bt-scenarios"><thead><tr><th>Model</th><th class="num">Zero cost</th>
<th class="num">Moderate ({esc(bt_meta['cost_scenarios']['moderate']['label'])})</th>
<th class="num">High ({esc(bt_meta['cost_scenarios']['high']['label'])})</th>
<th class="num">Positive windows (zero)</th><th class="num">Ruin windows (zero)</th></tr></thead><tbody>""")
    for m in backtests["models"]:
        z, mo, hi = (m["scenarios"][k] for k in ("zero", "moderate", "high"))
        add(f"""<tr><td class="sym">{esc(m['id'])} — {esc(m['name'])}</td>
<td class="num">{money(z['median_net_profit_usd'], 0)}</td>
<td class="num">{money(mo['median_net_profit_usd'], 0)}</td>
<td class="num">{money(hi['median_net_profit_usd'], 0)}</td>
<td class="num">{number(z['positive_windows_pct'], 1)}%</td>
<td class="num">{number(z['ruined_windows'])}</td></tr>""")
    add(f"""</tbody></table></div>
<h3>Median net profit by symbol (zero cost, compounding sizing)</h3>
<div class="table-wrap"><table id="bt-symbols"><thead><tr><th>Symbol</th>""")
    for m in backtests["models"]:
        add(f"<th class=\"num\">{esc(m['id'])} median $</th>")
    add("</tr></thead><tbody>")
    sym_set = []
    for m in backtests["models"]:
        for s in m["scenarios"]["zero"]["by_symbol_median_net_profit_usd"]:
            if s not in sym_set:
                sym_set.append(s)
    for s in sym_set:
        cells = []
        for m in backtests["models"]:
            v = m["scenarios"]["zero"]["by_symbol_median_net_profit_usd"].get(s)
            cls = "up" if (v or 0) > 0 else "down"
            cells.append(f'<td class="num {cls}">{money(v, 0) if v is not None else "—"}</td>')
        add(f'<tr><td class="sym">{esc(s)}</td>{"".join(cells)}</tr>')
    add(f"""</tbody></table></div>
<details class="assumptions"><summary>Sensitivity grid and declared assumptions</summary><ul>""")
    for a in bt_meta["assumptions"]:
        add(f"<li>{esc(a)}</li>")
    add("<li>Sensitivity variants (run at zero and moderate cost): "
        + esc("; ".join(f"{mid}: " + ", ".join(f"{label} = {params}" for label, params in grid.items())
                        for mid, grid in bt_meta["sensitivity_grid"].items())) + "</li>")
    add(f"""</ul></details>
<p class="note">Symbols excluded from testing and why: {esc('; '.join(f"{e['symbol']}: {e['reason']}" for e in bt_meta['symbols_excluded']) or 'none')}.</p>
<p class="note">Target context: the captured rank-{target_rank} P/L is {money(rank250_usd)} (snapshot {esc(bt_meta['contest_constants']['rank250_target_snapshot_utc'])}); a window counts as hitting the target when its net profit reaches that figure at that snapshot.</p>
<p class="note">Artifact stamp: <code>{esc(bt_stamp)}</code> — every run is byte-reproducible from the committed vendor captures via <code>python3 scripts/run_backtests.py --stamp {esc(bt_stamp)}</code>; the verifier re-runs exactly that and requires identical output.</p>
<p class="file-links"><a href="data/backtest_results.json">Full results (JSON)</a>
<a href="research/strategy/testing-plan.md">Testing protocol</a>
<a href="intel/">Engine source (intel/)</a></p></section>""")

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
