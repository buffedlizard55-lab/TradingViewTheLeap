"""Contrarian strategy library for the volatile-equity division (C6-C22).

The seventeen contrarian models here are pre-registered for the 20-stock volatile pool
(data/volatile_stocks.json). They share the accounting semantics of
intel.contrarian: a decision is evaluated on a bar's close and filled at that
series' NEXT bar open (the Pine broker-emulator default), subject to the rule
profile the runner passes in. No stops, no take-profits, no risk overlays: the
declared brief for this division is maximum simulated return in a paper
competition, and ruin (equity <= 0) is terminal because the official rules forbid
account resets.

Why these shapes:

- Single-stock paper tournaments are won on the tail of the return distribution.
  For a stock that can move 30-300% on news, the exploitable patterns are
  capitulation (forced selling) and blow-off tops (forced buying), both of which
  are visible in price and volume without any fundamental data.
- C6 and C9 are the SHORT side of that idea, C7, C10, C12, C15, C17 and C19 the LONG side,
  C8 fades the opening gap inside the session using hourly bars — the one model that
  cannot exist on daily bars — and C11, C13, C14 and C16 ride breakouts with
  pyramiding, because a paper tournament is scored on realised multiples, not Sharpe.
  C18 shorts vertical blow-offs and pyramids INTO further extension (averaging up):
  the deliberate paper-tournament tail bet that either ruins the edition or harvests
  the violent snapback at multiplied size.
- C19A is a structurally new two-stage absorption model (not a C19 parameter retune).
  It was frozen behind GATED_STOCK_MODEL_IDS until the 60/60 matrix confirmed frozen
  C19 zero-fire (H39 inconclusive, assigned 2026-09-20 at full coverage); it is now
  rostered on the full 20-stock daily pool as hypothesis H42 under the usernames
  TwoStepTessa / LagLiquidationLeo (research/strategy/C19-VARIANT-GATE.md).
- C20 (failed-breakdown spring) and C21 (wide-to-narrow climax reversal) are
  additional unique shapes, rostered under new usernames.
- C22 (volume-drought ignition) is the volume-compression dual of C11's price
  compression: five consecutive sessions each printing at most 0.6x their own
  20-session average volume mark quiet accumulation / seller withdrawal; a session
  that then trades at least 2.5x average volume and closes in the top 40% of its
  range, above its own open, is demand discovery, and the expansion phase is
  harvested long with pyramiding. The drought window is measured on the sessions
  strictly before the ignition bar, and the ignition bar's own volume is compared
  with the same 20-session baseline, so the pattern cannot look at the fill it
  triggers. The ignition thresholds were re-frozen once (3.0x / top-30% -> 2.5x /
  top-40%) on 2026-09-20 BEFORE any full-pool run, because the drafted pair
  produced zero ignition candidates across ~10 years of the six committed pool
  names while the strongest real candidates missed only on the close filter.
- Parameters are frozen in DEFAULT_PARAMS/VARIANTS below, pre-registered before any
  run, and reported in data/stock_competition_results.json so a reviewer can see the
  exact constants behind every number.

Nothing here is fitted on the captured data, and none of these models is claimed to
have an edge: the competition output is what the frozen arithmetic produced on
vendor history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import indicators as ind
from .contrarian import Decision, warmup as contrarian_warmup
from .data import Bar

STOCK_MODEL_IDS = ("C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13",
                   "C14", "C15", "C16", "C17", "C18", "C19", "C19A", "C20", "C21", "C22")
# C19A's gate fired on 2026-09-20: the 60/60 matrix (20/20 daily) confirmed frozen C19
# zero-fire (H39 inconclusive), so C19A was registered as H42 on the full 20-stock daily
# pool. The tuple stays (empty but present) so future gated variants have a home.
# See C19-VARIANT-GATE.md.
GATED_STOCK_MODEL_IDS = ()
CONTROL_MODEL_IDS = ("B1",)

MODEL_NAMES = {
    "C6": "Blow-off spike fade",
    "C7": "Capitulation pyramider (equity)",
    "C8": "Opening gap-trap reversal (hourly)",
    "C9": "Parabolic exhaustion short",
    "C10": "Volume-climax reversal",
    "C11": "Squeeze-breakout pyramider",
    "C12": "Flash-crash dip buyer",
    "C13": "Momentum runner surfer",
    "C14": "Gap-and-go momentum surfer",
    "C15": "Crash snapback sniper",
    "C16": "ATR-expansion breakout compounder",
    "C17": "Overnight implosion harvester",
    "C18": "Blow-off short avalanche",
    "C19": "Twin-hammer capitulation compounder",
    "C19A": "Delayed two-stage absorption (gated)",
    "C20": "Failed-breakdown spring",
    "C21": "Wide-to-narrow climax reversal",
    "C22": "Volume-drought ignition",
    "B1": "Volatility leader, always long (control)",
}

MODEL_KIND = {model: "contrarian" for model in STOCK_MODEL_IDS}
MODEL_KIND["B1"] = "control"

MODEL_CLAIMS = {
    "C6": "A >=3-session parabolic advance that stretches at least 2 ATR, prints on >=2x its 20-bar average volume and closes in the top quartile of its range is a blow-off, not information; it fades over the following ~8 sessions.",
    "C7": "A single-session collapse of >=2 ATR on >=1.5x average volume is forced selling rather than news; buying it and pyramiding on each further 1 ATR of recovery concentrates capital into the rare violent reversals the placement arithmetic requires.",
    "C8": "When the first hourly bar of a session gaps down >=1.5 ATR but closes in the upper half of its own range, the gap is a trap: the session tends to recover toward the prior close over the next few hours.",
    "C9": "A close >=3 population standard deviations above its 20-session basis after a >=15% five-session run is an exhaustion print, not a breakout; it reverts toward the basis within ~10 sessions.",
    "C10": "A session whose range is >=2 ATR with volume >=3x average and a close pinned in the extreme 15% of the range marks a volume climax; the next sessions revert.",
    "C11": "Extreme volatility compression (20-day standard deviation <= 1.2 ATR) followed by a >=2.5x volume expansion breakout signals institutional accumulation; buying the breakout and pyramiding every 1 ATR captures explosive multi-day trending expansions.",
    "C12": "A single-session crash of >=3.0 ATR on >=2.0x volume closing in the bottom decile represents forced margin liquidation; buying the panic close for next-open execution targets the violent mean-reversion snapback.",
    "C13": "A new 30-session high breakout accompanied by >=3x average volume and expanding ATR indicates an explosive momentum runner; entering long with full buying power and aggressive pyramiding targets runaway multiples (5x-20x).",
    "C14": "A session that gaps up >=1.5 ATR over the prior close and still closes in the top half of its own range with the close above the open has absorbed its opening supply; the gap holds and the runner continues over the next ~10 sessions.",
    "C15": "After a >=25% five-session drawdown, a session that closes in the top half of its own range on >=2x average volume marks the forced sellers' exhaustion; the snapback over the next ~4 sessions is harvested with a short hold and no adds.",
    "C16": "A close above the 20-session high while ATR(14) itself expands (>=1.2x its value 5 bars ago) is a volatility-backed breakout rather than a thin-air print; pyramiding every 0.5 ATR compounds the expansion phase.",
    "C17": "A session that gaps down >=2 ATR but still closes in the top half of its own range, above its own open, on >=2x average volume has absorbed its opening panic; the recovery continues over the next ~12 sessions and is compounded with pyramiding.",
    "C18": "A >=20% three-session vertical run on >=2x average volume with the close pinned in the top quartile is a blow-off, not a breakout; shorting it and adding into each further 1 ATR of extension harvests the violent snapback at multiplied size (or ruins the edition — the intended paper-tournament tail bet).",
    "C19": "Two consecutive >=1.5 ATR down closes where the second bar still closes in the top half of its own range mark a two-day liquidation cascade ending in absorption; the snapback over the next ~15 sessions is compounded with pyramiding.",
    "C19A": "A first liquidation bar (>=1.5 ATR close-to-close drop on >=2x volume) plus a second liquidation bar within the next three sessions (>=1.0 ATR down, low not more than 0.25 ATR below the first low, close in the top 40% of its range) is delayed absorption rather than a continuing cascade; long the next open and pyramid on +1 ATR closes (max 3 adds). Structurally distinct from frozen C19 (not a parameter retune).",
    "C20": "A new N-bar low that the next bar immediately reclaims (close back above that low on >=2x volume, close in the top half of its range) is a failed breakdown / spring; the snapback is harvested long with pyramiding.",
    "C21": "A climax bar whose range is >=2.5 ATR followed by a bar whose range is at most half of that climax, closing in the opposite direction, is a wide-to-narrow reversal: long after a down climax, short after an up climax.",
    "C22": "Five consecutive sessions each printing at most 0.6x their own 20-session average volume mark seller withdrawal / quiet accumulation; a session that then trades at least 2.5x that average volume, above its own open, and closes in the top 40% of its range is demand discovery, and the expansion over the next ~12 sessions is harvested long with pyramiding. (Thresholds re-frozen once on 2026-09-20, before any full-pool run: the drafted 3.0x / top-30% combination produced zero ignition candidates across ~10 years of the six committed pool names, missing the strongest real candidates only on the close-position filter; see the seventeenth-pass audit.)",
    "B1": "Control: hold the pool's highest trailing-volatility name at maximum size for the whole edition. If no contrarian model beats this on the same data, the contrarian roster has no edge to report.",
}

# Frozen parameters. Variants may only pin the pre-declared labels below.
DEFAULT_PARAMS: dict[str, dict] = {
    "C6": {
        "run_closes": 3,
        "run_atr_mult": 2.0,
        "volume_length": 20,
        "volume_mult": 2.0,
        "close_tail_fraction": 0.25,
        "hold_bars": 8,
    },
    "C7": {
        "crash_atr_mult": 2.0,
        "volume_length": 20,
        "volume_mult": 1.5,
        "add_atr_step": 1.0,
        "max_adds": 4,
        "hold_bars": 20,
    },
    "C8": {
        "gap_atr_mult": 1.5,
        "reversal_tail_fraction": 0.5,
        "hold_bars": 4,
    },
    "C9": {
        "band_length": 20,
        "band_deviation": 3.0,
        "run_closes": 5,
        "run_pct": 0.15,
        "hold_bars": 10,
    },
    "C10": {
        "range_atr_mult": 2.0,
        "volume_length": 20,
        "volume_mult": 3.0,
        "close_tail_fraction": 0.15,
        "hold_bars": 6,
    },
    "C11": {
        "squeeze_length": 20,
        "volume_length": 20,
        "volume_mult": 2.5,
        "add_atr_step": 1.0,
        "max_adds": 4,
        "hold_bars": 12,
    },
    "C12": {
        "crash_atr_mult": 3.0,
        "volume_length": 20,
        "volume_mult": 2.0,
        "close_tail_fraction": 0.10,
        "hold_bars": 5,
    },
    "C13": {
        "lookback": 30,
        "volume_length": 20,
        "volume_mult": 3.0,
        "add_atr_step": 1.5,
        "max_adds": 4,
        "hold_bars": 14,
    },
    "C14": {
        "gap_atr_mult": 1.5,
        "close_tail_fraction": 0.5,
        "add_atr_step": 1.0,
        "max_adds": 4,
        "hold_bars": 10,
    },
    "C15": {
        "drawdown_lookback": 5,
        "drawdown_pct": 0.25,
        "volume_length": 20,
        "volume_mult": 2.0,
        "close_tail_fraction": 0.5,
        "hold_bars": 4,
    },
    "C16": {
        "lookback": 20,
        "atr_expansion_mult": 1.2,
        "atr_expansion_lag": 5,
        "add_atr_step": 0.5,
        "max_adds": 6,
        "hold_bars": 12,
    },
    "C17": {
        "gap_atr_mult": 2.0,
        "close_tail_fraction": 0.5,
        "volume_length": 20,
        "volume_mult": 2.0,
        "add_atr_step": 0.5,
        "max_adds": 6,
        "hold_bars": 12,
    },
    "C18": {
        "run_closes": 3,
        "run_pct": 0.20,
        "volume_length": 20,
        "volume_mult": 2.0,
        "close_tail_fraction": 0.25,
        "add_atr_step": 1.0,
        "max_adds": 8,
        "hold_bars": 10,
    },
    "C19": {
        "crash_atr_mult": 1.5,
        "close_tail_fraction": 0.5,
        "volume_length": 20,
        "volume_mult": 2.0,
        "add_atr_step": 0.5,
        "max_adds": 8,
        "hold_bars": 15,
    },
    "C19A": {
        "stage1_crash_atr_mult": 1.5,
        "stage1_volume_mult": 2.0,
        "stage2_window": 3,
        "stage2_crash_atr_mult": 1.0,
        "stage2_low_atr_slack": 0.25,
        "stage2_close_tail_fraction": 0.40,
        "volume_length": 20,
        "add_atr_step": 1.0,
        "max_adds": 3,
        "hold_bars": 12,
    },
    "C20": {
        "lookback": 20,
        "volume_length": 20,
        "volume_mult": 2.0,
        "close_tail_fraction": 0.5,
        "add_atr_step": 1.0,
        "max_adds": 4,
        "hold_bars": 10,
    },
    "C21": {
        "climax_atr_mult": 2.5,
        "inside_range_fraction": 0.5,
        "hold_bars": 6,
    },
    "C22": {
        "drought_bars": 5,
        "drought_volume_fraction": 0.6,
        "volume_length": 20,
        "ignition_volume_mult": 2.5,
        "close_tail_fraction": 0.4,
        "add_atr_step": 1.0,
        "max_adds": 3,
        "hold_bars": 12,
    },
    "B1": {},
}

VARIANTS: dict[str, dict[str, dict]] = {
    "C6": {
        "aggressive": {"run_atr_mult": 1.5, "volume_mult": 1.5, "hold_bars": 12},
        "patient": {"run_atr_mult": 3.0, "volume_mult": 3.0, "hold_bars": 15},
    },
    "C7": {
        "rapid": {"add_atr_step": 0.5, "max_adds": 8, "crash_atr_mult": 1.5},
        "patient": {"add_atr_step": 2.0, "max_adds": 3, "crash_atr_mult": 2.5},
    },
    "C8": {
        "tight": {"gap_atr_mult": 1.0, "hold_bars": 3},
        "wide": {"gap_atr_mult": 2.0, "hold_bars": 6},
    },
    "C9": {
        "extreme": {"band_deviation": 3.5, "run_pct": 0.25, "hold_bars": 15},
        "loose": {"band_deviation": 2.5, "run_pct": 0.10, "hold_bars": 6},
    },
    "C10": {
        "volume_heavy": {"volume_mult": 5.0, "close_tail_fraction": 0.10},
        "range_heavy": {"range_atr_mult": 3.0, "close_tail_fraction": 0.20},
    },
    "C11": {
        "rapid": {"add_atr_step": 0.5, "max_adds": 6, "hold_bars": 8},
        "patient": {"add_atr_step": 1.5, "max_adds": 3, "hold_bars": 15},
    },
    "C12": {
        "deep": {"crash_atr_mult": 3.5, "volume_mult": 2.5, "hold_bars": 7},
        "quick": {"crash_atr_mult": 2.5, "volume_mult": 1.8, "hold_bars": 3},
    },
    "C13": {
        "aggressive": {"volume_mult": 2.0, "add_atr_step": 1.0, "max_adds": 6, "hold_bars": 10},
        "runner": {"volume_mult": 3.5, "add_atr_step": 2.0, "max_adds": 3, "hold_bars": 20},
    },
    "C14": {
        "aggressive": {"gap_atr_mult": 1.0, "max_adds": 6, "hold_bars": 14},
        "patient": {"gap_atr_mult": 2.5, "max_adds": 2, "hold_bars": 6},
    },
    "C15": {
        "deep": {"drawdown_pct": 0.35, "hold_bars": 6},
        "quick": {"drawdown_pct": 0.15, "hold_bars": 2},
    },
    "C16": {
        "runner": {"lookback": 30, "atr_expansion_mult": 1.1, "max_adds": 8, "hold_bars": 20},
        "tight": {"lookback": 10, "atr_expansion_mult": 1.5, "max_adds": 3, "hold_bars": 6},
    },
    "C17": {
        "aggressive": {"gap_atr_mult": 1.5, "max_adds": 8, "hold_bars": 15},
        "patient": {"gap_atr_mult": 3.0, "max_adds": 3, "hold_bars": 8},
    },
    "C18": {
        "aggressive": {"run_pct": 0.15, "add_atr_step": 0.75, "max_adds": 10},
        "patient": {"run_pct": 0.30, "add_atr_step": 1.5, "max_adds": 5},
    },
    "C19": {
        "aggressive": {"crash_atr_mult": 1.0, "max_adds": 10},
        "patient": {"crash_atr_mult": 2.0, "max_adds": 4},
    },
    "C19A": {},
    "C20": {
        "aggressive": {"lookback": 10, "volume_mult": 1.5, "max_adds": 6, "hold_bars": 8},
    },
    "C21": {
        "tight": {"climax_atr_mult": 2.0, "inside_range_fraction": 0.4, "hold_bars": 4},
    },
    "C22": {
        "deep": {"drought_bars": 8, "drought_volume_fraction": 0.5,
                 "ignition_volume_mult": 3.0, "close_tail_fraction": 0.35,
                 "max_adds": 5, "hold_bars": 15},
    },
    "B1": {},
}


def resolve_params(model: str, variant: Optional[str] = None) -> dict:
    """Frozen parameters for (model, variant). Raises on unknown names."""
    if model not in DEFAULT_PARAMS:
        raise ValueError(f"unknown stock model {model!r}")
    params = dict(DEFAULT_PARAMS[model])
    if variant:
        if variant not in VARIANTS[model]:
            raise ValueError(f"unknown variant {variant!r} for {model}")
        params.update(VARIANTS[model][variant])
    return params


def warmup(model: str, variant: Optional[str] = None) -> int:
    """First bar index at which the model's indicators are all defined."""
    if model in CONTROL_MODEL_IDS:
        return 60
    if model not in STOCK_MODEL_IDS:
        return contrarian_warmup(model, variant)
    p = resolve_params(model, variant)
    if model in ("C6", "C7", "C10", "C12", "C17", "C18", "C19", "C19A"):
        # ATR(14) needs 14 bars; the volume average needs its window.
        return max(14, p.get("volume_length", 20)) + 2
    if model == "C8":
        # hourly bars: ATR(14) on the hourly series, compared with the previous session's
        # last bar, so 16 hourly bars is the minimum reliable index.
        return 16
    if model == "C9":
        return p["band_length"] + p["run_closes"] + 1
    if model == "C11":
        return max(p.get("squeeze_length", 20), p.get("volume_length", 20)) + 14 + 2
    if model == "C13":
        return max(p.get("lookback", 30), p.get("volume_length", 20)) + 14 + 2
    if model == "C14":
        # ATR(14) plus one prior close for the gap reference.
        return 16
    if model == "C15":
        # ATR(14), the 5-session drawdown window and the volume average.
        return max(14, p.get("volume_length", 20), p.get("drawdown_lookback", 5)) + 2
    if model == "C16":
        # the breakout lookback window plus ATR(14) at the current and lagged bar.
        return max(p.get("lookback", 20), 14 + p.get("atr_expansion_lag", 5))
    if model == "C20":
        # N-bar low lookback, volume average, and ATR(14) on the reclaim bar.
        return max(p.get("lookback", 20), p.get("volume_length", 20), 14) + 2
    if model == "C21":
        # ATR(14) on the climax bar and the following inside bar.
        return 16
    if model == "C22":
        # the volume baseline, ATR(14), and the full drought window behind the ignition bar.
        return max(p.get("volume_length", 20), 14) + p.get("drought_bars", 5) + 2
    raise ValueError(f"unknown stock model {model!r}")


