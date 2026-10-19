"""API response/request models and conversion from engine results."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from re_uw.inputs import UnderwritingInputs
from re_uw.labels import METRICS
from re_uw.returns import UnderwritingResult

RowKind = Literal["money", "pct", "ratio", "psf", "num"]

EMPHASIS = {
    "Base rent collected", "Effective gross income", "Total operating expenses",
    "Net operating income", "Cash flow before debt", "Component revenue", "Unlevered cash flow",
    "Levered cash flow (gross of fund fees)", "Equity cash flow (net of fees)",
    "Closing balance", "LP net cash flow", "GP net cash flow",
}


class TableRow(BaseModel):
    label: str
    values: list[float | None]
    kind: RowKind = "money"
    emphasis: bool = False


class Table(BaseModel):
    columns: list[str]
    rows: list[TableRow]


class NamedTable(BaseModel):
    name: str
    table: Table


class SourceUseRow(BaseModel):
    side: Literal["Uses", "Sources"]
    item: str
    amount: float
    share: float


class Sizing(BaseModel):
    amount: float
    binding: str
    ltv_amount: float
    dscr_amount: float | None
    debt_yield_amount: float | None


class MetricInfo(BaseModel):
    key: str
    label: str
    format: Literal["money", "pct", "ratio", "psf"]
    group: str


class Series(BaseModel):
    years: list[str]  # Y0..YN labels
    noi: list[float]  # Y1..YN
    cf_before_debt: list[float]
    unlevered_cf: list[float]  # Y0..YN
    equity_cf: list[float]
    lp_cf: list[float]
    gp_cf: list[float]


class UnderwriteResponse(BaseModel):
    currency: str
    metrics: dict[str, float | None]
    sizing: Sizing
    sources_uses: list[SourceUseRow]
    operating: Table
    components: list[NamedTable]
    debt: Table
    cash_flows: Table
    waterfall: Table
    series: Series


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    updated_at: str


class ScenarioCreate(BaseModel):
    inputs: UnderwritingInputs
    id: str | None = Field(None, description="Optional id; derived from the name if omitted")


class DuplicateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ParameterInfo(BaseModel):
    key: str
    label: str
    unit: Literal["pct", "money", "psf", "ratio"]
    base: float
    step: float


class SensitivityRequest(BaseModel):
    inputs: UnderwritingInputs
    x: str
    y: str
    metric: str = "levered_irr"
    steps: int = Field(2, ge=1, le=5, description="Steps each side of the base value")
    x_values: list[float] | None = None
    y_values: list[float] | None = None


class SensitivityResponse(BaseModel):
    x: ParameterInfo
    y: ParameterInfo
    metric: str
    x_values: list[float]
    y_values: list[float]
    values: list[list[float | None]]  # [y][x]
    base: float | None


class TornadoRequest(BaseModel):
    inputs: UnderwritingInputs
    metric: str = "levered_irr"
    keys: list[str] | None = None


class TornadoBarOut(BaseModel):
    key: str
    label: str
    unit: str
    low_input: float
    high_input: float
    low: float | None
    high: float | None


class TornadoResponse(BaseModel):
    metric: str
    base: float | None
    bars: list[TornadoBarOut]


# ---------------------------------------------------------------------------
def _clean(v: float) -> float | None:
    v = float(v)
    return None if math.isnan(v) or math.isinf(v) else v


def df_to_table(df: pd.DataFrame) -> Table:
    rows = []
    for label, values in df.iterrows():
        label = str(label)
        vals = [_clean(v) for v in values.to_numpy(dtype=float)]
        kind: RowKind = "money"
        if label.endswith(" %"):
            label = label[:-2]
            vals = [None if v is None else v / 100 for v in vals]
            kind = "pct"
        elif label.startswith(("DSCR", "ICR")):
            kind = "ratio"
        elif "psf" in label:
            kind = "psf"
        rows.append(TableRow(label=label, values=vals, kind=kind, emphasis=label in EMPHASIS))
    return Table(columns=[str(c) for c in df.columns], rows=rows)


def metric_catalog() -> list[MetricInfo]:
    return [MetricInfo(key=k, label=v[0], format=v[1], group=v[2]) for k, v in METRICS.items()]


def to_response(res: UnderwritingResult) -> UnderwriteResponse:
    inp = res.inputs
    n = inp.analysis.hold_period_years
    start = inp.analysis.start_year
    su = res.sources_uses.table()

    def lst(a: np.ndarray) -> list[float]:
        return [float(x) for x in a]

    return UnderwriteResponse(
        currency=inp.analysis.currency,
        metrics={k: (None if v is None else _clean(v)) for k, v in res.metrics.items()},
        sizing=Sizing(**res.sizing.__dict__),
        sources_uses=[SourceUseRow(side=side, item=item, amount=amount, share=share)
                      for side, item, amount, share in su.itertuples(index=False)
                      if not item.startswith("Total")],
        operating=df_to_table(res.operating.table()),
        components=[
            NamedTable(name=c.name, table=df_to_table(res.operating.component_table(c.name)))
            for c in inp.components
        ],
        debt=df_to_table(res.debt_table()),
        cash_flows=df_to_table(res.cash_flow_table()),
        waterfall=df_to_table(res.waterfall.table(start)),
        series=Series(
            years=[f"Y{t} {start + t - 1}" for t in range(n + 1)],
            noi=lst(res.operating.noi[:n]),
            cf_before_debt=lst(res.operating.cf_before_debt[:n]),
            unlevered_cf=lst(res.unlevered_cf),
            equity_cf=lst(res.levered_net_cf),
            lp_cf=lst(res.waterfall.lp_cf),
            gp_cf=lst(res.waterfall.gp_cf),
        ),
    )
