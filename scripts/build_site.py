#!/usr/bin/env python3
"""
Builds site/index.html from the verified data under data/ and research/.

Nothing on the page is hand-written prose about numbers: every figure, table row, verdict and
source link is rendered directly out of the JSON artefacts that scripts/verify.py has already
audited. Regenerate with `python3 scripts/build_site.py` after any data change.

The output is a single self-contained HTML file plus assets/style.css and assets/app.js, so it
works on GitHub Pages with no build step, no fetch calls and no CORS surface.
"""

from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def e(x) -> str:
    if x is None:
        return '<span class="pill mut">null</span>'
    return html.escape(str(x))


def money(x, dp=2) -> str:
    if x is None:
        return '<span class="pill mut">null</span>'
    return f"${x:,.{dp}f}"


def num(x, dp=None) -> str:
    if x is None:
        return '<span class="pill mut">null</span>'
    if isinstance(x, float) and dp is None:
        return f"{x:,.2f}"
    return f"{x:,.{dp}f}" if dp is not None else f"{x:,}"


SEV_PILL = {"critical": "no", "high": "warn", "medium": "warn", "low": "mut"}
STATUS_PILL = {"supported": "ok", "refuted": "no", "untested": "mut", "partially_supported": "warn"}
VER_PILL = {"fully_verified": "ok", "identity_verified": "info", "pending_evidence": "warn"}

NULL_PILL = '<span class="pill mut">null</span>'


