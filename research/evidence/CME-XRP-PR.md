# Evidence: CME-XRP-PR

- **Publisher:** CME Group Inc.
- **URL:** https://www.cmegroup.com/media-room/press-releases/2025/4/24/cme_group_to_expandcryptoderivativessuitewithlaunchofxrpfutures.html
- **Title as served:** "CME Group to Expand Crypto Derivatives Suite with Launch of XRP Futures"
- **Accessed (UTC):** 2026-09-16
- **Tier:** official_primary (listing exchange press release)

## Q1 — Contract sizes and launch date

> CHICAGO, April 24, 2025 /PRNewswire/ -- CME Group, the world's leading derivatives
> marketplace, today announced plans to launch XRP futures on May 19, pending regulatory review.
> Market participants will have the choice to trade both a micro-sized contract (2,500 XRP) and
> a larger-sized contract (50,000 XRP)

## Q2 — Settlement

> CME Group XRP futures will be cash-settled and based on the CME CF XRP-Dollar Reference Rate,
> which serves as a once-a-day reference rate of the U.S. dollar price of XRP and is calculated
> daily at 4:00 p.m. London time.

## Q3 — Product context

> XRP futures will join the company's crypto product suite that includes Bitcoin and Ether
> futures and options, as well as recently launched SOL futures.

## Mapping to the contest universe

TradingView symbols `CME:XRP1!` (larger size) and `CME:MXP1!` (micro size) both appear in the
live contest's permitted instrument list (`data/contest_universe.json`). The 50,000 XRP and
2,500 XRP sizes are therefore attributed to XRP1! and MXP1! respectively.

## Caveat recorded at capture time

The press release states the launch was "pending regulatory review" as of 24 Apr 2025. This
evidence file does **not** independently confirm that trading actually commenced on 19 May 2025.
That gap is tracked as IR-06 in `research/irregularities.json` and the corresponding
`master_list.json` rows carry `verification_status: "identity_verified"` rather than
`"fully_verified"`.
