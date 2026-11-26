# Start the Tingathe API, freeing port 8000 first if a stale server holds it.
$ErrorActionPreference = "Stop"
$port = if ($env:PORT) { [int]$env:PORT } else { 8000 }

$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    $owner = $listener.OwningProcess
    try {
        $name = (Get-Process -Id $owner -ErrorAction Stop).ProcessName
    } catch {
        $name = "unknown"
    }
    Write-Host "Port $port is held by $name (PID $owner). Stopping it..."
    Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
}
if ($listeners) { Start-Sleep -Milliseconds 500 }

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $python. Run: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Push-Location $PSScriptRoot
try {
    & $python -m uvicorn main:app --reload --port $port
} finally {
    Pop-Location
}
