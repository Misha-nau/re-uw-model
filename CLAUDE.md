# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is
A real estate **acquisition underwriting model** for a Singapore office building with a retail
component. Python calculation engine + FastAPI backend + React (Mantine) frontend.
Single user (Misha), runs locally on Windows. No auth.

## How we work (important)
- **`PLAN.md` is the source of truth.** Work proceeds in phases; each ends at a **checkpoint**.
- Do only the phase(s) Misha has asked for, then **stop and report**. Don't start the next phase.
- Phases 1-10 are built. New work = Phase 11 extensions or changes Misha requests; add them
  to `PLAN.md` first.
- At each checkpoint: update phase status and the decision log in `PLAN.md`, and commit.
- Prefer small, reviewable changes. Ask before changing an agreed decision.

## Architecture
```
frontend (React/TS, Vite :5173) --/api proxy--> backend/api (FastAPI :8000) --> backend/re_uw (engine)
                                                         └--> scenarios/*.json
```
- `backend/re_uw/`: **pure engine**. No FastAPI, HTTP or UI imports here. Deterministic
  functions of validated inputs. All business logic lives here and is unit-tested.
- `backend/api/`: thin FastAPI layer: validation, routing, scenario storage. No finance math.
- `frontend/`: React + TypeScript + Mantine + TanStack Query. No finance math either; it
  displays what the API returns. TS types are generated from the OpenAPI spec.

## Layout
```
PLAN.md, CLAUDE.md, README.md, dev.bat / dev.ps1
backend/
  pyproject.toml          deps + pytest/ruff config
  re_uw/inputs.py         Pydantic input model (schema_version 1)
  re_uw/scenarios.py      load/save scenario JSON
  re_uw/sg_tax.py         SG stamp duty (BSD tiers, share duty)
  re_uw/cashflow.py       operating cash flow: rent -> NOI -> CF before debt (Years 1..N+1)
  re_uw/finance.py        irr, npv, equity multiple, annuity
  re_uw/debt.py           loan sizing (LTV/DSCR/debt yield) + debt schedule
  re_uw/returns.py        underwrite(): sources & uses, exit, fees, cash flow streams, metrics
  re_uw/waterfall.py      LP/GP waterfall (pref + IRR-hurdle promote tiers)
  re_uw/sensitivity.py    parameter registry, 2-way grid, tornado
  re_uw/labels.py         metric labels/formats shared by CLI, API and UI
  re_uw/report.py         CLI: print/export a scenario's full underwriting
  api/main.py             FastAPI routes (underwrite, scenarios CRUD, sensitivity, export)
  api/schemas.py          response models + engine->JSON conversion (tables, series)
  api/repository.py       scenario JSON storage (env RE_UW_SCENARIOS_DIR overrides folder)
  api/export.py           Excel export of results (values)
  scripts/                make_sample_scenario.py, gen_input_docs.py, export_openapi.py,
                          make_crosscheck_xlsx.py
  tests/                  pytest (engine, API)
frontend/src/
  main.tsx, App.tsx       providers, app shell, hash-based page switch (#underwriting etc.)
  api/client.ts           typed fetch client; api/schema.ts + openapi.json are GENERATED
  state/ScenarioContext   working inputs, saved snapshot, dirty flag, load/save/saveAs/delete
  hooks/useUnderwrite.ts  debounced recalculation (TanStack Query)
  components/             fields (path-bound inputs), InputsPanel, DataTable, KpiStrip,
                          ScenarioBar, charts (Recharts, reference palette)
  pages/                  UnderwritingPage, ComparePage, SensitivityPage
  lib/                    format.ts (accounting style), paths.ts (getIn/setIn/flatten) + tests
scenarios/                saved scenarios (JSON, one file each)
docs/inputs.md            GENERATED input reference (don't hand-edit)
docs/methodology.md       calculation logic, formula by formula
```

