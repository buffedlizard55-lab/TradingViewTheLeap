#!/usr/bin/env python3
"""Publish what a capture run actually did, from inside the run.

Why this exists: GitHub-hosted run logs and uploaded artifacts are served from a blob host
that the research sandbox cannot reach, so a green-but-empty capture run was indistinguishable
from a working one. This script posts the run's own evidence as a *commit comment* (readable
through the REST API from anywhere) and also writes a small report file the run tries to
commit. It never invents a value: every number is read from the capture index the fetch script
wrote, or from the tee'd stdout of the fetch steps, or is reported as absent.

Environment: GITHUB_SHA, GITHUB_REPOSITORY, GITHUB_RUN_ID, GH_TOKEN (all provided by Actions).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDEX = os.path.join(ROOT, "data", "intraday_index.json")
LOG = "/tmp/capture_log.txt"
REPORT = os.path.join(ROOT, "data", "intraday_capture_report.json")
MAX_LOG_LINES = 120


def log_tail() -> list[str]:
    if not os.path.exists(LOG):
        return ["(no capture log file: the fetch steps did not run or did not tee their output)"]
    with open(LOG, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    return lines[-MAX_LOG_LINES:]


def index_summary() -> dict:
    if not os.path.exists(INDEX):
        return {"present": False}
    with open(INDEX, encoding="utf-8") as fh:
        doc = json.load(fh)
    captures = doc.get("captures", [])
    captured = [c for c in captures if c.get("status") == "captured"]
    return {
        "present": True,
        "meta": {k: v for k, v in doc.get("_meta", {}).items()
                 if k in ("script_version", "fetched_at_utc", "captured_count", "failed_count",
                          "not_attempted_count", "captured_by_interval", "direct_rate_limited",
                          "direct_429_count", "fetch_environment")},
        "captured": [{"symbol": c["symbol"], "interval": c["interval"],
                      "bar_count": c.get("bar_count"), "file": c.get("file"),
                      "first_utc": c.get("first_utc"), "last_utc": c.get("last_utc")}
                     for c in captured],
        "not_captured": [{"symbol": c["symbol"], "interval": c["interval"],
                          "status": c.get("status"), "error": str(c.get("error"))[:300]}
                         for c in captures if c.get("status") != "captured"],
    }


def build_body(summary: dict, tail: list[str]) -> str:
    lines = [
        f"### Capture run diagnostics (`{os.environ.get('GITHUB_RUN_ID', '?')}`)",
        "",
        f"- run: {os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', '?')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '?')}",
        f"- commit: `{(os.environ.get('GITHUB_SHA') or '?')[:12]}`",
        f"- index written: **{summary['present']}**",
    ]
    if summary["present"]:
        meta = summary["meta"]
        lines += [
            f"- captured / failed / not attempted: **{meta.get('captured_count')} / "
            f"{meta.get('failed_count')} / {meta.get('not_attempted_count')}**",
            f"- by interval: `{meta.get('captured_by_interval')}`",
            f"- direct rate limited: `{meta.get('direct_rate_limited')}` "
            f"(429 count `{meta.get('direct_429_count')}`)",
            f"- fetched_at_utc: `{meta.get('fetched_at_utc')}` "
            f"(script_version {meta.get('script_version')})",
        ]
        if summary["captured"]:
            lines += ["", "| symbol | interval | bars | first | last |", "|---|---|---|---|---|"]
            lines += [f"| {c['symbol']} | {c['interval']} | {c['bar_count']} | "
                      f"{(c['first_utc'] or '')[:16]} | {(c['last_utc'] or '')[:16]} |"
                      for c in summary["captured"][:40]]
        if summary["not_captured"]:
            lines += ["", "<details><summary>Series not captured (first 20)</summary>", ""]
            lines += [f"- `{c['symbol']}[{c['interval']}]` {c['status']}: {c['error']}"
                      for c in summary["not_captured"][:20]]
            lines += ["", "</details>"]
    else:
        lines += ["", "The fetch script did not leave an index, so it either did not run or "
                      "exited before writing one."]
    lines += ["", "<details><summary>Capture log tail</summary>", "", "```text"]
    lines += [line[:240] for line in tail]
    lines += ["```", "", "</details>"]
    return "\n".join(lines)[:60000]


def post_comment(body: str) -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not (token and repo and sha):
        return "skipped: GH_TOKEN/GITHUB_REPOSITORY/GITHUB_SHA not all set"
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/comments"
    request = urllib.request.Request(
        url, data=json.dumps({"body": body}).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "capture-diagnostics"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return f"posted as comment {payload.get('id')}"
    except urllib.error.HTTPError as exc:
        return f"failed: HTTP {exc.code} {exc.read().decode('utf-8', 'replace')[:200]}"
    except Exception as exc:                                   # pragma: no cover - transport
        return f"failed: {exc}"


def main() -> int:
    summary = index_summary()
    tail = log_tail()
    body = build_body(summary, tail)
    print(body)
    result = post_comment(body)
    print(f"commit comment: {result}")
    report = {
        "_meta": {
            "kind": "intraday_capture_run_report",
            "description": ("What one capture run did, written by the run itself because its logs and "
                            "artifacts are not readable from the research sandbox. Written on every "
                            "run, including runs that stored nothing."),
            "run_url": (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                        f"{os.environ.get('GITHUB_REPOSITORY', '?')}/actions/runs/"
                        f"{os.environ.get('GITHUB_RUN_ID', '?')}"),
            "head_sha": os.environ.get("GITHUB_SHA", "unknown"),
            "generated_utc": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).replace(microsecond=0).isoformat(),
            "not_a_forecast": "Operational record of one capture attempt; contains no market view.",
        },
        "index": summary,
        "log_tail": tail,
        "commit_comment": result,
    }
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(f"wrote {os.path.relpath(REPORT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
