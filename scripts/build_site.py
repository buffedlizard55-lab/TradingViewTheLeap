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


def number_or_dash(value, decimals: int | None = None) -> str:
    """Render an optional number: missing values must never crash the build or print 'None'."""
    return "—" if value is None else number(value, decimals)


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



def load_optional(rel: str):
    """Load an artifact if it exists (new sections stay honest when data is pending)."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def render_exec_orders(exec_summary, stock_comp) -> str:
    """Machine-derived 'what gets placed next' block for the very top of the page.

    This is the explicit, obvious answer to 'what upcoming trades should be placed
    based on the top performing strategies on our simulated strategy competition list?'
    Every row is a mechanical replay of a frozen model's decision on committed vendor
    bars, sized from official rule constants (CME multipliers, TradingView caps) and
    labelled as simulated. Official sources:
    - Rules: https://www.tradingview.com/the-leap/amp-futures-september-2026/rules/
      (futures 250k, 20:1, section-08 per-symbol caps)
      https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/
      (stocks 100k, 1:1, 0.01% commission, 50-unit cap)
    - Multipliers: https://www.cmegroup.com/markets/cryptocurrencies/ether/ether/specs
      etc. (CME-SPEC-* sources)
    - Prices: vendor captures https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}
      (market_data_vendor tier, not exchange prints) and, when available,
      Alpaca IEX official provider https://docs.alpaca.markets/us/reference/stockbars
    No order here is advice, a forecast, or a guarantee; every figure is
    re-derivable from data/exec_summary.json which the verifier replays.
    """
    if not exec_summary or not (exec_summary.get("divisions") or {}):
        return ('<div class="callout warn"><h3>PENDING DATA — no executive summary yet</h3>'
                "<p>Run <code>python3 scripts/build_exec_summary.py</code> after the futures and "
                "stock competitions have been derived; until then no upcoming order is shown "
                "rather than a placeholder.</p></div>")
    rows = []
    waiting = []
    plain_orders = []
    order_symbols: list[str] = []
    for name, div in exec_summary["divisions"].items():
        for entry in div.get("recommendations", []):
            open_side = {p["symbol"]: p["side"] for p in entry.get("open_positions", [])}
            for order in entry["pending_orders"]:
                order_symbols.append(order["symbol"])
                size = order["indicative_size_units"]
                # The artifact publishes the rendered label, so the page cannot drift from the
                # builder's wording (the two copies disagreed on "1 unit" vs "1 units").
                size_text = order.get("indicative_size_label") or (
                    f"~{number_or_dash(size)} units" if size is not None
                    else "closes existing position")
                rows.append(
                    f'<tr data-ord="{esc(name)}">'
                    f'<td><span class="pill {"ok" if order["action"].startswith(("LONG", "BUY")) else "no" if order["action"].startswith(("SHORT", "SELL")) else "warn"}">'
                    f'{esc(order["action"])}</span></td>'
                    f'<td><code>{esc(order["symbol"])}</code></td>'
                    f'<td>{esc(entry["username"])}</td>'
                    f'<td>{esc(entry["model"])} · {esc(entry["model_name"])}</td>'
                    f'<td>{esc(name)}</td>'
                    f'<td>{size_text}</td>'
                    f'<td>{esc(order["decided_on"])}</td></tr>')
                # Plain-language sentence for the same order: the explicit, obvious answer to
                # "what upcoming trade should be placed", derived from the artifact only.
                action = order["action"]
                side = open_side.get(order["symbol"], "open")
                if action == "exit and reverse to LONG":
                    verb = f"Close the {side} position and open a LONG position ({size_text})"
                elif action == "exit and reverse to SHORT":
                    verb = f"Close the {side} position and open a SHORT position ({size_text})"
                elif action.startswith("exit"):
                    verb = "Close the open position and go FLAT (no new size)"
                elif action == "LONG (new position)":
                    verb = f"Open a new LONG position ({size_text})"
                elif action == "SHORT (new position)":
                    verb = f"Open a new SHORT position ({size_text})"
                elif action == "ADD (increase the open position)":
                    verb = f"ADD {size_text} to the open {side} position"
                else:
                    verb = f"{action} ({size_text})"
                plain_orders.append(
                    f'<li><strong>{esc(verb)}</strong> in <code>{esc(order["symbol"])}</code> — '
                    f'{esc(entry["username"])} ({esc(entry["model"])} · '
                    f'{esc(entry["model_name"])}, {esc(name)} season rank '
                    f'{esc(entry["season_rank"])}), signal bar '
                    f'{esc(order["decided_on"])}.</li>')
            if entry.get("waiting_for"):
                waiting.append(
                    f'<li><strong>{esc(entry["username"])}</strong> ({esc(entry["model"])} · '
                    f'{esc(entry["model_name"])}, {esc(name)}) is FLAT and waiting for: '
                    f'<em>{esc(entry["waiting_for"])}</em></li>')
    stamp = exec_summary["_meta"]["generated_utc"]
    pending = exec_summary["_meta"]["pending_order_count"]
    # Make the \"no order\" state unmissable and explicitly name the paper trades waiting to fire.
    # The table vs. waiting distinction: pending_orders are executable at next bar open;
    # waiting_for rows are frozen model conditions that have not yet triggered.
    if rows:
        first_symbol = order_symbols[0]
        banner = f"""<div class="callout good" style="border-left-width:6px;"><h3>\u2b22 UPCOMING PAPER TRADES — {number_or_dash(pending)} MECHANICAL ORDER(S) AT NEXT BAR OPEN</h3>
<p>Based on the <strong>top-performing simulated strategies</strong> on our multi-season competition leaderboard — every row is a mechanical replay of a frozen model on <strong>captured vendor pricing</strong>. Official-provider stock bars are still blocked, so these are not exchange-verified prices; sizes use official rule constants (CME multipliers, TradingView caps) and every row is labelled simulated.</p>
<ol class="compact">{''.join(plain_orders)}</ol>
<p class="note\">Top paper-trade signal: <code>{esc(first_symbol)}</code> and {number_or_dash(max(0, len(rows)-1))} more below — see <code>Signal bar</code> for the deciding session and verify each figure in <code>data/exec_summary.json</code>.</p></div>"""
        table = (banner + f"""<div class="table-wrap"><table>
<thead><tr><th>Order</th><th>Symbol</th><th>Username</th><th>Model</th><th>Division</th>
<th>Indicative size</th><th>Signal bar</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="note">Every order above is a <strong>market order at the next bar open</strong> of that
series, sized from the official rule constants at the last captured close
({esc(exec_summary["_meta"]["sizing_note"])}). <code>Signal bar</code> is the session whose close
produced the order; the hypothetical fill is the following bar's open, which is not present in this capture. It may already have occurred in real time. Verification: <code>python3 scripts/verify.py</code> replays each model on its committed bars and requires this table field-for-field.</p>""")
    else:
        table = ('<div class="callout good" style="border-left-width:6px;"><h3>\u2b22 UPCOMING PAPER TRADES — NO PENDING ORDER THIS BAR</h3>'
                 '<p>No top-ranked username has an order pending at the next bar open on the latest captured bar. '
                 'The mechanical entry condition each model is waiting for is listed under <em>What the top usernames are waiting for</em> below — every condition is frozen in <code>intel/*.py</code> and linked to its official or vendor source.</p></div>')
    waiting_block = ""
    if waiting:
        waiting_block = ('<h4>What the top usernames are waiting for (no pending order)</h4>'
                         f'<ul class="compact">{"" .join(waiting)}</ul>')
    return f"""<div class="callout good" style="border-left-width: 6px;">
<h3>HISTORICAL CANDIDATES — NOT RELEASED FOR EXECUTION</h3>
<p><strong>{number_or_dash(pending)} order(s)</strong> would be placed at the next bar open by the
top-ranked usernames of the repository's own paper competitions, replayed from their frozen
parameters on the committed vendor bars as of <code>{esc(stamp)}</code>. This is the explicit,
generated answer to "what should be placed next"; the narrative cards further down explain each
model. Everything here is a simulation of rules on historical vendor prices — it is not advice
and not a forecast.</p>
</div>
{table}
{waiting_block}"""


