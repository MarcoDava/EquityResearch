# Equity Research → Options Recommendation Workflow

> Draft plan handed to Ultraplan for refinement. Refine/expand this file.

## Context

User wants a repeatable workflow: give it a **ticker + company name**, and it produces an
equity research report that ends in a concrete recommendation on **which options contracts
(calls/puts) to buy**, justified by fundamentals, technicals, options analytics, sentiment,
and earnings calls.

Critical constraint from clarifications: **the user does not fully understand options.** So the
output must teach, not just rank. Every recommended contract explains in plain English: what it
is, what it costs (premium), max loss, breakeven, and what price move is needed to profit. The
workflow defaults to a **moderate, defined-risk** profile rather than assuming an expert.

Decisions locked in:
- **What to buy:** specific options contracts (strike + expiry), derived from a stock thesis.
- **Form:** hybrid — a Python package does data + quant heavy-lifting; a Claude Code skill
  orchestrates, adds web/earnings-call research, and writes the report.
- **Data:** free APIs (`yfinance`) for prices/fundamentals/option chains/earnings dates, plus
  Claude web research for sentiment, catalysts, analyst views, earnings-call highlights.
- **Output:** one file per run, named `TICKER-YYYY-MM-DD.md` (Markdown — readable, low-token),
  saved in `reports/`.

This is a greenfield project (empty repo). No existing code to reuse.

## Approach (recommended)

Python emits a **compact JSON** of pre-computed analytics so Claude never reads raw option
chains (token control). Claude reads that JSON, layers in web research, forms the thesis, picks
and explains contracts, writes the report.

```
EquityResearch/
├── equity_research/
│   ├── __init__.py
│   ├── data.py          # yfinance fetch: prices, fundamentals, option chain, earnings, rates
│   ├── technicals.py    # SMA 20/50/200, RSI14, MACD, 52wk range, realized vol, trend label
│   ├── fundamentals.py  # key ratios + simple 0-100 health score
│   ├── options.py       # Black-Scholes greeks, IV-vs-realized, liquidity filter, candidates
│   ├── report_data.py   # assemble everything into one compact dict
│   └── cli.py           # `python -m equity_research.cli TICKER` -> writes reports/TICKER_data.json
├── skills/equity-research/SKILL.md   # orchestration: run cli -> web research -> write report
├── reports/             # output dir (gitignored), holds TICKER-YYYY-MM-DD.md + *_data.json
├── requirements.txt     # yfinance, pandas, numpy  (no scipy)
└── README.md
```

### Python layer details

- **data.py** — wraps `yfinance.Ticker`. Pulls: 1y daily history; `.info`/fundamentals (PE, PEG,
  margins, debt/equity, revenue growth, market cap); analyst price targets; `.options` expiries
  and `.option_chain(expiry)` for calls/puts; `.calendar` for next earnings date. Risk-free rate
  from `^IRX` (13-week T-bill), fallback constant `0.043`. All network calls wrapped in
  try/except so a missing field degrades gracefully instead of crashing.

- **technicals.py** — pure pandas/numpy, no TA dependency: SMA20/50/200, RSI(14), MACD(12,26,9),
  52-week high/low + position, 20-day realized (historical) volatility annualized, and a derived
  trend label (`uptrend` / `downtrend` / `sideways`).

- **fundamentals.py** — collects the key ratios and produces a transparent 0–100 health score
  from a few weighted buckets (valuation, growth, profitability, balance sheet). Score is a
  signal, not gospel — report states the inputs.

