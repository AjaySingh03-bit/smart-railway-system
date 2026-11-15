Set-Location $PSScriptRoot

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   Smart Railway Seat Allocation Simulator (College)" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$pyCandidates = @(
    "D:\Downloads\railway allotment\.venv\Scripts\python.exe",
    "$PSScriptRoot\..\..\railway allotment\.venv\Scripts\python.exe",
    "$PSScriptRoot\..\railway allotment\.venv\Scripts\python.exe",
    "$PSScriptRoot\.venv\Scripts\python.exe",
    "python"
)

$pyExe = $null
foreach ($c in $pyCandidates) {
    if (Test-Path $c -ErrorAction SilentlyContinue) {
        $pyExe = $c
        break
    }
}

if (-not $pyExe) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) { $pyExe = "python" }
}

if (-not $pyExe) {
    Write-Host "[ERROR] Could not find Python. Please ensure Python is installed." -ForegroundColor Red
    Pause
    exit 1
}

Write-Host "[OK] Using Python: $pyExe" -ForegroundColor Green
Write-Host "[INFO] Opening browser at http://127.0.0.1:5000 ..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:5000"

& $pyExe app.py