def render_stock_division(stock_comp, exec_summary) -> str:
    if not stock_comp:
        return """<section id="stocksdivision"><h2>Volatile-stock division</h2>
<div class="callout warn"><h3>Pending: intraday + long daily captures</h3>
<p>The equity division needs the vendor captures from <code>scripts/fetch_intraday.py</code>
(15-minute, hourly and ~10-year daily bars for the 20-stock volatile pool). Until the GitHub
Actions capture job has stored <code>data/intraday_index.json</code>, no equity number is
computed here — the site deliberately shows nothing rather than a placeholder.</p></div>
</section>"""
    divisions = stock_comp["divisions"]
    cards = []
    for name, label in (("daily", "Daily division (multi-season)"),
                        ("hourly", "Hourly division (multi-season, intraday)"),
                        ("15minute", "15-minute division (multi-season, intraday)")):
        div = divisions.get(name) or {}
        if not div.get("leaderboard"):
            cards.append(f'<div class="card"><h3>{esc(label)}</h3>'
                         f'<p class="note">status: {esc(str(div.get("status", "not run")))}</p></div>')
            continue
        rows = "".join(
            f'<tr data-srow="{esc(r["username"])}"><td>#{number_or_dash(r["season_rank"])}</td>'
            f'<td><code>{esc(r["username"])}</code></td><td>{esc(r["model"])}</td>'
            f'<td>{money(r["season_realized_pnl_usd"])}</td>'
            f'<td>{number_or_dash(r["season_multiple"])}x</td>'
            f'<td>{number_or_dash(r["best_edition_multiple"])}x</td>'
            f'<td>{number_or_dash(r["median_edition_multiple"])}x</td>'
            f'<td>{number_or_dash(r["editions_ge_2x"])}</td></tr>'
            for r in div["leaderboard"])
        ts = div["target_summary"]
        cards.append(f"""<div class="card">
<h3>{esc(label)}</h3>
<p class="note">{number_or_dash(div["season_editions"])} editions · {number_or_dash(len(div["eligible_symbols"]))}
symbols · {esc(div["profile"])} · {number_or_dash(ts["participant_editions"])} participant-editions ·
mean edition multiple {number_or_dash(ts["mean_equity_multiple"])}x ·
editions ≥2x: {number_or_dash(ts["ge_2x"])} · ≥5x: {number_or_dash(ts["ge_5x"])} ·
≥10x: {number_or_dash(ts["ge_10x"])} · ruined: {number_or_dash(ts["ruined_participant_editions"])}</p>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Username</th><th>Model</th>
<th>Season P/L</th><th>Season ×</th><th>Best edition ×</th><th>Median edition ×</th>
<th>Editions ≥2x</th></tr></thead><tbody>{rows}</tbody></table></div></div>""")

    latency_rows = []
    for name, rows in (stock_comp.get("latency_sensitivity") or {}).items():
        for row in rows:
            latency_rows.append(
                f'<tr><td>{esc(name)}</td><td>{number_or_dash(row["latency_bars"])}</td>'
                f'<td>{number_or_dash(row["total_trades"])}</td>'
                f'<td>{number_or_dash(row["mean_edition_multiple"])}x</td>'
                f'<td>{number_or_dash(row["median_edition_multiple"])}x</td>'
                f'<td>{number_or_dash(row["best_edition_multiple"])}x</td></tr>')
    latency_block = ""
    if latency_rows:
        latency_block = f"""<h3>Execution latency sensitivity (real bars, delayed fills)</h3>
<p class="note">The same editions re-run with every fill delayed by 1, 2 and 5 bars: the engine
places the order at the open of bar i+1+L instead of i+1. This is the measured cost of
execution latency inside the simulation, not an assumed number.</p>
<div class="table-wrap"><table><thead><tr><th>Division</th><th>Latency (bars)</th><th>Trades</th>
<th>Mean edition ×</th><th>Median edition ×</th><th>Best edition ×</th></tr></thead>
<tbody>{''.join(latency_rows)}</tbody></table></div>"""

    bound = stock_comp.get("official_rule_bound", {}).get("summary") or {}
    bound_block = ""
    if bound:
        bound_block = f"""<h3>Single-hold scenario — not a competition return ceiling</h3>
<p>Applying the historical stock-edition sizing constants to the captured subset yields a
largest single-hold scenario of <strong>{number_or_dash(bound.get("max_edition_multiple_observed_bound"))}x</strong>
across {number_or_dash(bound.get("editions_evaluated", 0))} editions.
This does not bound repeated trading, short selling or compounding and does not establish
whether 5x–100x competition returns are achievable. Coverage is incomplete.</p>
<p class="note">{esc(bound.get("method", ""))}</p>"""

    cf = stock_comp.get("counterfactual_20x") or {}
    cf_block = ""
    if cf:
        lines = []
        for name, div in cf.items():
            ts = div.get("target_summary", {})
            best = max((p["best_edition_multiple"] for p in div.get("participants", [])),
                       default=None)
            best_text = f"{number_or_dash(best)}x" if best is not None else "n/a"
            lines.append(f'<li><strong>{esc(name)}</strong>: {number_or_dash(div.get("editions_covered", 0))} '
                         f'editions · best single-edition multiple among participants '
                         f'{best_text} · editions ≥5x: {number_or_dash(ts.get("ge_5x", 0))} · '
                         f'≥10x: {number_or_dash(ts.get("ge_10x", 0))}</li>')
        cf_block = ('<h3>Counterfactual 20:1 run (NOT an official rule set)</h3>'
                    '<div class="callout high"><p>No official TradingView rules page grants 20:1 on '
                    'stocks. This run exists only to separate "signal" from "buying power" in the '
                    'explosive-return question and must never be read as an achievable contest '
                    f'outcome.</p><ul>{"".join(lines)}</ul></div>')

    fwd_parts = []
    for name, label in (("daily", "Daily"), ("hourly", "Hourly"), ("15minute", "15-minute")):
        div = divisions.get(name) or {}
        fwd = div.get("forward_held_out") or {}
        in_lb = fwd.get("in_sample_leaderboard")
        out_lb = fwd.get("forward_leaderboard")
        if not in_lb or not out_lb:
            continue
        window = fwd.get("held_out_window") or {}
        in_rows = "".join(
            f'<tr><td>#{number_or_dash(r["season_rank"])}</td><td><code>{esc(r["username"])}</code></td>'
            f'<td>{esc(r["model"])}</td><td>{money(r["season_realized_pnl_usd"])}</td>'
            f'<td>{number_or_dash(r["best_edition_multiple"])}x</td></tr>'
            for r in in_lb[:5])
        out_rows = "".join(
            f'<tr><td>#{number_or_dash(r["season_rank"])}</td><td><code>{esc(r["username"])}</code></td>'
            f'<td>{esc(r["model"])}</td><td>{money(r["season_realized_pnl_usd"])}</td>'
            f'<td>{number_or_dash(r["best_edition_multiple"])}x</td></tr>'
            for r in out_lb[:5])
        fwd_parts.append(f"""<div class="card"><h3>{esc(label)} — forward held-out window</h3>
<p class="note">Trailing {number_or_dash(fwd.get("held_out_editions"))} season editions held out
({esc(str(window.get("start_date", "")))} → {esc(str(window.get("end_date", "")))}); the frozen
models have no fitted parameters, so both windows are out-of-sample. Top 5 of each:</p>
<div class="grid cols-2"><div><h4>In-sample ({number_or_dash(fwd.get("in_sample_editions"))} editions)</h4>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Username</th><th>Model</th>
<th>Season P/L</th><th>Best ×</th></tr></thead><tbody>{in_rows}</tbody></table></div></div>
<div><h4>Forward held-out ({number_or_dash(fwd.get("held_out_editions"))} editions)</h4>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Username</th><th>Model</th>
<th>Season P/L</th><th>Best ×</th></tr></thead><tbody>{out_rows}</tbody></table></div></div></div></div>""")
    fwd_block = ""
    if fwd_parts:
        fwd_block = ("<h3>Forward-held-out test (trailing editions the models never saw in design)</h3>"
                     f'<div class="grid">{"".join(fwd_parts)}</div>')

    return f"""<section id="stocksdivision"><h2>Volatile-stock division (our own multi-season competition)</h2>
<p class="lead">The captured subset of the intended 20-stock volatile pool competes in our paper competition under
two rule profiles: the official stocks-edition constants (primary) and a declared 20:1
counterfactual. Usernames, frozen model parameters and every edition's ranking are in
<code>data/stock_competition_results.json</code>; the engine is the same one the futures division
uses, verified to reproduce the original futures engine byte-for-byte at zero latency.</p>
<div class="grid cols-2">{''.join(cards)}</div>
{fwd_block}
{latency_block}
{bound_block}
{cf_block}
</section>"""


