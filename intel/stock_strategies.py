"""Contrarian strategy library for the volatile-equity division (C6-C10).

The five contrarian models here are pre-registered for the 20-stock volatile pool
(data/volatile_stocks.json). They share the accounting semantics of
intel.contrarian: a decision is evaluated on a bar's close and filled at that
series' NEXT bar open (the Pine broker-emulator default), subject to the rule
profile the runner passes in. No stops, no take-profits, no risk overlays: the
declared brief for this division is maximum simulated return in a paper
competition, and ruin (equity <= 0) is terminal because the official rules forbid
account resets.

Why these five shapes:

- Single-stock paper tournaments are won on the tail of the return distribution.
  For a stock that can move 30-300% on news, the exploitable patterns are
  capitulation (forced selling) and blow-off tops (forced buying), both of which
  are visible in price and volume without any fundamental data.
- C6 and C9 are the SHORT side of that idea, C7 and C10 the LONG side, and C8 fades
  the opening gap inside the session using hourly bars — the one model that cannot
  exist on daily bars.
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

STOCK_MODEL_IDS = ("C6", "C7", "C8", "C9", "C10")
CONTROL_MODEL_IDS = ("B1",)

MODEL_NAMES = {
    "C6": "Blow-off spike fade",
    "C7": "Capitulation pyramider (equity)",
    "C8": "Opening gap-trap reversal (hourly)",
    "C9": "Parabolic exhaustion short",
    "C10": "Volume-climax reversal",
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
    if model in ("C6", "C7", "C10"):
        # ATR(14) needs 14 bars; the volume average needs its window.
        return max(14, p.get("volume_length", 20)) + 2
    if model == "C8":
        # hourly bars: ATR(14) on the hourly series, compared with the previous session's
        # last bar, so 16 hourly bars is the minimum reliable index.
        return 16
    if model == "C9":
        return p["band_length"] + p["run_closes"] + 1
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
