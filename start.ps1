# AI Translate Agent - Startup Script (uv + PowerShell)
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
$Root        = $PSScriptRoot
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvDir     = Join-Path $BackendDir ".venv"

function Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Ok    { param($msg) Write-Host "[ OK ]  $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Fatal { param($msg) Write-Host "[FAIL]  $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  AI Translate Agent" -ForegroundColor Magenta
Write-Host ""

# 1. Check uv
Info "Checking uv..."
$uvCheck = uv --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Fatal "uv not found. Install: irm https://astral.sh/uv/install.ps1 | iex"
}
Ok "Found $uvCheck"

# 2. Check Node.js
Info "Checking Node.js..."
$nodeCheck = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Fatal "node not found. Install from https://nodejs.org"
}
Ok "Found Node.js $nodeCheck"

# 3. Check .env
$EnvFile = Join-Path $Root ".env"
if (-not (Test-Path $EnvFile)) {
    Warn ".env not found, creating template..."
    Set-Content $EnvFile -Encoding ASCII -Value "OPENAI_API_KEY=your_api_key_here`nOPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`nDEFAULT_MODEL=qwen-plus"
    Warn "Please edit .env and set a real OPENAI_API_KEY, then re-run."
    exit 0
}
$envContent = Get-Content $EnvFile -Raw
if ($envContent -match "your_api_key_here") {
    Fatal "Please set a real OPENAI_API_KEY in .env first."
}
Ok ".env is ready"

# 4. uv sync (create/update .venv)
$uvicornExePath = Join-Path $VenvDir "Scripts\uvicorn.exe"
if (Test-Path $uvicornExePath) {
    Ok "Backend venv already exists, skipping uv sync"
} else {
    Info "Syncing backend Python venv with uv..."
    Push-Location $BackendDir
    uv sync --quiet
    $syncExit = $LASTEXITCODE
    Pop-Location
    if ($syncExit -ne 0) {
        Fatal "uv sync failed. Check pyproject.toml or network."
    }
}
Ok "Backend venv ready: $VenvDir"

# 5. npm install
$NodeModulesDir = Join-Path $FrontendDir "node_modules"
Info "Checking frontend dependencies..."
if (-not (Test-Path $NodeModulesDir)) {
    Info "Running npm install (first time)..."
    Push-Location $FrontendDir
    npm install --silent
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) { Fatal "npm install failed." }
    Ok "Frontend dependencies installed"
} else {
    Ok "node_modules already present"
}

# 6. Stop old backend / frontend processes
Info "Stopping old processes..."
$stoppedAny = $false
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like '*uvicorn.exe*app.main:app*' -or
    $_.CommandLine -like '*node*vite*'
} | ForEach-Object {
    try {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
        Warn "Stopped old process PID=$($_.ProcessId)"
        $stoppedAny = $true
    } catch {}
}
if ($stoppedAny) { Start-Sleep -Seconds 1 }
Ok "Old processes cleaned"

# 7. Start backend in new window
Info "Starting backend on port 8000..."
$uvicornExe = Join-Path $VenvDir "Scripts\uvicorn.exe"
$backendScript = @"
Get-Content '$EnvFile' | ForEach-Object {
    if (`$_ -match '^\s*([^#][^=]+)=(.*)$') {
        `$k = `$Matches[1].Trim()
        `$v = `$Matches[2].Trim()
        [System.Environment]::SetEnvironmentVariable(`$k, `$v, 'Process')
        Write-Host "[BackendEnv] `$k=`$v" -ForegroundColor DarkGray
    }
}
Set-Location '$BackendDir'
`$env:PYTHONPATH = '$BackendDir'
Write-Host '[Backend] FastAPI port 8000 - Ctrl+C to stop' -ForegroundColor Cyan
& '$uvicornExe' app.main:app --reload --port 8000 --host 0.0.0.0
"@
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendScript) -WindowStyle Normal

Start-Sleep -Seconds 2

# 8. Start frontend in new window
Info "Starting frontend on port 5173..."
$frontendScript = "Set-Location '$FrontendDir'; Write-Host '[Frontend] Vite port 5173 - Ctrl+C to stop' -ForegroundColor Cyan; npm run dev"
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendScript) -WindowStyle Normal

Start-Sleep -Seconds 2

# Done
Write-Host ""
Ok "=== Services started in separate windows ==="
Write-Host ""
Write-Host "  Frontend : " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend  : " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Swagger  : " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Info "Close the popup windows to stop each service."