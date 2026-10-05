# start_backend.ps1 — Khởi động FastAPI backend server
# Usage: .\scripts\start_backend.ps1

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI CV Skill Gap — Backend (FastAPI)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  URL:  http://localhost:8000" -ForegroundColor Green
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $backendDir

# Kích hoạt venv nếu có
$venvPython = ".\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m uvicorn app.main:app --reload --port 8000
} else {
    python -m uvicorn app.main:app --reload --port 8000
}