def render_intraday_study(study, intraday_index) -> str:
    if not study:
        return """<section id="intraday"><h2>Intraday gap fills and execution latency</h2>
<div class="callout warn"><p>Pending the intraday capture: <code>data/intraday_study.json</code>
is produced by <code>scripts/run_intraday_study.py</code> once
<code>data/intraday_index.json</code> exists.</p></div></section>"""
    coverage = study["coverage"]
    agg = study["gap_fill"]["aggregate_by_kind"]
    agg_rows = "".join(
        f'<tr><td>{esc(kind)}</td><td>{number_or_dash(row["sessions_with_gap"])}</td>'
        f'<td>{number_or_dash(row["fill_rate_all"], 4)}</td>'
        f'<td>{number_or_dash(row["sessions_with_gap_ge_1_atr"])}</td>'
        f'<td>{number_or_dash(row["fill_rate_ge_1_atr"], 4)}</td>'
        f'<td>{number_or_dash(row["median_abs_gap_atr"], 4)}</td>'
        f'<td>{number_or_dash(row["median_bars_to_fill"], 2)}</td></tr>'
        for kind, row in sorted(agg.items()))
    bucket_rows = "".join(
        f'<tr><td>{esc(r["kind"])}</td><td>{esc(r["bucket"])}</td><td>{esc(r["direction"])}</td>'
        f'<td>{number_or_dash(r["sessions"])}</td><td>{number_or_dash(r["fill_rate"], 4)}</td>'
        f'<td>{number_or_dash(r["median_bars_to_fill"], 2)}</td>'
        f'<td>{number_or_dash(r["median_fill_fraction_of_session"], 4)}</td>'
        f'<td>{number_or_dash(r["close_through_rate"], 4)}</td></tr>'
        for r in study["gap_fill"]["buckets"])
    latency_rows = []
    for row in study["execution_latency"]["by_kind_interval"]:
        ss = row["same_session_next_open"]
        sb = row["session_boundary_next_open"]
        d2 = row["delay_2_bar_close_delta"]
        d5 = row["delay_5_bar_close_delta"]
        latency_rows.append(
            f'<tr><td>{esc(row["kind"])}</td><td>{esc(row["interval"])}</td>'
            f'<td>{number_or_dash(ss.get("observations", 0))}</td>'
            f'<td>{number_or_dash(ss.get("median_abs_bps"), 2)}</td>'
            f'<td>{number_or_dash(sb.get("median_abs_bps"), 2)}</td>'
            f'<td>{number_or_dash(d2.get("median_abs_bps"), 2)}</td>'
            f'<td>{number_or_dash(d5.get("median_abs_bps"), 2)}</td>'
            f'<td>{number_or_dash(ss.get("share_above_50bps_abs", 0), 4)}</td></tr>')
    cov_rows = "".join(
        f'<tr data-icov="{esc(c["symbol"])}"><td><code>{esc(c["symbol"])}</code></td>'
        f'<td>{esc(c["kind"])}</td><td>{esc(c["interval"])}</td><td>{number_or_dash(c["bars"])}</td>'
        f'<td>{esc(c["first_utc"][:10])}</td><td>{esc(c["last_utc"][:10])}</td>'
        f'<td><code>{esc(c["stored_sha256"][:16])}…</code></td></tr>'
        for c in coverage)
    index_meta = (intraday_index or {}).get("_meta", {})
    diag = study.get("calendar_diagnostics") or {}
    cal_rows = "".join(
        f'<tr><td><code>{esc(r["symbol"])}</code></td><td>{esc(r["interval"])}</td>'
        f'<td>{number_or_dash(r["sessions_on_full_closure"])}</td>'
        f'<td>{number_or_dash(r["boundaries_spanning_closure"])}</td>'
        f'<td>{number_or_dash(r["gaps_spanning_closure"])}</td></tr>'
        for r in (diag.get("per_series") or []) if r.get("calendar_applies"))
    cal_identity = diag.get("calendar") or {}
    window = diag.get("studied_window") or {}
    calendar_block = f"""<h3>Exchange-holiday annotation (NYSE full-closure table)</h3>
<p class="note">Sessions stay grouped by UTC date; the calendar only annotates them, so weekend gaps
can be told apart from gaps spanning an exchange holiday. Table <code>{esc(str(cal_identity.get("version", "")))}</code>
(<code>intel/calendar.py</code>, rule-based transcription of
<a href="https://www.nyse.com/markets/hours-calendars" rel="noopener noreferrer">the official NYSE calendar ↗</a>,
pending line-by-line network re-verification). Window {esc(str(window.get("start", "—")))} →
{esc(str(window.get("end", "—")))}: {number_or_dash(len(diag.get("full_closures_in_window") or {}))}
full closures inside, {number_or_dash(diag.get("sessions_on_full_closure_total", 0))} studied sessions
dated on a closure, {number_or_dash(diag.get("boundaries_spanning_closure_total", 0))} boundaries spanning one.</p>
<div class="table-wrap"><table><thead><tr><th>Symbol</th><th>Interval</th>
<th>Sessions on a closure</th><th>Boundaries spanning a closure</th><th>Gaps spanning a closure</th>
</tr></thead><tbody>{cal_rows or '<tr><td colspan="5">No equity intraday series studied yet.</td></tr>'}</tbody></table></div>"""
    return f"""<section id="intraday"><h2>Intraday gap fills and execution latency (measured)</h2>
<p class="lead">Two measurements on the committed vendor captures, no modelling: (1) do session
gaps fill, and how fast; (2) what does execution latency cost, in basis points of the decision
close. Method and assumptions are recorded inside
<code>data/intraday_study.json</code>; every number is re-derivable from the stored bars.</p>
<div class="callout info"><p><strong>Capture provenance.</strong>
{number_or_dash(index_meta.get("captured_count", len(coverage)))} series stored, by interval
{esc(str(index_meta.get("captured_by_interval", "")))}, direct requests rate-limited by the
vendor: <strong>{esc(str(index_meta.get("direct_rate_limited", "unknown")))}</strong>, fetched
<code>{esc(str(index_meta.get("fetched_at_utc", "")))}</code>. Method: {esc(strip_html(str(study["_meta"]["methodology"][0])))}</p></div>
<h3>Gap-fill aggregate by asset class</h3>
<div class="table-wrap"><table><thead><tr><th>Kind</th><th>Sessions with a gap</th>
<th>Fill rate (all)</th><th>Sessions ≥1 ATR</th><th>Fill rate ≥1 ATR</th>
<th>Median |gap| (ATR)</th><th>Median bars to fill</th></tr></thead><tbody>{agg_rows}</tbody></table></div>
<h3>Gap fill by size bucket and direction</h3>
<div class="table-wrap"><table><thead><tr><th>Kind</th><th>|gap| bucket</th><th>Direction</th>
<th>Sessions</th><th>Fill rate</th><th>Median bars to fill</th>
<th>Median fill point (session fraction)</th><th>Closed through prior close</th></tr></thead>
<tbody>{bucket_rows}</tbody></table></div>
<h3>Execution latency cost (basis points of the decision close)</h3>
<div class="table-wrap"><table><thead><tr><th>Kind</th><th>Interval</th><th>Observations</th>
<th>Same-session next open (median |bps|)</th><th>Session-boundary next open</th>
<th>2-bar delay</th><th>5-bar delay</th><th>Share &gt;50 bps</th></tr></thead>
<tbody>{''.join(latency_rows)}</tbody></table></div>
<h3>Captured series audited here</h3>
<div class="table-wrap"><table><thead><tr><th>Symbol</th><th>Kind</th><th>Interval</th><th>Bars</th>
<th>First session</th><th>Last session</th><th>Stored SHA-256</th></tr></thead>
<tbody>{cov_rows}</tbody></table></div>
{calendar_block}</section>"""


def strip_html(text: str) -> str:
    import re as _re
    return _re.sub(r"<[^>]+>", "", text)


