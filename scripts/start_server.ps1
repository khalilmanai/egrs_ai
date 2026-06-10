param(
    [int]$Port = 5000,
    [string]$Host = "0.0.0.0",
    [string]$LogFile = "server.log"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$RunPy = Join-Path $ProjectRoot "run.py"
$PidFile = Join-Path $ProjectRoot "server.pid"
$LogPath = Join-Path $ProjectRoot $LogFile

Write-Host "=== EGRS AI Server Launcher ===" -ForegroundColor Cyan
Write-Host "Port: $Port"
Write-Host "Host: $Host"
Write-Host "Project: $ProjectRoot"
Write-Host ""

# Check if already running
if (Test-Path $PidFile) {
    $OldPid = Get-Content $PidFile -Raw | ForEach-Object { $_.Trim() }
    $Running = Get-Process -Id $OldPid -ErrorAction SilentlyContinue
    if ($Running -and $Running.ProcessName -eq "python") {
        Write-Host "Server already running (PID: $OldPid)" -ForegroundColor Yellow
        exit 0
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Check if port is in use
$PortInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Host "Port $Port already in use. Server may already be running." -ForegroundColor Yellow
    $Existing = Get-Process -Id $PortInUse.OwningProcess -ErrorAction SilentlyContinue
    if ($Existing) {
        Write-Host "Process: $($Existing.ProcessName) (PID: $($Existing.Id))"
    }
    exit 0
}

# Verify Python environment
if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Virtual env python not found at $VenvPython" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $RunPy)) {
    Write-Host "ERROR: run.py not found at $RunPy" -ForegroundColor Red
    exit 1
}

Write-Host "Starting server..."
$env:PYTHONPATH = $ProjectRoot

$process = Start-Process -NoNewWindow -FilePath $VenvPython -ArgumentList @(
    "-u", $RunPy
) -PassThru -RedirectStandardOutput $LogPath -RedirectStandardError "${LogPath}.err"

$process.Id | Out-File -FilePath $PidFile -Encoding utf8
Write-Host "Server starting (PID: $($process.Id))..." -ForegroundColor Green

# Wait for server to be ready (poll /health)
$Timeout = 30
$Elapsed = 0
$HealthUrl = "http://localhost:$Port/api/v1/health"

Write-Host "Waiting for server to be ready..."
while ($Elapsed -lt $Timeout) {
    Start-Sleep -Seconds 1
    $Elapsed++
    try {
        $response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Server is ready! ($Elapsed seconds)" -ForegroundColor Green
            Write-Host "URL: http://localhost:$Port"
            Write-Host "Docs: http://localhost:$Port/docs"
            exit 0
        }
    } catch {
        # Still starting
    }
}

Write-Host "Warning: Server started but health check timed out after ${Timeout}s" -ForegroundColor Yellow
Write-Host "Check logs at: $LogPath"
exit 1
