"""CLI entry point: fetch + analyze a ticker, write the compact JSON.

    python -m equity_research.cli AAPL --company "Apple Inc."

Writes ``reports/<TICKER>_data.json``. Invalid tickers / network problems print a
clean one-line error and exit non-zero -- no traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report_data import build_report_data

REPORTS_DIR = Path("reports")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="equity_research.cli",
                                     description="Fetch + analyze a ticker; emit compact JSON.")
    parser.add_argument("ticker", help="stock ticker, e.g. AAPL")
    parser.add_argument("--company", default=None, help='company name, e.g. "Apple Inc."')
    parser.add_argument("--out-dir", default=str(REPORTS_DIR), help="output directory")
    args = parser.parse_args(argv)

    try:
        report = build_report_data(args.ticker, args.company)
    except ValueError as e:
        print(f"error: {args.ticker.upper()}: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # network / yfinance failure
        print(f"error: failed to fetch data for {args.ticker.upper()}: {e}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report['ticker']}_data.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    n = len(report.get("candidates", []))
    print(f"wrote {out_path}  (direction={report['preliminary_direction']}, "
          f"candidates={n}, spot={report['spot']})")
    if report.get("warnings"):
        for w in report["warnings"]:
            print(f"  warning: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
