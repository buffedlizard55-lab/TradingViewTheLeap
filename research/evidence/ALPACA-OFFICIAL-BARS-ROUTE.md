# Alpaca IEX official-provider route — status and evidence

**Status at 2026-09-20: blocked on credentials. No Alpaca bar is committed, and none is
fabricated.**

## What the route is

`scripts/fetch_official_bars.py`, driven by `.github/workflows/official-bars.yml`, calls the
Alpaca US equity bars API (IEX feed, split-adjusted) documented at
<https://docs.alpaca.markets/us/reference/stockbars>. It is the repository's
official-provider alternative to the vendor-tier Yahoo captures under `data/intraday/`:

- runs daily on cron (`41 3 * * *`) and on manual dispatch;
- reads repository secrets `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` (values are never printed);
- **fails closed**: with no credentials it writes `data/official_bars/availability.json` with
  `status: "blocked"` and exits non-zero without issuing a single network request (the current
  committed artifact says exactly this, stamp 2026-09-18T22:31:46Z);
- with credentials it stores raw provider bodies under `data/official_bars/raw/` (git-ignored
  pending license review) and commits only canonical per-series files plus an index;
- `make spot-check` then compares official closes against the vendor closes, split-step aware.

## Why it is blocked

1. This repository currently has **no Alpaca credentials**. A free Alpaca Basic account provides
   the IEX feed these scripts use; creating an account and generating an API key pair is a
   human account-owner action (https://alpaca.markets — sign in, API keys page).
2. The automation agent running this research has **no permission to manage repository
   secrets** (`gh secret list` returns HTTP 403 "Resource not accessible by integration"), so it
   cannot provision the secrets itself and will not fabricate values.

## How a human unblocks it (two minutes)

1. Create/sign in to a free Alpaca account and generate an API key pair (Basic tier is enough
   for IEX bars).
2. GitHub → this repository → **Settings → Secrets and variables → Actions → New repository
   secret**: add `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`.
3. Wait for the next daily cron run of `official-bars.yml` (or dispatch it manually). The lane
   captures the 20-stock pool, writes `data/official_bars/index.json`, re-runs the intraday
   study and the stock division on official bars, spot-checks official vs vendor closes, and
   commits the audited result.

Until then, every stock price in this repository stays explicitly vendor-tier (Yahoo Finance),
and no artifact describes it as exchange-verified.

## Observed in this pass

- 2026-09-20: `gh secret list` → HTTP 403 for the research agent's token (cannot read or set
  secrets).
- 2026-09-18T22:31:46Z: `data/official_bars/availability.json` written with
  `status: "blocked"`, `reason: "Alpaca Basic API credentials unavailable; no network request
  or fabricated bars"` — unchanged at this commit.
