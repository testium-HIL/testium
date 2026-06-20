# Build the Windows installer: PyInstaller one-folder build (fast start) + Inno Setup.
# Install ISCC without admin: winget install --id JRSoftware.InnoSetup -e

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$pyiDir = Join-Path $repoRoot 'package\pyinstaller'

# Locate PyInstaller: PATH first, then the known project venvs.
$pyi = (Get-Command pyinstaller.exe -ErrorAction SilentlyContinue).Source
if (-not $pyi) {
    foreach ($p in @(
        (Join-Path $repoRoot 'test\tmp\testium_venv\Scripts\pyinstaller.exe'),
        (Join-Path $repoRoot 'test\tmp\.venv\Scripts\pyinstaller.exe'))) {
        if (Test-Path $p) { $pyi = $p; break }
    }
}
if (-not $pyi) { throw "pyinstaller.exe not found (PATH or project venv)." }

# One-folder PyInstaller build => dist\testium\testium.exe + dist\testium\_internal\.
Write-Host "Building one-folder exe with: $pyi"
Remove-Item -Recurse -Force (Join-Path $pyiDir 'build'), (Join-Path $pyiDir 'dist') -ErrorAction SilentlyContinue
Push-Location $pyiDir
try {
    $env:TESTIUM_ONEDIR = '1'
    & $pyi 'testium.spec'
    if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed with exit code $LASTEXITCODE" }
} finally {
    Remove-Item Env:\TESTIUM_ONEDIR -ErrorAction SilentlyContinue
    Pop-Location
}

# Locate ISCC: PATH, then the usual install dirs.
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
