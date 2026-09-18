"""Pre-registered contrarian strategy library for the shadow competition.

Five unique contrarian decision models (C1-C5) plus re-use of the three trend
baselines (S1-S3) from intel.strategy so a competition roster can compare
contrarian and trend participants on identical data and rules.

Design principles, frozen before any competition run:

- Every model is CONTRARIAN: it positions AGAINST the most recent visible
  impulse (panic collapse, opening gap, band pierce, exhaustion bar). C5 keeps
  the contrarian entry but then pyramids with full reinvestment, which the
  project's placement arithmetic (data/leaderboard_lab.json) shows is the only
  way a daily-bar process can even theoretically reach 5x-100x.
- Daily-bar decisions only. Signals are evaluated on a bar's close and fill at
  the NEXT bar's open of the same series (Pine broker-emulator default), the
  same order semantics used by intel.backtest.
- No stops, no take-profits, no position limits besides the official rules
  (whole contracts, per-symbol cap, 20:1 buying power). This is deliberate:
  the brief for this experiment is maximum simulated return in a paper
  competition, not risk management. Ruin (equity <= 0) is terminal because the
  official rules forbid account resets.
- Every parameter below is frozen here and copied into
  data/competition/roster.json. Nothing is fitted on the data.

Hold policies use bars of the same series; an edition's auto-close (the
analog of the official end-of-competition auto-close) always applies last.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import indicators as ind
from .data import Bar
from .strategy import generate_signals as trend_signals
from .strategy import warmup_bars as trend_warmup

CONTRARIAN_MODEL_IDS = ("C1", "C2", "C3", "C4", "C5")
BASELINE_MODEL_IDS = ("S1", "S2", "S3")
ALL_MODEL_IDS = CONTRARIAN_MODEL_IDS + BASELINE_MODEL_IDS

MODEL_NAMES = {
    "C1": "Capitulation reversal",
    "C2": "Gap fade",
    "C3": "Band-pierce reversion",
    "C4": "Exhaustion-bar reversal",
    "C5": "Capitulation pyramider",
    "S1": "Donchian breakout (baseline)",
    "S2": "EMA impulse (baseline)",
    "S3": "Squeeze release (baseline)",
}

MODEL_KIND = {
    "C1": "contrarian",
    "C2": "contrarian",
    "C3": "contrarian",
    "C4": "contrarian",
    "C5": "contrarian",
    "S1": "baseline",
    "S2": "baseline",
    "S3": "baseline",
}

MODEL_CLAIMS = {
    "C1": "A multi-day collapse (or euphoria run) that stretches price by >=1 ATR over 3 closes with ATR expanding is over-extended and mean-reverts over the next ~10 sessions.",
    "C2": "An opening gap larger than 1.5 ATR(14) is over-reaction, not information: fading the gap direction captures the close-the-gap drift over ~5 sessions.",
    "C3": "A close outside the 2-sigma band that re-enters the 1-sigma zone the next session marks the impulse as exhausted; price reverts toward the basis.",
    "C4": "A range-expansion exhaustion bar (true range >= 2x ATR with the close pinned in the extreme quartile of the bar) marks liquidation climax; the next sessions revert.",
    "C5": "Contrarian capitulation entries followed by full-reinvestment pyramiding every 1 ATR of favourable drift concentrate capital into the rare explosive reversals the placement arithmetic requires.",
    "S1": "Baseline trend-following Donchian breakout (for contrast against the contrarian roster).",
    "S2": "Baseline EMA-crossover impulse continuation (for contrast against the contrarian roster).",
    "S3": "Baseline Bollinger squeeze release (for contrast against the contrarian roster).",
}

# Frozen parameters. Roster entries may only pin the pre-declared variant label;
# the variant overrides live here so code and roster can never disagree.
DEFAULT_PARAMS: dict[str, dict] = {
    "C1": {
        "lookback_closes": 3,        # consecutive-direction run length proxy
        "extension_atr_mult": 1.0,   # collapse size >= this x ATR(14)
        "atr_baseline_length": 50,
        "atr_expansion_factor": 1.05,
        "hold_bars": 10,
    },
    "C2": {
        "gap_atr_mult": 1.5,
        "hold_bars": 5,
    },
    "C3": {
        "band_length": 20,
        "band_deviation": 2.0,
        "reentry_deviation": 1.0,
        "hold_bars": 5,
    },
    "C4": {
        "tr_atr_mult": 2.0,
        "close_tail_fraction": 0.25,
        "hold_bars": 5,
    },
    "C5": {
        "lookback_closes": 3,
        "extension_atr_mult": 1.0,
        "atr_baseline_length": 50,
        "atr_expansion_factor": 1.05,
        "add_atr_step": 1.0,
        "max_adds": 4,
    },
    "S1": {},
    "S2": {},
    "S3": {},
}

# Pre-declared variant overrides (label -> params delta). Frozen before any run.
VARIANTS: dict[str, dict[str, dict]] = {
    "C1": {
        "fast3": {"lookback_closes": 2, "hold_bars": 6},
        "deep": {"extension_atr_mult": 1.5, "hold_bars": 15},
    },
    "C2": {
        "wide": {"gap_atr_mult": 2.5},
        "tight": {"gap_atr_mult": 1.0},
    },
    "C3": {
        "wideband": {"band_deviation": 2.5},
        "quick": {"hold_bars": 3, "reentry_deviation": 1.5},
    },
    "C4": {
        "extreme": {"tr_atr_mult": 2.5, "close_tail_fraction": 0.15},
        "loose": {"tr_atr_mult": 1.5, "close_tail_fraction": 0.35},
    },
    "C5": {
        "rapid": {"add_atr_step": 0.75, "max_adds": 6},
        "patient": {"add_atr_step": 1.5, "max_adds": 3},
    },
    "S1": {},
    "S2": {},
    "S3": {},
}

HOLD_BARS = {"C2": 5, "C3": 5, "C4": 5, "C1": 10}


@dataclass(frozen=True)
class Decision:
    """An order decision evaluated on bar `index` (fills next bar's open).

    action: "long" | "short" | "exit" | "add"
    """

    index: int
    action: str
    atr: float
    reason: str = ""


@dataclass
class _State:
    position: Optional[str] = None      # "long" | "short"
    bars_held: int = 0
    adds: int = 0
    last_tranche_price: Optional[float] = None
    entry_atr: Optional[float] = None
    armed: Optional[str] = None         # C3: direction armed by the pierce bar
    pending: list = field(default_factory=list)


def resolve_params(model: str, variant: Optional[str]) -> dict:
    """Frozen parameters for (model, variant). Raises on unknown names."""
    if model not in DEFAULT_PARAMS:
        raise ValueError(f"unknown model {model!r}")
    params = dict(DEFAULT_PARAMS[model])
    if variant:
        if variant not in VARIANTS[model]:
            raise ValueError(f"unknown variant {variant!r} for {model}")
        params.update(VARIANTS[model][variant])
    if model in HOLD_BARS and "hold_bars" not in params:
        params["hold_bars"] = HOLD_BARS[model]
    return params


def warmup(model: str, variant: Optional[str] = None) -> int:
    """First bar index at which the model's indicators are all defined."""
    if model in BASELINE_MODEL_IDS:
        return trend_warmup(model)
    p = resolve_params(model, variant)
    if model in ("C1", "C5"):
        # ATR(14) RMA warmup (14 bars) + SMA baseline over atr_baseline_length,
        # plus one more close for the k-bar lookback.
        atr_ready = (14 - 1) + (p["atr_baseline_length"] - 1)
        return max(atr_ready + 1, p["lookback_closes"] + 1)
    if model == "C2":
        return 14 + 1  # ATR(14) shifted one bar
    if model == "C3":
        return p["band_length"]  # SMA+stdev window, plus the pierce bar
    if model == "C4":
        return 14 + 1  # ATR(14) shifted one bar
    raise ValueError(f"unknown model {model!r}")


def _atr_base(series_atr: list[Optional[float]], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(series_atr)
    running: list[float] = []
    total = 0.0
    for i, v in enumerate(series_atr):
        if v is None:
            running.clear()
            total = 0.0
            continue
        running.append(v)
        total += v
        if len(running) > length:
            total -= running.pop(0)
        if len(running) == length:
            out[i] = total / length
    return out


def _decide_contrarian(
    model: str,
    bars: list[Bar],
    variant: Optional[str],
) -> list[Decision]:
    p = resolve_params(model, variant)
    closes = [b.close for b in bars]
    opens = [b.open for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    atr14 = ind.atr(highs, lows, closes, 14)
    decisions: list[Decision] = []
    st = _State()

    def emit(i: int, action: str, note: str) -> None:
        a = atr14[i]
        decisions.append(Decision(index=i, action=action, atr=a if a is not None else 0.0, reason=note))

    if model in ("C1", "C5"):
        atr_base = _atr_base(atr14, p["atr_baseline_length"])
        for i in range(warmup(model, variant), len(bars)):
            a, ab = atr14[i], atr_base[i]
            if a is None or ab is None:
                continue
            expanding = a > ab * p["atr_expansion_factor"]
            k = p["lookback_closes"]
            if i < k:
                continue
            drop = closes[i - k] - closes[i]
            rise = closes[i] - closes[i - k]
            panic_long = drop >= p["extension_atr_mult"] * a and expanding
            panic_short = rise >= p["extension_atr_mult"] * a and expanding
            if model == "C1":
                if st.position is None:
                    if panic_long:
                        emit(i, "long", "capitulation long")
                        st.position = "long"
                        st.bars_held = 0
                    elif panic_short:
                        emit(i, "short", "euphoria short")
                        st.position = "short"
                        st.bars_held = 0
                else:
                    st.bars_held += 1
                    opposite = (st.position == "long" and panic_short) or (
                        st.position == "short" and panic_long
                    )
                    if opposite:
                        emit(i, "exit", "opposite capitulation")
                        emit(i, "short" if st.position == "long" else "long", "reverse")
                        st.position = "short" if st.position == "long" else "long"
                        st.bars_held = 0
                    elif st.bars_held >= p["hold_bars"]:
                        emit(i, "exit", "hold elapsed")
                        st.position = None
                        st.bars_held = 0
            else:  # C5
                if st.position is None:
                    if panic_long:
                        emit(i, "long", "capitulation long")
                        st.position = "long"
                        st.adds = 0
                        st.last_tranche_price = closes[i]
                        st.entry_atr = a
                    elif panic_short:
                        emit(i, "short", "euphoria short")
                        st.position = "short"
                        st.adds = 0
                        st.last_tranche_price = closes[i]
                        st.entry_atr = a
                else:
                    step = p["add_atr_step"] * (st.entry_atr or a)
                    moved = (
                        closes[i] - st.last_tranche_price
                        if st.position == "long"
                        else st.last_tranche_price - closes[i]
                    )
                    opposite = (st.position == "long" and panic_short) or (
                        st.position == "short" and panic_long
                    )
                    if opposite:
                        emit(i, "exit", "opposite capitulation")
                        emit(i, "short" if st.position == "long" else "long", "reverse")
                        st.position = "short" if st.position == "long" else "long"
                        st.adds = 0
                        st.last_tranche_price = closes[i]
                        st.entry_atr = a
                    elif moved >= step and st.adds < p["max_adds"]:
                        emit(i, "add", f"pyramid add {st.adds + 1}")
                        st.adds += 1
                        st.last_tranche_price = closes[i]

    elif model == "C2":
        for i in range(warmup(model, variant), len(bars)):
            a = atr14[i - 1]
            if a is None:
                continue
            gap = opens[i] - closes[i - 1]
            if st.position is not None:
                st.bars_held += 1
                if st.bars_held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    st.position = None
                    st.bars_held = 0
                continue
            if gap >= p["gap_atr_mult"] * a:
                emit(i, "short", "fade up-gap")
                st.position = "short"
                st.bars_held = 0
            elif -gap >= p["gap_atr_mult"] * a:
                emit(i, "long", "fade down-gap")
                st.position = "long"
                st.bars_held = 0

    elif model == "C3":
        basis = ind.sma(closes, p["band_length"])
        dev = ind.stdev(closes, p["band_length"])
        upper2 = [(b + p["band_deviation"] * d) if b is not None and d is not None else None
                  for b, d in zip(basis, dev)]
        lower2 = [(b - p["band_deviation"] * d) if b is not None and d is not None else None
                  for b, d in zip(basis, dev)]
        for i in range(warmup(model, variant), len(bars)):
            u2, l2, bs, dv = upper2[i], lower2[i], basis[i], dev[i]
            if None in (u2, l2, bs, dv):
                continue
            if st.position is not None:
                st.bars_held += 1
                if st.bars_held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    st.position = None
                    st.bars_held = 0
                continue
            if st.armed == "long":
                if closes[i] >= bs - p["reentry_deviation"] * dv:
                    emit(i, "long", "pierce re-entered band")
                    st.position = "long"
                    st.bars_held = 0
                st.armed = None
            elif st.armed == "short":
                if closes[i] <= bs + p["reentry_deviation"] * dv:
                    emit(i, "short", "pierce re-entered band")
                    st.position = "short"
                    st.bars_held = 0
                st.armed = None
            else:
                if closes[i] < l2:
                    st.armed = "long"
                elif closes[i] > u2:
                    st.armed = "short"

    elif model == "C4":
        for i in range(warmup(model, variant), len(bars)):
            a = atr14[i - 1]
            if a is None or a <= 0:
                continue
            rng = highs[i] - lows[i]
            if rng <= 0:
                continue
            if st.position is not None:
                st.bars_held += 1
                if st.bars_held >= p["hold_bars"]:
                    emit(i, "exit", "hold elapsed")
                    st.position = None
                    st.bars_held = 0
                continue
            close_pos = (closes[i] - lows[i]) / rng  # 0 = close at the low
            exhaustion_down = rng >= p["tr_atr_mult"] * a and close_pos <= p["close_tail_fraction"]
            exhaustion_up = rng >= p["tr_atr_mult"] * a and close_pos >= 1.0 - p["close_tail_fraction"]
            if exhaustion_down:
                emit(i, "long", "exhaustion down bar")
                st.position = "long"
                st.bars_held = 0
            elif exhaustion_up:
                emit(i, "short", "exhaustion up bar")
                st.position = "short"
                st.bars_held = 0

    return decisions


def generate_decisions(
    bars: list[Bar],
    model: str,
    variant: Optional[str] = None,
) -> list[Decision]:
    """Ordered decisions for one model on one series.

    Baselines S1-S3 reuse intel.strategy signals: an entry in the opposite
    direction of the held position is expressed as exit + entry (the portfolio
    engine fills both at the same next open, mirroring a single-fill reversal
    at the same price under identical slippage).
    """
    if model in BASELINE_MODEL_IDS:
        params = resolve_params(model, variant)
        sigs = trend_signals(bars, model, params)
        out: list[Decision] = []
        held: Optional[str] = None
        by_index: dict[int, list] = {}
        for s in sigs:
            by_index.setdefault(s.index, []).append(s)
        for i in sorted(by_index):
            for s in by_index[i]:
                if held is None:
                    out.append(Decision(index=i, action=s.direction, atr=s.atr, reason="baseline entry"))
                    held = s.direction
                elif held != s.direction:
                    out.append(Decision(index=i, action="exit", atr=s.atr, reason="baseline reverse"))
                    out.append(Decision(index=i, action=s.direction, atr=s.atr, reason="baseline reverse entry"))
                    held = s.direction
        return out
    return _decide_contrarian(model, bars, variant)
