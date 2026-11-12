$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Test-Python {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python 3.10+ is required and was not found on PATH."
    }
    $version = python -c "import sys; print(str(sys.version_info[0]) + '.' + str(sys.version_info[1]))"
    $parts = $version.Split(".")
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        throw "Python 3.10+ is required. Found $version."
    }
}

function Invoke-Poetry {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PoetryArgs)

    # Prefer the Poetry module. The poetry.exe shim can be blocked by
    # application control even when "python -m poetry" works.
    & python -m poetry @PoetryArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Poetry command failed: python -m poetry $($PoetryArgs -join ' ')"
    }
}

Test-Python

$poetryReady = $false
$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& python -m poetry --version 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $poetryReady = $true
}
$ErrorActionPreference = $previous

if (-not $poetryReady) {
    Write-Host "Poetry is not available. Installing it for the current user..."
    python -m pip install --user poetry
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install Poetry."
    }
}

Write-Host "Installing project dependencies..."
Invoke-Poetry install

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Add the sandbox API key, secret, and payment page uid before running tests."
}

Write-Host ""
Write-Host "Dependencies are installed. From this folder, run:"
Write-Host "  poetry run pytest              # all tests"
Write-Host "  poetry run pytest -m api       # API only"
Write-Host "  poetry run pytest -m ui        # UI only"
Write-Host "  poetry run pytest -m e2e       # end-to-end only"
Write-Host "  poetry run pytest --headed     # visible browser"
Write-Host ""
Write-Host "If the poetry executable cannot start, use the same commands with 'python -m poetry' instead of 'poetry'."
