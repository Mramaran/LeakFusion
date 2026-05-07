# Dev launcher: start FastAPI + Vite in two new PowerShell windows.
# Usage:  scripts\dev.ps1
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repo
try {
    Write-Host "Repo root: $repo"

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$repo'; python -m uvicorn leakfusion.api.main:app --reload --port 8000"
    )

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$repo\web'; npm run dev"
    )

    Write-Host ""
    Write-Host "API: http://127.0.0.1:8000/api/health"
    Write-Host "Web: http://localhost:5173"
}
finally {
    Pop-Location
}