def _volume_average(bars: list[Bar], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(bars)
    window: list[float] = []
    total = 0.0
    for i, bar in enumerate(bars):
        vol = float(bar.volume or 0)
        window.append(vol)
        total += vol
        if len(window) > length:
            total -= window.pop(0)
        if len(window) == length:
            out[i] = total / length
    return out


def _session_open_flags(bars: list[Bar]) -> list[bool]:
    """True at the first bar of each UTC session (used by the hourly gap-trap model)."""
    flags = []
    prior = None
    for bar in bars:
        flags.append(bar.date != prior)
        prior = bar.date
    return flags


def generate_stock_decisions(
    bars: list[Bar],
    model: str,
    variant: Optional[str] = None,
) -> list[Decision]:
    """Ordered decisions for one stock model on one series."""
    if model not in STOCK_MODEL_IDS:
        raise ValueError(f"generate_stock_decisions handles {STOCK_MODEL_IDS}, got {model!r}")
    p = resolve_params(model, variant)
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    atr14 = ind.atr(highs, lows, closes, 14)
    decisions: list[Decision] = []
    start = warmup(model, variant)

    def emit(i: int, action: str, note: str) -> None:
        value = atr14[i]
        decisions.append(Decision(index=i, action=action, atr=value if value else 0.0, reason=note))

    if model == "C6":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None:
                continue
            rng = highs[i] - lows[i]
            if position is not None:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
                continue
            if rng <= 0:
                continue
            k = p["run_closes"]
            if i < k:
                continue
            run = closes[i] - closes[i - k]
            close_pos = (closes[i] - lows[i]) / rng
            blowoff = (
                run >= p["run_atr_mult"] * a
                and float(bars[i].volume or 0) >= p["volume_mult"] * va
                and close_pos >= 1.0 - p["close_tail_fraction"]
            )
            if blowoff:
                emit(i, "short", "blow-off spike fade")
                position = "short"
                held = 0
    elif model == "C7":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        adds = 0
        last_add_price: Optional[float] = None
        entry_atr: Optional[float] = None
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                drop = closes[i - 1] - closes[i]
                crash = (
                    drop >= p["crash_atr_mult"] * a
                    and float(bars[i].volume or 0) >= p["volume_mult"] * va
                )
                if crash:
                    emit(i, "long", "capitulation crash long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C8":
        session_open = _session_open_flags(bars)
        prior_session_close: Optional[float] = None
        position: Optional[str] = None
        held = 0
        for i in range(start, len(bars)):
            a = atr14[i - 1]
            if session_open[i]:
                if a is not None and prior_session_close is not None and a > 0:
                    bar = bars[i]
                    gap = bar.open - prior_session_close
                    rng = bar.high - bar.low
                    if position is None and gap < 0 and rng > 0:
                        close_pos = (bar.close - bar.low) / rng
                        if (
                            -gap >= p["gap_atr_mult"] * a
                            and close_pos >= p["reversal_tail_fraction"]
                            and bar.close > bar.open
                        ):
                            emit(i, "long", "gap-trap reversal")
                            position = "long"
                            held = 0
                prior_session_close = bars[i].close
            else:
                prior_session_close = bars[i].close
            if position is not None and not session_open[i]:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C9":
        basis = ind.sma(closes, p["band_length"])
        dev = ind.stdev(closes, p["band_length"])
        position: Optional[str] = None
        held = 0
        for i in range(start, len(bars)):
            b, d = basis[i], dev[i]
            if b is None or d is None or d <= 0:
                continue
            if position is not None:
                held += 1
                if held >= p["hold_bars"] or closes[i] <= b:
                    emit(i, "exit", "reverted or hold elapsed")
                    position = None
                    held = 0
                continue
            upper = b + p["band_deviation"] * d
            k = p["run_closes"]
            if i < k or closes[i - k] <= 0:
                continue
            run_pct = closes[i] / closes[i - k] - 1.0
            if closes[i] >= upper and run_pct >= p["run_pct"]:
                emit(i, "short", "parabolic exhaustion short")
                position = "short"
                held = 0
    elif model == "C10":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is not None:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
                continue
            rng = highs[i] - lows[i]
            if rng <= 0 or va <= 0:
                continue
            close_pos = (closes[i] - lows[i]) / rng
            volume_climax = (
                rng >= p["range_atr_mult"] * a
                and float(bars[i].volume or 0) >= p["volume_mult"] * va
            )
            if not volume_climax:
                continue
            if close_pos <= p["close_tail_fraction"]:
                emit(i, "long", "down-climax reversal")
                position = "long"
                held = 0
            elif close_pos >= 1.0 - p["close_tail_fraction"]:
                emit(i, "short", "up-climax reversal")
                position = "short"
                held = 0
    elif model == "C11":
        vol_avg = _volume_average(bars, p["volume_length"])
        stdev_series = ind.stdev(closes, p["squeeze_length"])
        position: Optional[str] = None
        held = 0
        adds = 0
        last_add_price: Optional[float] = None
        entry_atr: Optional[float] = None
        sq_len = p["squeeze_length"]
        for i in range(start, len(bars)):
            a, va, sd = atr14[i], vol_avg[i], stdev_series[i]
            if a is None or va is None or sd is None or a <= 0:
                continue
            if position is None:
                prior_sd = stdev_series[i - 1]
                prior_a = atr14[i - 1]
                is_squeeze = (prior_sd is not None and prior_a is not None and prior_sd <= prior_a * 1.2)
                is_breakout = i >= sq_len and closes[i] > max(highs[i - sq_len : i])
                vol_surge = float(bars[i].volume or 0) >= p["volume_mult"] * va
                if is_squeeze and is_breakout and vol_surge:
                    emit(i, "long", "squeeze breakout long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C12":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is not None:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
                continue
            rng = highs[i] - lows[i]
            if rng <= 0 or va <= 0:
                continue
            drop = closes[i - 1] - closes[i]
            close_pos = (closes[i] - lows[i]) / rng
            crash = (
                drop >= p["crash_atr_mult"] * a
                and float(bars[i].volume or 0) >= p["volume_mult"] * va
                and close_pos <= p["close_tail_fraction"]
            )
            if crash:
                emit(i, "long", "flash-crash capitulation buy")
                position = "long"
                held = 0
    elif model == "C13":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        adds = 0
        last_add_price: Optional[float] = None
        entry_atr: Optional[float] = None
        lb = p["lookback"]
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                is_breakout = i >= lb and closes[i] > max(highs[i - lb : i])
                vol_surge = float(bars[i].volume or 0) >= p["volume_mult"] * va
                if is_breakout and vol_surge:
                    emit(i, "long", "momentum runner breakout")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C14":
        position: Optional[str] = None
        held = 0
        adds = 0
        last_add_price: Optional[float] = None
        entry_atr: Optional[float] = None
        for i in range(start, len(bars)):
            a = atr14[i]
            if a is None or a <= 0:
                continue
            if position is None:
                bar = bars[i]
                rng = bar.high - bar.low
                if rng <= 0 or closes[i - 1] <= 0:
                    continue
                gap = bar.open - closes[i - 1]
                close_pos = (bar.close - bar.low) / rng
                held_gap = (
                    gap >= p["gap_atr_mult"] * a
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                    and bar.close > bar.open
                )
                if held_gap:
                    emit(i, "long", "gap-and-go momentum long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C15":
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        look = p["drawdown_lookback"]
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is not None:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
                continue
            bar = bars[i]
            rng = bar.high - bar.low
            if rng <= 0 or va <= 0 or i < look:
                continue
            peak = max(closes[i - look : i + 1])
            trough = closes[i]
            if peak <= 0:
                continue
            drawdown = peak / trough - 1.0 if trough > 0 else 0.0
            close_pos = (bar.close - bar.low) / rng
            snapback = (
                drawdown >= p["drawdown_pct"]
                and close_pos >= 1.0 - p["close_tail_fraction"]
                and float(bar.volume or 0) >= p["volume_mult"] * va
            )
            if snapback:
                emit(i, "long", "crash snapback sniper long")
                position = "long"
                held = 0
    elif model == "C16":
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        lb = p["lookback"]
        lag = p["atr_expansion_lag"]
        for i in range(start, len(bars)):
            a = atr14[i]
            if a is None or a <= 0:
                continue
            if position is None:
                if i < lb or i < lag:
                    continue
                prior_high = max(highs[i - lb : i])
                lagged = atr14[i - lag]
                if lagged is None or lagged <= 0:
                    continue
                breakout = closes[i] > prior_high and a >= p["atr_expansion_mult"] * lagged
                if breakout:
                    emit(i, "long", "ATR-expansion breakout long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C17":
        vol_avg = _volume_average(bars, p["volume_length"])
        position: Optional[str] = None
        held = 0
        adds = 0
        last_add_price: Optional[float] = None
        entry_atr: Optional[float] = None
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                bar = bars[i]
                rng = bar.high - bar.low
                if rng <= 0 or va <= 0 or closes[i - 1] <= 0:
                    continue
                gap = bar.open - closes[i - 1]
                close_pos = (bar.close - bar.low) / rng
                implosion = (
                    -gap >= p["gap_atr_mult"] * a
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                    and bar.close > bar.open
                    and float(bar.volume or 0) >= p["volume_mult"] * va
                )
                if implosion:
                    emit(i, "long", "overnight implosion harvester long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C18":
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        k = p["run_closes"]
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                rng = highs[i] - lows[i]
                if rng <= 0 or va <= 0 or i < k or closes[i - k] <= 0:
                    continue
                run_pct = closes[i] / closes[i - k] - 1.0
                close_pos = (closes[i] - lows[i]) / rng
                blowoff = (
                    run_pct >= p["run_pct"]
                    and float(bars[i].volume or 0) >= p["volume_mult"] * va
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                )
                if blowoff:
                    emit(i, "short", "blow-off avalanche short")
                    position = "short"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                # Adverse pyramid: add INTO further extension (averaging up the short).
                # In a paper tournament this is the tail bet: small size if the top holds,
                # multiplied size into the snapback if the run extends first.
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"avalanche add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C19":
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                bar = bars[i]
                rng = bar.high - bar.low
                if rng <= 0 or va <= 0 or i < 2:
                    continue
                drop1 = closes[i - 2] - closes[i - 1]
                drop2 = closes[i - 1] - closes[i]
                close_pos = (bar.close - bar.low) / rng
                twin_hammer = (
                    drop1 >= p["crash_atr_mult"] * a
                    and drop2 >= p["crash_atr_mult"] * a
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                    and float(bar.volume or 0) >= p["volume_mult"] * va
                )
                if twin_hammer:
                    emit(i, "long", "twin-hammer capitulation long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C19A":
        # Delayed two-stage absorption: Stage 1 is a single liquidation print;
        # Stage 2 is a second liquidation within `stage2_window` sessions whose low
        # holds near Stage 1 and whose close is absorbed in the top 40%. Distinct
        # from C19 (adjacent-bar 1.5 ATR cascade, top-half close, 0.5 ATR adds).
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        stage1: Optional[tuple[int, float]] = None
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                if stage1 is not None and i - stage1[0] > p["stage2_window"]:
                    stage1 = None
                bar = bars[i]
                rng = bar.high - bar.low
                drop = closes[i - 1] - closes[i]
                close_pos = (bar.close - bar.low) / rng if rng > 0 else 0.0
                if (stage1 is not None
                        and 1 <= (i - stage1[0]) <= p["stage2_window"]
                        and rng > 0):
                    s_low = stage1[1]
                    stage2 = (
                        drop >= p["stage2_crash_atr_mult"] * a
                        and lows[i] >= s_low - p["stage2_low_atr_slack"] * a
                        and close_pos >= 1.0 - p["stage2_close_tail_fraction"]
                    )
                    if stage2:
                        emit(i, "long", "delayed two-stage absorption long")
                        position = "long"
                        held = 0
                        adds = 0
                        last_add_price = closes[i]
                        entry_atr = a
                        stage1 = None
                        continue
                stage1_hit = (
                    drop >= p["stage1_crash_atr_mult"] * a
                    and float(bar.volume or 0) >= p["stage1_volume_mult"] * va
                )
                if stage1_hit:
                    stage1 = (i, lows[i])
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C20":
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        lb = p["lookback"]
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0:
                continue
            if position is None:
                if i < lb + 1:
                    continue
                bar = bars[i]
                rng = bar.high - bar.low
                if rng <= 0 or va <= 0:
                    continue
                prior_min = min(lows[i - lb - 1:i - 1])
                breakdown_low = lows[i - 1]
                is_new_low = breakdown_low <= prior_min
                close_pos = (bar.close - bar.low) / rng
                spring = (
                    is_new_low
                    and closes[i] > breakdown_low
                    and float(bar.volume or 0) >= p["volume_mult"] * va
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                )
                if spring:
                    emit(i, "long", "failed-breakdown spring long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
    elif model == "C21":
        position = None
        held = 0
        for i in range(start, len(bars)):
            a = atr14[i]
            prior_a = atr14[i - 1]
            if a is None or prior_a is None or a <= 0 or prior_a <= 0:
                continue
            if position is not None:
                held += 1
                if held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0
                continue
            prev_rng = highs[i - 1] - lows[i - 1]
            rng = highs[i] - lows[i]
            if prev_rng <= 0 or rng <= 0:
                continue
            climax = prev_rng >= p["climax_atr_mult"] * prior_a
            inside = rng <= p["inside_range_fraction"] * prev_rng
            if not (climax and inside):
                continue
            close_pos = (closes[i] - lows[i]) / rng
            prior_open = bars[i - 1].open
            if closes[i - 1] < prior_open and close_pos >= 0.5:
                emit(i, "long", "wide-to-narrow down-climax reversal")
                position = "long"
                held = 0
            elif closes[i - 1] > prior_open and close_pos <= 0.5:
                emit(i, "short", "wide-to-narrow up-climax reversal")
                position = "short"
                held = 0
    elif model == "C22":
        vol_avg = _volume_average(bars, p["volume_length"])
        position = None
        held = 0
        adds = 0
        last_add_price = None
        entry_atr = None
        db = p["drought_bars"]
        for i in range(start, len(bars)):
            a, va = atr14[i], vol_avg[i]
            if a is None or va is None or a <= 0 or va <= 0:
                continue
            if position is None:
                if i < db:
                    continue
                # Drought: every one of the db sessions strictly before the candidate
                # ignition bar printed at most the drought fraction of its own trailing
                # volume baseline (which includes that session itself, exactly as the
                # ignition comparison below includes the ignition bar itself).
                drought = True
                for k in range(1, db + 1):
                    base = vol_avg[i - k]
                    if base is None or base <= 0:
                        drought = False
                        break
                    if float(bars[i - k].volume or 0) > p["drought_volume_fraction"] * base:
                        drought = False
                        break
                if not drought:
                    continue
                bar = bars[i]
                rng = bar.high - bar.low
                if rng <= 0:
                    continue
                close_pos = (bar.close - bar.low) / rng
                ignition = (
                    float(bar.volume or 0) >= p["ignition_volume_mult"] * va
                    and close_pos >= 1.0 - p["close_tail_fraction"]
                    and bar.close > bar.open
                )
                if ignition:
                    emit(i, "long", "volume-drought ignition long")
                    position = "long"
                    held = 0
                    adds = 0
                    last_add_price = closes[i]
                    entry_atr = a
            else:
                held += 1
                step = p["add_atr_step"] * (entry_atr or a)
                if closes[i] - (last_add_price or closes[i]) >= step and adds < p["max_adds"]:
                    emit(i, "add", f"pyramid add {adds + 1}")
                    adds += 1
                    last_add_price = closes[i]
                elif held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    position = None
                    held = 0

    return decisions


def trailing_volatility(bars: list[Bar], end_index: int, length: int = 60) -> Optional[float]:
    """Population standard deviation of the last `length` daily returns ending at end_index.

    Used by the B1 control to pick the pool's highest-volatility name at an edition's
    start, using only bars strictly before the edition window.
    """
    if end_index < length:
        return None
    closes = [bars[i].close for i in range(end_index - length, end_index + 1)]
    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    return variance ** 0.5
