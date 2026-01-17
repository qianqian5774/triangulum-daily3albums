$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  throw "Python is required to update golden fixtures."
}

$scriptPath = Join-Path $repoRoot "scripts/golden_check.py"
& $python.Path $scriptPath --update