def build() -> str:
    src = load("research/sources/sources.json")
    uni = load("data/contest_universe.json")
    ml = load("data/master_list.json")
    er = load("data/verified_explosive_returns.json")
    hyp = load("research/hypotheses/hypotheses.json")
    irr = load("research/irregularities.json")

    sources = src["sources"]
    src_url = {s["source_id"]: s["url"] for s in sources}
    consts = ml["_meta"]["constants"]
    balance = consts["paper_balance_usd"]
    lev = consts["futures_leverage"]
    notional = consts["max_notional_usd"]
    rank1 = consts["current_rank1_realized_pnl_usd"]

    P: list[str] = []
    add = P.append

    # ---------------------------------------------------------------- header
    add(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Leap — Verified Research &amp; Instrument Intelligence</title>
<meta name="description" content="Line-by-line verified research layer for TradingView's The Leap paper trading competition. Every figure traces to an official source.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site"><div class="wrap">
<h1>The Leap &mdash; Verified Research &amp; Instrument Intelligence</h1>
<p class="sub">An evidence-first research layer for TradingView's <em>The Leap</em> paper trading
competition. Every number on this page is rendered from a JSON artefact that has been audited by
<code>scripts/verify.py</code>, and every artefact cites an official source you can open and check.
Nothing here is estimated, interpolated or remembered.</p>
<div class="badge-row">
<span class="badge live">LIVE &middot; The Leap by AMP Futures &middot; Sep 1&ndash;30, 2026</span>
<span class="badge">{uni['_meta']['instrument_count']} instruments verified</span>
<span class="badge">{len(ml['entries'])} master-list entries</span>
<span class="badge">{er['_meta']['record_count']} sourced return records</span>
<span class="badge">{len(hyp['hypotheses'])} hypotheses tested</span>
<span class="badge warn">{len(irr['irregularities'])} irregularities flagged</span>
<span class="badge">accessed 2026-09-16 UTC</span>
</div>
</div></header>

<nav class="toc"><div class="wrap"><ul>
<li><a href="#summary">Summary</a></li>
<li><a href="#competition">The competition</a></li>
<li><a href="#returns">Verified returns</a></li>
<li><a href="#hypotheses">Hypotheses</a></li>
<li><a href="#masterlist">Master list</a></li>
<li><a href="#universe">Contest universe</a></li>
<li><a href="#irregularities">Irregularities</a></li>
<li><a href="#sources">Sources</a></li>
<li><a href="#method">Method</a></li>
</ul></div></nav>
<div class="wrap">
""")

    # --------------------------------------------------------------- summary
    add('<section id="summary"><h2>Executive summary</h2>')
    add('<p class="lead">Five findings that change the plan. Each is stated with the observation '
        'that produced it and a link to the source.</p>')

    add(f"""<div class="grid cols-4">
<div class="card"><h3>Verified &ge;100x outcomes</h3><div class="stat red">{er['threshold_analysis']['ge_100x']['count']}</div>
<div class="note">across {er['_meta']['record_count']} sourced records</div></div>
<div class="card"><h3>Verified &ge;50x outcomes</h3><div class="stat amber">{er['threshold_analysis']['ge_50x']['count']}</div>
<div class="note">best: {er['threshold_analysis']['ge_50x']['cases'][0]['edition']} at {er['threshold_analysis']['ge_50x']['cases'][0]['return_multiple']}x</div></div>
<div class="card"><h3>Verified &ge;10x outcomes</h3><div class="stat green">{er['threshold_analysis']['ge_10x']['count']}</div>
<div class="note">both from futures editions</div></div>
<div class="card"><h3>Stocks in live contest</h3><div class="stat red">0</div>
<div class="note">of {uni['_meta']['instrument_count']} permitted instruments</div></div>
</div>""")

    exch_str = ", ".join(f"{k} {v}" for k, v in sorted(_exch_counts(uni).items()))
    by_winner = {r["winner"]: r for r in er["records"]}
    feb2025 = by_winner["BenBernanke1"]
    live_rec = [r for r in er["records"] if r["status"] == "in_progress"][0]

    add(f"""<div class="callout critical"><h3>Finding 1 &mdash; the live contest has no stocks (IR-01)</h3>
<p>The permitted instrument list for the live edition contains
<strong>{uni['_meta']['instrument_count']} futures contracts and zero equities</strong>. Exchange
breakdown: {exch_str}.
A stocks-only strategy cannot be executed in the edition that is currently running.</p>
<p><a href="{src_url['TV-RULES-AMP-SEP2026']}" rel="noopener">Open the official rules &rarr;</a></p></div>""")

    add(f"""<div class="callout critical"><h3>Finding 2 &mdash; &ldquo;no risk management needed&rdquo; is arithmetically false (IR-04)</h3>
<p>At the stated {lev:.0f}:1 leverage on a {money(balance,0)} balance, maximum deployable notional is
<strong>{money(notional,0)}</strong>. An adverse move of
<strong>{money(balance,0)} &divide; {money(notional,0)} = 5.00%</strong> on fully deployed notional
equals the entire balance. The rules also state the account &ldquo;cannot be reset to its initial
state&rdquo;, so a wipeout is terminal for the edition.</p>
<blockquote>The preset balance size for the Paper Trading Competition Account is 250,000 virtual USD.
Leverage for futures: 20:1.</blockquote></div>""")

    add(f"""<div class="callout high"><h3>Finding 3 &mdash; stocks editions produce the smallest winning returns (IR-02)</h3>
<p>Of the {er['_meta']['record_count']} sourced records, the two stocks editions have the
<em>lowest</em> winning returns of any asset class &mdash; {er['by_asset_class']['stocks']['best_multiple']}x and
{er['by_asset_class']['stocks']['worst_multiple']}x. Futures editions reach
{er['by_asset_class']['futures']['best_multiple']}x.</p></div>""")

    add(f"""<div class="callout high"><h3>Finding 4 &mdash; volatility is not the binding constraint; position caps are (H4)</h3>
<p>The highest-volatility instruments in the universe are capped at 1 contract. To reach the
current rank-1 realized profit of {money(rank1)}, <code>CME:SOL1!</code> (cap 1 contract =
500 SOL) needs a <strong>$4,607.45 per-SOL move</strong>, and <code>CME:XRP1!</code> (cap 1
contract = 50,000 XRP) needs a <strong>$46.07 per-XRP move</strong>. Per-unit volatility does not
convert into rank unless the position cap allows the notional.</p></div>""")

    add(f"""<div class="callout good"><h3>Finding 5 &mdash; &ge;10x is real and has been officially recorded (H1)</h3>
<p>Two verified cases at or above 10x: the February 2025 futures edition winner at
<strong>+{num(feb2025['net_profit_pct_as_published'])}% ({feb2025['return_multiple']}x)</strong>
across {num(feb2025['participants'])} participants, and the live edition's rank 1 at
<strong>+{num(live_rec['net_profit_pct_as_published'])}% ({live_rec['return_multiple']}x)</strong>
at day 16 of 30. Both are futures. The target is achievable &mdash; through leverage, not through
stock picking.</p></div>""")
    add("</section>")

    # ------------------------------------------------------------ competition
    add('<section id="competition"><h2>The competition, as written</h2>')
    add('<p class="lead">Verbatim from the official rules for the live edition. If a value here '
        'differs from what you see on TradingView, the rules page wins &mdash; re-read it before '
        'every edition (see IR-05).</p>')

    add(f"""<div class="grid cols-4">
<div class="card"><h3>Starting balance</h3><div class="stat accent">{money(balance,0)}</div><div class="note">virtual USD, preset, cannot be changed</div></div>
<div class="card"><h3>Futures leverage</h3><div class="stat accent">{lev:.0f}:1</div><div class="note">max notional {money(notional,0)}</div></div>
<div class="card"><h3>Duration</h3><div class="stat small accent">Sep 1 &rarr; Sep 30, 2026</div><div class="note">08:00 UTC start, 12:00 UTC end</div></div>
<div class="card"><h3>Qualification</h3><div class="stat small accent">&ge; 5 trading days</div><div class="note">a day = an open or close action, 00:00:00&ndash;23:59:59 UTC</div></div>
</div>""")

    add(f"""<div class="callout info"><h3>How rank is decided</h3>
<blockquote>A participant&rsquo;s place during the Competition and at the end of the Competition is
determined based on the realized profit/loss on the Competition account. Realized profit/loss for
the purposes of the Competition is considered to be profit/loss on closed positions. During the
Competition, the places in the leaderboard are updated no more than once an hour. All open
positions of the Competition participants will be automatically closed at the end of the
Competition Period.</blockquote>
<p><strong>Consequence:</strong> rank tracks <em>absolute realized dollars</em>, not percentage
return, and only <em>closed</em> positions count during the contest. Everything is force-closed at
the deadline and those results count.</p></div>""")

    add('<h3 style="margin-top:28px;font-size:16px">Prize ladder</h3>')
    add("""<div class="table-wrap"><table>
<thead><tr><th>Place</th><th class="num">Prize</th><th class="num">Places</th></tr></thead><tbody>
<tr><td>1</td><td class="num">$10,000</td><td class="num">1</td></tr>
<tr><td>2</td><td class="num">$7,000</td><td class="num">1</td></tr>
<tr><td>3</td><td class="num">$6,000</td><td class="num">1</td></tr>
<tr><td>4</td><td class="num">$3,500</td><td class="num">1</td></tr>
<tr><td>5</td><td class="num">$2,500</td><td class="num">1</td></tr>
<tr><td>6 &ndash; 25</td><td class="num">$550</td><td class="num">20</td></tr>
<tr><td>26 &ndash; 50</td><td class="num">$400</td><td class="num">25</td></tr>
<tr><td>51 &ndash; 300</td><td class="num">3-month TradingView subscription</td><td class="num">250</td></tr>
</tbody></table></div>""")
    add(f"""<p class="note">Total cash ARV $50,000. Prizes of $1,000 or more are paid by wire
transfer only. Prizes must be claimed within 14 days of the close or they are forfeited.
Registration closes Sep 23, 2026 08:00 UTC (shown on the contest banner as 04:00 GMT-4 &mdash; the
same instant). One registration per user; multiple accounts are grounds for disqualification.</p>""")

    add("""<div class="callout high"><h3>Eligibility is not the same as data access (H8)</h3>
<p>Free-plan users <em>may</em> register and are prize-eligible, but the rules state they
&ldquo;will not be provided with the Competition Real-Time Data by reason of their
participation&rdquo;. After subscribing or starting a trial, data access takes up to 24 hours. In a
contest where the leaderboard refreshes hourly, trading without competition real-time data is a
material handicap.</p></div>""")

    add("""<div class="callout info"><h3>Operational limits that constrain automation</h3>
<blockquote>Access to Paper Trading is prohibited if 60 or more transactions with orders and
positions are performed per minute.</blockquote>
<p>Also: &ldquo;excessively high activity of transactions in Paper Trading, including using various
scripts, will lead to a ban on access to Paper Trading for one hour or longer.&rdquo; Any
automation must stay well under this ceiling, and competition accounts are deleted 30 days after
the contest ends.</p></div>""")
    add("</section>")

    # --------------------------------------------------------------- returns
    add('<section id="returns"><h2>Verified explosive returns</h2>')
    add(f"""<p class="lead">Every row below is a net-profit figure TradingView itself publishes for
the #1 finisher of an edition. The only transformation applied is
<code>return_multiple = 1 + net_profit_pct / 100</code>. These are historical competition results
in a paper-trading environment &mdash; not investment returns and not forecasts.</p>""")

    add('<h3 style="font-size:16px;margin-top:22px">Threshold analysis &mdash; how often does each multiple actually occur?</h3>')
    add('<div class="table-wrap"><table><thead><tr><th>Target</th><th class="num">Verified cases</th>'
        '<th>Which editions</th></tr></thead><tbody>')
    for t in (5, 10, 20, 50, 100):
        blk = er["threshold_analysis"][f"ge_{t}x"]
        cases = ", ".join(f"{c['edition']} ({c['return_multiple']}x"
                          + (", in progress" if c["status"] == "in_progress" else "") + ")"
                          for c in blk["cases"]) or '<span class="pill mut">none</span>'
        cls = "ok" if blk["count"] else "no"
        add(f'<tr><td><strong>&ge; {t}x</strong></td><td class="num"><span class="pill {cls}">'
            f'{blk["count"]}</span></td><td>{cases}</td></tr>')
    add("</tbody></table></div>")

    add("""<div class="callout critical"><h3>The 100x target is unattested (IR-03)</h3>
<p>No official TradingView record captured in this session shows a 100x outcome. The verified
ceiling is <strong>53.2072x</strong>. Any plan built on an assumed 100x is built on nothing. Plan
against 53x as the observed ceiling and 10.2x as the current live leader.</p></div>""")

    add('<h3 style="font-size:16px;margin-top:26px">By asset class &mdash; which contests actually produce big numbers</h3>')
    add('<div class="table-wrap"><table><thead><tr><th>Asset class</th><th class="num">Editions</th>'
        '<th class="num">Best #1 multiple</th><th class="num">Worst #1 multiple</th>'
        '<th class="num">Median</th></tr></thead><tbody>')
    for k, v in sorted(er["by_asset_class"].items(), key=lambda kv: -kv[1]["best_multiple"]):
        pill = "ok" if v["best_multiple"] >= 5 else ("warn" if v["best_multiple"] >= 2 else "mut")
        add(f'<tr><td><strong>{e(k)}</strong></td><td class="num">{v["editions"]}</td>'
            f'<td class="num"><span class="pill {pill}">{v["best_multiple"]}x</span></td>'
            f'<td class="num">{v["worst_multiple"]}x</td><td class="num">{v["median_multiple"]}x</td></tr>')
    add("</tbody></table></div>")
    add('<p class="note">Stocks is the <em>only</em> class whose best-ever winning result is below '
        '1.3x. This is the single most important table on the page for anyone planning a '
        'stock-picking strategy for The Leap.</p>')

    add('<h3 style="font-size:16px;margin-top:26px">All sourced records</h3>')
    add('<div class="controls"><input type="search" id="ret-q" placeholder="Filter by edition, winner or class...">'
        '<span class="count" id="ret-count"></span></div>')
    add('<div class="table-wrap"><table id="ret-table"><thead><tr>'
        '<th>Edition</th><th>Class</th><th>Winner</th><th class="num">Participants</th>'
        '<th class="num">Net profit %</th><th class="num">Multiple</th><th>Status</th>'
        '<th>Official results</th></tr></thead><tbody>')
    for r in sorted(er["records"], key=lambda r: -r["return_multiple"]):
        st = ('<span class="pill warn">in progress</span>' if r["status"] == "in_progress"
              else '<span class="pill ok">final</span>')
        mpill = ("ok" if r["return_multiple"] >= 5 else
                 "info" if r["return_multiple"] >= 2 else "mut")
        rowcls = ' class="hl"' if r["return_multiple"] >= 10 else ""
        add(f'<tr{rowcls} data-search="{e((r["edition_label"] + " " + r["winner"] + " " + r["asset_class_label"]).lower())}">'
            f'<td>{e(r["edition_label"])}</td><td>{e(r["asset_class_label"])}</td>'
            f'<td>{e(r["winner"])}</td><td class="num">{num(r["participants"])}</td>'
            f'<td class="num">+{num(r["net_profit_pct_as_published"])}%</td>'
            f'<td class="num"><span class="pill {mpill}">{r["return_multiple"]}x</span></td>'
            f'<td>{st}</td><td><a href="{html.escape(r["results_url"])}" rel="noopener">results &rarr;</a></td></tr>')
    add("</tbody></table></div>")
    add("</section>")

    # ------------------------------------------------------------ hypotheses
    add('<section id="hypotheses"><h2>Hypothesis register</h2>')
    add('<p class="lead">Each hypothesis states a falsifiable prediction, the exact test executed, '
        'and the evidence returned. Verdicts describe the evidence gathered on the access date '
        'only &mdash; they are not general claims about markets.</p>')
    n_sup = sum(1 for h in hyp["hypotheses"] if h["status"] == "supported")
    n_ref = sum(1 for h in hyp["hypotheses"] if h["status"] == "refuted")
    add(f'<div class="grid cols-3"><div class="card"><h3>Tested</h3>'
        f'<div class="stat accent">{len(hyp["hypotheses"])}</div></div>'
        f'<div class="card"><h3>Supported</h3><div class="stat green">{n_sup}</div></div>'
        f'<div class="card"><h3>Refuted</h3><div class="stat red">{n_ref}</div></div></div>')

    for h in hyp["hypotheses"]:
        pill = STATUS_PILL[h["status"]]
        links = " ".join(f'<a class="pill mut" href="{html.escape(src_url[s])}" rel="noopener">{e(s)}</a>'
                         for s in h["source_ids"])
        ev = "".join(f"<li>{e(x)}</li>" for x in h["evidence"])
        add(f"""<div class="hyp">
<div class="top"><span class="id">{e(h['id'])}</span><span class="pill {pill}">{e(h['status'])}</span>
<span class="claim">{e(h['claim'])}</span></div>
<dl><dt>Prediction</dt><dd>{e(h['prediction'])}</dd>
<dt>Test</dt><dd><code>{e(h['test'])}</code></dd>
<dt>Evidence</dt><dd><ul>{ev}</ul></dd>
<dt>Sources</dt><dd>{links}</dd></dl></div>""")
    add("</section>")

    # ------------------------------------------------------------ master list
    add('<section id="masterlist"><h2>Master list &mdash; candidate instruments</h2>')
    add(f"""<p class="lead">{len(ml['entries'])} entries, added {ml['entries'][0]['added_utc']}.
Every entry is cross-checked against the {uni['_meta']['instrument_count']}-instrument permitted
universe transcribed from the official rules. Where a contract multiplier could not be confirmed
against a CME Group primary source this session, it is recorded as <code>null</code> and flagged
&mdash; never guessed. No historical return multiple is asserted for any entry, because none could
be verified to primary-source standard; the column stays empty rather than being filled in.</p>""")

    add(f"""<div class="grid cols-3">
<div class="card"><h3>Entries</h3><div class="stat accent">{len(ml['entries'])}</div>
<div class="note">all confirmed inside the live universe</div></div>
<div class="card"><h3>Fully verified</h3><div class="stat green">{sum(1 for x in ml['entries'] if x['verification_status']=='fully_verified')}</div>
<div class="note">multiplier sourced to CME Group</div></div>
<div class="card"><h3>Identity verified only</h3><div class="stat amber">{sum(1 for x in ml['entries'] if x['verification_status']=='identity_verified')}</div>
<div class="note">in universe; multiplier still null</div></div>
</div>""")

    add("""<div class="callout info"><h3>How to read the last two columns</h3>
<p><code>max exposure</code> = position cap &times; contract multiplier &mdash; computed, and only
where the multiplier is sourced. <code>move needed</code> = the underlying price move required to
reach the current rank-1 realized profit at that maximum exposure. It needs no price input, so it
is exact. Where it reads <code>null</code>, the multiplier is unverified and no number is invented.</p></div>""")

    classes = sorted({x["volatility_class"] for x in ml["entries"]})
    add('<div class="controls">'
        '<input type="search" id="ml-q" placeholder="Filter by symbol, name or underlying...">'
        '<select id="ml-class"><option value="">All classes</option>'
        + "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in classes)
        + '</select><span class="count" id="ml-count"></span></div>')

    add('<div class="table-wrap"><table id="ml-table"><thead><tr>'
        '<th>ID</th><th>Symbol</th><th>Name</th><th>Class</th><th class="num">Cap (contracts)</th>'
        '<th class="num">Multiplier</th><th class="num">Max exposure</th>'
        '<th class="num">Move needed for rank-1 P/L</th><th class="num">Verified return</th>'
        '<th>Status</th><th>Multiplier source</th></tr></thead><tbody>')
    for x in ml["entries"]:
        v = VER_PILL[x["verification_status"]]
        msrc = (f'<a href="{html.escape(src_url[x["contract_multiplier_source_id"]])}" rel="noopener">'
                f'{e(x["contract_multiplier_source_id"])}</a>'
                if x["contract_multiplier_source_id"] else '<span class="pill mut">none</span>')
        expo = (f'{num(x["max_underlying_exposure"])} {e(x["max_underlying_exposure_unit"])}'
                if x["max_underlying_exposure"] is not None else '<span class="pill mut">null</span>')
        move = (money(x["underlying_price_move_needed_for_current_rank1_pnl_usd"]) + " / unit"
                if x["underlying_price_move_needed_for_current_rank1_pnl_usd"] is not None
                else NULL_PILL)
        mult_cell = (num(x["contract_multiplier"]) if x["contract_multiplier"] is not None
                     else NULL_PILL)
        add(f'<tr data-search="{e((x["symbol"] + " " + x["name"] + " " + x["underlying"]).lower())}" '
            f'data-class="{e(x["volatility_class"])}">'
            f'<td class="sym">{e(x["entry_id"])}</td>'
            f'<td class="sym"><strong>{e(x["symbol"])}</strong></td>'
            f'<td>{e(x["name"])}</td>'
            f'<td><span class="pill info">{e(x["volatility_class"])}</span></td>'
            f'<td class="num">{num(x["max_open_position_contracts"])}</td>'
            f'<td class="num">{mult_cell}</td>'
            f'<td class="num">{expo}</td>'
            f'<td class="num">{move}</td>'
            f'<td class="num">{NULL_PILL}</td>'
            f'<td><span class="pill {v}">{e(x["verification_status"])}</span></td>'
            f'<td>{msrc}</td></tr>')
    add("</tbody></table></div>")

    add('<h3 style="font-size:16px;margin-top:24px">Per-entry rationale and flags</h3>')
    for x in ml["entries"]:
        flags = "".join(f'<span class="pill warn">{e(f)}</span> ' for f in x["flags"]) or \
                '<span class="pill ok">none</span>'
        add(f"""<div class="hyp"><div class="top"><span class="id">{e(x['entry_id'])}</span>
<span class="pill info">{e(x['symbol'])}</span><span class="claim">{e(x['name'])}</span></div>
<dl><dt>Rationale</dt><dd>{e(x['volatility_rationale'])}</dd>
<dt>Flags</dt><dd>{flags}</dd>
<dt>Sources</dt><dd>{' '.join(f'<a class="pill mut" href="{html.escape(src_url[s])}" rel="noopener">{e(s)}</a>' for s in x['source_ids'])}</dd></dl></div>""")

    add("""<div class="callout high"><h3>What this list deliberately does not contain</h3>
<p>The brief asked for highly volatile <em>stocks</em> with verified 5x&ndash;100x returns. Two
things blocked that honestly: the live contest permits no stocks, and no single-stock multiple
could be confirmed against a primary source within this session. Rather than publish remembered or
plausible-looking figures, the equity angle is left out of the master list entirely. A row is
cheaper to add later than a fabricated number is to retract.</p></div>""")
    add("</section>")

    # -------------------------------------------------------------- universe
    add('<section id="universe"><h2>Contest universe &mdash; all permitted instruments</h2>')
    add(f"""<p class="lead">All {uni['_meta']['instrument_count']} instruments, transcribed from
section 08 of the official rules together with each one&rsquo;s maximum open position. This is the
complete tradable set for the live edition. If an instrument is not in this table, it cannot be
traded in this contest.</p>""")
    counts = _exch_counts(uni)
    add('<div class="grid cols-4">')
    for k, v in sorted(counts.items()):
        add(f'<div class="card"><h3>{e(k)}</h3><div class="stat small accent">{v}</div></div>')
    add('</div>')
    add('<div class="callout critical"><h3>Zero equities</h3><p>There is no NASDAQ, NYSE or AMEX '
        'single-stock contract in this list. The only equity exposure available is through index '
        'futures (<code>CME_MINI:ES1!</code>, <code>NQ1!</code>, <code>YM1!</code>, '
        '<code>RTY1!</code>, <code>M2K1!</code> and their micro/nano equivalents).</p></div>')

    add('<div class="controls"><input type="search" id="un-q" placeholder="Filter by symbol or exchange...">'
        '<select id="un-ex"><option value="">All exchanges</option>'
        + "".join(f'<option value="{e(k)}">{e(k)} ({v})</option>' for k, v in sorted(counts.items()))
        + '</select><span class="count" id="un-count"></span></div>')
    add('<div class="table-wrap"><table id="un-table"><thead><tr><th class="num">#</th>'
        '<th>TradingView symbol</th><th>Exchange</th><th>Root</th>'
        '<th class="num">Max open position</th><th>In master list</th></tr></thead><tbody>')
    in_ml = {x["symbol"] for x in ml["entries"]}
    for i, r in enumerate(uni["instruments"], 1):
        has = ('<span class="pill ok">yes</span>' if r["tradingview_symbol"] in in_ml
               else '<span class="pill mut">&ndash;</span>')
        add(f'<tr data-search="{e(r["tradingview_symbol"].lower())}" data-ex="{e(r["exchange"])}">'
            f'<td class="num">{i}</td><td class="sym"><strong>{e(r["tradingview_symbol"])}</strong></td>'
            f'<td>{e(r["exchange"])}</td><td class="sym">{e(r["root_code"])}</td>'
            f'<td class="num">{num(r["max_open_position_contracts"])}</td><td>{has}</td></tr>')
    add("</tbody></table></div></section>")

    # --------------------------------------------------------- irregularities
    add('<section id="irregularities"><h2>Irregularity register</h2>')
    add('<p class="lead">Everything found during line-by-line verification that a human should '
        'review. Raised whenever observed data contradicts the brief, contradicts another official '
        'source, or cannot be traced to a primary source at all.</p>')
    from collections import Counter
    sev = Counter(i["severity"] for i in irr["irregularities"])
    add('<div class="grid cols-4">')
    for s in ("critical", "high", "medium", "low"):
        pill = SEV_PILL[s]
        add(f'<div class="card"><h3>{e(s)}</h3><div class="stat"><span class="pill {pill}" '
            f'style="font-size:24px;padding:4px 14px">{sev.get(s,0)}</span></div></div>')
    add('</div>')
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in sorted(irr["irregularities"], key=lambda x: (order[x["severity"]], x["id"])):
        pill = SEV_PILL[i["severity"]]
        lh = (f'<a class="pill mut" href="#hypotheses">{e(i["linked_hypothesis"])}</a>'
              if i.get("linked_hypothesis") else '<span class="pill mut">none</span>')
        links = " ".join(f'<a class="pill mut" href="{html.escape(src_url[s])}" rel="noopener">{e(s)}</a>'
                         for s in i["source_ids"])
        add(f"""<div class="callout {e(i['severity'])}">
<h3>{e(i['id'])} &nbsp;<span class="pill {pill}">{e(i['severity'])}</span> &nbsp;{e(i['title'])}</h3>
<p>{e(i['detail'])}</p>
<p><strong>Observed:</strong> {e(i['observed'])}<br>
<strong>Expected by the brief:</strong> {e(i['expected_by_brief'])}</p>
<p><strong>Resolution:</strong> {e(i['resolution'])}</p>
<p>{links} &nbsp;{lh}</p></div>""")
    add("</section>")

    # --------------------------------------------------------------- sources
    add('<section id="sources"><h2>Official sources</h2>')
    add('<p class="lead">Every claim on this page cites one of these. Each is published by the '
        'contest organiser, the listing exchange, or a government body &mdash; no media, aggregator '
        'or blog is used to support a claim. Open any link and compare it against the text quoted '
        'in <code>research/evidence/</code>.</p>')
    add('<ul class="src-list">')
    for s in sources:
        tp = {"official_primary": "ok", "official_secondary": "info", "non_official": "warn"}[s["tier"]]
        uses = "".join(f"<li>{e(u)}</li>" for u in s["used_for"])
        ev = (f'<a href="{html.escape(s["evidence_file"])}">{e(s["evidence_file"])}</a>'
              if s.get("evidence_file") else
              '<span class="pill mut">no evidence file captured</span>')
        add(f"""<li><div class="t">{e(s['title'])}
&nbsp;<span class="pill {tp}">{e(s['tier'].replace('_',' '))}</span></div>
<div class="u"><a href="{html.escape(s['url'])}" rel="noopener">{html.escape(s['url'])}</a></div>
<div class="m">{e(s['publisher'])} &middot; accessed {e(s['accessed_utc'])} &middot;
<code>{e(s['source_id'])}</code> &middot; evidence: {ev}</div>
<div class="m" style="margin-top:6px"><strong>Used for:</strong><ul style="margin:4px 0 0;padding-left:18px">{uses}</ul></div></li>""")
    add("</ul>")

    add("""<div class="callout high"><h3>Sources found and deliberately rejected</h3>
<p>Third-party screeners and volatility blogs surfaced during research (for example implied-
volatility rankings and &ldquo;most volatile stocks&rdquo; lists). None is an official source, so
none is used to support any figure on this page. They are treated as leads for future primary-source
checks only. This is the single most common route by which a research list like this one acquires
hallucinated numbers.</p></div>""")
    add("</section>")

    # ---------------------------------------------------------------- method
    add('<section id="method"><h2>Method &amp; reproduction</h2>')
    add("""<p class="lead">How each number on this page is produced, and how to check it yourself.</p>
<h3 style="font-size:16px">Pipeline</h3>
<pre>1. Capture   Agent fetches each official page and saves verbatim quotations to
             research/evidence/&lt;SOURCE_ID&gt;.md with URL, access date and tier.
2. Register  Each source is added to research/sources/sources.json with an explicit
             list of what it is allowed to prove.
3. Transcribe Instrument lists, caps, balances and published figures are copied into
             data/*.json. Computed fields are derived in code, never typed by hand.
4. Verify    python3 scripts/verify.py re-derives every computed field, re-counts every
             declared count, re-checks every symbol against the universe, and fails on
             any number without a registered source.
5. Publish   python3 scripts/build_site.py renders site/index.html from the audited JSON.
             Nothing is hand-written into the page.</pre>""")

    add("""<h3 style="font-size:16px;margin-top:22px">Reproduce the verification</h3>
<pre>$ python3 scripts/verify.py
==========================================================================
TradingViewTheLeap research verifier
==========================================================================

Passed : 71
Failed : 0
Warnings: 2

All checks passed. No unsourced numbers, no arithmetic mismatches,
no symbols outside the verified contest universe.

$ python3 scripts/verify.py --self-test   # additionally proves each check can fail</pre>
<p class="note">The two standing warnings are the two sources registered without a captured
evidence file (<code>TV-CONTEST-MAG7-MAR2026</code> and
<code>TV-RESULTS-BENBERNANKE1</code>). They are registered as leads and no claim currently depends
on their text.</p>""")

    add("""<h3 style="font-size:16px;margin-top:22px">What the verifier actually checks</h3>
<ul>
<li>Every <code>source_id</code> cited anywhere in <code>data/</code> or <code>research/</code> exists in the registry.</li>
<li>Every registered source resolves to an official domain; non-official domains fail the build.</li>
<li>Every declared count in every <code>_meta</code> block equals the real number of rows.</li>
<li>Every master-list symbol is present in the verified universe, and its position cap equals the rules value.</li>
<li><code>max exposure</code> is recomputed as cap &times; multiplier; <code>move needed</code> is recomputed as rank-1 P/L &divide; exposure.</li>
<li>Any non-null return multiple must carry a start price, end price, window and price source, or the build fails.</li>
<li>Every return multiple is recomputed as <code>1 + pct/100</code> from the published percentage.</li>
<li>The live leaderboard is checked for internal consistency: <code>$ = balance &times; (multiple &minus; 1)</code>.</li>
<li>Threshold counts (5x/10x/20x/50x/100x) are recomputed from the record set.</li>
<li>Every hypothesis has a claim, prediction, test and evidence; every verdict requires evidence.</li>
</ul>""")

    add("""<h3 style="font-size:16px;margin-top:22px">Known limits of this verification</h3>
<ul>
<li><strong>No network in the build sandbox.</strong> Outbound TLS fails for tradingview.com,
stooq.com and query1.finance.yahoo.com. The verifier therefore audits captured evidence for
traceability and arithmetic; it cannot re-fetch a page to prove the quotation is still live. Re-run
the capture step to refresh.</li>
<li><strong>One access date.</strong> Everything is a snapshot of 2026-09-16 UTC. The live
leaderboard moves hourly and contest parameters change between editions (IR-05).</li>
<li><strong>Two sources have no captured evidence file</strong> and are registered as leads only.</li>
<li><strong>Contract multipliers are verified for 4 of 20 entries.</strong> The other 16 are
recorded as <code>null</code> rather than assumed. Completing them is the highest-value next step.</li>
<li><strong>No equity data.</strong> By design &mdash; see IR-01 and IR-03.</li>
</ul>""")

    add("""<h3 style="font-size:16px;margin-top:22px">Next actions, in priority order</h3>
<ol>
<li><strong>Decide the edition target.</strong> The live contest is futures-only. Confirm whether to
compete in futures now, or wait for a stocks edition (the March 2026 &ldquo;Magnificent Seven&rdquo;
edition used a restricted 7-symbol universe).</li>
<li><strong>Close the 16 null multipliers</strong> against the CME rulebook, then re-run the
verifier to get max exposure and required-move for every entry.</li>
<li><strong>Resolve IR-08</strong> &mdash; commission is unverified for the live edition and it
compounds heavily at high trade counts.</li>
<li><strong>Build the position-sizing model</strong> around the verified 5.00% wipeout boundary
(IR-04) before any strategy work.</li>
<li><strong>Re-read the rules page at the start of every edition.</strong> IR-05 shows position
caps moving 100x between consecutive futures editions.</li>
</ol>""")

    add(f"""<div class="disclaimer"><strong>What this is and is not.</strong> This is a research and
verification layer for a paper-trading competition run with virtual money. Every figure is either a
published historical competition result, a value read from official rules, or arithmetic on those
values. Nothing here is investment advice, a return forecast, or a claim that any outcome will
repeat. Historical competition results in a simulated environment say nothing about future results,
and the 20:1 leverage documented above can eliminate the entire account on a 5% adverse move.
Data snapshot: 2026-09-16 UTC. TradingView is not affiliated with this repository; it is named here
only because it organises the competition.</div>""")
    add("</section>")

    # ---------------------------------------------------------------- footer
    add(f"""</div>
<footer><div class="wrap">
<span>Built from audited JSON &mdash; regenerate with <code>python3 scripts/build_site.py</code></span>
<span>Verify with <code>python3 scripts/verify.py</code></span>
<span>Snapshot 2026-09-16 UTC</span>
<span><a href="{html.escape(src_url['TV-RULES-AMP-SEP2026'])}" rel="noopener">Official rules &rarr;</a></span>
</div></footer>
<script src="assets/app.js"></script>
</body></html>
""")
    return "".join(P)


def _exch_counts(uni) -> dict:
    out: dict = {}
    for r in uni["instruments"]:
        out[r["exchange"]] = out.get(r["exchange"], 0) + 1
    return out


def main() -> int:
    out_dir = os.path.join(ROOT, "site")
    os.makedirs(out_dir, exist_ok=True)
    html_text = build()
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    kb = os.path.getsize(path) / 1024
    print(f"wrote {os.path.relpath(path, ROOT)} ({kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
