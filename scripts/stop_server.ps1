param(
    [int]$Port = 5000,
    [string]$ApiKey = "egrs-ai-internal-key-2026",
    [string]$ShutdownEndpoint = "http://localhost:$Port/api/v1/health/shutdown"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $ProjectRoot "server.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No PID file found. Server may not be running." -ForegroundColor Yellow
    exit 0
}

$OldPid = Get-Content $PidFile -Raw | ForEach-Object { $_.Trim() }

# Verify the process exists and is a Python process
$Process = Get-Process -Id $OldPid -ErrorAction SilentlyContinue
if (-not $Process) {
    Write-Host "Process $OldPid not found. Removing stale PID file." -ForegroundColor Yellow
    Remove-Item $PidFile -Force
    exit 0
}
if ($Process.ProcessName -ne "python") {
    Write-Host "PID $OldPid is not a Python process (name: $($Process.ProcessName)). Not killing." -ForegroundColor Red
    Remove-Item $PidFile -Force
    exit 1
}

Write-Host "Stopping server (PID: $OldPid)..." -ForegroundColor Cyan

# Step 1: Try graceful shutdown via HTTP endpoint
try {
    Write-Host "Requesting graceful shutdown via $ShutdownEndpoint ..."
    Invoke-WebRequest -Uri $ShutdownEndpoint -Method POST -UseBasicParsing -TimeoutSec 5 -Headers @{"X-API-Key" = $ApiKey} -ErrorAction Stop | Out-Null
    Write-Host "Graceful shutdown request sent. Waiting 5 seconds..." -ForegroundColor Green
    Start-Sleep -Seconds 5
} catch {
    Write-Host "Graceful shutdown endpoint not available (server may already be stopping)." -ForegroundColor Yellow
}

# Step 2: Check if process exited gracefully
$Process.Refresh()
if ($Process.HasExited) {
    Write-Host "Server stopped gracefully." -ForegroundColor Green
    Remove-Item $PidFile -Force
    exit 0
}

# Step 3: Force-kill if still running
Write-Host "Force stopping with taskkill..." -ForegroundColor Yellow
taskkill /PID $OldPid /F 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Server force-stopped." -ForegroundColor Green
} else {
    Write-Host "Warning: taskkill returned exit code $LASTEXITCODE" -ForegroundColor Red
}

Remove-Item $PidFile -Force
Write-Host "Server stopped." -ForegroundColor Green
