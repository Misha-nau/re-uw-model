"""Print or export a scenario's underwriting: operating cash flow, debt, returns.

Usage (from backend/):
    python -m re_uw.report                                   # sample scenario
    python -m re_uw.report ../scenarios/other.json
    python -m re_uw.report --csv ../reports/cashflow.csv     # also write CSVs (full precision)
    python -m re_uw.report --components                      # include per-component tables
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .labels import METRICS
from .returns import underwrite
from .scenarios import SCENARIOS_DIR, load_scenario

DEFAULT = SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"

LABELS = {k: v[0] for k, v in METRICS.items()}
FORMATS = {k: v[1] for k, v in METRICS.items()}


def _fmt(key: str, v: float | None, cur: str) -> str:
    if v is None:
        return "n/a"
    fmt = FORMATS[key]
    if fmt == "pct":
        return f"{v:.2%}"
    if fmt == "ratio":
        return f"{v:.2f}x"
    if fmt == "psf":
        return f"{cur} {v:,.0f}"
    return f"{cur} {v / 1e6:,.2f}m"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("scenario", nargs="?", default=str(DEFAULT))
    ap.add_argument("--csv", help="write cash flow CSVs; this path is the operating CF file")
    ap.add_argument("--components", action="store_true", help="print per-component tables")
    args = ap.parse_args(argv)

    inp = load_scenario(args.scenario)
    res = underwrite(inp)
    ocf = res.operating
    cur = inp.analysis.currency
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print(f"\n{inp.scenario.name}  |  {inp.property.name}  |  {cur} millions")
    print("\n== Operating cash flow ==")
    print(ocf.table(scale=1e6).round(2).to_string())
    if args.components:
        for c in inp.components:
            print(f"\n-- {c.name} ({c.nla_sqft:,.0f} sq ft) --")
            print(ocf.component_table(c.name, scale=1e6).round(2).to_string())

    print("\n== Sources & uses ==")
    su = res.sources_uses.table()
    su["amount"] = (su["amount"] / 1e6).round(2)
    su["% of total"] = (su["% of total"] * 100).round(1)
    print(su.to_string(index=False))
    s = res.sizing
    print(f"\nLoan sizing: binding = {s.binding}; LTV amount {s.ltv_amount / 1e6:,.1f}m"
          + (f"; DSCR amount {s.dscr_amount / 1e6:,.1f}m" if s.dscr_amount is not None else "")
          + (f"; debt-yield amount {s.debt_yield_amount / 1e6:,.1f}m"
             if s.debt_yield_amount is not None else ""))

    print("\n== Debt schedule ==")
    print(res.debt_table(scale=1e6).round(2).to_string())

    print("\n== Cash flows (Years 0..N) ==")
    print(res.cash_flow_table(scale=1e6).round(2).to_string())

    print("\n== Equity waterfall ==")
    print(res.waterfall.table(inp.analysis.start_year, scale=1e6).round(2).to_string())

    print("\n== Returns and metrics ==")
    for key, label in LABELS.items():
        print(f"  {label:<40} {_fmt(key, res.metrics[key], cur)}")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        ocf.table().to_csv(out)
        res.cash_flow_table().to_csv(out.with_name(out.stem + "_returns.csv"))
        print(f"\nwrote {out} and {out.with_name(out.stem + '_returns.csv')}")


if __name__ == "__main__":
    main()
