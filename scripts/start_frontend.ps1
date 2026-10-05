# start_frontend.ps1 — Khởi động React + Vite frontend dev server
# Usage: .\scripts\start_frontend.ps1

$root = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $root "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI CV Skill Gap — Frontend (React)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:5173" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $frontendDir
npm run dev
