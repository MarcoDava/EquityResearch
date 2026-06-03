"""Options analytics: Black-Scholes greeks, IV signal, liquidity filter, and
beginner-friendly candidate generation (long calls/puts + vertical debit spreads).

Pure ``math``/``numpy`` only -- normal CDF via ``math.erf`` so no scipy dependency.
Everything here is offline-testable; nothing touches the network.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Optional

SQRT2 = math.sqrt(2.0)
SQRT_2PI = math.sqrt(2.0 * math.pi)

# ----------------------------------------------------------------------------
# Black-Scholes
# ----------------------------------------------------------------------------


def norm_cdf(x: float) -> float:
    """Standard normal CDF via erf (no scipy)."""
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        raise ValueError("S, K, T, sigma must be positive for Black-Scholes")
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S: float, K: float, T: float, r: float, sigma: float, kind: str = "call") -> float:
    """Black-Scholes price of a European call or put."""
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    disc = math.exp(-r * T)
    if kind == "call":
        return S * norm_cdf(d1) - K * disc * norm_cdf(d2)
    if kind == "put":
        return K * disc * norm_cdf(-d2) - S * norm_cdf(-d1)
    raise ValueError("kind must be 'call' or 'put'")


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float, kind: str = "call") -> dict:
    """Delta, gamma, theta (per day), vega (per 1 vol point) for a call/put."""
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    disc = math.exp(-r * T)
    pdf_d1 = norm_pdf(d1)
    sqrtT = math.sqrt(T)

    if kind == "call":
        delta = norm_cdf(d1)
        theta_year = (-(S * pdf_d1 * sigma) / (2 * sqrtT)) - r * K * disc * norm_cdf(d2)
    elif kind == "put":
        delta = norm_cdf(d1) - 1.0
        theta_year = (-(S * pdf_d1 * sigma) / (2 * sqrtT)) + r * K * disc * norm_cdf(-d2)
    else:
        raise ValueError("kind must be 'call' or 'put'")

    gamma = pdf_d1 / (S * sigma * sqrtT)
    vega = S * pdf_d1 * sqrtT / 100.0  # per 1% change in vol
    theta = theta_year / 365.0  # per calendar day

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 5),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
    }


# ----------------------------------------------------------------------------
# IV signal
# ----------------------------------------------------------------------------


def iv_signal(atm_iv: Optional[float], realized_vol: Optional[float]) -> dict:
    """Label options 'cheap'/'fair'/'expensive' by comparing ATM implied vol to
    20-day realized vol. Honest proxy for IV rank -- free data lacks a year of IV
    history, so the report carries this caveat.
    """
    caveat = "proxy: ATM IV vs 20d realized vol, not full IV-rank history"
    if not atm_iv or not realized_vol or realized_vol <= 0:
        return {"atm_iv": atm_iv, "realized_vol": realized_vol,
                "iv_signal": "unknown", "caveat": caveat}
    ratio = atm_iv / realized_vol
    if ratio < 0.9:
        signal = "cheap"
    elif ratio <= 1.2:
        signal = "fair"
    else:
        signal = "expensive"
    return {"atm_iv": round(atm_iv, 4), "realized_vol": round(realized_vol, 4),
            "ratio": round(ratio, 2), "iv_signal": signal, "caveat": caveat}


# ----------------------------------------------------------------------------
# Liquidity
# ----------------------------------------------------------------------------


def is_liquid(bid: float, ask: float, open_interest: float, volume: float,
              min_oi: int = 50, max_spread_pct: float = 0.15) -> bool:
    """Tradeable-for-a-beginner test: real two-sided market, decent open interest,
    and a bid/ask spread that is not a rip-off.
    """
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return False
    oi = open_interest or 0
    vol = volume or 0
    if oi < min_oi and vol < min_oi:
        return False
    mid = 0.5 * (bid + ask)
    if mid <= 0:
        return False
    spread_pct = (ask - bid) / mid
    return spread_pct <= max_spread_pct


# ----------------------------------------------------------------------------
# Candidate dataclasses + arithmetic
# ----------------------------------------------------------------------------


@dataclass
class SingleLeg:
    type: str           # "long_call" | "long_put"
    expiry: str
    dte: int
    strike: float
    premium: float      # per-share mid
    delta: float
    spot: float
    liquidity_ok: bool = True

    def to_dict(self) -> dict:
        kind = "call" if self.type == "long_call" else "put"
        cost = round(self.premium * 100, 2)
        if kind == "call":
            breakeven = self.strike + self.premium
        else:
            breakeven = self.strike - self.premium
        pct_move = round((breakeven - self.spot) / self.spot * 100, 2)
        return {
            "type": self.type,
            "expiry": self.expiry,
            "dte": self.dte,
            "strike": self.strike,
            "premium": round(self.premium, 2),
            "cost": cost,
            "delta": round(self.delta, 3),
            "breakeven": round(breakeven, 2),
            "max_loss": cost,
            "max_gain": "uncapped",
            "pct_move_to_breakeven": pct_move,
            "liquidity_ok": self.liquidity_ok,
        }


@dataclass
class VerticalSpread:
    type: str           # "bull_call_spread" | "bear_put_spread"
    expiry: str
    dte: int
    long_strike: float
    short_strike: float
    net_debit: float    # per-share
    spot: float
    liquidity_ok: bool = True

    def to_dict(self) -> dict:
        width = abs(self.short_strike - self.long_strike)
        cost = round(self.net_debit * 100, 2)
        max_gain = round((width - self.net_debit) * 100, 2)
        if self.type == "bull_call_spread":
            breakeven = self.long_strike + self.net_debit
        else:  # bear_put_spread
            breakeven = self.long_strike - self.net_debit
        pct_move = round((breakeven - self.spot) / self.spot * 100, 2)
        return {
            "type": self.type,
            "expiry": self.expiry,
            "dte": self.dte,
            "long_strike": self.long_strike,
            "short_strike": self.short_strike,
            "net_debit": round(self.net_debit, 2),
            "cost": cost,
            "breakeven": round(breakeven, 2),
            "max_loss": cost,
            "max_gain": max_gain,
            "pct_move_to_breakeven": pct_move,
            "liquidity_ok": self.liquidity_ok,
        }


def _mid(bid: float, ask: float, last: float) -> Optional[float]:
    if bid and ask and bid > 0 and ask > 0:
        return 0.5 * (bid + ask)
    if last and last > 0:
        return float(last)
    return None


def generate_candidates(direction: str, spot: float, r: float, dte: int,
                        expiry: str, calls: list[dict], puts: list[dict],
                        target_delta: float = 0.40) -> list[dict]:
    """Build up to 3 ranked, beginner-friendly candidates from one expiry's chain.

    ``calls``/``puts`` are lists of dicts with keys: strike, bid, ask, lastPrice,
    impliedVolatility, openInterest, volume. Returns a list of candidate dicts.
    Liquidity-filtered; if nothing is liquid the list is empty (caller warns).
    """
    if dte <= 0:
        return []
    T = dte / 365.0
    bullish = direction == "bullish"
    legs = calls if bullish else puts
    kind = "call" if bullish else "put"

    # Attach computed delta + mid to each liquid leg.
    enriched = []
    for row in legs:
        bid, ask, last = row.get("bid"), row.get("ask"), row.get("lastPrice")
        if not is_liquid(bid, ask, row.get("openInterest"), row.get("volume")):
            continue
        mid = _mid(bid, ask, last)
        sigma = row.get("impliedVolatility")
        if mid is None or not sigma or sigma <= 0:
            continue
        try:
            greeks = bs_greeks(spot, row["strike"], T, r, sigma, kind)
        except ValueError:
            continue
        enriched.append({**row, "mid": mid, "delta": greeks["delta"], "sigma": sigma})

    if not enriched:
        return []

    candidates: list[dict] = []

    # 1) Single long leg nearest the target absolute delta (0.30-0.45 band).
    long_leg = min(enriched, key=lambda x: abs(abs(x["delta"]) - target_delta))
    candidates.append(SingleLeg(
        type="long_call" if bullish else "long_put",
        expiry=expiry, dte=dte, strike=long_leg["strike"],
        premium=long_leg["mid"], delta=long_leg["delta"], spot=spot,
    ).to_dict())

    # 2) Vertical debit spread: buy the long leg above, sell a cheaper further-OTM leg
    #    (~0.25 delta) to cap cost and define risk.
    short_target = 0.25
    if bullish:
        otm = [e for e in enriched if e["strike"] > long_leg["strike"]]
    else:
        otm = [e for e in enriched if e["strike"] < long_leg["strike"]]
    if otm:
        short_leg = min(otm, key=lambda x: abs(abs(x["delta"]) - short_target))
        net_debit = long_leg["mid"] - short_leg["mid"]
        if net_debit > 0:
            candidates.append(VerticalSpread(
                type="bull_call_spread" if bullish else "bear_put_spread",
                expiry=expiry, dte=dte,
                long_strike=long_leg["strike"], short_strike=short_leg["strike"],
                net_debit=net_debit, spot=spot,
            ).to_dict())

    return candidates[:3]
