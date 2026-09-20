# Alpaca IEX official-provider route — status and evidence

- **Publisher:** Alpaca (brokerage and market-data API provider; authoritative for its own API — not an exchange, regulator, or the contest organiser)
- **URL:** https://docs.alpaca.markets/us/reference/stockbars
- **Accessed (UTC):** 2026-09-20 (documentation reference only; no bar request was possible — see below)
- **Tier:** official_secondary (provider documentation for the credential-gated official-provider bar route)
- **Use:** documents the official-provider alternative to vendor-tier Yahoo bars that
  `.github/workflows/official-bars.yml` → `scripts/fetch_official_bars.py` implements, and
  records why it stays `blocked` in this session.

## What is committed

`data/official_bars/availability.json` (generated 2026-09-18T22:31:46Z by
`scripts/fetch_official_bars.py`, unchanged at this commit):

> "status": "blocked",
> "reason": "Alpaca Basic API credentials unavailable; no network request or fabricated bars"
> "limitation": "IEX-only, split-adjusted research prices; not consolidated executable quotes"

The lane itself (`.github/workflows/official-bars.yml`) fails closed when the repository
secrets are absent:

> ::warning::APCA_API_KEY_ID / APCA_API_SECRET_KEY not configured - official bars stay
> 'blocked' (no fabrication)

## Why it is blocked in this session

1. This repository currently holds **no Alpaca credentials**. A free Alpaca account provides
   the IEX feed these scripts use; generating an API key pair is a human account-owner action.
2. The automation agent's token was **refused secret management outright** on 2026-09-20
   (`gh secret list` → HTTP 403 "Resource not accessible by integration"), so the agent can
   neither read nor set the two secrets, and the brief's no-fabrication rule forbids
   inventing values. Logged as IR-32.

## How a human unblocks it (two minutes)

1. Create/sign in to a free Alpaca account (https://alpaca.markets) and generate an API key
   pair (Basic tier is enough for IEX bars).
2. GitHub → repository → **Settings → Secrets and variables → Actions → New repository
   secret**: add `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`.
3. Wait for the daily cron (`41 3 * * *`) or dispatch `official-bars.yml` manually. The lane
   then captures the 20-stock pool, writes `data/official_bars/index.json`, re-runs the
   intraday study and the stock division on official bars, spot-checks official vs vendor
   closes (`scripts/spot_check_official_vs_vendor.py`), and commits the audited result.

Until then, every stock price in this repository stays explicitly vendor-tier (Yahoo Finance),
and no artifact describes it as exchange-verified.
