"""Fundamental ratios + a transparent 0-100 health score.

The score is the weighted average of four 0-100 buckets (valuation, growth,
profitability, balance sheet). Buckets whose inputs are missing are dropped and
the remaining weights renormalized, so a thinly-covered ticker still yields a
score from whatever data exists (never crashes on ``None``).
"""

from __future__ import annotations

from typing import Optional

# Bucket weights (sum to 1.0 when all present).
WEIGHTS = {"valuation": 0.25, "growth": 0.25, "profitability": 0.30, "balance_sheet": 0.20}


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _score_valuation(pe: Optional[float], peg: Optional[float]) -> Optional[float]:
    parts = []
    if pe is not None and pe > 0:
        # Cheaper PE -> higher score. ~15 PE = 75, 40 PE -> ~10.
        parts.append(_clamp(100 - (pe - 10) * 3))
    if peg is not None and peg > 0:
        # PEG ~1 is fair (=70); >2 poor.
        parts.append(_clamp(100 - (peg - 1) * 50))
    if not parts:
        return None
    return sum(parts) / len(parts)


def _score_growth(rev_growth: Optional[float]) -> Optional[float]:
    if rev_growth is None:
        return None
    # rev_growth is a fraction (0.15 = 15%). 0% -> 40, 25% -> 90.
    return _clamp(40 + rev_growth * 200)


def _score_profitability(margin: Optional[float]) -> Optional[float]:
    if margin is None:
        return None
    # profit margin fraction. 0% -> 30, 25% -> 90.
    return _clamp(30 + margin * 240)


def _score_balance_sheet(debt_to_equity: Optional[float]) -> Optional[float]:
    if debt_to_equity is None:
        return None
    # yfinance reports D/E as a percent (e.g. 150 = 1.5x). Lower is healthier.
    de = debt_to_equity / 100.0 if debt_to_equity > 5 else debt_to_equity
    return _clamp(100 - de * 40)


def health_score(metrics: dict) -> dict:
    """Compute the 0-100 score plus the per-bucket breakdown.

    ``metrics`` keys (any may be None): pe, peg, rev_growth, profit_margin,
    debt_to_equity.
    """
    buckets = {
        "valuation": _score_valuation(metrics.get("pe"), metrics.get("peg")),
        "growth": _score_growth(metrics.get("rev_growth")),
        "profitability": _score_profitability(metrics.get("profit_margin")),
        "balance_sheet": _score_balance_sheet(metrics.get("debt_to_equity")),
    }
    present = {k: v for k, v in buckets.items() if v is not None}
    if not present:
        return {"score": None, "buckets": buckets}

    total_w = sum(WEIGHTS[k] for k in present)
    score = sum(present[k] * WEIGHTS[k] for k in present) / total_w
    rounded = {k: (round(v, 1) if v is not None else None) for k, v in buckets.items()}
    return {"score": round(score, 1), "buckets": rounded}


def build_fundamentals(info: dict) -> dict:
    """Pull the ratios we care about from a yfinance ``.info`` dict and score them.

    Missing fields are tolerated (``.get`` everywhere).
    """
    pe = info.get("trailingPE") or info.get("forwardPE")
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    rev_growth = info.get("revenueGrowth")
    profit_margin = info.get("profitMargins")
    debt_to_equity = info.get("debtToEquity")
    market_cap = info.get("marketCap")
    analyst_target = info.get("targetMeanPrice")

    scored = health_score({
        "pe": pe, "peg": peg, "rev_growth": rev_growth,
        "profit_margin": profit_margin, "debt_to_equity": debt_to_equity,
    })

    return {
        "score": scored["score"],
        "buckets": scored["buckets"],
        "pe": pe,
        "peg": peg,
        "rev_growth": rev_growth,
        "profit_margin": profit_margin,
        "debt_to_equity": debt_to_equity,
        "market_cap": market_cap,
        "analyst_target": analyst_target,
    }
