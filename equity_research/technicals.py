"""Technical indicators on a daily close series. Pure pandas/numpy -- no TA lib.

Functions accept a pandas Series of closes (oldest -> newest) and return plain
floats or small dicts so the output JSON stays compact and easy to test.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


def sma(close: pd.Series, n: int) -> Optional[float]:
    """Latest n-period simple moving average."""
    if len(close) < n:
        return None
    return round(float(close.tail(n).mean()), 4)


def rsi(close: pd.Series, n: int = 14) -> Optional[float]:
    """Latest Wilder-smoothed RSI."""
    if len(close) < n + 1:
        return None
    delta = close.diff().dropna()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    # Wilder smoothing via exponential moving average with alpha = 1/n.
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(float(100.0 - (100.0 / (1.0 + rs))), 2)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD line, signal line and histogram (latest values)."""
    if len(close) < slow + signal:
        return {"macd": None, "signal": None, "hist": None}
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "hist": round(float(hist.iloc[-1]), 4),
    }


def realized_vol(close: pd.Series, n: int = 20) -> Optional[float]:
    """Annualized realized volatility from the last n daily log returns."""
    if len(close) < n + 1:
        return None
    log_ret = np.log(close / close.shift(1)).dropna().tail(n)
    if len(log_ret) < 2:
        return None
    daily_std = float(log_ret.std(ddof=1))
    return round(daily_std * math.sqrt(252), 4)


def wk52_range(close: pd.Series) -> dict:
    """52-week high/low and where the latest price sits within that range (0-100%)."""
    window = close.tail(252)
    hi = float(window.max())
    lo = float(window.min())
    last = float(close.iloc[-1])
    pos = None
    if hi > lo:
        pos = round((last - lo) / (hi - lo) * 100, 1)
    return {"wk52_high": round(hi, 4), "wk52_low": round(lo, 4), "wk52_pos_pct": pos}


def trend_label(close: pd.Series) -> str:
    """Derive a coarse trend from the price/SMA stack."""
    last = float(close.iloc[-1])
    s20, s50, s200 = sma(close, 20), sma(close, 50), sma(close, 200)
    if s50 is None:
        return "unknown"
    if s200 is not None and last > s50 > s200 and last > s20:
        return "uptrend"
    if s200 is not None and last < s50 < s200 and last < s20:
        return "downtrend"
    if s20 is not None and last > s20 > s50:
        return "uptrend"
    if s20 is not None and last < s20 < s50:
        return "downtrend"
    return "sideways"


def compute_technicals(close: pd.Series) -> dict:
    """Assemble the full technicals block for the compact JSON."""
    block = {
        "sma20": sma(close, 20),
        "sma50": sma(close, 50),
        "sma200": sma(close, 200),
        "rsi14": rsi(close, 14),
        "macd": macd(close),
        "realized_vol": realized_vol(close, 20),
        "trend": trend_label(close),
    }
    block.update(wk52_range(close))
    return block