## Commands (Windows PowerShell, from repo root)
The Python venv lives **outside OneDrive** at `%USERPROFILE%\.venvs\re-uw-model`.
```powershell
.\dev.bat                                              # set up (first run) + start backend and frontend
$py = "$env:USERPROFILE\.venvs\re-uw-model\Scripts\python.exe"
cd backend; & $py -m pytest -q                         # backend tests
cd backend; & $py -m ruff check . ; & $py -m ruff format .
cd backend; & $py scripts\make_sample_scenario.py      # regenerate sample scenario JSON
cd backend; & $py scripts\gen_input_docs.py            # regenerate docs/inputs.md
cd backend; & $py -m re_uw.report --csv ..\reports\cashflow.csv  # print + export sample cash flow
cd backend; & $py scripts\make_crosscheck_xlsx.py     # Excel cross-check -> reports\phase4_crosscheck.xlsx
cd backend; & $py scripts\export_openapi.py; cd ..\frontend; npm run gen:api  # after API changes
cd frontend; npm test; npm run typecheck; npm run build
```
- Backend: http://127.0.0.1:8000/api/docs. Frontend: http://127.0.0.1:5173

## Model conventions
- **Rates are decimals** (0.05 = 5%). The UI converts to/from % for display only.
- Rents and component opex are **per sq ft per month** (SG "psf pm"); default currency **SGD**.
- **Annual periods.** Year 0 = acquisition; Years 1..N = hold; sale at end of Year N.
  `exit.noi_basis="forward"` values the exit on Year N+1 NOI, so projections run to N+1.
- Rent growth applies **from Year 2**; Year 1 rent = `rent_psf_pm`.
- Per-year overrides are `dict[int, float]` keyed by year (JSON keys are strings; Pydantic coerces).
- Credit loss and rent-free are applied to rent **after** vacancy.
- SG property tax: `property_tax_rate` × Annual Value; AV from `annual_value_year1` or
  `av_to_gpr_ratio` × GPR **before vacancy** (IRAS taxes vacant space too).
- All figures **ex-GST** (acquisition assumed a transfer of going concern) and **pre-tax**.
- Market-rent leasing costs are steady-state: 1/term of occupied area re-leases each year.
- Formulas live in `docs/methodology.md`; keep it in sync with the engine.
- `underwrite(inputs)` in `re_uw/returns.py` is the engine's single entry point.
- Three cash flow streams: unlevered (property, no fund fees), levered gross of fund fees,
  equity net of fees (what the waterfall distributes).
- Revenue per component has a `method` discriminator. Only `"market"` exists today; a
  `"rent_roll"` model will be added as another member of the `Revenue` union.
- Input models use `extra="forbid"`: unknown keys in scenario JSON are errors (catches typos).

## UI conventions
- Inputs are edited through path-bound field components (`fields.tsx`): `NumField kind="pct"`
  shows % but stores fractions. Nullable inputs clear to `null`.
- Results tables come from the API as generic `Table {columns, rows[{label, values, kind}]}`;
  the UI only formats (accounting style: negatives in brackets, zero as an en dash).
- Charts use the dataviz reference palette in fixed order (`components/charts.tsx`); heatmap is
  diverging blue (better) / red (worse) around the base case. Never put finance math in the UI.

## Changing inputs (checklist)
1. Edit `backend/re_uw/inputs.py` (add a `description=` on the Field; add validators if needed).
2. Update `backend/scripts/make_sample_scenario.py`, then regenerate the sample JSON.
3. Regenerate `docs/inputs.md`.
4. Add or adjust tests in `backend/tests/test_inputs.py`.
5. Breaking change to saved JSON? Bump `SCHEMA_VERSION` and add a migration in `scenarios.py`.
6. Regenerate frontend API types (`export_openapi.py` then `npm run gen:api`), add the field to
   `InputsPanel.tsx`, and (if it should be a sensitivity driver) to `sensitivity.py`.

## Testing rules
- Every engine function gets unit tests with **hand-checkable numbers** (small round inputs).
- Financial outputs: compare with `pytest.approx` (rel 1e-9) and state the hand calc in a comment.
- Run `pytest` and `ruff check` before finishing any phase; `npm run build` if the frontend changed.

## Environment notes
- The repo is inside **OneDrive** (by choice). Never create a venv inside the repo.
  `node_modules` stays in `frontend/` and is git-ignored; pause OneDrive if `npm install` is slow.
- Python 3.13, Node 24 on Misha's machine.
- Git: remote `origin` = https://github.com/Misha-nau/re-uw-model (branch `main`). Commit at each
  checkpoint with a clear message; push when Misha asks.
- Write files with LF line endings (see `.gitattributes`); `.bat`/`.ps1` use CRLF.
