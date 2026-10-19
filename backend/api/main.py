"""FastAPI application. Thin layer over the re_uw engine: no finance math here.

Run (from backend/):  uvicorn api.main:app --reload --port 8000
Docs:                 http://127.0.0.1:8000/api/docs
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from re_uw import __version__
from re_uw.inputs import UnderwritingInputs
from re_uw.returns import underwrite
from re_uw.sensitivity import available_parameters, base_value, get_param, grid, tornado

from .export import result_to_xlsx
from .repository import ScenarioExists, ScenarioNotFound, ScenarioRepository
from .schemas import (
    DuplicateRequest,
    MetricInfo,
    ParameterInfo,
    ScenarioCreate,
    ScenarioSummary,
    SensitivityRequest,
    SensitivityResponse,
    TornadoBarOut,
    TornadoRequest,
    TornadoResponse,
    UnderwriteResponse,
    metric_catalog,
    to_response,
)

app = FastAPI(
    title="RE Underwriting Model API",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    separate_input_output_schemas=False,
)

# The Vite dev server proxies /api to this app; CORS is only a fallback.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_repo = ScenarioRepository()


def get_repo() -> ScenarioRepository:
    return _repo


Repo = Annotated[ScenarioRepository, Depends(get_repo)]


class Health(BaseModel):
    status: str
    version: str


@app.get("/api/health", response_model=Health, tags=["system"])
def health() -> Health:
    return Health(status="ok", version=__version__)


# --- calculation --------------------------------------------------------------------
@app.post("/api/underwrite", response_model=UnderwriteResponse, tags=["model"])
def underwrite_endpoint(inputs: UnderwritingInputs) -> UnderwriteResponse:
    return to_response(underwrite(inputs))


@app.get("/api/metrics", response_model=list[MetricInfo], tags=["model"])
def metrics() -> list[MetricInfo]:
    return metric_catalog()


@app.post("/api/export", tags=["model"],
          responses={200: {"content": {"application/vnd.openxmlformats-officedocument."
                                       "spreadsheetml.sheet": {}}}})
def export(inputs: UnderwritingInputs) -> Response:
    data = result_to_xlsx(underwrite(inputs))
    name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in inputs.scenario.name)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name.strip()}.xlsx"'},
    )


# --- scenarios ------------------------------------------------------------------------
@app.get("/api/scenarios", response_model=list[ScenarioSummary], tags=["scenarios"])
def list_scenarios(repo: Repo) -> list[dict]:
    return repo.list()


@app.get("/api/scenarios/{scenario_id}", response_model=UnderwritingInputs, tags=["scenarios"])
def get_scenario(scenario_id: str, repo: Repo) -> UnderwritingInputs:
    try:
        return repo.get(scenario_id)
    except ScenarioNotFound as e:
        raise HTTPException(404, f"scenario '{scenario_id}' not found") from e


@app.post("/api/scenarios", response_model=ScenarioSummary, status_code=201, tags=["scenarios"])
def create_scenario(body: ScenarioCreate, repo: Repo) -> dict:
    try:
        sid = repo.create(body.inputs, body.id)
    except ScenarioExists as e:
        raise HTTPException(409, f"scenario '{body.id}' already exists") from e
    except ScenarioNotFound as e:
        raise HTTPException(422, "invalid scenario id (use a-z, 0-9, _ and -)") from e
    return _summary(repo, sid)


@app.put("/api/scenarios/{scenario_id}", response_model=ScenarioSummary, tags=["scenarios"])
def save_scenario(scenario_id: str, inputs: UnderwritingInputs, repo: Repo) -> dict:
    try:
        repo.save(scenario_id, inputs)
    except ScenarioNotFound as e:
        raise HTTPException(404, f"scenario '{scenario_id}' not found") from e
    return _summary(repo, scenario_id)


@app.post("/api/scenarios/{scenario_id}/duplicate", response_model=ScenarioSummary,
          status_code=201, tags=["scenarios"])
def duplicate_scenario(scenario_id: str, body: DuplicateRequest, repo: Repo) -> dict:
    src = get_scenario(scenario_id, repo)
    copy = src.model_copy(update={"scenario": src.scenario.model_copy(update={"name": body.name})})
    return _summary(repo, repo.create(copy))


@app.delete("/api/scenarios/{scenario_id}", status_code=204, tags=["scenarios"])
def delete_scenario(scenario_id: str, repo: Repo) -> Response:
    try:
        repo.delete(scenario_id)
    except ScenarioNotFound as e:
        raise HTTPException(404, f"scenario '{scenario_id}' not found") from e
    return Response(status_code=204)


def _summary(repo: ScenarioRepository, sid: str) -> dict:
    return next(s for s in repo.list() if s["id"] == sid)


# --- sensitivity ------------------------------------------------------------------------
def _param_info(inputs: UnderwritingInputs, key: str) -> ParameterInfo:
    p = get_param(inputs, key)
    b = base_value(inputs, p)
    return ParameterInfo(key=p.key, label=p.label, unit=p.unit, base=b,
                         step=b * p.shock if p.relative else p.shock)


@app.post("/api/sensitivity/parameters", response_model=list[ParameterInfo],
          tags=["sensitivity"])
def parameters(inputs: UnderwritingInputs) -> list[ParameterInfo]:
    return [_param_info(inputs, p.key) for p in available_parameters(inputs)]


@app.post("/api/sensitivity", response_model=SensitivityResponse, tags=["sensitivity"])
def sensitivity(req: SensitivityRequest) -> SensitivityResponse:
    try:
        g = grid(req.inputs, req.x, req.y, req.metric, req.steps, req.x_values, req.y_values)
    except KeyError as e:
        raise HTTPException(422, str(e)) from e
    return SensitivityResponse(
        x=_param_info(req.inputs, req.x), y=_param_info(req.inputs, req.y), metric=req.metric,
        x_values=g.x_values, y_values=g.y_values, values=g.values, base=g.base,
    )


@app.post("/api/tornado", response_model=TornadoResponse, tags=["sensitivity"])
def tornado_endpoint(req: TornadoRequest) -> TornadoResponse:
    base, bars = tornado(req.inputs, req.metric, req.keys)
    return TornadoResponse(
        metric=req.metric, base=base,
        bars=[TornadoBarOut(key=b.param.key, label=b.param.label, unit=b.param.unit,
                            low_input=b.low_input, high_input=b.high_input,
                            low=b.low, high=b.high) for b in bars],
    )