def render_tv_benchmark(bench) -> str:
    if not bench:
        return """<section id="tvbench"><h2>Pine broker emulator vs Python fills</h2>
<div class="callout warn"><p>Pending: run <code>python3 scripts/tv_benchmark.py</code>.</p></div>
</section>"""
    meta = bench["_meta"]
    real = bench.get("exports", [])
    fixtures = bench.get("fixtures", [])
    rows = []
    for record in real + fixtures:
        fb = record.get("fill_benchmark", {})
        rows.append(
            f'<tr><td>{esc(record.get("path", ""))}</td>'
            f'<td>{"fixture" if record.get("is_fixture") else "real export"}</td>'
            f'<td>{esc(str(fb.get("status", record.get("status", ""))))}</td>'
            f'<td>{number_or_dash(record.get("trade_rows", 0))}</td>'
            f'<td>{number_or_dash(fb.get("fills_compared"))}</td>'
            f'<td>{number_or_dash(fb.get("share_exact_open_match"), 4)}</td>'
            f'<td>{number_or_dash(fb.get("median_abs_delta_vs_bar_open_bps"), 3)}</td>'
            f'<td>{number_or_dash(fb.get("median_abs_delta_vs_python_fill_bps"), 3)}</td></tr>')
    status_callout = (
        f'<div class="callout high"><h3>STATUS: {esc(str(meta["status"]).upper())}</h3>'
        f'<p>{esc(str(meta.get("blocked_reason") or "A real export is present; see the table."))}</p>'
        f'<p class="note">How to complete it:</p><ol class="compact">'
        + "".join(f"<li>{esc(step)}</li>" for step in meta.get("how_to_complete_this_benchmark", []))
        + "</ol></div>")
    rules = meta.get("pine_emulator_rules", {})
    return f"""<section id="tvbench"><h2>Pine broker emulator vs Python backtest fills</h2>
<p class="lead">TradingView publishes the Strategy Report export one tab at a time (CSV per the
support page; workbooks are read through their first worksheet) and documents the broker
emulator's fill rules. This section imports any real export committed to
<code>data/tv_reports/</code> — <code>.csv</code> or <code>.xlsx</code> — audits it row by row
(observed header, column mapping, SHA-256, rejected rows, arithmetic P/L cross-check) and
compares each exported fill with the same vendor bar and with the Python engine's fill model.</p>
{status_callout}
<div class="callout info"><h3>Documented emulator rules the benchmark tests against</h3>
<ul class="compact">
<li><strong>Market order:</strong> {esc(rules.get("market_order_default", ""))}</li>
<li><strong>Intrabar assumption:</strong> {esc(rules.get("intrabar_assumption", ""))}</li>
<li><strong>Gap rule:</strong> {esc(rules.get("gap_rule", ""))}</li>
<li>Source: {link(rules.get("source", ""), "Pine Script v6 — Concepts / Strategies ↗")}</li>
</ul></div>
<div class="table-wrap"><table><thead><tr><th>Export</th><th>Type</th><th>Fill benchmark</th>
<th>Trade rows</th><th>Fills compared</th><th>Exact next-open match</th>
<th>Median |Δ| vs bar open (bps)</th><th>Median |Δ| vs Python fill (bps)</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="note">{esc(bench.get("fixture_notice", ""))}</p></section>"""



def _order_line(order, source_url, spec_source_by_symbol, equity_source_by_symbol) -> str:
    """One pending order rendered from the artifact, with whatever official spec link exists."""
    symbol = order.get("symbol", "")
    size = order.get("indicative_size_units")
    size_text = order.get("indicative_size_label") or (
        f"{number_or_dash(size)} unit(s)" if size is not None else "closes the existing position")
    sid = spec_source_by_symbol.get(symbol) or equity_source_by_symbol.get(symbol)
    source = link(source_url[sid], "contract/price source ↗") if sid in source_url else ""
    close = number_or_dash(order.get("decided_close"), 4) if order.get("decided_close") is not None else "n/a"
    return (f'<li><code>{esc(symbol)}</code> — <strong>{esc(order.get("action", ""))}</strong> '
            f'({size_text}; {esc(order.get("order_type", ""))}; signal bar '
            f'{esc(order.get("decided_on", ""))}, close {close}) {source}</li>')


def render_top_performer_cards(exec_summary, stock_comp, source_url, spec_source_by_symbol,
                               equity_source_by_symbol) -> str:
    """Narrative cards for the top-ranked usernames, every field read from exec_summary.json."""
    if not exec_summary:
        return ""
    cards = []
    for name, division in exec_summary.get("divisions", {}).items():
        label = {"futures": "Futures division (official AMP rules)",
                 "stocks_daily": "Volatile-stock division (official stocks-edition rules)",
                 "stocks_hourly": "Volatile-stock hourly division"}.get(name, name)
        if division.get("status") and division["status"] != "run":
            cards.append(f"""<div class="card"><h3>{esc(label)}</h3>
<p class="note">Status: <strong>{esc(str(division.get("status")))}</strong> — {esc(str(division.get("reason", "")))}</p></div>""")
            continue
        for rec in division.get("recommendations", []):
            orders = rec.get("pending_orders") or []
            positions = rec.get("open_positions") or []
            pos_rows = "".join(
                f'<tr><td><code>{esc(p["symbol"])}</code></td>'
                f'<td><span class="pill {"ok" if p["side"] == "long" else "no"}">{esc(p["side"])}</span></td>'
                f'<td>{esc(p.get("since", ""))}</td>'
                f'<td class="num">{number_or_dash(p.get("last_close"), 4)}</td></tr>' for p in positions)
            pos_block = (f'<div class="table-wrap"><table><thead><tr><th>Open position</th><th>Side</th>'
                         f'<th>Since</th><th>Last captured close</th></tr></thead><tbody>{pos_rows}</tbody></table></div>'
                         if pos_rows else
                         '<p class="note">Currently flat: no position is open, so the next signal opens one.</p>')
            orders_block = ('<ul class="compact">' + "".join(
                _order_line(o, source_url, spec_source_by_symbol, equity_source_by_symbol) for o in orders)
                + '</ul>') if orders else '<p class="note">No mechanical order is due at the next bar open.</p>'
            waiting = (f'<p><strong>Waiting for:</strong> <em>{esc(rec["waiting_for"])}</em></p>'
                       if rec.get("waiting_for") else "")
            multi = rec.get("best_edition_multiple")
            title = "; ".join(f'{o["action"]} {o["symbol"]}' for o in orders) or "no order due"
            variant = f' (variant {esc(rec["variant"])})' if rec.get("variant") else ""
            params = f' · params {esc(rec["params_label"])}' if rec.get("params_label") else ""
            sizing_rule = orders[0].get("sizing_rule") if orders else "no order pending"
            cards.append(f"""<div class="card strategy-card">
<div class="model-head"><span class="pill purple">{esc(label)}</span>
<span class="pill ok">SEASON RANK {number_or_dash(rec.get("season_rank"))}</span>
<span class="pill info">{money(rec.get("season_realized_pnl_usd", 0.0))} season P/L</span>
<span class="pill mut">best edition {number_or_dash(multi) if multi is not None else "n/a"}×</span></div>
<h3>{esc(rec.get("username", ""))} — {esc(title)}</h3>
<p><strong>Model:</strong> {esc(rec.get("model", ""))} · {esc(rec.get("model_name", ""))}{variant}{params}</p>
<p><strong>Rule profile:</strong> {esc(rec.get("rule_profile", ""))} ·
<strong>as of last captured bar:</strong> {esc(rec.get("as_of_last_bar", ""))}</p>
<p><strong>Why this model is here:</strong> {esc(rec.get("entry_condition", ""))}</p>
{orders_block}
{waiting}
{pos_block}
<p class="note">Sizing rule for the next order: {esc(sizing_rule)}. Indicative sizes use the official
rule constants at the last captured close; an actual fill happens at the next bar's open, which does
not exist yet, so a live size would differ.</p></div>""")
    return f'<div class="grid cols-2">{"".join(cards)}</div>' if cards else ""


def render_stock_opportunity_note(stocks, stock_comp) -> str:
    """Volatile-pool context rendered from the archived, recomputable multiples."""
    records = sorted(stocks["records"], key=lambda r: -r["return_multiple"])
    chips = " · ".join(f"<strong>{esc(r['symbol'])} {number_or_dash(r['return_multiple'], 2)}×</strong>"
                       for r in records[:8])
    div = ((stock_comp or {}).get("divisions") or {}).get("daily") or {}
    leader = (div.get("leaderboard") or [{}])[0]
    if leader.get("username"):
        status = (f"our own daily division leader right now is <code>{esc(leader['username'])}</code> "
                  f"({esc(leader.get('model', ''))}, season P&amp;L "
                  f"{money(leader.get('season_realized_pnl_usd', 0.0))}, best edition "
                  f"{number_or_dash(leader.get('best_edition_multiple'))}×)")
    else:
        status = ("the stock division has not been run yet — it needs the intraday capture — so no "
                  "division result is shown here")
    return f"""<div class="callout info" style="margin-top: 22px;">
<h3>VOLATILE-EQUITY POOL &middot; WINDOW-BOUNDED PRICE HISTORY</h3>
<p>The largest archived trough&rarr;peak multiples in the 20-name pool are {chips}. Each ratio is
recomputable from the adjusted closes stored in <code>data/volatile_stocks.json</code> and is
re-derived by <code>scripts/verify.py</code>; each is <strong>window-bounded</strong> (the extremum lies
inside the documented fetch window) and comes from a market-data vendor, not an exchange or the contest
organiser. In the repository's own paper division — no risk management, maximum deployment, official
stocks-edition constants — {status}.</p>
<p class="note"><a href="research/evidence/VOLATILE-STOCKS-YAHOO-DAILY.md">Stock-multiple evidence file</a>
· <a href="research/evidence/YAHOO-INTRADAY-CAPTURE.md">Intraday capture evidence file</a>
· {link("https://www.tradingview.com/the-leap/magnificent-seven-2026/rules/", "Official stocks-edition rules ↗")}</p></div>"""


