# Build the Testium installer from testium.iss (needs Inno Setup 6 / ISCC.exe).
# Install ISCC without admin: winget install --id JRSoftware.InnoSetup -e

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# The PyInstaller exe must exist first.
$exe = Join-Path $scriptDir '..\pyinstaller\dist\testium.exe'
if (-not (Test-Path $exe)) {
    throw "PyInstaller build not found: $exe`nRun package\pyinstaller\build first."
}

# Locate ISCC.exe: PATH, then the usual install dirs.
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $p) { $iscc = $p; break }
    }
}
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6:`n    winget install --id JRSoftware.InnoSetup -e"
}

Write-Host "Using ISCC: $iscc"
& $iscc (Join-Path $scriptDir 'testium.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host "`nInstaller built in: $(Join-Path $scriptDir 'dist')"
