# EquityResearch

Given a **ticker + company name**, produce an equity research report that ends in a concrete,
beginner-friendly recommendation on **which options contracts (calls/puts) to buy** — justified
by fundamentals, technicals, options analytics, sentiment, and earnings-call findings.

The user is assumed **new to options**, so every recommended contract is explained in plain
English (what it is, what it costs, max loss, breakeven, what move is needed), and the workflow
defaults to a **moderate, defined-risk** profile: long calls/puts and vertical debit spreads only.

> Educational research only. **Not financial advice.**

## How it works (hybrid)

```
ticker ─► python -m equity_research.cli ─► reports/TICKER_data.json (compact analytics + candidates)
                                                       │
        Claude skill (skills/equity-research) ─────────┘
          reads JSON → web/earnings research → thesis → picks → reports/TICKER-YYYY-MM-DD.md
```

The Python package does the data + quant heavy-lifting (free `yfinance` data) and emits a small
JSON. The Claude skill reads only that JSON (never raw option chains, to keep tokens low), adds
web research, and writes the final Markdown report.

### Package layout
- `equity_research/data.py` — yfinance fetch (prices, fundamentals, option chain, earnings, risk-free rate). Only networked module.
- `equity_research/technicals.py` — SMA 20/50/200, RSI(14), MACD, 52-wk range, realized vol, trend.
- `equity_research/fundamentals.py` — key ratios + transparent 0–100 health score.
- `equity_research/options.py` — Black-Scholes greeks (no scipy), IV-vs-realized signal, liquidity filter, candidate generation.
- `equity_research/report_data.py` — assembles the compact JSON.
- `equity_research/cli.py` — `python -m equity_research.cli TICKER --company "..."`.
- `skills/equity-research/SKILL.md` — orchestration.
- `tests/` — offline unit tests (Black-Scholes, technicals, fundamentals).

## Usage

```bash
pip install -r requirements.txt

# 1. data + quant -> reports/AAPL_data.json
python -m equity_research.cli AAPL --company "Apple Inc."

# 2. then invoke the equity-research skill (in Claude Code) with the same ticker + company
#    -> writes reports/AAPL-YYYY-MM-DD.md
```

Run the offline tests with:

```bash
pytest -q
```

Requires Python 3.10+ and a network where Yahoo Finance is reachable (for the live `cli` run).
Reports are written to `reports/` (gitignored).
