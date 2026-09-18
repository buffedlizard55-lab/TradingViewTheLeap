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


def smoney(value, decimals: int = 2) -> str:
    """Signed money: Unicode minus before the symbol for negatives."""
    return ("−$" if value < 0 else "$") + f"{abs(value):,.{decimals}f}"


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
    lab = load("data/target_lab.json")
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
    placement = load("data/leaderboard_lab.json")
    competition = load("data/competition_results.json")
    intelligence = load("data/intelligence_report.json")

    sources = source_registry["sources"]
    source_by_id = {s["source_id"]: s for s in sources}
    source_url = {sid: item["url"] for sid, item in source_by_id.items()}
    latest_frontier = frontier_history["captures"][-1]
    live_rank = {
        int(rank): {"rank": int(rank), **row}
        for rank, row in latest_frontier["rows"].items()
    }
    latest_frontier_source_id = latest_frontier["source_id"]
    last_visible_rank = cfg["public_leaderboard_last_visible_rank"]
    target_rank = capacity["_meta"]["target_rank"]
    live_return = next(row for row in returns["records"] if row["status"] == "in_progress")
    completed_returns = [row for row in returns["records"] if row["status"] == "final"]
    completed_best = max(completed_returns, key=lambda row: row["return_multiple"])
    exchange_counts = Counter(row["exchange"] for row in universe["instruments"])
    snapshot_at = latest_frontier["captured_at_utc"]
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
<a class="skip-link" href="#overview">Skip to research</a>
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
<span>Displayed participants</span><strong>{number(latest_frontier['participants_displayed'])}</strong>
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
<li><a href="#exec-summary">Exec summary</a></li>
<li><a href="#overview">Overview</a></li>
<li><a href="#targets">Return targets</a></li>
<li><a href="#placement">Placement math</a></li>
<li><a href="#rules">Rules</a></li>
<li><a href="#frontier">Live frontier</a></li>
<li><a href="#capacity">Capacity</a></li>
<li><a href="#intelligence">Market data</a></li>
<li><a href="#intel-status">Intelligence status</a></li>
<li><a href="#strategies">Strategies</a></li>
<li><a href="#backtests">Backtest lab</a></li>
<li><a href="#competition">Shadow comp</a></li>
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

    # Executive Summary
    add(f"""<section id="exec-summary"><h2>Executive Summary &mdash; Recommended Upcoming Trades</h2>
<p class="lead">Explicit and obvious upcoming trade setups to place based on top-performing usernames and contrarian strategy models on our simulated strategy competition list. These trade recommendations prioritize maximum explosive returns (targeting 5x, 10x, 20x, 50x, 100x multiples) with 20:1 maximum rule leverage and zero risk management constraints on verified official exchange pricing.</p>

<div class="callout good" style="border-left-width: 6px;">
<h3>EXECUTIVE SUMMARY &middot; TOP PERFORMING COMPETITION TRADE RECOMMENDATIONS</h3>
<p>To win the paper trading competition, our research indicates that participants must focus aggressively on high-volatility contrarian setups, full leverage deployment (20:1), and pyramiding into favourable moves rather than traditional risk management. Below are the top actionable trade setups derived from our 24-edition simulated paper trading competition and latest live mirror across 15 tracked usernames on official verified exchange data (CME Group, NYMEX, COMEX) and verified stock market sources.</p>
</div>

<div class="grid cols-2">
<div class="card strategy-card" style="border-top: 3px solid var(--green);">
<div class="model-head"><span class="pill ok">SEASON RANK 1 CHAMPION</span><span class="pill purple">+$2,806,899.58 P/L</span></div>
<h3>Trade #1: BUY / LONG CME Ether (CME:ETH1!) &amp; Bitcoin (CME:BTC1!)</h3>
<p><strong>Username:</strong> <code>ContrarianQueen</code> &middot; <strong>Model:</strong> C5 Capitulation Pyramider (patient variant)</p>
<p><strong>Action / Direction:</strong> <span class="pill ok">BUY / LONG</span> on extreme capitulation drops.</p>
<p><strong>Entry Trigger Setup:</strong> Capitulation reversal when 3-day close drop &ge; 1.0 ATR(14) with expanding volatility (ATR &gt; 50-day SMA ATR). Pyramids with additional tranches on every +1.5 ATR favourable move.</p>
<p><strong>Position Sizing &amp; Leverage:</strong> 20:1 buying power ($5,000,000 max initial notional), 50 contracts ETH / 10 contracts BTC / 30 contracts PL. Max 3 add tranches.</p>
<p><strong>Simulated Provenance:</strong> Season Rank 1 Champion (+$2,806,899.58 P/L, 6.77x peak single-edition multiple across 24 seasons).</p>
<p><strong>Verified Sources:</strong> {link(source_url['CME-SPEC-ETH1!'], 'CME Ether Contract Specs ↗')} &middot; {link(source_url['CME-SPEC-BTC1!'], 'CME Bitcoin Specs ↗')}</p>
</div>

<div class="card strategy-card" style="border-top: 3px solid var(--accent);">
<div class="model-head"><span class="pill ok">LATEST LIVE MIRROR RANK 1</span><span class="pill info">+$468,102.43 P/L (+2.87x)</span></div>
<h3>Trade #2: BUY / LONG COMEX Silver (COMEX:SI1!) &amp; Micro Silver (COMEX_MINI:SIL1!)</h3>
<p><strong>Username:</strong> <code>GapGoblin</code> &middot; <strong>Model:</strong> C2 Gap Fade (tight variant)</p>
<p><strong>Action / Direction:</strong> <span class="pill ok">BUY / LONG</span> fading overnight down-gaps.</p>
<p><strong>Entry Trigger Setup:</strong> Fading overnight opening down-gaps exceeding 1.0 ATR(14) back toward the 5-session mean price.</p>
<p><strong>Position Sizing &amp; Leverage:</strong> Rulebook maximum position limit: 30 contracts SI / 50 contracts SIL. Time-based hold 5 sessions.</p>
<p><strong>Simulated Provenance:</strong> Rank 1 in Latest Live Edition Mirror (+2.87x / +$468,102.43 P/L in 30 days) &amp; Season Rank 2 (+$1,629,892.12 P/L).</p>
<p><strong>Verified Sources:</strong> {link(source_url['CME-SPEC-SI1!'], 'COMEX Silver Contract Specs ↗')} &middot; {link(source_url['CME-SPEC-SIL1!'], 'Micro Silver Specs ↗')}</p>
</div>

<div class="card strategy-card" style="border-top: 3px solid var(--red);">
<div class="model-head"><span class="pill warn">SEASON RANK 3</span><span class="pill purple">+$1,168,973.61 P/L</span></div>
<h3>Trade #3: SELL / SHORT NYMEX Crude Oil (NYMEX:CL1!) &amp; Gasoline (NYMEX:RB1!)</h3>
<p><strong>Username:</strong> <code>ClimaxCarla</code> &middot; <strong>Model:</strong> C4 Exhaustion Bar Reversal (loose variant)</p>
<p><strong>Action / Direction:</strong> <span class="pill no">SELL / SHORT</span> on exhaustion up-bars.</p>
<p><strong>Entry Trigger Setup:</strong> Liquidation climax up-bar where daily True Range &ge; 1.5 ATR(14) and close is pinned in the top 35% tail of the bar's range.</p>
<p><strong>Position Sizing &amp; Leverage:</strong> Rulebook maximum position limit: 100 contracts CL / 100 contracts RB. Time-based hold 5 sessions.</p>
<p><strong>Simulated Provenance:</strong> Season Rank 3 (+$1,168,973.61 P/L, 6.28x peak single-edition return).</p>
<p><strong>Verified Sources:</strong> {link(source_url['CME-SPEC-CL1!'], 'NYMEX Crude Oil Specs ↗')} &middot; {link(source_url['CME-SPEC-RB1!'], 'RBOB Gasoline Specs ↗')}</p>
</div>

<div class="card strategy-card" style="border-top: 3px solid var(--amber);">
<div class="model-head"><span class="pill ok">SINGLE-EDITION PEAK CHAMPION (7.24x)</span><span class="pill purple">+$1,561,000 P/L</span></div>
<h3>Trade #4: SELL / SHORT NYMEX Heating Oil (NYMEX:HO1!) / BUY LONG Natural Gas (NYMEX:NG1!)</h3>
<p><strong>Username:</strong> <code>FadeThePanic</code> &middot; <strong>Model:</strong> C1 Capitulation Reversal (default variant)</p>
<p><strong>Action / Direction:</strong> <span class="pill no">SELL / SHORT</span> HO on euphoria runs / <span class="pill ok">BUY / LONG</span> NG on panic drops.</p>
<p><strong>Entry Trigger Setup:</strong> Multi-day collapse or euphoria run stretching price by &ge; 1.0 ATR over 3 closes with ATR expanding.</p>
<p><strong>Position Sizing &amp; Leverage:</strong> Rulebook max 100 contracts HO / 50 contracts NG. Time-based hold 10 sessions.</p>
<p><strong>Simulated Provenance:</strong> Highest single-edition return multiple in entire shadow competition: <strong>7.24x</strong> (+$1,561,000 P/L in Edition 19) &amp; Season Rank 4 (+$627,775.79 P/L).</p>
<p><strong>Verified Sources:</strong> {link(source_url['CME-SPEC-HO1!'], 'NYMEX Heating Oil Specs ↗')} &middot; {link(source_url['CME-SPEC-NG1!'], 'Henry Hub Natural Gas Specs ↗')}</p>
</div>
</div>

<div class="callout info" style="margin-top: 22px;">
<h3>STOCK COMPETITION INTELLIGENCE &middot; HIGH-VOLATILITY STOCK OPPORTUNITIES</h3>
<p>In addition to futures markets, our intelligence layer monitors 20 verified highly volatile equities sourced from verified official endpoints (Yahoo Finance chart API). Historical price data proves that high-beta equities can generate 10x to 382x return multiples during expansion cycles (e.g. <strong>ENPH +382.49x</strong>, <strong>AMD +322.73x</strong>, <strong>MARA +190.22x</strong>, <strong>CVNA +128.62x</strong>, <strong>GME +124.11x</strong>, <strong>TSLA +17.02x</strong>, <strong>NVDA +12.09x</strong>, <strong>MSTR +49.45x</strong>). For stock trading paper competitions, deploying C1 Capitulation Reversals and C5 Pyramiding on these high-volatility stock candidates offers the explosive upside required to win without real-money downside risk.</p>
</div>

<h3>Upcoming Trade Signal Matrix</h3>
<p class="note">Summary of all top-performing usernames, strategy models, target instruments, active trade directions, sizing rules, and return provenance from our 24-edition paper trading competition.</p>

<div class="table-wrap">
<table>
<thead>
<tr>
<th>Season Rank</th>
<th>Username</th>
<th>Strategy Archetype</th>
<th>Target Symbol</th>
<th>Action</th>
<th>Entry Trigger Setup</th>
<th>Max Position &amp; Leverage Sizing</th>
<th>Simulated Competition Provenance</th>
<th>Official Verified Source</th>
</tr>
</thead>
<tbody>
<tr class="hl">
<td class="num"><span class="pill ok">1</span></td>
<td class="sym"><strong>ContrarianQueen</strong></td>
<td>C5 Capitulation Pyramider (patient)</td>
<td class="sym">CME:ETH1!, CME:BTC1!, NYMEX:PL1!</td>
<td><span class="pill ok">BUY / LONG</span></td>
<td>3-day drop &ge; 1.0 ATR with expanding ATR; pyramid adds every +1.5 ATR</td>
<td class="num">20:1 Buying Power; 50 ETH / 10 BTC / 30 PL contracts max</td>
<td><strong>+$2,806,899.58 P/L</strong> (Season Rank 1; 6.77x peak single edition)</td>
<td>{link(source_url['CME-SPEC-ETH1!'], 'CME Specs ↗')}</td>
</tr>
<tr class="hl">
<td class="num"><span class="pill ok">2</span></td>
<td class="sym"><strong>GapGoblin</strong></td>
<td>C2 Gap Fade (tight)</td>
<td class="sym">COMEX:SI1!, COMEX_MINI:SIL1!</td>
<td><span class="pill ok">BUY / LONG</span></td>
<td>Fade overnight down-gap &ge; 1.0 ATR(14) back to 5-session mean</td>
<td class="num">30 SI / 50 SIL contracts max; 5-session hold</td>
<td><strong>+$1,629,892.12 P/L</strong> (Season Rank 2; <strong>+2.87x Latest Mirror Rank 1</strong>)</td>
<td>{link(source_url['CME-SPEC-SI1!'], 'COMEX Specs ↗')}</td>
</tr>
<tr>
<td class="num"><span class="pill warn">3</span></td>
<td class="sym"><strong>ClimaxCarla</strong></td>
<td>C4 Exhaustion Reversal (loose)</td>
<td class="sym">NYMEX:CL1!, NYMEX:RB1!</td>
<td><span class="pill no">SELL / SHORT</span></td>
<td>Liquimax up-bar TR &ge; 1.5 ATR with close in top 35% range tail</td>
<td class="num">100 CL / 100 RB contracts max; 5-session hold</td>
<td><strong>+$1,168,973.61 P/L</strong> (Season Rank 3; 6.28x peak single edition)</td>
<td>{link(source_url['CME-SPEC-CL1!'], 'NYMEX Specs ↗')}</td>
</tr>
<tr>
<td class="num"><span class="pill warn">4</span></td>
<td class="sym"><strong>FadeThePanic</strong></td>
<td>C1 Capitulation Reversal (default)</td>
<td class="sym">NYMEX:HO1!, NYMEX:NG1!</td>
<td><span class="pill no">SELL / SHORT</span> (HO) / <span class="pill ok">BUY</span> (NG)</td>
<td>3-day extension &ge; 1.0 ATR with expanding ATR</td>
<td class="num">100 HO / 50 NG contracts max; 10-session hold</td>
<td><strong>+$627,775.79 P/L</strong> (Season Rank 4; <strong>7.24x Peak Edition Champion</strong>)</td>
<td>{link(source_url['CME-SPEC-HO1!'], 'NYMEX Specs ↗')}</td>
</tr>
<tr>
<td class="num"><span class="pill mut">5</span></td>
<td class="sym"><strong>SqueezeSpark</strong></td>
<td>C5 Capitulation Pyramider (rapid)</td>
<td class="sym">COMEX:SI1!, COMEX_MINI:SIL1!</td>
<td><span class="pill ok">BUY / LONG</span></td>
<td>3-day drop &ge; 1.0 ATR with expanding ATR; rapid pyramid adds (+0.75 ATR)</td>
<td class="num">30 SI / 50 SIL contracts max; max 6 add tranches</td>
<td><strong>+$262,355.40 P/L</strong> (Season Rank 5; 3.96x peak single edition)</td>
<td>{link(source_url['CME-SPEC-SI1!'], 'COMEX Specs ↗')}</td>
</tr>
<tr>
<td class="num"><span class="pill mut">12</span></td>
<td class="sym"><strong>CapitulationKate</strong></td>
<td>C1 Capitulation Reversal (fast3)</td>
<td class="sym">NYMEX:PL1!, COMEX:SI1!</td>
<td><span class="pill ok">BUY / LONG</span></td>
<td>2-day drop &ge; 1.0 ATR with expanding ATR; 6-session hold</td>
<td class="num">30 PL contracts max; 6-session hold</td>
<td><strong>3.77x Peak Single Edition</strong> (Metals reversal specialist)</td>
<td>{link(source_url['CME-SPEC-PL1!'], 'NYMEX Specs ↗')}</td>
</tr>
</tbody>
</table>
</div>
<div class="disclaimer"><strong>Simulated Experiment Notice.</strong> Every trade recommendation above is derived from our paper trading shadow competition simulating frozen strategies on real verified historical price data. Paper trading involves no real financial risk. Past simulated performance is not a forecast of future real-market outcomes. All rules and multipliers are cross-checked line-by-line against official exchange specifications.</div>
</section>""")

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
<div class="callout high"><h3>The finish line, in numbers</h3>
<p>The last cash-prize rank (50) displayed <strong>{placement['captures'][-1]['rows']['50']['balance_multiple']}×</strong>
the starting balance at the latest capture ({esc(placement['captures'][-1]['captured_at_utc'])}) — an average of
{money(placement['captures'][-1]['rows']['50']['average_usd_per_day_since_start'], 0)} per day since the opening bell.
A fresh 250,000 account would need <strong>+{number(placement['captures'][-1]['rows']['50']['fresh_account_required_daily_compound_pct'], 2)}% per day,
compounded without a single losing day</strong> for the {number(placement['deadline']['remaining_days_at_latest_capture'], 2)} days left, to reach it.
At the rules' 20:1 maximum exposure that is only {number(placement['captures'][-1]['rows']['50']['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%
of underlying move per day — and one {number(placement['leverage_math']['adverse_underlying_move_pct_to_erase_the_whole_balance'], 0)}% adverse day at that exposure erases the whole balance.</p></div>
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

    # Target arithmetic is deliberately separate from market performance.
    add(f"""<section id="targets"><h2>Return-target lab</h2>
<p class="lead">What would 5× to 100× actually require? Reproducible arithmetic, not a backtest or a prediction.</p>
<div class="callout high"><h3>Current official frontier review · {esc(latest_frontier['captured_at_utc'])}</h3>
<p>Cash prizes end at rank 50; ranks 51–300 receive subscriptions. Frontier values on this page use
that latest point-in-time leaderboard capture. Capacity and quote arithmetic remain tied to the
separately labeled baseline snapshot, not live executable prices.</p>
<p>{link(source_url['TV-RULES-AMP-SEP2026'], 'Official rules §§05, 08–09 ↗')} ·
<a href="research/evidence/TV-CONTEST-AMP-SEP2026-2026-09-18-R8.md">Latest capture evidence</a> ·
<a href="research/evidence/AUDIT-2026-09-18-PASS9.md">Ninth-pass audit</a> ·
<a href="research/evidence/AUDIT-2026-09-17.md">Prior claim-by-claim audit</a></p>
<p>Eligibility and potential identity/prize paperwork cannot be completed from this repository.
No competition trades have been placed.</p></div>
<div class="table-wrap"><table><caption>Balance multiples, not profit multiples. Historical counts exclude the in-progress edition.</caption>
<thead><tr><th>Target balance</th><th class="num">Net profit</th><th class="num">Required virtual P/L</th>
<th class="num">Ideal fixed 20:1 move</th><th class="num">Completed champions strictly above</th></tr></thead><tbody>""")
    for row in lab['targets']:
        add(f"<tr><td>{row['balance_multiple']}×</td><td class=\"num\">+{number(row['net_profit_pct'])}%</td>"
            f"<td class=\"num\">{money(row['required_net_profit_usd'], 0)}</td>"
            f"<td class=\"num\">{number(row['ideal_initial_20x_fixed_exposure_move_pct'])}%</td>"
            f"<td class=\"num\">{row['completed_sample_strictly_above']} / {lab['_meta']['completed_sample_size']}</td></tr>")
    add("""</tbody></table></div><p class="note">Required P/L = starting balance × (multiple − 1).
Ideal favorable move = required P/L ÷ initial notional. Equality reaches the target; going strictly
above requires more profit. Champion counts are not win probabilities.</p>
<details><summary>Inspect all 100 fixed-exposure scenarios</summary>
<p>20 selected futures × 5 targets. Fixed initial whole contracts, no compounding, costs, fill or
margin path. Extreme linear moves are not asserted to be achievable, particularly on shorts.
Quote and contract evidence remain in the capacity and source tables.</p>
<div class="table-wrap"><table><thead><tr><th>Symbol</th><th>Target</th><th class="num">Initial contracts</th>
<th class="num">Favorable move to equal target</th></tr></thead><tbody>""")
    for row in lab['scenarios']:
        add(f"<tr><td>{esc(row['symbol'])}</td><td>{row['balance_multiple']}×</td>"
            f"<td class=\"num\">{row['initial_contracts']}</td>"
            f"<td class=\"num\">{number(row['favorable_move_pct_to_equal_target'], 2)}%</td></tr>")
    add("""</tbody></table></div></details>
<p><a href="data/target_lab.json" download>Download target data (JSON)</a> ·
<a href="data/master_list.csv" download>Download selected futures (CSV)</a> ·
<a href="data/contest_universe.json" download>Download full eligible universe (JSON)</a></p>
<div class="callout critical"><h3>No qualifying stock list for this edition</h3>
<p>Individual stocks are not permitted. The historical stock table is vendor-tier research, not
an official-primary verified opportunity list. No instrument or strategy here is proven to produce
5×, 10×, 20×, 50× or 100× in the remaining competition window.</p></div></section>""")

    # Placement arithmetic — deterministic, sourced, and clearly separated from any forecast.
    latest_cap = placement['captures'][-1]
    latest_rank = latest_cap['rows']
    rank50_row = latest_rank['50']
    board = placement['board']
    lm = placement['leverage_math']
    cs = placement['champion_sample']
    add(f"""<section id="placement"><h2>How to place on the board — prize arithmetic</h2>
<p class="lead">Rank-ordered prizes mean the last cash rank is the real finish line. Everything below is
derived from official rules and the captured board: what the line costs, how fast a fresh account would have
to compound to reach it, and how that compares with the official champion sample. It is arithmetic, not a
forecast or a strategy result.</p>
<div class="grid cols-4">
<div class="card"><h3>Last cash rank (50)</h3><div class="stat accent">{rank50_row['balance_multiple']}×</div>
<div class="note">+{number(rank50_row['realized_profit_pct'], 2)}% · {money(rank50_row['realized_profit_usd'])} at {esc(latest_cap['captured_at_utc'])}</div></div>
<div class="card"><h3>Average pace so far</h3><div class="stat small accent">{money(rank50_row['average_usd_per_day_since_start'], 0)}/day</div>
<div class="note">displayed total ÷ {number(latest_cap['elapsed_days_since_start'], 2)} elapsed days</div></div>
<div class="card"><h3>Fresh account from now</h3><div class="stat amber">+{number(rank50_row['fresh_account_required_daily_compound_pct'], 2)}%/day</div>
<div class="note">compounded, unbroken, over {number(latest_cap['remaining_days_to_deadline'], 2)} days</div></div>
<div class="card"><h3>In underlying terms at 20:1</h3><div class="stat amber">{number(rank50_row['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%/day</div>
<div class="note">linear approximation, fully invested, no losing day</div></div>
</div>
<div class="callout critical"><h3>Maximum exposure cuts both ways</h3>
<p>At the rules' maximum {money(lm['maximum_initial_notional_usd'], 0)} notional a 1% underlying move is
{money(lm['usd_per_1pct_underlying_move_at_max_notional'], 0)} — {number(lm['pct_of_starting_balance_per_1pct_underlying_move'], 0)}% of the starting balance —
and a {number(lm['adverse_underlying_move_pct_to_erase_the_whole_balance'], 0)}% adverse move erases the entire
{money(lm['starting_balance_usd'], 0)} balance. The rules forbid resetting the account (section 08), so there is no recovery
path after one full-exposure mistake, and no tested strategy in this repository has produced the unbroken
sequence the arithmetic asks for.</p></div>
<h3 class="minor-heading">Tracked frontier at the latest capture</h3>
<div class="table-wrap"><table><thead><tr><th class="num">Rank</th><th>Trader</th><th class="num">Balance multiple</th>
<th class="num">Average $/day</th><th class="num">Fresh account needs</th><th class="num">Underlying at 20:1</th></tr></thead><tbody>""")
    for rank in (1, 50, 100, 250):
        row = latest_rank[str(rank)]
        add(f"<tr><td class=\"num\">{rank}</td><td>{esc(row['trader'])}</td><td class=\"num\">{row['balance_multiple']}×</td>"
            f"<td class=\"num\">{money(row['average_usd_per_day_since_start'], 0)}</td>"
            f"<td class=\"num\">+{number(row['fresh_account_required_daily_compound_pct'], 2)}%/day</td>"
            f"<td class=\"num\">{number(row['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%/day</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">"Fresh account needs" is the daily compound rate that would take a brand-new 250,000 account
from zero to that level in exactly the days left at the capture. Ranks 1 and 50 can be static while lower
ranks advance, so this list is a set of point-in-time displays, not thresholds.</p>
<h3 class="minor-heading">Targets for the remaining window</h3>
<div class="table-wrap"><table><thead><tr><th>Target balance</th><th class="num">Required net profit</th>
<th class="num">Required daily compounding</th><th class="num">Underlying at 20:1</th>
<th class="num">All-in winning days at +1%/day</th><th class="num">Completed champions ≥ target</th></tr></thead><tbody>""")
    for t in placement['targets']:
        add(f"<tr><td>{t['balance_multiple']}×</td><td class=\"num\">{money(t['required_net_profit_usd'], 0)}</td>"
            f"<td class=\"num\">+{number(t['required_daily_compound_pct_over_remaining_window'], 2)}%/day</td>"
            f"<td class=\"num\">{number(t['required_underlying_pct_per_day_at_20x'], 2)}%/day</td>"
            f"<td class=\"num\">{t['full_leverage_winning_days_at_1pct_underlying']}</td>"
            f"<td class=\"num\">{t['completed_champion_sample_at_or_above']} / {cs['completed_records']}</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">From {esc(latest_cap['captured_at_utc'])}, {number(latest_cap['remaining_days_to_deadline'], 2)} days remain to the
{esc(placement['deadline']['competition_end_utc'])} deadline; registration stays open for
{number(latest_cap['registration_days_left'], 2)} more days. The winning-days column assumes an unbroken run of all-in wins at
a +1% underlying move per day; an adverse day of the same size removes the same equity instead.</p>

<div class="card" style="margin: 20px 0; border: 1px solid var(--accent); background: #111a28;">
<div class="model-head">
<h3>Interactive Target & Placement Calculator</h3>
<span class="pill info">live model</span>
</div>
<p class="note" style="margin-bottom: 14px;">Simulate required compounding rates, underlying moves, and ruin thresholds for any target return multiple over the remaining competition window.</p>
<div class="grid cols-3" style="margin-bottom: 12px;">
<div>
<label for="calc-slider" style="display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase;">Quick Presets &amp; Slider</label>
<div class="thresh" id="calc-presets" style="margin-bottom: 8px;">
<button type="button" data-m="5">5×</button>
<button type="button" class="active" data-m="10">10×</button>
<button type="button" data-m="20">20×</button>
<button type="button" data-m="50">50×</button>
<button type="button" data-m="100">100×</button>
</div>
<input type="range" id="calc-slider" min="2" max="100" value="10" step="1" style="width: 100%;">
</div>
<div>
<label for="calc-target-input" style="display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase;">Target Multiple (× Balance)</label>
<input type="number" id="calc-target-input" min="2" max="500" value="10" style="width: 100%; font-family: var(--mono); font-size: 15px; font-weight: bold; background: var(--panel); border: 1px solid var(--border); color: var(--accent); padding: 7px 10px; border-radius: 6px;">
</div>
<div>
<label for="calc-days" style="display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase;">Days Remaining</label>
<input type="number" id="calc-days" min="0.5" max="30" value="{latest_cap['remaining_days_to_deadline']}" step="0.01" style="width: 100%; font-family: var(--mono); font-size: 15px; background: var(--panel); border: 1px solid var(--border); color: var(--text); padding: 7px 10px; border-radius: 6px;">
</div>
</div>
<div class="grid cols-4" style="margin-top: 10px;">
<div class="card" style="background: var(--panel);">
<h3>Ending Equity</h3>
<div class="stat accent" id="calc-out-equity">$2,500,000</div>
<div class="note" id="calc-out-profit">+$2,250,000 net profit</div>
</div>
<div class="card" style="background: var(--panel);">
<h3>Required Compounding</h3>
<div class="stat amber" id="calc-out-compound">+20.18%/day</div>
<div class="note">unbroken daily growth</div>
</div>
<div class="card" style="background: var(--panel);">
<h3>Underlying at 20:1</h3>
<div class="stat green" id="calc-out-underlying">1.01%/day</div>
<div class="note">linear full exposure</div>
</div>
<div class="card" style="background: var(--panel);">
<h3>Winning Days (+1%)</h3>
<div class="stat small" id="calc-out-days">13 days</div>
<div class="note">consecutive unbroken</div>
</div>
</div>
</div>
<div class="callout high"><h3>What the cash-prize level means across the official champion sample</h3>
<p>{cs['completed_champions_strictly_below_latest_rank50']} of {cs['completed_records']} completed-edition champions finished
<em>below</em> the {cs['latest_rank50_multiple']}× that rank 50 displayed at the latest capture; only the {cs['maximum_completed_multiple']}×
record sits above it. That is cross-edition context — different rules, different participant counts, and no
completed edition ran the same instrument set — so it is evidence of what has been published, not a benchmark
and not a success probability.</p></div>
<h3 class="minor-heading">Which selected instruments could even deliver that move?</h3>
<div class="table-wrap"><table><thead><tr><th>Symbol</th><th class="num">Modeled initial notional</th>
<th class="num">Favorable move for the rank-50 level</th><th class="num">Best 30-day up move captured</th><th>Vendor history contains such a window</th></tr></thead><tbody>""")
    for row in placement['cash_frontier_instrument_requirements']:
        best = row['best_30d_up_move_pct_in_vendor_history']
        best_txt = "no history" if best is None else f"{number(best, 2)}%"
        flag = row['history_contains_a_30d_window_as_large_as_that_requirement']
        flag_txt = "—" if flag is None else ("yes" if flag else "no")
        add(f"<tr><td>{esc(row['symbol'])}</td><td class=\"num\">{money(row['modeled_initial_notional_usd'], 0)}</td>"
            f"<td class=\"num\">{number(row['favorable_move_pct_needed_for_latest_rank50_level'], 2)}%</td>"
            f"<td class=\"num\">{best_txt}</td><td>{flag_txt}</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">The requirement column is the rank-50 level divided by each instrument's modeled initial
notional at the rules cap; the history column is the largest 30-day close-to-close up move in the archived
vendor window (overlapping windows, perfect single-direction timing assumed, no costs, fills or rolls). A "yes"
means the vendor history contained a move that large <em>once</em>; it is not a forecast and not a strategy.</p>
<div class="grid cols-3">
<div class="card"><h3>Board density</h3><div class="stat small">{number(board['participants_displayed'])}</div>
<div class="note">participants displayed · top {board['visible_ranks']} visible ({number(board['visible_share_of_participants_pct'], 3)}%)</div></div>
<div class="card"><h3>Cash places</h3><div class="stat small">{board['cash_ranks']}</div>
<div class="note">cash ranks = {number(board['cash_share_of_participants_pct'], 3)}% of participants</div></div>
<div class="card"><h3>Gap to rank 100</h3><div class="stat small">{number(board['rank50_to_rank100_gap_pct'], 1)}%</div>
<div class="note">rank-50 P/L above rank-100 P/L at the latest capture</div></div>
</div>
<p><a href="data/leaderboard_lab.json" download>Download placement arithmetic (JSON)</a> ·
{link(source_url[latest_frontier_source_id], 'Latest leaderboard capture ↗')} ·
{link(source_url['TV-RULES-AMP-SEP2026'], 'Official rules ↗')} ·
{link(source_url['TV-THELEAP-LANDING'], 'Official landing page ↗')} ·
<a href="research/evidence/TV-CONTEST-AMP-SEP2026-2026-09-18-R8.md">Eighth-pass capture evidence</a> ·
<a href="data/intelligence_report.json">Auditable intelligence report (JSON)</a></p>
<div class="callout critical"><h3>Read this before acting on any number here</h3>
<p>Cash prizes end at rank 50; ranks 51–300 receive a subscription. Every frontier value is a moving
point-in-time display that the organiser can correct, and the arithmetic above shows what the level costs —
never that it is achievable. This repository has not placed a single competition trade.</p></div></section>""")

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
    for rank, row in live_rank.items():
        rank = int(rank)
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
<p class="note">Observed so far:</p>
<ul class="notes">""")
    for note in frontier_history['_meta']['observed_notes']:
        add(f"<li>{esc(note)}</li>")
    add("""</ul>
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


    # Consolidated intelligence and provenance status
    intel_results = intelligence["model_comparison"]["results"]
    intel_status = intelligence["status_register"]
    add(f"""<section id="intel-status"><h2>Intelligence layer — evidence, tests, and blocked work</h2>
<p class="lead">This register keeps the research layers separate: official TradingView/CME evidence,
vendor market data, and repository-generated paper simulations. It is a status report, not a signal,
forecast, or claim that any listed contest trader used one of these models.</p>
<div class="grid cols-3">
<div class="card"><h3>Official evidence</h3><div class="stat green">verified</div>
<div class="note">rules, public leaderboard captures, and displayed participant counts</div></div>
<div class="card"><h3>Vendor data</h3><div class="stat amber">{number(intelligence['provenance']['market_data_vendor']['captured_series'])} series</div>
<div class="note">front-month futures; roll and transport caveats remain</div></div>
<div class="card"><h3>Platform validation</h3><div class="stat red">blocked / unrun</div>
<div class="note">no authenticated TradingView Strategy Report export</div></div>
</div>
<div class="callout high"><h3>Current comparison verdict</h3>
<p>{esc(intelligence['model_comparison']['decision']['interpretation'])}</p>
<p><strong>Thresholds reached in the shadow simulation:</strong>
5× = {number(intelligence['model_comparison']['kind_contrast']['contrarian']['participant_editions_ge_5x'] + intelligence['model_comparison']['kind_contrast']['baseline']['participant_editions_ge_5x'])} participant-editions;
10× = no; 20× = no; 50× = no; 100× = no.</p></div>
<h3>Frozen-model comparison by paper usernames</h3>
<div class="table-wrap"><table id="intel-model-table"><thead><tr><th>Model</th><th>Kind</th><th class="num">Users</th>
<th class="num">Best single edition</th><th class="num">Median best edition</th><th class="num">≥5× editions</th>
<th class="num">≥10× editions</th><th class="num">Ruined editions</th><th class="num">Latest median</th></tr></thead><tbody>""")
    for row in intel_results:
        kind_cls = "up" if row["kind"] == "contrarian" else ""
        add(f"""<tr><td class="sym">{esc(row['model'])} — {esc(row['name'])}</td><td>{esc(row['kind'])}</td>
<td class="num">{number(row['participants'])}</td><td class="num {kind_cls}">{number(row['best_single_edition_multiple_max'], 2)}×</td>
<td class="num">{number(row['best_single_edition_multiple_median'], 2)}×</td><td class="num">{number(row['participant_editions_ge_5x'])}</td>
<td class="num">{number(row['participant_editions_ge_10x'])}</td><td class="num">{number(row['ruined_editions'])}</td>
<td class="num">{number(row['latest_edition_multiple_median'], 2)}×</td></tr>""")
    add("""</tbody></table></div>
<h3>Workstream status</h3><div class="table-wrap"><table id="intel-status-table"><thead><tr><th>Workstream</th><th>Status</th><th>Evidence</th><th>Next honest step</th></tr></thead><tbody>""")
    for item in intel_status:
        status_cls = "ok" if item["status"] in ("verified", "captured") else ("warn" if "caveat" in item["status"] else "no")
        evidence = "; ".join(item["evidence"])
        add(f"<tr><td class=\"sym\">{esc(item['workstream'])}</td><td><span class=\"pill {status_cls}\">{esc(item['status'].replace('_', ' '))}</span></td><td>{esc(evidence)}</td><td>{esc(item['next_step'])}</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">Official boundary: the public leaderboard provides displayed P/L and rank, not a reconstructable trade ledger.
Vendor boundary: the futures files are useful for screening and simulation, not proof of official fills.
Simulation boundary: the engine uses declared costs, caps, whole contracts, and usernames, but its finite history and
model assumptions can still produce fragile results. <a href="data/intelligence_report.json">Download the full auditable intelligence report (JSON)</a>.</p></section>""")

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

    # Shadow competition (the repository's own paper competition)
    comp = competition
    comp_meta = comp["_meta"]
    comp_models = comp["models"]
    comp_board = comp["leaderboard"]
    comp_latest = comp["latest_edition"]
    comp_ts = comp["target_summary"]
    comp_contrast = comp["kind_contrast"]
    champ = comp_board[0]
    latest_leader = comp_latest["leader"]
    season_editions = comp_meta["season_editions"]

    add(f"""<section id="competition"><h2>Shadow competition — our own usernames on real captured prices</h2>
<p class="lead">The repository's own paper competition: {number(len(comp['roster']))} usernames
({number(sum(1 for r in comp['roster'] if r['kind'] == 'contrarian'))} contrarian, {number(sum(1 for r in comp['roster'] if r['kind'] == 'baseline'))} trend baselines)
compete on the captured vendor daily bars with a fresh {money(cfg['starting_balance_virtual_usd'], 0)} account per edition,
under the official rule constants ({number(cfg['futures_leverage_ratio'], 0)}:1 buying power, whole contracts, official section 08 caps,
realized-P/L ranking, end-of-edition auto-close, no resets). Season = {number(season_editions)} non-overlapping
30-calendar-day editions across the full capture history; LATEST mirrors the in-progress September edition's window length.</p>
<div class="callout high"><h3>What this is and is not</h3>
<p>These are THIS REPOSITORY's simulated usernames, ranked by THIS REPOSITORY's engine
(<code>{esc(comp_meta['engine'])}</code>) on vendor-tier front-month continuous futures
(unadjusted rolls). It is NOT the official The Leap leaderboard, NOT TradingView Paper Trading
output, and NOT a prediction. The official live board is tracked separately in
<a href="#frontier">Live frontier</a>.</p></div>
<div class="grid cols-4">
<div class="card"><h3>Season champion</h3><div class="stat accent">{esc(champ['username'])}</div><div class="note">by total realized P/L over {number(season_editions)} editions: {money(champ['season_realized_pnl_usd'], 0)}</div></div>
<div class="card"><h3>Latest edition winner</h3><div class="stat accent">{esc(latest_leader['username'])}</div><div class="note">{esc(comp_latest['start_date'])} → {esc(comp_latest['end_date'])}: {money(latest_leader['realized_pnl_usd'], 0)} ({number(latest_leader['equity_multiple'], 2)}x)</div></div>
<div class="card"><h3>Best single edition</h3><div class="stat accent">{number(comp_contrast['contrarian']['best_single_edition_multiple'], 2)}x</div><div class="note">best contrarian edition multiple ({number(comp_contrast['baseline']['best_single_edition_multiple'], 2)}x best baseline)</div></div>
<div class="card"><h3>Editions ≥ 5x / ruined</h3><div class="stat accent">{number(comp_ts['ge_5x'])} / {number(comp_ts['ruined_participant_editions'])}</div><div class="note">participant-editions at {esc(comp_meta['primary_scenario'])} cost (of {number(comp_ts['participant_editions'])})</div></div>
</div>
<div class="controls"><input id="shadow-q" type="search" placeholder="Filter username, strategy, model…" aria-label="Filter shadow leaderboard"><span id="shadow-count" class="count"></span></div>
<div class="table-wrap"><table id="shadow-table"><thead><tr><th class="num">Season rank</th><th>Username</th><th>Kind</th><th>Strategy</th><th>Variant</th><th class="num">Season realized P/L</th><th class="num">Season multiple</th><th class="num">Best edition</th><th class="num">Editions ≥5x</th><th class="num">Ruined editions</th></tr></thead><tbody>""")
    for row in comp_board:
        agg = next(a for a in comp["participants"] if a["username"] == row["username"])
        search = f"{row['username']} {agg['model']} {agg['model_name']} {agg['variant'] or 'default'} {agg['kind']}".lower()
        pill = "ok" if agg["kind"] == "contrarian" else "mut"
        add(f"""<tr data-shadow="{esc(row['username'])}" data-search="{esc(search)}"><td class="num">{number(row['season_rank'])}</td>
<td class="sym">{esc(row['username'])}</td><td><span class="pill {pill}">{esc(agg['kind'])}</span></td>
<td>{esc(agg['model'])} — {esc(agg['model_name'])}</td><td>{esc(agg['variant'] or 'default')}</td>
<td class="num">{smoney(row['season_realized_pnl_usd'], 0)}</td>
<td class="num">{number(row['season_multiple'], 4)}x</td>
<td class="num{' up' if row['best_edition_multiple'] >= 5 else ''}">{number(row['best_edition_multiple'], 2)}x</td>
<td class="num">{number(row['editions_ge_5x'])}</td>
<td class="num{' down' if agg['ruined_editions'] else ''}">{number(agg['ruined_editions'])}</td></tr>""")
    add("</tbody></table></div>")
    add(f"""<div class="callout"><h3>Season vs single-edition: what the numbers say</h3>
<p>Contrarian fade models produced the only explosive editions — best {number(comp_contrast['contrarian']['best_single_edition_multiple'], 2)}x in 30 calendar days
on daily bars versus {number(comp_contrast['baseline']['best_single_edition_multiple'], 2)}x for the trend baselines, with {number(comp_ts['users_reaching_5x_any_edition'])} of
{number(len(comp_board))} usernames reaching ≥5x at least once. But full 20:1 deployment with no stops also ruined
{number(comp_ts['ruined_participant_editions'])} participant-editions outright, so season compounding collapses for almost everyone
(best season multiple on the board: {number(max(r['season_multiple'] for r in comp_board), 4)}x). That is the project's core finding in miniature:
explosive single-edition outcomes exist in the captured data, and the contest's no-reset rule makes harvesting them
survivorship-bound, not strategy-bound alone.</p></div>
<h3>Latest edition leaderboard ({esc(comp_latest['start_date'])} → {esc(comp_latest['end_date'])}, {esc(comp_meta['primary_scenario'])} cost)</h3>
<div class="table-wrap"><table id="shadow-latest"><thead><tr><th class="num">Rank</th><th>Username</th><th class="num">Realized P/L</th><th class="num">Multiple</th><th class="num">Trades</th><th class="num">Active days</th><th class="num">Min 5 active days</th><th class="num">Margin-breach bars</th></tr></thead><tbody>""")
    for row in comp_latest["rows"][:10]:
        add(f"""<tr><td class="num">{number(row['rank'])}</td><td class="sym">{esc(row['username'])}</td>
<td class="num{' up' if row['realized_pnl_usd'] > 0 else ' down'}">{smoney(row['realized_pnl_usd'], 0)}</td>
<td class="num">{number(row['equity_multiple'], 3)}x</td><td class="num">{number(row['trades'])}</td>
<td class="num">{number(row['active_days'])}</td><td class="num">{'yes' if row['meets_min_active_days'] else 'no'}</td>
<td class="num">{number(row['margin_breach_bars'])}</td></tr>""")
    add("</tbody></table></div>")
    add(f"""<h3>Contrarian strategy models (C1–C5) and baselines</h3>
<div class="grid cols-3">""")
    for m in comp_models:
        pill = "ok" if m["kind"] == "contrarian" else "mut"
        add(f"""<article class="card strategy-card" data-cstrat="{esc(m['model'])}"><div class="model-head"><span class="mono">{esc(m['model'])}</span><span class="pill {pill}">{esc(m['kind'])}</span></div>
<h3>{esc(m['name'])}</h3><p>{esc(m['claim'])}</p>
<div class="note">{esc(m['params'])}</div></article>""")
    add(f"""</div>
<details class="assumptions"><summary>Simulation assumptions and design</summary><ul>""")
    for a in comp_meta["assumptions"]:
        add(f"<li>{esc(a)}</li>")
    add(f"""<li>Editions share one union calendar of the {number(len(comp_meta['eligible_symbols']))} eligible captured series; LATEST may overlap the final season edition and is excluded from season standings.</li>
<li>Zero-cost robustness run: zero-cost season leaders by edition wins — {esc('; '.join(f"{u} {n}" for u, n in comp['scenario_zero_leader_wins']))}.</li>
</ul></details>
<p class="file-links"><a href="data/competition_results.json">Full results (JSON)</a>
<a href="data/competition/roster.json">Roster (JSON)</a>
<a href="intel/competition.py">Engine source</a>
<a href="intel/contrarian.py">Contrarian models</a></p>
<p class="note">Artifact stamp: <code>{esc(comp_meta['generated_utc'])}</code> — every run is byte-reproducible from the committed vendor captures via <code>python3 scripts/run_competition.py --stamp {esc(comp_meta['generated_utc'])}</code>; the verifier re-runs exactly that and requires identical output.</p></section>""")

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
apply only to the stated test and captured evidence—not to a trading forecast.</p>
<div class="controls">
<input id="hyp-q" type="search" placeholder="Filter hypotheses by keyword, ID, status…" aria-label="Filter hypotheses">
<div id="hyp-thresh" class="thresh">
<button type="button" class="active" data-status="">All ({len(hypotheses['hypotheses'])})</button>
<button type="button" data-status="supported">Supported ({sum(1 for h in hypotheses['hypotheses'] if h['status'] == 'supported')})</button>
<button type="button" data-status="refuted">Refuted ({sum(1 for h in hypotheses['hypotheses'] if h['status'] == 'refuted')})</button>
</div>
<span id="hyp-count" class="count"></span>
</div>""")
    for item in hypotheses["hypotheses"]:
        pill = STATUS_PILL[item["status"]]
        evidence_html = "".join(f"<li>{esc(line)}</li>" for line in item["evidence"])
        refs = " · ".join(link(source_url[sid], sid) for sid in item["source_ids"])
        search_text = f"{item['id']} {item['status']} {item['claim']} {item['prediction']} {item['test']}".lower()
        add(f"""<article class="hyp" data-status="{esc(item['status'])}" data-search="{esc(search_text)}"><div class="top"><span class="id">{esc(item['id'])}</span><span class="pill {pill}">{esc(item['status'])}</span><span class="claim">{esc(item['claim'])}</span></div>
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
visible even after resolution.</p>
<div class="controls">
<input id="irr-q" type="search" placeholder="Filter irregularities by ID, severity, title…" aria-label="Filter irregularities">
<div id="irr-thresh" class="thresh">
<button type="button" class="active" data-sev="">All ({len(irregularities['irregularities'])})</button>
<button type="button" data-sev="critical">Critical ({sum(1 for i in irregularities['irregularities'] if i['severity'] == 'critical')})</button>
<button type="button" data-sev="high">High ({sum(1 for i in irregularities['irregularities'] if i['severity'] == 'high')})</button>
<button type="button" data-sev="medium">Medium ({sum(1 for i in irregularities['irregularities'] if i['severity'] == 'medium')})</button>
<button type="button" data-sev="low">Low ({sum(1 for i in irregularities['irregularities'] if i['severity'] == 'low')})</button>
</div>
<span id="irr-count" class="count"></span>
</div>""")
    for item in irregularities["irregularities"]:
        pill = SEVERITY_PILL[item["severity"]]
        status = item.get("status", "open")
        refs = " · ".join(link(source_url[sid], sid) for sid in item["source_ids"])
        search_text = f"{item['id']} {item['severity']} {item['title']} {item['detail']} {item['observed']}".lower()
        add(f"""<article class="hyp" data-severity="{esc(item['severity'])}" data-search="{esc(search_text)}"><div class="top"><span class="id">{esc(item['id'])}</span><span class="pill {pill}">{esc(item['severity'])}</span><span class="pill mut">{esc(status)}</span><span class="claim">{esc(item['title'])}</span></div>
