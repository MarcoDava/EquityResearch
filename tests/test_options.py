"""Offline tests for the options quant core (no network)."""

import math

import pytest

from equity_research.options import (
    bs_price, bs_greeks, iv_signal, is_liquid,
    SingleLeg, VerticalSpread, generate_candidates,
)

# Reference Black-Scholes case: S=100, K=100, T=1, r=0.05, sigma=0.20.
S, K, T, R, SIG = 100.0, 100.0, 1.0, 0.05, 0.20


def test_bs_price_known_values():
    assert bs_price(S, K, T, R, SIG, "call") == pytest.approx(10.4506, abs=1e-3)
    assert bs_price(S, K, T, R, SIG, "put") == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity():
    call = bs_price(S, K, T, R, SIG, "call")
    put = bs_price(S, K, T, R, SIG, "put")
    assert (call - put) == pytest.approx(S - K * math.exp(-R * T), abs=1e-6)


def test_bs_greeks_known_values():
    g = bs_greeks(S, K, T, R, SIG, "call")
    assert g["delta"] == pytest.approx(0.6368, abs=1e-3)
    assert g["gamma"] == pytest.approx(0.018762, abs=1e-4)
    assert g["vega"] == pytest.approx(0.3752, abs=1e-3)
    # Put delta = call delta - 1.
    gp = bs_greeks(S, K, T, R, SIG, "put")
    assert gp["delta"] == pytest.approx(-0.3632, abs=1e-3)


def test_bs_rejects_bad_inputs():
    with pytest.raises(ValueError):
        bs_price(S, K, 0.0, R, SIG, "call")
    with pytest.raises(ValueError):
        bs_price(S, K, T, R, SIG, "banana")


def test_iv_signal_buckets():
    assert iv_signal(0.31, 0.27)["iv_signal"] == "fair"
    assert iv_signal(0.50, 0.20)["iv_signal"] == "expensive"
    assert iv_signal(0.15, 0.30)["iv_signal"] == "cheap"
    assert iv_signal(None, 0.30)["iv_signal"] == "unknown"
    assert iv_signal(0.3, 0)["iv_signal"] == "unknown"


def test_is_liquid():
    assert is_liquid(bid=7.8, ask=8.0, open_interest=500, volume=100) is True
    assert is_liquid(bid=0, ask=8.0, open_interest=500, volume=100) is False     # no bid
    assert is_liquid(bid=1.0, ask=2.0, open_interest=1, volume=0) is False        # illiquid
    assert is_liquid(bid=1.0, ask=2.0, open_interest=500, volume=0) is False      # 67% spread


def test_single_leg_call_arithmetic():
    d = SingleLeg(type="long_call", expiry="2026-08-15", dte=73, strike=195,
                  premium=7.85, delta=0.42, spot=190.12).to_dict()
    assert d["cost"] == 785.0
    assert d["breakeven"] == 202.85
    assert d["max_loss"] == 785.0
    assert d["max_gain"] == "uncapped"
    assert d["pct_move_to_breakeven"] == pytest.approx(6.7, abs=0.1)


def test_single_leg_put_arithmetic():
    d = SingleLeg(type="long_put", expiry="2026-08-15", dte=73, strike=185,
                  premium=6.0, delta=-0.40, spot=190.12).to_dict()
    assert d["breakeven"] == 179.0           # 185 - 6
    assert d["cost"] == 600.0
    assert d["pct_move_to_breakeven"] < 0    # needs price to fall


def test_vertical_spread_arithmetic():
    d = VerticalSpread(type="bull_call_spread", expiry="2026-08-15", dte=73,
                       long_strike=195, short_strike=210, net_debit=4.10,
                       spot=190.12).to_dict()
    assert d["cost"] == 410.0
    assert d["max_loss"] == 410.0
    assert d["max_gain"] == 1090.0           # (15 - 4.10) * 100
    assert d["breakeven"] == 199.10


def _liquid_call(strike, bid, ask, iv):
    return {"strike": strike, "bid": bid, "ask": ask, "lastPrice": (bid + ask) / 2,
            "impliedVolatility": iv, "openInterest": 1000, "volume": 200}


def test_generate_candidates_bullish():
    spot = 100.0
    calls = [_liquid_call(k, max(spot - k, 0) + 3, max(spot - k, 0) + 3.4, 0.30)
             for k in range(90, 121, 5)]
    out = generate_candidates(direction="bullish", spot=spot, r=0.04, dte=60,
                              expiry="2026-08-01", calls=calls, puts=[])
    assert len(out) >= 1
    assert out[0]["type"] == "long_call"
    assert out[0]["breakeven"] > out[0]["strike"]
    # If a spread was built it must have a finite, positive max_gain.
    spreads = [c for c in out if c["type"] == "bull_call_spread"]
    if spreads:
        assert spreads[0]["max_gain"] > 0
        assert spreads[0]["short_strike"] > spreads[0]["long_strike"]


def test_generate_candidates_empty_when_illiquid():
    spot = 100.0
    calls = [{"strike": 100, "bid": 1, "ask": 2, "lastPrice": 1.5,
              "impliedVolatility": 0.3, "openInterest": 0, "volume": 0}]
    out = generate_candidates(direction="bullish", spot=spot, r=0.04, dte=60,
                              expiry="2026-08-01", calls=calls, puts=[])
    assert out == []
