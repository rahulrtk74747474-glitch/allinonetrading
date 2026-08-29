$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env from .env.example. Add your rotated values, then run this command again."
    exit 1
}

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & py -m venv .venv
}

$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
& $pythonPath -m pip install -e .\services\api
& $pythonPath -m pip install -r .\services\api\requirements-broker.txt

$apiCommand = "Set-Location -LiteralPath '$repoRoot'; & '$pythonPath' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir services/api"
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $apiCommand
)

pnpm --filter @allinone/web dev
