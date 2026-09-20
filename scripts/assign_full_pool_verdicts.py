#!/usr/bin/env python3
"""Assign the H34-H39/H41 full-pool verdicts mechanically, from the committed competition run.

Why this is a script and not a sentence somebody typed
------------------------------------------------------
H34-H39 and H41 are the seven hypotheses that claim a frozen stock model (C14-C19, C22)
beats the B1 control on the *full* 20-stock daily pool. Each one was registered with its prediction and
its test written down before any full-pool result existed, and `scripts/verify.py` refuses
to let any of them carry a `supported`/`refuted` status until the capture matrix holds all
60 stock series (20 symbols x 15m/1h/1d, including 20/20 daily).

So when coverage finally lands, the verdict must not be eyeballed off a leaderboard. This
script reads `data/stock_competition_results.json`, applies the decision rule below, and
writes both the derivation and the resulting status. The verifier then re-runs the same
rule and fails if the committed verdict or the committed hypothesis status disagrees, so a
hand-edited verdict cannot survive a build.

The pre-registered decision rule (verbatim from the seven predictions)
----------------------------------------------------------------------
Every H34-H39/H41 prediction has the same shape:

    "the C<nn> usernames (<a>, <b>) finish ahead of VolatilityVera (B1) by season realized
     P/L in the primary profile, in-sample and forward-held-out alike."

Read literally that is a claim about *both* usernames, tested in *both* splits. So:

* ``beat_all``    - every username of the model beats the B1 control's season realized P/L
                    in the full-season leaderboard AND in the forward-held-out leaderboard.
* ``beat_any``    - at least one username does, in both splits.
* ``zero_fire``   - the model's usernames took no trades at all in the season
                    (``total_trades == 0``). Per research/strategy/C19-VARIANT-GATE.md a
                    zero-fire result is evidence about coverage, not about the thesis.

Mapping to the register's status vocabulary:

* ``beat_all``                              -> ``supported``
* ``beat_any`` and not ``beat_all``         -> ``partially_supported``
* ``zero_fire``                             -> ``inconclusive``  (never ``refuted``)
* otherwise                                 -> ``refuted``

Everything the rule consumed is written to ``data/full_pool_verdicts.json``: the per-username
season and forward P/L, the control's, the trade counts, the split windows, the coverage
counts, and the rule text itself. Nothing here reads the network and nothing here invents a
number - a missing username or a missing control row is a hard error, not a silent pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPOTHESES_PATH = os.path.join(ROOT, "research", "hypotheses", "hypotheses.json")
COMPETITION_PATH = os.path.join(ROOT, "data", "stock_competition_results.json")
INTRADAY_INDEX_PATH = os.path.join(ROOT, "data", "intraday_index.json")
VOLATILE_PATH = os.path.join(ROOT, "data", "volatile_stocks.json")
OUT_PATH = os.path.join(ROOT, "data", "full_pool_verdicts.json")

INTERVALS = ("15m", "1h", "1d")
FULL_POOL_HYPOTHESES = ("H34", "H35", "H36", "H37", "H38", "H39", "H41")
CONTROL_USERNAME = "VolatilityVera"
CONTROL_MODEL = "B1"

DECISION_RULE = (
    "For each hypothesis, take every rostered username of its model on the daily division "
    "under the primary profile (stocks_official_leap). beat_all = every one of those "
    "usernames has a higher season_realized_pnl_usd than the B1 control (VolatilityVera) in "
    "BOTH the full-season leaderboard and the forward-held-out leaderboard. beat_any = at "
    "least one does, in both splits. zero_fire = every one of those usernames has "
    "total_trades == 0 for the season. Verdict: beat_all -> supported; beat_any and not "
    "beat_all -> partially_supported; zero_fire -> inconclusive (never refuted, per "
    "research/strategy/C19-VARIANT-GATE.md); otherwise refuted."
)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def coverage() -> dict:
    """Captured stock-series counts, computed exactly the way the verifier's gate does."""
    pool = [r["symbol"] for r in load(VOLATILE_PATH)["records"]]
    have = set()
    for rec in load(INTRADAY_INDEX_PATH).get("captures", []):
        if rec.get("status") != "captured":
            continue
        if rec.get("kind") not in (None, "equity"):
            continue
        if rec.get("symbol") in pool and rec.get("interval") in INTERVALS:
            have.add((rec["symbol"], rec["interval"]))
    wanted = {(s, iv) for s in pool for iv in INTERVALS}
    daily = {s for s, iv in have if iv == "1d"}
    return {
        "pool_symbols": len(pool),
        "series_captured": len(have),
        "series_required": len(wanted),
        "daily_captured": len(daily),
        "complete": have == wanted and daily == set(pool),
        "missing": sorted(f"{s}[{iv}]" for s, iv in wanted - have),
    }