def render_signal_matrix(exec_summary, source_url, spec_source_by_symbol, equity_source_by_symbol) -> str:
    """The signal matrix, generated row by row from the artifact (no hardcoded values)."""
    if not exec_summary:
        return ""
    rows = []
    for name, division in exec_summary.get("divisions", {}).items():
        if division.get("status") and division["status"] != "run":
            rows.append(f'<tr><td>{esc(name)}</td><td colspan="9" class="note">'
                        f'{esc(str(division.get("status")))} — {esc(str(division.get("reason", "")))}</td></tr>')
            continue
        for rec in division.get("recommendations", []):
            orders = rec.get("pending_orders") or []
            positions = rec.get("open_positions") or []
            if orders:
                action_cells = []
                for o in orders:
                    bullish = o["action"].split()[-1].upper() in ("LONG", "BUY")
                    action_cells.append(f'<span class="pill {"ok" if bullish else "warn"}">'
                                        f'{esc(o["action"])}</span> <code>{esc(o["symbol"])}</code>')
                action = "<br>".join(action_cells)
                sizing = "; ".join(
                    (f'{number_or_dash(o["indicative_size_units"])} unit(s) at the last close'
                     if o.get("indicative_size_units") is not None
                     else "exit leg: closes the existing position") for o in orders)
            elif rec.get("waiting_for"):
                action = '<span class="pill mut">WAITING</span>'
                sizing = "no order until the stated condition fires"
            else:
                action = '<span class="pill mut">FLAT</span>'
                sizing = "no order pending"
            symbols = rec.get("symbols_watched") or [p["symbol"] for p in positions]
            probe = [o["symbol"] for o in orders] or [p["symbol"] for p in positions][:3]
            links = []
            for sym in probe:
                sid = spec_source_by_symbol.get(sym) or equity_source_by_symbol.get(sym)
                if sid in source_url and source_url[sid] not in links:
                    links.append(source_url[sid])
            link_cell = " · ".join(link(u, "source ↗") for u in links[:3]) or "—"
            variant = f' ({esc(rec["variant"])})' if rec.get("variant") else ""
            multi = rec.get("best_edition_multiple")
            rows.append(f"""<tr><td>{esc(name)}</td>
<td class="num"><span class="pill ok">{number_or_dash(rec.get("season_rank"))}</span></td>
<td><strong>{esc(rec.get("username", ""))}</strong></td>
<td>{esc(rec.get("model", ""))} · {esc(rec.get("model_name", ""))}{variant}</td>
<td class="sym">{esc(", ".join(symbols))}</td>
<td>{action}</td>
<td>{esc(sizing)}</td>
<td class="num">{money(rec.get("season_realized_pnl_usd", 0.0))}</td>
<td class="num">{number_or_dash(multi) if multi is not None else "n/a"}×</td>
<td>{link_cell}</td></tr>""")
    return f"""<h3>Signal matrix &middot; every cell read from the generated artifact</h3>
<p class="note">Rows are the top-ranked usernames of each division in <code>data/exec_summary.json</code>
(futures division: the 24-edition season on vendor front-month bars under the official AMP rules; stock
division: the multi-season paper division on the volatile pool). A "WAITING" row means the frozen model
has no order due at the next bar open — the model card above states the exact condition it waits for.</p>
<div class="table-wrap"><table><thead><tr><th>Division</th><th>Rank</th><th>Username</th><th>Model</th>
<th>Symbols</th><th>Next mechanical order</th><th>Sizing</th><th>Season P/L</th><th>Best edition ×</th>
<th>Official source links</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""


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
    exec_summary = load_optional("data/exec_summary.json")
    stock_comp = load_optional("data/stock_competition_results.json")
    intraday_study = load_optional("data/intraday_study.json")
    intraday_index = load_optional("data/intraday_index.json")
    tv_bench = load_optional("data/tv_benchmark.json")

    sources = source_registry["sources"]
    source_by_id = {s["source_id"]: s for s in sources}
    source_url = {sid: item["url"] for sid, item in source_by_id.items()}
    # Official spec-source lookup for the generated order tables: futures symbols resolve to the
    # CME contract-specification source registered on the master list entry, equity symbols to the
    # vendor capture source registered on the volatile-stock record. Missing mappings render as
    # "no link" rather than a guessed URL.
    spec_source_by_symbol: dict = {}
    for entry in master["entries"]:
        for sid in entry.get("source_ids", []):
            if sid.startswith("CME-SPEC-") and entry["symbol"] not in spec_source_by_symbol:
                spec_source_by_symbol[entry["symbol"]] = sid
    equity_source_by_symbol = {r["symbol"]: r["source_ids"][0] for r in stocks["records"]}
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
    intraday_records = load("data/intraday_index.json")["captures"]
    stock_series_captured = sum(r.get("status") == "captured" and r.get("kind") == "equity" for r in intraday_records)
    stock_series_total = 60
    full_pool_verdicts = load_optional("data/full_pool_verdicts.json")
    verdicts_assigned = bool(full_pool_verdicts and full_pool_verdicts.get("verdicts"))
    if stock_series_captured == stock_series_total and verdicts_assigned:
        coverage_note = ("full 60/60 coverage is present; full-pool verdicts H34–H39, H41 and H42 "
                         "are assigned (data/full_pool_verdicts.json)")
    elif stock_series_captured == stock_series_total:
        coverage_note = "full 60/60 coverage is present; H34–H39 may be re-run"
    else:
        coverage_note = (f"coverage is {stock_series_captured}/{stock_series_total}; "
                         "H34–H39 full-pool verdicts remain withheld")
    # Header capsule: the upcoming-trade answer must be visible at the very top of the page,
    # above the fold, straight from the generated artifact (never hardcoded).
    if exec_summary and exec_summary.get("_meta", {}).get("pending_order_count"):
        pending_n = exec_summary["_meta"]["pending_order_count"]
        first_sym = next(
            (o["symbol"] for div in exec_summary["divisions"].values()
             for rec in div.get("recommendations", [])
             for o in rec.get("pending_orders", [])),
            None,
        )
        first_txt = f" incl. <code>{esc(first_sym)}</code>" if first_sym else ""
        exec_capsule = (f'<span>Upcoming paper trades</span><strong><a href="#exec-summary">'
                        f'{pending_n} order(s) at next bar open →</a></strong>'
                        f'<span class="note">Top signal{first_txt}; '
                        f'mechanical replays, paper only</span>')
    elif exec_summary:
        exec_capsule = ('<span>Upcoming paper trades</span><strong><a href="#exec-summary">'
                        'No pending order this bar →</a></strong>'
                        '<span class="note">Top usernames are waiting; paper only</span>')
    else:
        exec_capsule = ""

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
<span>Displayed participants</span><strong>{number_or_dash(latest_frontier['participants_displayed'])}</strong>
{exec_capsule}
</div></div>
<div class="badge-row">
<span class="badge">{number_or_dash(universe['_meta']['instrument_count'])} eligible futures</span>
<span class="badge">{number_or_dash(master['_meta']['row_count'])} selected contracts</span>
<span class="badge">{number_or_dash(returns['_meta']['record_count'])} contest return records</span>
<span class="badge">{number_or_dash(stocks['_meta']['record_count'])} stock market records</span>
<span class="badge">{number_or_dash(len(captured_syms))} captured vendor series</span>
<span class="badge">{number_or_dash(len(backtests['models']))} walk-forward tested models</span>
<span class="badge">{number_or_dash(models['_meta']['model_count'])} untested strategy candidates</span>
<span class="badge warn">{number_or_dash(irregularities['_meta']['count'])} irregularities logged</span>
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
<li><a href="#stocksdivision">Stock division</a></li>
<li><a href="#intraday">Intraday &amp; latency</a></li>
<li><a href="#tvbench">Pine vs Python</a></li>
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
    add(f"""<section id="exec-summary"><h2>Executive Summary &mdash; Upcoming Paper Trades</h2>