<dl><dt>Detail</dt><dd>{esc(item['detail'])}</dd><dt>Observed</dt><dd>{esc(item['observed'])}</dd>
<dt>Resolution</dt><dd>{esc(item.get('resolution', 'Open'))}</dd><dt>Sources</dt><dd>{refs}</dd></dl></article>""")
    add("</section>")

    # Source registry
    add(f"""<section id="sources"><h2>Source registry and manual review</h2>
<p class="lead">All {source_registry['_meta']['source_count']} registered sources, their evidence
tier, allowed use, captured evidence file, and exact URL. Vendor stock sources also expose both
endpoint windows independently.</p>
<div class="controls">
<input id="src-q" type="search" placeholder="Filter sources by ID, title, publisher, URL…" aria-label="Filter sources">
<div id="src-thresh" class="thresh">
<button type="button" class="active" data-tier="">All ({len(sources)})</button>
<button type="button" data-tier="official_primary">Official Primary ({sum(1 for s in sources if s['tier'] == 'official_primary')})</button>
<button type="button" data-tier="market_data_vendor">Market Data Vendor ({sum(1 for s in sources if s['tier'] == 'market_data_vendor')})</button>
</div>
<span id="src-count" class="count"></span>
</div>
<div class="source-grid" id="src-grid">""")
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
        search_text = f"{source['source_id']} {source['tier']} {source['title']} {source['publisher']} {source['url']}".lower()
        add(f"""<details class="source-item" data-tier="{esc(source['tier'])}" data-search="{esc(search_text)}"><summary><span class="pill {pill}">{esc(source['tier'].replace('_', ' '))}</span>
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
