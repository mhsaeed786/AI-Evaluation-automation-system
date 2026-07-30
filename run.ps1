<#
.SYNOPSIS
  Ollama Cloud evaluation system — Windows bootstrap + launcher.

.DESCRIPTION
  One-shot script that:
    1. finds a usable Python (3.11+ preferred; the builtin engine runs on 3.14),
    2. creates + activates a local .venv,
    3. installs Tier-1 deps (pip install -r requirements.txt),
    4. verifies your key/endpoint via the smoke test, and
    5. launches the benchmark runner.

  Optional Tier-2 harness deps (lm-eval / evalplus) are NOT installed by
  default — pass -InstallHarness (and prefer Python 3.11/3.12 for those).

.PARAMETER SmokeOnly
  Stop after the smoke test (do not run benchmarks). Use this to pin the
  endpoint / verify your key the first time.

.PARAMETER Quick
  Pass --quick to the runner (small per-benchmark limits; ~minutes).

.PARAMETER Models
  --models value (default: auto = discover via /v1/models).

.PARAMETER Benchmarks
  --benchmarks value (default: mmlu,gsm8k).

.PARAMETER Engine
  builtin | lm_eval | evalplus (default: builtin).

.PARAMETER InstallHarness
  Also pip install -r requirements-harness.txt (Tier 2). Use with 3.11/3.12.

.EXAMPLE
  .\run.ps1 -SmokeOnly
  .\run.ps1 -Quick
  .\run.ps1 -Quick -Benchmarks all
  .\run.ps1 -Engine lm_eval -InstallHarness
#>
[CmdletBinding()]
param(
    [switch]$SmokeOnly,
    [switch]$Quick,
    [string]$Models = "auto",
    [string]$Benchmarks = "mmlu,gsm8k",
    [string]$Engine = "builtin",
    [switch]$InstallHarness
)

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Find-Python {
    # Prefer the highest available Python 3 (3.14 > 3.13 > ... > 3.9).
    # Dependencies (datasets, pandas, flask, ...) are installed under Python 3.14
    # on this machine, so we bias toward that if present.
    $candidates = @("py -3.14", "py -3.13", "py -3.12", "py -3.11", "py -3", "python")
    $best = $null; $bestMajor = 0; $bestMinor = 0
    foreach ($c in $candidates) {
        try {
            $ver = (Invoke-Expression "$c --version") 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]; $minor = [int]$Matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 9)) {
                    if (-not $best -or $major -gt $bestMajor -or ($major -eq $bestMajor -and $minor -gt $bestMinor)) {
                        $best = $c; $bestMajor = $major; $bestMinor = $minor
                    }
                }
            }
        } catch { }
    }
    if (-not $best) {
        Write-Host "No Python 3.9+ found on PATH. Install Python from https://python.org" -ForegroundColor Red
        exit 1
    }
    Write-Host "Using: Python $bestMajor.$bestMinor ($best)" -ForegroundColor Green
    return $best
}

$py = Find-Python

# 1. venv ---------------------------------------------------------------
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    Invoke-Expression "$py -m venv .venv"
    if ($LASTEXITCODE -ne 0) { Write-Host "venv creation failed." -ForegroundColor Red; exit 1 }
}
. .\.venv\Scripts\Activate.ps1

# 2. deps ---------------------------------------------------------------
Write-Host "Installing Tier-1 dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ($InstallHarness) {
    Write-Host "Installing Tier-2 harness dependencies..." -ForegroundColor Cyan
    python -m pip install -r requirements-harness.txt
}

# 3. key check ----------------------------------------------------------
if (-not (Test-Path ".env")) {
    Write-Host ".env not found. Copying .env.example -> .env ..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}
$envContent = Get-Content ".env" -ErrorAction SilentlyContinue
$keyLine = $envContent | Where-Object { $_ -match "^OLLAMA_API_KEY=" } | Select-Object -First 1
$keySet = $keyLine -and ($keyLine -notmatch "=\s*$") -and ($keyLine -notmatch "oll_XXXX")
if (-not $keySet) {
    Write-Host "OLLAMA_API_KEY is not set in .env." -ForegroundColor Yellow
    Write-Host "Edit .env and paste your Ollama Cloud key, then re-run this script." -ForegroundColor Yellow
    Write-Host "  Get a key at https://ollama.com/cloud" -ForegroundColor DarkGray
    exit 1
}

# 4. smoke test (pins the endpoint) -------------------------------------
Write-Host "`nRunning smoke test (discovers models + confirms endpoint/key)..." -ForegroundColor Cyan
python -m src.smoke_test
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nSmoke test failed. See the message above - most often the base URL " -ForegroundColor Red
    Write-Host "or key needs correcting in .env (see README 'Pinning the endpoint')." -ForegroundColor Red
    exit 1
}

if ($SmokeOnly) {
    Write-Host "`n-SmokeOnly set: endpoint confirmed, not running benchmarks." -ForegroundColor Green
    exit 0
}

# 5. run ----------------------------------------------------------------
$runnerArgs = @("-m", "src.runner", "--models", $Models, "--benchmarks", $Benchmarks, "--engine", $Engine)
if ($Quick) { $runnerArgs += "--quick" }
Write-Host "`nLaunching runner: $runnerArgs" -ForegroundColor Cyan
python @runnerArgs

Write-Host "`nDone. Generate a comparison report with:  python -m src.report" -ForegroundColor Green
