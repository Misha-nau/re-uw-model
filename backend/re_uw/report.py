"""Print or export the operating cash flow for a scenario.

Usage (from backend/):
    python -m re_uw.report                                   # sample scenario
    python -m re_uw.report ../scenarios/other.json
    python -m re_uw.report --csv ../out/cashflow.csv         # also write CSV (full precision)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .cashflow import operating_cash_flow
from .scenarios import SCENARIOS_DIR, load_scenario
from .sg_tax import acquisition_stamp_duty

DEFAULT = SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("scenario", nargs="?", default=str(DEFAULT))
    ap.add_argument("--csv", help="write property-level cash flow (full precision) to this CSV")
    args = ap.parse_args(argv)

    inp = load_scenario(args.scenario)
    ocf = operating_cash_flow(inp)
    cur = inp.analysis.currency
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print(f"\n{inp.scenario.name}  |  {inp.property.name}  |  {cur} millions\n")
    print(ocf.table(scale=1e6).round(2).to_string())
    for c in inp.components:
        print(f"\n-- {c.name} ({c.nla_sqft:,.0f} sq ft) --")
        print(ocf.component_table(c.name, scale=1e6).round(2).to_string())

    price = inp.acquisition.purchase_price
    noi1 = ocf.noi[0]
    duty = acquisition_stamp_duty(inp.acquisition)
    facts = [
        ("NOI", f"{cur} {noi1 / 1e6:,.2f}m ({noi1 / inp.total_nla_sqft:,.2f} psf pa)"),
        ("Entry cap rate (NOI / price)", f"{noi1 / price:.2%}"),
        ("NOI margin (NOI / EGI)", f"{noi1 / ocf['egi'][0]:.1%}"),
        ("Price psf", f"{cur} {inp.price_psf:,.0f}"),
        (f"Stamp duty ({inp.acquisition.deal_structure} deal)", f"{cur} {duty / 1e6:,.2f}m"),
    ]
    print("\nKey Year 1 figures")
    for label, value in facts:
        print(f"  {label:<30} {value}")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        ocf.table().to_csv(out)
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
