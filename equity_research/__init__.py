"""Equity research -> options recommendation workflow.

A small package that pulls free market data (yfinance), computes fundamentals,
technicals and options analytics, and emits a compact JSON shortlist of
beginner-friendly options-contract candidates. A Claude Code skill consumes the
JSON, adds web research, and writes the final report.

Educational research only. Not financial advice.
"""

__version__ = "0.1.0"
