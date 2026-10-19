"""Sensitivity analysis (Phase 10 engine): parameter registry, 2D grid and tornado.

A parameter is a path into the inputs (e.g. ``exit.exit_cap_rate`` or
``components.0.revenue.rent_psf_pm``). Changed inputs are re-validated, so a value that
breaks a rule (e.g. vacancy > 100%) yields ``None`` for that cell instead of an error.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from .inputs import UnderwritingInputs
from .returns import underwrite

Unit = Literal["pct", "money", "psf", "ratio"]


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    path: tuple[str | int, ...]
    unit: Unit
    shock: float  # one step / tornado move
    relative: bool  # shock is a fraction of the base value


def available_parameters(inp: UnderwritingInputs) -> list[Parameter]:
    params = [
        Parameter("price", "Purchase price", ("acquisition", "purchase_price"), "money", 0.05,
                  True),
        Parameter("exit_cap", "Exit cap rate", ("exit", "exit_cap_rate"), "pct", 0.0025, False),
        Parameter("base_rate", "Interest base rate", ("debt", "base_rate"), "pct", 0.005, False),
        Parameter("ltv", "Target LTV", ("debt", "target_ltv"), "pct", 0.05, False),
        Parameter("am_fee", "Asset mgmt fee", ("fees", "asset_mgmt_fee_pct"), "pct", 0.0025,
                  False),
        Parameter("selling_cost", "Selling costs", ("exit", "selling_cost_pct"), "pct", 0.005,
                  False),
    ]
    for i, c in enumerate(inp.components):
        n = c.name
        params += [
            Parameter(f"c{i}_rent", f"{n}: rent psf pm",
                      ("components", i, "revenue", "rent_psf_pm"), "psf", 0.05, True),
            Parameter(f"c{i}_growth", f"{n}: rent growth",
                      ("components", i, "revenue", "rent_growth"), "pct", 0.01, False),
            Parameter(f"c{i}_vacancy", f"{n}: vacancy",
                      ("components", i, "revenue", "vacancy"), "pct", 0.02, False),
            Parameter(f"c{i}_opex", f"{n}: opex psf pm", ("components", i, "opex_psf_pm"),
                      "psf", 0.10, True),
        ]
    return params


def get_param(inp: UnderwritingInputs, key: str) -> Parameter:
    for p in available_parameters(inp):
        if p.key == key:
            return p
    raise KeyError(f"unknown sensitivity parameter '{key}'")


def _get(d: Any, path: tuple[str | int, ...]) -> Any:
    for k in path:
        d = d[k]
    return d


def base_value(inp: UnderwritingInputs, p: Parameter) -> float:
    return float(_get(inp.model_dump(), p.path))


def with_value(inp: UnderwritingInputs, changes: dict[tuple[str | int, ...], float]
               ) -> UnderwritingInputs:
    d = copy.deepcopy(inp.model_dump())
    for path, v in changes.items():
        parent = _get(d, path[:-1])
        parent[path[-1]] = v
    return UnderwritingInputs.model_validate(d)


def step_values(inp: UnderwritingInputs, p: Parameter, steps: int) -> list[float]:
    b = base_value(inp, p)
    step = b * p.shock if p.relative else p.shock
    return [b + k * step for k in range(-steps, steps + 1)]


def _metric(inp: UnderwritingInputs, changes: dict, metric: str) -> float | None:
    try:
        return underwrite(with_value(inp, changes)).metrics.get(metric)
    except (ValidationError, ValueError, ZeroDivisionError, FloatingPointError):
        return None


@dataclass
class Grid:
    x: Parameter
    y: Parameter
    x_values: list[float]
    y_values: list[float]
    metric: str
    values: list[list[float | None]]  # [y][x]
    base: float | None


def grid(inp: UnderwritingInputs, x_key: str, y_key: str, metric: str, steps: int = 2,
         x_values: list[float] | None = None, y_values: list[float] | None = None) -> Grid:
    px, py = get_param(inp, x_key), get_param(inp, y_key)
    xs = x_values or step_values(inp, px, steps)
    ys = y_values or step_values(inp, py, steps)
    vals = [[_metric(inp, {px.path: xv, py.path: yv}, metric) for xv in xs] for yv in ys]
    return Grid(px, py, xs, ys, metric, vals, underwrite(inp).metrics.get(metric))


@dataclass
class TornadoBar:
    param: Parameter
    low_input: float
    high_input: float
    low: float | None
    high: float | None

    @property
    def swing(self) -> float:
        if self.low is None or self.high is None:
            return 0.0
        return abs(self.high - self.low)


def tornado(inp: UnderwritingInputs, metric: str, keys: list[str] | None = None
            ) -> tuple[float | None, list[TornadoBar]]:
    params = [p for p in available_parameters(inp) if keys is None or p.key in keys]
    bars = []
    for p in params:
        lo, _, hi = step_values(inp, p, 1)
        bars.append(TornadoBar(p, lo, hi, _metric(inp, {p.path: lo}, metric),
                               _metric(inp, {p.path: hi}, metric)))
    bars.sort(key=lambda b: b.swing, reverse=True)
    return underwrite(inp).metrics.get(metric), bars
