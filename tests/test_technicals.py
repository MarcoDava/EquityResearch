"""Offline tests for technical indicators (no network)."""

import numpy as np
import pandas as pd
import pytest

from equity_research.technicals import (
    sma, rsi, macd, realized_vol, wk52_range, trend_label, compute_technicals,
)


def test_sma_exact():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert sma(s, 5) == 3.0
    assert sma(s, 3) == 4.0          # mean of 3,4,5
    assert sma(s, 10) is None        # not enough data


def test_rsi_extremes():
    rising = pd.Series(np.arange(1, 40, dtype=float))
    assert rsi(rising, 14) == 100.0
    falling = pd.Series(np.arange(40, 1, -1, dtype=float))
    assert rsi(falling, 14) == 0.0


def test_rsi_none_when_short():
    assert rsi(pd.Series([1.0, 2.0, 3.0]), 14) is None


def test_macd_keys_and_shape():
    s = pd.Series(np.linspace(10, 50, 60))
    m = macd(s)
    assert set(m) == {"macd", "signal", "hist"}
    # Steady uptrend -> MACD line above signal line.
    assert m["macd"] is not None and m["macd"] > m["signal"]


def test_realized_vol_positive():
    rng = np.random.default_rng(0)
    s = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 60)))
    rv = realized_vol(s, 20)
    assert rv is not None and rv > 0


def test_wk52_range():
    s = pd.Series(np.arange(1, 101, dtype=float))   # 1..100, last = 100 = high
    r = wk52_range(s)
    assert r["wk52_high"] == 100.0
    assert r["wk52_low"] == 1.0
    assert r["wk52_pos_pct"] == 100.0


def test_trend_label_uptrend_downtrend():
    up = pd.Series(np.arange(1, 261, dtype=float))
    assert trend_label(up) == "uptrend"
    down = pd.Series(np.arange(260, 0, -1, dtype=float))
    assert trend_label(down) == "downtrend"


def test_compute_technicals_block():
    s = pd.Series(np.linspace(10, 60, 260))
    block = compute_technicals(s)
    for key in ("sma20", "sma50", "sma200", "rsi14", "macd", "realized_vol",
                "trend", "wk52_high", "wk52_low", "wk52_pos_pct"):
        assert key in block
