# Run backend (PowerShell)
param(
    [switch]$Install = $false
)

# Try to activate a virtualenv in repository root or backend
$rootVenv = Join-Path $PSScriptRoot '..\.venv\Scripts\Activate.ps1'
$localVenv = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $rootVenv) {
    . $rootVenv
} elseif (Test-Path $localVenv) {
    . $localVenv
} else {
    Write-Warning "Virtualenv activation script not found. Activate your venv manually."
}

if ($Install) {
    Write-Host "Installing dependencies from requirements.txt"
    pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
}

Write-Host "Starting backend using uvicorn..."
Push-Location $PSScriptRoot
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Pop-Location
