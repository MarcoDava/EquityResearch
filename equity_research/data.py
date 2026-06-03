"""Network layer: fetch everything we need from yfinance.

Every call is wrapped so a missing/blocked field degrades to ``None``/empty
rather than crashing. The only hard failure is an invalid ticker (no price
history at all), which raises ``ValueError`` for ``cli.py`` to report cleanly.

This module is the *only* place that touches the network, so the rest of the
package stays offline-testable.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

import pandas as pd

DEFAULT_RISK_FREE = 0.043  # fallback if ^IRX is unavailable


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_ticker(symbol: str):
    import yfinance as yf
    return yf.Ticker(symbol)


def fetch_history(tk) -> pd.Series:
    """1y daily close series (oldest -> newest). Raises ValueError if empty."""
    hist = _safe(lambda: tk.history(period="1y", auto_adjust=True))
    if hist is None or hist.empty or "Close" not in hist:
        raise ValueError("no price history (invalid or delisted ticker?)")
    return hist["Close"].dropna()


def fetch_info(tk) -> dict:
    info = _safe(lambda: tk.info, default={}) or {}
    if not info:
        info = _safe(lambda: tk.get_info(), default={}) or {}
    return info


def fetch_risk_free_rate() -> float:
    """13-week T-bill yield (^IRX) as a decimal; fallback constant."""
    def _pull():
        import yfinance as yf
        irx = yf.Ticker("^IRX").history(period="5d")
        if irx is None or irx.empty:
            return None
        return float(irx["Close"].dropna().iloc[-1]) / 100.0
    rate = _safe(_pull)
    return rate if rate and rate > 0 else DEFAULT_RISK_FREE


def fetch_next_earnings(tk) -> Optional[str]:
    """Next earnings date as YYYY-MM-DD, if available."""
    cal = _safe(lambda: tk.calendar)
    if cal is None:
        return None
    # Newer yfinance returns a dict; older returns a DataFrame.
    try:
        if isinstance(cal, dict):
            dates = cal.get("Earnings Date")
            if dates:
                d = dates[0] if isinstance(dates, (list, tuple)) else dates
                return _to_date_str(d)
        else:  # DataFrame
            val = cal.loc["Earnings Date"][0]
            return _to_date_str(val)
    except Exception:
        return None
    return None


def _to_date_str(d) -> Optional[str]:
    try:
        if isinstance(d, str):
            return d[:10]
        if isinstance(d, (_dt.date, _dt.datetime)):
            return d.strftime("%Y-%m-%d")
        return pd.Timestamp(d).strftime("%Y-%m-%d")
    except Exception:
        return None


def _chain_rows(df) -> list[dict]:
    """Convert a yfinance option-chain DataFrame to a list of plain dicts."""
    if df is None or getattr(df, "empty", True):
        return []
    cols = ["strike", "bid", "ask", "lastPrice", "impliedVolatility",
            "openInterest", "volume"]
    keep = [c for c in cols if c in df.columns]
    rows = []
    for _, row in df[keep].iterrows():
        rows.append({c: (None if pd.isna(row[c]) else float(row[c])) for c in keep})
    return rows


def pick_expiry(expiries: list[str], min_dte: int = 30, max_dte: int = 90,
                today: Optional[_dt.date] = None) -> Optional[str]:
    """Choose the expiry whose DTE best fits the 30-90 day window.

    Prefer expiries inside [min_dte, max_dte] (closest to the window midpoint);
    otherwise the expiry with DTE nearest the window.
    """
    today = today or _dt.date.today()
    dated = []
    for e in expiries:
        try:
            d = _dt.datetime.strptime(e, "%Y-%m-%d").date()
        except ValueError:
            continue
        dte = (d - today).days
        if dte > 0:
            dated.append((e, dte))
    if not dated:
        return None
    in_window = [x for x in dated if min_dte <= x[1] <= max_dte]
    mid = (min_dte + max_dte) / 2
    pool = in_window or dated
    return min(pool, key=lambda x: abs(x[1] - mid))[0]


def fetch_option_chain(tk, expiry: str) -> dict:
    """Return {'calls': [...], 'puts': [...]} of plain dicts for one expiry."""
    chain = _safe(lambda: tk.option_chain(expiry))
    if chain is None:
        return {"calls": [], "puts": []}
    return {"calls": _chain_rows(chain.calls), "puts": _chain_rows(chain.puts)}


def fetch_expiries(tk) -> list[str]:
    return list(_safe(lambda: tk.options, default=()) or ())
