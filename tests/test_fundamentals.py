"""Offline tests for the fundamentals health score (no network)."""

from equity_research.fundamentals import health_score, build_fundamentals, WEIGHTS


def test_all_none_score_is_none():
    out = health_score({"pe": None, "peg": None, "rev_growth": None,
                        "profit_margin": None, "debt_to_equity": None})
    assert out["score"] is None
    assert all(v is None for v in out["buckets"].values())


def test_partial_inputs_renormalize_and_score_in_range():
    # Only profitability present -> score equals that bucket alone.
    out = health_score({"pe": None, "peg": None, "rev_growth": None,
                        "profit_margin": 0.25, "debt_to_equity": None})
    assert out["score"] is not None
    assert 0 <= out["score"] <= 100
    assert out["buckets"]["profitability"] is not None
    # With a single present bucket, the weighted score == that bucket value.
    assert out["score"] == out["buckets"]["profitability"]


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_healthy_company_scores_higher_than_weak():
    strong = health_score({"pe": 15, "peg": 1.0, "rev_growth": 0.25,
                           "profit_margin": 0.30, "debt_to_equity": 30})
    weak = health_score({"pe": 60, "peg": 3.0, "rev_growth": -0.10,
                         "profit_margin": 0.01, "debt_to_equity": 300})
    assert strong["score"] > weak["score"]


def test_build_fundamentals_tolerates_empty_info():
    out = build_fundamentals({})
    assert out["score"] is None
    assert out["pe"] is None
    assert "buckets" in out


def test_build_fundamentals_reads_info_keys():
    info = {"trailingPE": 20, "revenueGrowth": 0.12, "profitMargins": 0.18,
            "debtToEquity": 120, "marketCap": 1_000_000, "targetMeanPrice": 250}
    out = build_fundamentals(info)
    assert out["pe"] == 20
    assert out["market_cap"] == 1_000_000
    assert out["analyst_target"] == 250
    assert out["score"] is not None
