# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is
A real estate **acquisition underwriting model** for a Singapore office building with a retail
component. Python calculation engine + FastAPI backend + React (Mantine) frontend.
Single user (Misha), runs locally on Windows. No auth.

## How we work (important)
- **`PLAN.md` is the source of truth.** Work proceeds in phases; each ends at a **checkpoint**.
- Do only the phase(s) Misha has asked for, then **stop and report**. Don't start the next phase.
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
  displays what the API returns. (From Phase 6, TS types are generated from OpenAPI.)

## Layout
```
PLAN.md, CLAUDE.md, README.md, dev.bat / dev.ps1
backend/
  pyproject.toml          deps + pytest/ruff config
  re_uw/inputs.py         Pydantic input model (schema_version 1)
  re_uw/scenarios.py      load/save scenario JSON
  re_uw/sg_tax.py         SG stamp duty (BSD tiers, share duty)
  api/main.py             FastAPI app (/api/health, docs at /api/docs)
  scripts/                make_sample_scenario.py, gen_input_docs.py
  tests/                  pytest
frontend/
  src/main.tsx, App.tsx, theme.ts, api/client.ts
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
cd frontend; npm run typecheck; npm run build
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
- Revenue per component has a `method` discriminator. Only `"market"` exists today; a
  `"rent_roll"` model will be added as another member of the `Revenue` union.
- Input models use `extra="forbid"`: unknown keys in scenario JSON are errors (catches typos).

## Changing inputs (checklist)
1. Edit `backend/re_uw/inputs.py` (add a `description=` on the Field; add validators if needed).
2. Update `backend/scripts/make_sample_scenario.py`, then regenerate the sample JSON.
3. Regenerate `docs/inputs.md`.
4. Add or adjust tests in `backend/tests/test_inputs.py`.
5. Breaking change to saved JSON? Bump `SCHEMA_VERSION` and add a migration in `scenarios.py`.
6. (From Phase 6) regenerate frontend API types.

## Testing rules
- Every engine function gets unit tests with **hand-checkable numbers** (small round inputs).
- Financial outputs: compare with `pytest.approx` (rel 1e-9) and state the hand calc in a comment.
- Run `pytest` and `ruff check` before finishing any phase; `npm run build` if the frontend changed.

## Environment notes
- The repo is inside **OneDrive** (by choice). Never create a venv inside the repo.
  `node_modules` stays in `frontend/` and is git-ignored; pause OneDrive if `npm install` is slow.
- Python 3.13, Node 24 on Misha's machine.
- Git: **local repo only, no remote.** Commit at each checkpoint with a clear message.
- Write files with LF line endings (see `.gitattributes`); `.bat`/`.ps1` use CRLF.
