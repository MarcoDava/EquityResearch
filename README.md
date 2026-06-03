# EquityResearch

Workflow: given a **ticker + company name**, produce an equity research report ending in a
concrete, beginner-friendly recommendation on **which options contracts (calls/puts) to buy** —
justified by fundamentals, technicals, options analytics, sentiment, and earnings calls.

Hybrid design: a Python package does data + quant heavy-lifting (free `yfinance` data); a Claude
Code skill orchestrates, adds web/earnings-call research, and writes a `TICKER-YYYY-MM-DD.md`
report under `reports/`.

> Educational research only. Not financial advice.

Status: planning / scaffold. See the implementation plan for the full design.
