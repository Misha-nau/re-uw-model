# Start the RE Underwriting Model for local development.
# - Creates the Python venv OUTSIDE OneDrive on first run
# - Installs/updates backend and frontend dependencies when needed
# - Starts FastAPI (8000) and Vite (5173) in separate windows, then opens the browser

$ErrorActionPreference = "Stop"
$Root     = $PSScriptRoot
$Backend  = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Venv     = Join-Path $env:USERPROFILE ".venvs\re-uw-model"
$Py       = Join-Path $Venv "Scripts\python.exe"

# --- Python venv -------------------------------------------------------------
if (-not (Test-Path $Py)) {
    Write-Host "Creating Python venv at $Venv ..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force (Split-Path $Venv) | Out-Null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.13 -m venv $Venv
    } else {
        python -m venv $Venv
    }
    if (-not (Test-Path $Py)) { throw "Failed to create venv. Is Python 3.13 installed?" }
}

# Re-install backend when pyproject.toml is newer than the last install.
$Stamp   = Join-Path $Venv ".re-uw-installed"
$PyProj  = Join-Path $Backend "pyproject.toml"
if (-not (Test-Path $Stamp) -or ((Get-Item $PyProj).LastWriteTime -gt (Get-Item $Stamp).LastWriteTime)) {
    Write-Host "Installing backend dependencies ..." -ForegroundColor Cyan
    & $Py -m pip install --upgrade pip --quiet
    & $Py -m pip install -e "$Backend[dev]"
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    New-Item -ItemType File -Force $Stamp | Out-Null
}

# --- Frontend packages ---------------------------------------------------------
$NodeModules = Join-Path $Frontend "node_modules"
$Lock        = Join-Path $Frontend "package-lock.json"
$LockStamp   = Join-Path $NodeModules ".package-lock.json"
if (-not (Test-Path $NodeModules) -or ((Test-Path $LockStamp) -and ((Get-Item $Lock).LastWriteTime -gt (Get-Item $LockStamp).LastWriteTime))) {
    Write-Host "Installing frontend packages (npm install) ..." -ForegroundColor Cyan
    Push-Location $Frontend
    try { npm install --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw "npm install failed" } }
    finally { Pop-Location }
}

# --- Start servers -------------------------------------------------------------
Write-Host "Starting API on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'RE UW - API'; Set-Location -LiteralPath '$Backend'; & '$Py' -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"
)

Write-Host "Starting UI on http://127.0.0.1:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'RE UW - UI'; Set-Location -LiteralPath '$Frontend'; npm run dev"
)

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:5173"
Write-Host "Running. Close the 'RE UW - API' and 'RE UW - UI' windows to stop." -ForegroundColor Green
