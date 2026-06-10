$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "server.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No PID file found. Server may not be running." -ForegroundColor Yellow
    exit 0
}

$OldPid = Get-Content $PidFile -Raw | ForEach-Object { $_.Trim() }
$Process = Get-Process -Id $OldPid -ErrorAction SilentlyContinue

if (-not $Process) {
    Write-Host "Process $OldPid not found. Removing stale PID file." -ForegroundColor Yellow
    Remove-Item $PidFile -Force
    exit 0
}

Write-Host "Stopping server (PID: $OldPid)..." -ForegroundColor Cyan
$Process.CloseMainWindow() | Out-Null
Start-Sleep -Seconds 3

if (-not $Process.HasExited) {
    Write-Host "Force stopping..." -ForegroundColor Yellow
    $Process.Kill()
}

Remove-Item $PidFile -Force
Write-Host "Server stopped." -ForegroundColor Green