<div class="callout high"><h3>PLACE NO NEW TRADES FROM THIS PAGE — RESEARCH ONLY</h3>
<p>Official-source pricing and authenticated TradingView fill validation are not complete.
The historical rankings below are exploratory, not a verified current order queue.
Only {sum(r.get("status") == "captured" and r.get("interval") == "1d" for r in load("data/intraday_index.json")["captures"])}
stock daily series are currently captured in the legacy index; the intended pool has 20 names. The matrix is at
{stock_series_captured} of {stock_series_total} stock series; {coverage_note}.
Missing prices are never synthesized. The stock pool is our own experiment, not the eligible
universe of the current futures-only Leap contest.</p>
<p><a href="research/implementation_review.md">Three-pass audit and remaining blockers</a> ·
<a href="https://docs.alpaca.markets/us/docs/about-market-data-api">Official free-feed documentation</a> ·
<a href="https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/">Official export documentation</a></p></div>
{render_exec_orders(exec_summary, stock_comp)}
<p class="lead">Explicit and obvious upcoming trade setups derived from the top-ranked usernames
of this repository's own simulated strategy competitions. Every card and every matrix cell below is
rendered field by field from <code>data/exec_summary.json</code>, which is itself re-derived from the
frozen model parameters, the committed vendor bars and the official rule constants — the page cannot
display a number here that the generator did not produce. The brief behind the models is maximum
simulated return: targets of 5&times;, 10&times;, 20&times;, 50&times; and 100&times;, full
rule-permitted deployment and no risk management, on paper accounts only. Rules, multipliers and caps
come from official sources (CME Group contract specifications, TradingView contest rules); prices come
from vendor captures and are labelled vendor-tier everywhere they appear.</p>

{render_top_performer_cards(exec_summary, stock_comp, source_url, spec_source_by_symbol, equity_source_by_symbol)}

{render_stock_opportunity_note(stocks, stock_comp)}

{render_signal_matrix(exec_summary, source_url, spec_source_by_symbol, equity_source_by_symbol)}

<div class="disclaimer"><strong>Simulated experiment notice.</strong> Every row above is a mechanical
replay of a frozen model on committed vendor history inside a paper competition. No real order has been
placed, no figure here is a forecast, and none of it is investment advice. The repository's verifier
re-derives these numbers from the artifacts before the page can be rebuilt.</div>
</section>""")

    # Overview
    add(f"""<section id="overview"><h2>What matters now</h2>
