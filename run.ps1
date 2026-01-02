$AppName = "testium"

# 1. Set working directory to the script's location
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $PSScriptRoot

$VenvPath = Join-Path $PSScriptRoot $(Join-Path "test\tmp\" ("$AppName"+"_venv"))
$Requirements = Join-Path $PSScriptRoot "src\requirements.txt"
$PythonScript = Join-Path $PSScriptRoot $(Join-Path "src" "$AppName")

Write-Host "[1/4] Searching for Python..." -ForegroundColor Cyan

# 2. Python detection (checks for 'python' then 'py' launcher)
$PythonExe = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $PythonExe) {
    $PythonExe = Get-Command py.exe -ErrorAction SilentlyContinue
}

if (-not $PythonExe) {
    Write-Host "###########################################################" -ForegroundColor Red
    Write-Host "ERROR: Python was not detected on this system."
    Write-Host "Please install Python and check 'Add Python to PATH'."
    Write-Host "###########################################################" -ForegroundColor Red
    Pause
    exit
}

Write-Host "[+] Python found: $($PythonExe.Source)" -ForegroundColor Green

$is_venv = $false

# 3. Virtual Environment management
if (-not (Test-Path $VenvPath)) {
    Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Cyan
    & $PythonExe.Source -m venv $VenvPath
} else {
    $is_venv = $true
    Write-Host "[2/4] Virtual environment already exists." -ForegroundColor Green
}

# 4. Activation and Dependencies
Write-Host "[3/4] Activating venv and updating dependencies..." -ForegroundColor Cyan
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

# Execute the activation script
& $ActivateScript

if ($env:VIRTUAL_ENV -and (Test-Path $env:VIRTUAL_ENV)) {
    Write-Host "[+] Verified: Running inside venv ($env:VIRTUAL_ENV)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to activate virtual environment. Aborting install." -ForegroundColor Red
    pause
    exit
}

# 5. Execution
try {
    if ((Test-Path $Requirements) -and -not $is_venv) {
        Write-Host "[+] Installing requirements..." -ForegroundColor Yellow
        python -m pip install --upgrade pip --quiet
        pip install -r $Requirements
    }
    if (-not (Test-Path $PythonScript)) {
        Write-Host "ERROR: File '$PythonScript' not found in $PSScriptRoot" -ForegroundColor Red
    }
    Write-Host "[4/4] Starting $AppName..." -ForegroundColor Cyan
    Write-Host "-----------------------------------------------------------" -ForegroundColor Gray
    python $PythonScript $args
}
catch {
    Write-Host "An error occurred during execution." -ForegroundColor Red
}
finally {
    # This runs even if the script fails
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
        Write-Host "Virtual environment deactivated." -ForegroundColor Gray
    }
}

Write-Host "-----------------------------------------------------------" -ForegroundColor Gray
Write-Host "$AppName execution finished."