def row_by_username(leaderboard) -> dict:
    return {row["username"]: row for row in leaderboard}


def model_usernames(participants, model: str) -> list[dict]:
    return [p for p in participants if p.get("model") == model and p.get("division") == "daily"]


def verdict_for(model: str, season: dict, forward: dict, participants: dict) -> dict:
    users = model_usernames(participants, model)
    if not users:
        raise SystemExit(f"{model}: no rostered daily username - cannot evaluate")
    if CONTROL_USERNAME not in season or CONTROL_USERNAME not in forward:
        raise SystemExit(f"control {CONTROL_USERNAME} (B1) is missing from the leaderboards")
    b1_season = season[CONTROL_USERNAME]["season_realized_pnl_usd"]
    b1_forward = forward[CONTROL_USERNAME]["season_realized_pnl_usd"]

    per_user = []
    for p in sorted(users, key=lambda r: r["username"]):
        name = p["username"]
        if name not in season or name not in forward:
            raise SystemExit(f"{name} ({model}) is missing from a leaderboard")
        s_pnl = season[name]["season_realized_pnl_usd"]
        f_pnl = forward[name]["season_realized_pnl_usd"]
        beats_both = s_pnl > b1_season and f_pnl > b1_forward
        per_user.append(
            {
                "username": name,
                "variant": p.get("variant"),
                "season_realized_pnl_usd": s_pnl,
                "season_multiple": season[name].get("season_multiple"),
                "forward_realized_pnl_usd": f_pnl,
                "total_trades": p.get("total_trades"),
                "total_add_tranches": p.get("total_add_tranches"),
                "ruined_editions": p.get("ruined_editions"),
                "beats_control_season": s_pnl > b1_season,
                "beats_control_forward": f_pnl > b1_forward,
                "beats_control_both": beats_both,
            }
        )

    beat_all = all(u["beats_control_both"] for u in per_user)
    beat_any = any(u["beats_control_both"] for u in per_user)
    zero_fire = all((u["total_trades"] or 0) == 0 for u in per_user)
    if beat_all:
        status = "supported"
    elif beat_any:
        status = "partially_supported"
    elif zero_fire:
        status = "inconclusive"
    else:
        status = "refuted"
    return {
        "model": model,
        "status": status,
        "beat_all": beat_all,
        "beat_any": beat_any,
        "zero_fire": zero_fire,
        "control": {
            "username": CONTROL_USERNAME,
            "model": CONTROL_MODEL,
            "season_realized_pnl_usd": b1_season,
            "forward_realized_pnl_usd": b1_forward,
            "total_trades": next(
                (p.get("total_trades") for p in participants
                 if p.get("username") == CONTROL_USERNAME), None),
        },
        "usernames": per_user,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-hypotheses", action="store_true",
                        help="also update the status and evidence of H34-H39 in the register")
    parser.add_argument("--force", action="store_true",
                        help="evaluate even when the matrix is not 60/60 (recorded as such)")
    args = parser.parse_args()

    cov = coverage()
    out_path = OUT_PATH
    if not cov["complete"]:
        detail = (f"matrix is {cov['series_captured']}/{cov['series_required']} series "
                  f"(daily {cov['daily_captured']}/{cov['pool_symbols']}); missing {cov['missing']}")
        if not args.force:
            print(f"refusing to assign full-pool verdicts: {detail}")
            return 2
        # --force is a rehearsal aid only. It must never be able to put a partial-pool
        # verdict at the canonical path the verifier and the site read, and it must never
        # touch the hypothesis register.
        out_path = os.path.join(ROOT, "data", "full_pool_verdicts_REHEARSAL.json")
        args.write_hypotheses = False
        print(f"REHEARSAL ONLY (coverage incomplete: {detail}); "
              f"writing {os.path.relpath(out_path, ROOT)} and leaving the register untouched")

    comp = load(COMPETITION_PATH)
    daily = comp["divisions"]["daily"]
    if daily.get("profile") != "stocks_official_leap":
        raise SystemExit(f"unexpected primary profile {daily.get('profile')!r}")
    season = row_by_username(daily["leaderboard"])
    forward_held_out = daily.get("forward_held_out") or {}
    forward = row_by_username(forward_held_out.get("forward_leaderboard") or [])
    in_sample = row_by_username(forward_held_out.get("in_sample_leaderboard") or [])
    participants = daily.get("participants") or []

    hyps = {h["id"]: h for h in load(HYPOTHESES_PATH)["hypotheses"]}
    models = {"H34": "C14", "H35": "C15", "H36": "C16",
              "H37": "C17", "H38": "C18", "H39": "C19",
              "H41": "C22"}

    verdicts = {}
    for hid in FULL_POOL_HYPOTHESES:
        if hid not in hyps:
            raise SystemExit(f"{hid} is missing from the register")
        verdicts[hid] = verdict_for(models[hid], season, forward, participants)

    doc = {
        "_meta": {
            "kind": "full_pool_hypothesis_verdicts",
            "description": (
                "Mechanical verdicts for H34-H39 and H41, derived from data/stock_competition_results.json "
                "by the pre-registered decision rule below. scripts/verify.py re-runs the same "
                "rule and fails if this file or the hypothesis register disagrees."
            ),
            "engine": "full-pool-verdicts-1",
            "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "competition_generated_utc": comp["_meta"].get("generated_utc"),
            "competition_engine": comp["_meta"].get("engine"),
            "primary_profile": daily.get("profile"),
            "division": "daily",
            "decision_rule": DECISION_RULE,
            "coverage": cov,
            "coverage_complete": cov["complete"],
            "rehearsal_on_incomplete_coverage": not cov["complete"],
            "season_editions": daily.get("season_editions"),
            "eligible_symbols": daily.get("eligible_symbols"),
            "missing_symbols": daily.get("missing_symbols"),
            "forward_window": forward_held_out.get("held_out_window"),
            "forward_editions": forward_held_out.get("held_out_editions"),
            "in_sample_editions": forward_held_out.get("in_sample_editions"),
            "not_a_forecast": True,
            "price_source": comp["_meta"].get("price_source"),
        },
        "verdicts": verdicts,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")

    for hid, v in verdicts.items():
        users = ", ".join(f"{u['username']} {u['season_realized_pnl_usd']:+,.2f}"
                          for u in v["usernames"])
        print(f"{hid} ({v['model']}): {v['status']}  | control "
              f"{v['control']['season_realized_pnl_usd']:+,.2f} | {users}")

    if args.write_hypotheses:
        path = HYPOTHESES_PATH
        register = load(path)
        stamp = doc["_meta"]["generated_utc"]
        for row in register["hypotheses"]:
            hid = row["id"]
            if hid not in verdicts:
                continue
            v = verdicts[hid]
            row["status"] = v["status"]
            names = ", ".join(u["username"] for u in v["usernames"])
            trades = ", ".join(f"{u['username']} {u['total_trades']}" for u in v["usernames"])
            row["evidence"].append(
                f"Full-pool verdict assigned mechanically by scripts/assign_full_pool_verdicts.py "
                f"on {stamp}: coverage {cov['series_captured']}/{cov['series_required']} series "
                f"(daily {cov['daily_captured']}/{cov['pool_symbols']}), "
                f"{doc['_meta']['season_editions']} season editions on "
                f"{len(doc['_meta'].get('eligible_symbols') or [])} eligible symbols. "
                f"Control {CONTROL_USERNAME} (B1) season P/L "
                f"${v['control']['season_realized_pnl_usd']:,.2f} vs {names}. "
                f"Season trades: {trades}. Decision rule and every consumed number are in "
                f"data/full_pool_verdicts.json."
            )
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(register, fh, indent=2)
            fh.write("\n")
        print("hypotheses.json updated for H34-H39 and H41")

    return 0


if __name__ == "__main__":
    sys.exit(main())