- **options.py** — the quant core:
  - Black-Scholes price + greeks (delta, gamma, theta, vega) using a normal-CDF via `math.erf`
    (avoids the scipy dependency).
  - **IV signal:** compare current ATM implied vol (from the chain) to 20-day realized vol →
    label options as "expensive" / "fair" / "cheap". Honest proxy for IV rank since free data
    lacks a year of historical IV; the report says so.
  - **Liquidity filter:** drop contracts with zero/low open interest, low volume, or wide
    bid/ask spread (% of mid). Beginners must only see tradeable contracts.
  - **Candidate generation** for a moderate profile, expiries ~30–90 days out:
    - Bullish thesis → long call near 0.30–0.45 delta **and** a bull-call (debit) spread.
    - Bearish thesis → long put **and** a bear-put (debit) spread.
    - For each candidate compute: cost (premium × 100), breakeven, max loss, max gain (spreads),
      and the % underlying move to breakeven.
  - Output the top 2–3 ranked candidates with all those numbers.

- **cli.py** — `python -m equity_research.cli AAPL` → builds the compact dict and writes
  `reports/AAPL_data.json`. The thesis direction (bull/bear) at this stage is a *preliminary*
  read from technicals+fundamentals score; the skill can override after web research. Keeps
  greeks/strikes only for the shortlisted candidates, not the whole chain → small JSON.

### Skill orchestration (`skills/equity-research/SKILL.md`)

Steps the skill runs:
1. Validate input (ticker + company name). Run `python -m equity_research.cli TICKER`.
2. Read `reports/TICKER_data.json` (compact — fundamentals score, technicals, IV signal,
   candidate contracts with all numbers).
3. **Web research** via WebSearch / firecrawl: recent news & catalysts, upcoming earnings,
   analyst sentiment, and latest **earnings-call highlights** (management tone, guidance).
   Keep to a handful of high-signal findings.
4. **Synthesize thesis:** reconcile quant direction with web research. State conviction
   (low/med/high) and horizon. If signals conflict, say so and lean conservative.
5. **Pick & explain contracts:** choose top picks from the candidate list. For each, plain-English
   block: *what this trade is, what you pay, most you can lose, breakeven price, what has to
   happen to win.* Because the user is new to options, include a one-line "in simple terms".
6. Write `reports/TICKER-YYYY-MM-DD.md`.

### Report structure (Markdown, concise)

```
# {Company} ({TICKER}) — {date}
## Recommendation         <- one-line verdict + conviction up top
## Thesis                 <- 3-5 bullets, the "why"
## The Options Picks      <- table + per-pick plain-English explanation (cost/max loss/breakeven)
## Supporting Data        <- compact tables: fundamentals score, technicals, IV signal
## Catalysts & Sentiment  <- web/earnings-call findings
## Risks & What Would Change This
```

A short **"New to options? read this"** callout box defines call/put/premium/breakeven/max-loss
in two sentences each, so the report is self-contained for a beginner.

## Out of scope (YAGNI)

- No paid data, no live brokerage/order placement, no backtesting engine.
- No multi-leg exotics (iron condors etc.) — only long calls/puts and vertical debit spreads,
  which are the easiest defined-risk trades to explain to a beginner.
- Not financial advice — report carries a one-line disclaimer.

## Verification

1. **Setup:** `pip install -r requirements.txt` (needs Python 3.10+ on the machine).
2. **Data layer:** `python -m equity_research.cli AAPL` → confirm `reports/AAPL_data.json` exists,
   contains non-null fundamentals, technicals, an IV signal, and ≥1 liquid candidate contract
   with cost/breakeven/max-loss populated.
3. **Edge cases:** run on a ticker with thin options (e.g. a small-cap) → liquidity filter should
   yield few/zero candidates and the JSON should flag that rather than crash. Run on an invalid
   ticker → clean error, no traceback.
4. **Greeks sanity:** spot-check one Black-Scholes delta/price against an online options
   calculator (within rounding).
5. **End-to-end:** invoke the skill with a ticker + company name → confirm a
   `reports/TICKER-YYYY-MM-DD.md` is produced, picks include plain-English cost/max-loss/breakeven,
   the beginner callout is present, and web/earnings findings appear.
6. **Token check:** confirm the skill reads only the compact JSON, not raw chains.

## Open prerequisite

Python must be installed on this Windows machine. First implementation step verifies
`python --version`; if absent, install before proceeding.
