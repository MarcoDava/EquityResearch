---
name: equity-research
description: Use when the user gives a stock ticker + company name and wants equity research that ends in a concrete, beginner-friendly recommendation on which options contracts (calls/puts) to buy. Runs the local equity_research Python package for data + quant, adds web/earnings research, and writes a dated Markdown report.
---

# Equity Research → Options Recommendation

Produce a research report that ends in a concrete options-contract recommendation,
explained so a beginner understands the cost, max loss, and breakeven of each pick.

> Educational research only. Not financial advice. Always say this in the report.

## Inputs
- **ticker** (e.g. `AAPL`) — required
- **company name** (e.g. `Apple Inc.`) — required

## Steps

1. **Run the data/quant layer.** From the repo root:
   ```
   python -m equity_research.cli <TICKER> --company "<COMPANY>"
   ```
   This writes `reports/<TICKER>_data.json` (compact analytics + a shortlist of
   liquid options candidates). If it errors (invalid ticker / network), report the
   message and stop.

2. **Read only the JSON** at `reports/<TICKER>_data.json`. Never fetch or read raw
   option chains — the JSON already holds the pre-computed shortlist. Note the
   `preliminary_direction`, `fundamentals.score` (+buckets), `technicals`,
   `options_iv` (with its caveat), `candidates`, `next_earnings`, and any `warnings`.

3. **Web research** (WebSearch / WebFetch). Gather a handful of high-signal items:
   recent news & catalysts, upcoming earnings date confirmation, analyst sentiment /
   price targets, and the latest **earnings-call highlights** (management tone,
   guidance). Cite sources. Keep it tight.

4. **Synthesize the thesis.** Reconcile the quant `preliminary_direction` with the
   web findings. State a direction, a **conviction** (low / medium / high), and a
   **horizon**. If quant and news conflict, say so explicitly and lean conservative.
   If `candidates` is empty (thin options), recommend *no options trade* and explain
   why (illiquid) rather than forcing a pick.

5. **Pick & explain contracts.** Choose the best 1–2 from `candidates`. For each,
   write a plain-English block:
   - **What this trade is** — "a call that profits if the stock rises above X".
   - **What you pay** — `cost` (the premium × 100).
   - **Most you can lose** — `max_loss`.
   - **Breakeven** — the price the stock must reach to start profiting, and the
     `pct_move_to_breakeven`.
   - **What has to happen to win**, and a one-line **"in simple terms"**.
   Prefer the defined-risk spread for a nervous/beginner profile; mention the single
   long leg as the higher-risk / higher-reward alternative.

6. **Write the report** to `reports/<TICKER>-<YYYY-MM-DD>.md` using the structure
   below. Keep it concise.

## Report structure

```
# {Company} ({TICKER}) — {date}
## Recommendation         <- one-line verdict + conviction, up top
## Thesis                 <- 3-5 bullets, the "why"
## The Options Picks      <- table + per-pick plain-English explanation (cost / max loss / breakeven)
## New to options? Read this   <- 2-sentence defs: call, put, premium, breakeven, max loss
## Supporting Data        <- compact tables: fundamentals score+buckets, technicals, IV signal (+caveat)
## Catalysts & Sentiment  <- web / earnings-call findings, with sources
## Risks & What Would Change This
> _Educational research only. Not financial advice._
```

## Guardrails
- Do not invent numbers. Every contract figure comes from the JSON; every news claim
  has a source.
- Surface the `options_iv.caveat` (the IV signal is a realized-vol proxy, not full
  IV-rank history).
- Respect `warnings` from the JSON in the Risks section.
