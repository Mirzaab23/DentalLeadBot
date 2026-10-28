$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE) { throw 'Dependency installation failed' }
& .\.venv\Scripts\python.exe -m playwright install chromium
if ($LASTEXITCODE) { throw 'Chromium installation failed' }
New-Item -ItemType Directory -Force data, logs, exports | Out-Null
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe -c "from database.models import initialize; initialize()"
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE) { throw 'Tests failed' }
Write-Host 'Setup complete.'
