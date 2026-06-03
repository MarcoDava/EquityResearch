"""Assemble the compact JSON contract from the data + analytics layers.

This is the single hand-off between Python and the Claude skill. It deliberately
keeps only pre-computed analytics and a shortlist of candidates -- never the raw
option chain -- so the skill reads very few tokens.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from . import data as _data
from .fundamentals import build_fundamentals
from .options import generate_candidates, iv_signal
from .technicals import compute_technicals


def _atm_iv(calls: list[dict], spot: float) -> Optional[float]:
    """Implied vol of the call whose strike is nearest spot."""
    usable = [c for c in calls if c.get("strike") and c.get("impliedVolatility")]
    if not usable:
        return None
    nearest = min(usable, key=lambda c: abs(c["strike"] - spot))
    iv = nearest.get("impliedVolatility")
    return float(iv) if iv and iv > 0 else None


def preliminary_direction(technicals: dict, fund_score: Optional[float], spot: float) -> str:
    """Coarse bull/bear read from trend + fundamentals; the skill may override."""
    trend = technicals.get("trend")
    trend_signal = {"uptrend": 1, "downtrend": -1}.get(trend, 0)
    fund_signal = 0
    if fund_score is not None:
        fund_signal = 1 if fund_score >= 55 else -1
    total = trend_signal + fund_signal
    if total > 0:
        return "bullish"
    if total < 0:
        return "bearish"
    # Tie-breaker: price vs 50-day SMA.
    sma50 = technicals.get("sma50")
    if sma50:
        return "bullish" if spot >= sma50 else "bearish"
    return "bullish"


def build_report_data(symbol: str, company: Optional[str] = None,
                      today: Optional[_dt.date] = None) -> dict:
    """Fetch + compute everything, return the compact dict. Network-bound."""
    today = today or _dt.date.today()
    symbol = symbol.upper().strip()

    tk = _data.get_ticker(symbol)
    close = _data.fetch_history(tk)          # raises ValueError on invalid ticker
    spot = round(float(close.iloc[-1]), 4)
    info = _data.fetch_info(tk)
    r = _data.fetch_risk_free_rate()

    technicals = compute_technicals(close)
    fundamentals = build_fundamentals(info)
    direction = preliminary_direction(technicals, fundamentals.get("score"), spot)

    warnings: list[str] = []

    # Options.
    expiries = _data.fetch_expiries(tk)
    candidates: list[dict] = []
    options_iv = iv_signal(None, technicals.get("realized_vol"))
    next_earnings = _data.fetch_next_earnings(tk)

    if not expiries:
        warnings.append("no listed options for this ticker")
    else:
        expiry = _data.pick_expiry(expiries, today=today)
        if expiry is None:
            warnings.append("no expiry in a usable date range")
        else:
            chain = _data.fetch_option_chain(tk, expiry)
            dte = (_dt.datetime.strptime(expiry, "%Y-%m-%d").date() - today).days
            atm = _atm_iv(chain["calls"], spot)
            options_iv = iv_signal(atm, technicals.get("realized_vol"))
            candidates = generate_candidates(
                direction=direction, spot=spot, r=r, dte=dte, expiry=expiry,
                calls=chain["calls"], puts=chain["puts"],
            )
            if not candidates:
                warnings.append("thin options: no liquid candidates passed the filter")
            elif len(candidates) == 1:
                warnings.append("thin options: only 1 liquid candidate found")

    out = {
        "ticker": symbol,
        "company": company or info.get("shortName") or info.get("longName") or symbol,
        "as_of": today.strftime("%Y-%m-%d"),
        "spot": spot,
        "risk_free_rate": round(r, 4),
        "fundamentals": fundamentals,
        "technicals": technicals,
        "options_iv": options_iv,
        "preliminary_direction": direction,
        "next_earnings": next_earnings,
        "candidates": candidates,
    }
    if warnings:
        out["warnings"] = warnings
    return out