<p class="lead">A concise read of the current evidence. Live values are snapshots, historical
champions are simulated outcomes, and stock multiples are real market-price ratios.</p>
<div class="grid cols-4">
<div class="card"><h3>Live rank 1</h3><div class="stat accent">{live_return['return_multiple']}x</div>
<div class="note">+{number_or_dash(live_rank[1]['realized_profit_pct'], 2)}% · {money(live_rank[1]['realized_profit_usd'])} realized P/L</div></div>
<div class="card"><h3>Last public row</h3><div class="stat amber">rank {last_visible_rank}</div>
<div class="note">+{number_or_dash(live_rank[last_visible_rank]['realized_profit_pct'], 2)}% · not the hidden rank-{cfg['maximum_prize_recipients']} frontier</div></div>
<div class="card"><h3>Best completed sample</h3><div class="stat green">{completed_best['return_multiple']}x</div>
<div class="note">{esc(completed_best['asset_class_label'])} · official champion summary</div></div>
<div class="card"><h3>Captured ≥100x contest outcomes</h3><div class="stat red">{returns['threshold_analysis']['ge_100x']['count']}</div>
<div class="note">unattested in this sample, not proven impossible</div></div>
</div>
<div class="callout high"><h3>The finish line, in numbers</h3>
<p>The last cash-prize rank (50) displayed <strong>{placement['captures'][-1]['rows']['50']['balance_multiple']}×</strong>
the starting balance at the latest capture ({esc(placement['captures'][-1]['captured_at_utc'])}) — an average of
{money(placement['captures'][-1]['rows']['50']['average_usd_per_day_since_start'], 0)} per day since the opening bell.
A fresh 250,000 account would need <strong>+{number_or_dash(placement['captures'][-1]['rows']['50']['fresh_account_required_daily_compound_pct'], 2)}% per day,
compounded without a single losing day</strong> for the {number_or_dash(placement['deadline']['remaining_days_at_latest_capture'], 2)} days left, to reach it.
At the rules' 20:1 maximum exposure that is only {number_or_dash(placement['captures'][-1]['rows']['50']['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%
of underlying move per day — and one {number_or_dash(placement['leverage_math']['adverse_underlying_move_pct_to_erase_the_whole_balance'], 0)}% adverse day at that exposure erases the whole balance.</p></div>
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
        add(f"<tr><td>{row['balance_multiple']}×</td><td class=\"num\">+{number_or_dash(row['net_profit_pct'])}%</td>"
            f"<td class=\"num\">{money(row['required_net_profit_usd'], 0)}</td>"
            f"<td class=\"num\">{number_or_dash(row['ideal_initial_20x_fixed_exposure_move_pct'])}%</td>"
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
            f"<td class=\"num\">{number_or_dash(row['favorable_move_pct_to_equal_target'], 2)}%</td></tr>")
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
<div class="note">+{number_or_dash(rank50_row['realized_profit_pct'], 2)}% · {money(rank50_row['realized_profit_usd'])} at {esc(latest_cap['captured_at_utc'])}</div></div>
<div class="card"><h3>Average pace so far</h3><div class="stat small accent">{money(rank50_row['average_usd_per_day_since_start'], 0)}/day</div>
<div class="note">displayed total ÷ {number_or_dash(latest_cap['elapsed_days_since_start'], 2)} elapsed days</div></div>
<div class="card"><h3>Fresh account from now</h3><div class="stat amber">+{number_or_dash(rank50_row['fresh_account_required_daily_compound_pct'], 2)}%/day</div>
<div class="note">compounded, unbroken, over {number_or_dash(latest_cap['remaining_days_to_deadline'], 2)} days</div></div>
<div class="card"><h3>In underlying terms at 20:1</h3><div class="stat amber">{number_or_dash(rank50_row['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%/day</div>
<div class="note">linear approximation, fully invested, no losing day</div></div>
</div>
<div class="callout critical"><h3>Maximum exposure cuts both ways</h3>
<p>At the rules' maximum {money(lm['maximum_initial_notional_usd'], 0)} notional a 1% underlying move is
{money(lm['usd_per_1pct_underlying_move_at_max_notional'], 0)} — {number_or_dash(lm['pct_of_starting_balance_per_1pct_underlying_move'], 0)}% of the starting balance —
and a {number_or_dash(lm['adverse_underlying_move_pct_to_erase_the_whole_balance'], 0)}% adverse move erases the entire
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
            f"<td class=\"num\">+{number_or_dash(row['fresh_account_required_daily_compound_pct'], 2)}%/day</td>"
            f"<td class=\"num\">{number_or_dash(row['fresh_account_required_underlying_pct_per_day_at_20x'], 2)}%/day</td></tr>")
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
            f"<td class=\"num\">+{number_or_dash(t['required_daily_compound_pct_over_remaining_window'], 2)}%/day</td>"
            f"<td class=\"num\">{number_or_dash(t['required_underlying_pct_per_day_at_20x'], 2)}%/day</td>"
            f"<td class=\"num\">{t['full_leverage_winning_days_at_1pct_underlying']}</td>"
            f"<td class=\"num\">{t['completed_champion_sample_at_or_above']} / {cs['completed_records']}</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">From {esc(latest_cap['captured_at_utc'])}, {number_or_dash(latest_cap['remaining_days_to_deadline'], 2)} days remain to the
{esc(placement['deadline']['competition_end_utc'])} deadline; registration stays open for
{number_or_dash(latest_cap['registration_days_left'], 2)} more days. The winning-days column assumes an unbroken run of all-in wins at
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
        best_txt = "no history" if best is None else f"{number_or_dash(best, 2)}%"
        flag = row['history_contains_a_30d_window_as_large_as_that_requirement']
        flag_txt = "—" if flag is None else ("yes" if flag else "no")
        add(f"<tr><td>{esc(row['symbol'])}</td><td class=\"num\">{money(row['modeled_initial_notional_usd'], 0)}</td>"
            f"<td class=\"num\">{number_or_dash(row['favorable_move_pct_needed_for_latest_rank50_level'], 2)}%</td>"
            f"<td class=\"num\">{best_txt}</td><td>{flag_txt}</td></tr>")
    add(f"""</tbody></table></div>
<p class="note">The requirement column is the rank-50 level divided by each instrument's modeled initial
notional at the rules cap; the history column is the largest 30-day close-to-close up move in the archived
vendor window (overlapping windows, perfect single-direction timing assumed, no costs, fills or rolls). A "yes"
means the vendor history contained a move that large <em>once</em>; it is not a forecast and not a strategy.</p>
<div class="grid cols-3">
<div class="card"><h3>Board density</h3><div class="stat small">{number_or_dash(board['participants_displayed'])}</div>
<div class="note">participants displayed · top {board['visible_ranks']} visible ({number_or_dash(board['visible_share_of_participants_pct'], 3)}%)</div></div>
<div class="card"><h3>Cash places</h3><div class="stat small">{board['cash_ranks']}</div>
<div class="note">cash ranks = {number_or_dash(board['cash_share_of_participants_pct'], 3)}% of participants</div></div>
<div class="card"><h3>Gap to rank 100</h3><div class="stat small">{number_or_dash(board['rank50_to_rank100_gap_pct'], 1)}%</div>
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
<div class="card"><h3>Futures leverage</h3><div class="stat accent">{number_or_dash(cfg['futures_leverage_ratio'], 0)}:1</div><div class="note">{money(cfg['maximum_initial_notional_usd'], 0)} maximum initial notional</div></div>
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
        add(f"<tr><td class=\"num\">{rank}</td><td>{esc(row['trader'])}</td><td class=\"num\">+{number_or_dash(row['realized_profit_pct'], 2)}%</td><td class=\"num\">+{money(row['realized_profit_usd'])}</td><td>{esc(prize)}</td></tr>")
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
<td class="num">{number_or_dash(cap['participants_displayed'])}</td>
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
captured TradingView display prices, verified contract multipliers, rule caps, and initial {number_or_dash(cfg['futures_leverage_ratio'], 0)}:1
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
<td class="num">{number_or_dash(row['quote_price'], 4)}</td><td class="num">{number_or_dash(row['rules_position_cap_contracts'])}</td>
<td class="num">{row['max_whole_contracts_at_initial_balance']}</td><td>{esc(row['initial_constraint'].replace('_', ' '))}</td>
<td class="num">{money(row['modeled_initial_notional_usd'], 0)}</td>
<td class="num">{money(row['modeled_pnl_for_favorable_1pct_move_usd'], 0)}</td>
<td class="num">{number_or_dash(row['favorable_move_pct_needed_for_rank250_snapshot'], 2)}%</td>
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
            delta_cell = f'<span class="{cls}">{number_or_dash(d_pct, 2)}%</span>'
        add(f"""<tr data-mhsym="{esc(tv)}"><td class="sym">{esc(tv)}</td>
<td>{esc(c.get('vendor_reported_contract') or '?')}</td><td>{esc(c.get('transport') or '?')}</td>
<td class="num">{number_or_dash(c['sessions_valid'])}</td><td>{esc(c['first_session_utc'])}</td><td>{esc(c['last_session_utc'])}</td>
<td class="num">{number_or_dash(c['last_close'], 4)}</td><td class="num">{delta_cell}</td>
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
<td class="num">{number_or_dash(r['ann_vol_full_pct'], 1)}%</td>
<td class="num">{number_or_dash(r['mean_atr14_pct'], 2)}%</td>
<td class="num">{number_or_dash(r['best_30d_up_move_pct'], 1)}%</td>
<td class="num">−{number_or_dash(r['best_30d_down_move_pct'], 1)}%</td>
<td class="num">{number_or_dash(r['windows_30d_ge_10pct_up'])}</td>
<td class="num">{number_or_dash(r['windows_30d_ge_25pct_up'])}</td>
<td class="num">{number_or_dash(r['largest_abs_overnight_gap_pct'], 2)}%</td>
<td class="num">{number_or_dash(r['favorable_move_pct_needed_for_rank250_snapshot'], 2)}%</td>
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
<div class="card"><h3>Vendor data</h3><div class="stat amber">{number_or_dash(intelligence['provenance']['market_data_vendor']['captured_series'])} series</div>
<div class="note">front-month futures; roll and transport caveats remain</div></div>
<div class="card"><h3>Platform validation</h3><div class="stat red">blocked / unrun</div>
<div class="note">no authenticated TradingView Strategy Report export</div></div>
</div>
<div class="callout high"><h3>Current comparison verdict</h3>
<p>{esc(intelligence['model_comparison']['decision']['interpretation'])}</p>
<p><strong>Thresholds reached in the shadow simulation:</strong>
5× = {number_or_dash(intelligence['model_comparison']['kind_contrast']['contrarian']['participant_editions_ge_5x'] + intelligence['model_comparison']['kind_contrast']['baseline']['participant_editions_ge_5x'])} participant-editions;
10× = no; 20× = no; 50× = no; 100× = no.</p></div>
<h3>Frozen-model comparison by paper usernames</h3>
<div class="table-wrap"><table id="intel-model-table"><thead><tr><th>Model</th><th>Kind</th><th class="num">Users</th>
<th class="num">Best single edition</th><th class="num">Median best edition</th><th class="num">≥5× editions</th>
<th class="num">≥10× editions</th><th class="num">Ruined editions</th><th class="num">Latest median</th></tr></thead><tbody>""")
    for row in intel_results:
        kind_cls = "up" if row["kind"] == "contrarian" else ""
        add(f"""<tr><td class="sym">{esc(row['model'])} — {esc(row['name'])}</td><td>{esc(row['kind'])}</td>
<td class="num">{number_or_dash(row['participants'])}</td><td class="num {kind_cls}">{number_or_dash(row['best_single_edition_multiple_max'], 2)}×</td>
<td class="num">{number_or_dash(row['best_single_edition_multiple_median'], 2)}×</td><td class="num">{number_or_dash(row['participant_editions_ge_5x'])}</td>
<td class="num">{number_or_dash(row['participant_editions_ge_10x'])}</td><td class="num">{number_or_dash(row['ruined_editions'])}</td>
<td class="num">{number_or_dash(row['latest_edition_multiple_median'], 2)}×</td></tr>""")
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
from a fresh {money(cfg['starting_balance_virtual_usd'], 0)} account at {number_or_dash(cfg['futures_leverage_ratio'], 0)}:1, across
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
<dl><dt>Windows / trades</dt><dd>{number_or_dash(zero['windows'])} / {number_or_dash(zero['trades'])}</dd>
<dt>Bootstrap 95% CI of median</dt><dd>{money(zero['bootstrap95_median_ci_usd'][0], 0)} … {money(zero['bootstrap95_median_ci_usd'][1], 0)}</dd>
<dt>Windows ≥ 5x / ≥ 10x</dt><dd>{number_or_dash(zero['windows_ge_5x'])} / {number_or_dash(zero['windows_ge_10x'])}</dd>
<dt>Best window</dt><dd>{esc(zero['best_window']['symbol'])} {esc(zero['best_window']['start'])} → {esc(zero['best_window']['end'])}: {money(zero['best_window']['net_profit_usd'], 0)} ({number_or_dash(zero['best_window']['equity_multiple'], 2)}x)</dd>
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
<td class="num">{number_or_dash(z['positive_windows_pct'], 1)}%</td>
<td class="num">{number_or_dash(z['ruined_windows'])}</td></tr>""")
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
<p class="lead">The repository's own paper competition: {number_or_dash(len(comp['roster']))} usernames
({number_or_dash(sum(1 for r in comp['roster'] if r['kind'] == 'contrarian'))} contrarian, {number_or_dash(sum(1 for r in comp['roster'] if r['kind'] == 'baseline'))} trend baselines)
compete on the captured vendor daily bars with a fresh {money(cfg['starting_balance_virtual_usd'], 0)} account per edition,
under the official rule constants ({number_or_dash(cfg['futures_leverage_ratio'], 0)}:1 buying power, whole contracts, official section 08 caps,
realized-P/L ranking, end-of-edition auto-close, no resets). Season = {number_or_dash(season_editions)} non-overlapping
30-calendar-day editions across the full capture history; LATEST mirrors the in-progress September edition's window length.</p>
<div class="callout high"><h3>What this is and is not</h3>
<p>These are THIS REPOSITORY's simulated usernames, ranked by THIS REPOSITORY's engine
(<code>{esc(comp_meta['engine'])}</code>) on vendor-tier front-month continuous futures
(unadjusted rolls). It is NOT the official The Leap leaderboard, NOT TradingView Paper Trading
output, and NOT a prediction. The official live board is tracked separately in
<a href="#frontier">Live frontier</a>.</p></div>
<div class="grid cols-4">
<div class="card"><h3>Season champion</h3><div class="stat accent">{esc(champ['username'])}</div><div class="note">by total realized P/L over {number_or_dash(season_editions)} editions: {money(champ['season_realized_pnl_usd'], 0)}</div></div>
<div class="card"><h3>Latest edition winner</h3><div class="stat accent">{esc(latest_leader['username'])}</div><div class="note">{esc(comp_latest['start_date'])} → {esc(comp_latest['end_date'])}: {money(latest_leader['realized_pnl_usd'], 0)} ({number_or_dash(latest_leader['equity_multiple'], 2)}x)</div></div>
<div class="card"><h3>Best single edition</h3><div class="stat accent">{number_or_dash(comp_contrast['contrarian']['best_single_edition_multiple'], 2)}x</div><div class="note">best contrarian edition multiple ({number_or_dash(comp_contrast['baseline']['best_single_edition_multiple'], 2)}x best baseline)</div></div>
<div class="card"><h3>Editions ≥ 5x / ruined</h3><div class="stat accent">{number_or_dash(comp_ts['ge_5x'])} / {number_or_dash(comp_ts['ruined_participant_editions'])}</div><div class="note">participant-editions at {esc(comp_meta['primary_scenario'])} cost (of {number_or_dash(comp_ts['participant_editions'])})</div></div>
</div>
<div class="controls"><input id="shadow-q" type="search" placeholder="Filter username, strategy, model…" aria-label="Filter shadow leaderboard"><span id="shadow-count" class="count"></span></div>
<div class="table-wrap"><table id="shadow-table"><thead><tr><th class="num">Season rank</th><th>Username</th><th>Kind</th><th>Strategy</th><th>Variant</th><th class="num">Season realized P/L</th><th class="num">Season multiple</th><th class="num">Best edition</th><th class="num">Editions ≥5x</th><th class="num">Ruined editions</th></tr></thead><tbody>""")
    for row in comp_board:
        agg = next(a for a in comp["participants"] if a["username"] == row["username"])
        search = f"{row['username']} {agg['model']} {agg['model_name']} {agg['variant'] or 'default'} {agg['kind']}".lower()
        pill = "ok" if agg["kind"] == "contrarian" else "mut"
        add(f"""<tr data-shadow="{esc(row['username'])}" data-search="{esc(search)}"><td class="num">{number_or_dash(row['season_rank'])}</td>
<td class="sym">{esc(row['username'])}</td><td><span class="pill {pill}">{esc(agg['kind'])}</span></td>
<td>{esc(agg['model'])} — {esc(agg['model_name'])}</td><td>{esc(agg['variant'] or 'default')}</td>
<td class="num">{smoney(row['season_realized_pnl_usd'], 0)}</td>
<td class="num">{number_or_dash(row['season_multiple'], 4)}x</td>
<td class="num{' up' if row['best_edition_multiple'] >= 5 else ''}">{number_or_dash(row['best_edition_multiple'], 2)}x</td>
<td class="num">{number_or_dash(row['editions_ge_5x'])}</td>
<td class="num{' down' if agg['ruined_editions'] else ''}">{number_or_dash(agg['ruined_editions'])}</td></tr>""")
    add("</tbody></table></div>")
    add(f"""<div class="callout"><h3>Season vs single-edition: what the numbers say</h3>
<p>Contrarian fade models produced the only explosive editions — best {number_or_dash(comp_contrast['contrarian']['best_single_edition_multiple'], 2)}x in 30 calendar days
on daily bars versus {number_or_dash(comp_contrast['baseline']['best_single_edition_multiple'], 2)}x for the trend baselines, with {number_or_dash(comp_ts['users_reaching_5x_any_edition'])} of
{number_or_dash(len(comp_board))} usernames reaching ≥5x at least once. But full 20:1 deployment with no stops also ruined
{number_or_dash(comp_ts['ruined_participant_editions'])} participant-editions outright, so season compounding collapses for almost everyone
(best season multiple on the board: {number_or_dash(max(r['season_multiple'] for r in comp_board), 4)}x). That is the project's core finding in miniature:
explosive single-edition outcomes exist in the captured data, and the contest's no-reset rule makes harvesting them
survivorship-bound, not strategy-bound alone.</p></div>
<h3>Latest edition leaderboard ({esc(comp_latest['start_date'])} → {esc(comp_latest['end_date'])}, {esc(comp_meta['primary_scenario'])} cost)</h3>
<div class="table-wrap"><table id="shadow-latest"><thead><tr><th class="num">Rank</th><th>Username</th><th class="num">Realized P/L</th><th class="num">Multiple</th><th class="num">Trades</th><th class="num">Active days</th><th class="num">Min 5 active days</th><th class="num">Margin-breach bars</th></tr></thead><tbody>""")
    for row in comp_latest["rows"][:10]:
        add(f"""<tr><td class="num">{number_or_dash(row['rank'])}</td><td class="sym">{esc(row['username'])}</td>
<td class="num{' up' if row['realized_pnl_usd'] > 0 else ' down'}">{smoney(row['realized_pnl_usd'], 0)}</td>
<td class="num">{number_or_dash(row['equity_multiple'], 3)}x</td><td class="num">{number_or_dash(row['trades'])}</td>
<td class="num">{number_or_dash(row['active_days'])}</td><td class="num">{'yes' if row['meets_min_active_days'] else 'no'}</td>
<td class="num">{number_or_dash(row['margin_breach_bars'])}</td></tr>""")
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
    add(f"""<li>Editions share one union calendar of the {number_or_dash(len(comp_meta['eligible_symbols']))} eligible captured series; LATEST may overlap the final season edition and is excluded from season standings.</li>
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
        participants = number_or_dash(row["participants"]) if row.get("participants") is not None else "not published"
        add(f"""<tr data-search="{esc(search)}"><td><span class="pill {pill}">{esc(row['status'])}</span></td>
<td>{esc(row['edition_label'])}</td><td>{esc(row['asset_class_label'])}</td><td>{esc(row['winner'])}</td>
<td class="num">{participants}</td><td class="num">+{number_or_dash(row['net_profit_pct_as_published'], 2)}%</td>
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
<td class="num">{number_or_dash(row['trough']['adjclose'], 4)}<br><span class="note">{esc(row['trough']['date_utc'])}</span></td>
<td class="num">{number_or_dash(row['peak']['adjclose'], 4)}<br><span class="note">{esc(row['peak']['date_utc'])}</span></td>
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
<button type="button" data-status="untested">Untested ({sum(1 for h in hypotheses['hypotheses'] if h['status'] == 'untested')})</button>
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
        cap_link = link(source_url["TV-RULES-AMP-SEP2026"], number_or_dash(row["max_open_position_contracts"]))
        multiplier_label = f"{number_or_dash(row['contract_multiplier'])} {row['contract_multiplier_unit']}"
        multiplier_link = link(source_url[row["contract_multiplier_source_id"]], multiplier_label)
        add(f"""<tr data-search="{esc(search)}" data-class="{esc(row['volatility_class'])}"><td class="sym">{esc(row['symbol'])}</td><td>{esc(row['name'])}</td>
<td>{esc(row['volatility_class'].replace('_', ' '))}</td><td class="num">{cap_link}</td>
<td class="num">{multiplier_link}</td>
<td class="num">{number_or_dash(row['max_underlying_exposure'])} {esc(row['max_underlying_exposure_unit'])}</td>
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
<td class="sym">{esc(row['tradingview_symbol'])}</td><td>{esc(row['exchange'])}</td><td class="sym">{esc(row['root_code'])}</td><td class="num">{number_or_dash(row['max_open_position_contracts'])}</td></tr>""")
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

    # Volatile-stock division, intraday study, and the Pine-vs-Python benchmark
    add(render_stock_division(stock_comp, exec_summary))
    add(render_intraday_study(intraday_study, intraday_index))
    add(render_tv_benchmark(tv_bench))

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

    # docs/ mirror. GitHub Pages for this repository is configured in LEGACY mode against
    # the root of `main`, so docs/ is not what publishes - but the directory is committed
    # and has been linked to, and a hand-copied mirror goes stale the first time anyone
    # forgets (it already had: docs/index.html was two derives behind). Writing it here
    # makes staleness impossible, and scripts/verify.py fails the build if the two copies
    # or their stylesheets diverge.
    mirror = os.path.join(ROOT, "docs")
    os.makedirs(os.path.join(mirror, "assets"), exist_ok=True)
    with open(os.path.join(mirror, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html_text)
    with open(os.path.join(mirror, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    for name in ("style.css", "app.js"):
        src = os.path.join(ROOT, "assets", name)
        if os.path.exists(src):
            with open(src, encoding="utf-8") as fh:
                payload = fh.read()
            with open(os.path.join(mirror, "assets", name), "w", encoding="utf-8") as fh:
                fh.write(payload)
    print(f"wrote {os.path.relpath(os.path.join(mirror, 'index.html'), ROOT)} (mirror)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
